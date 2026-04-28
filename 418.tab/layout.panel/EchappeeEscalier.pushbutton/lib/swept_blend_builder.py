# -*- coding: utf-8 -*-
# Construction et insertion des DirectShape de contrôle d'échappée.
# Pour chaque face de marche, on extrude verticalement le contour de la face
# vers le haut d'une hauteur h (en pieds). Tous les solides d'une volée sont
# regroupés dans un seul DirectShape nommé "418_EchappeeEscalier_<run_id>".

PREFIXE_NOM = "418_EchappeeEscalier_"

try:
    from Autodesk.Revit.DB import (
        DirectShape, GeometryCreationUtilities, GeometryObject,
        FilteredElementCollector, ElementId, BuiltInCategory, XYZ
    )
    from System.Collections.Generic import List as CSharpList
    _revit_disponible = True
except Exception:
    _revit_disponible = False


def supprimer_formes_existantes(doc):
    """Supprime les DirectShape créés lors d'un lancement précédent."""
    if not _revit_disponible:
        return
    try:
        existants = [
            e for e in FilteredElementCollector(doc)
            .OfClass(DirectShape)
            .ToElements()
            if e.Name.startswith(PREFIXE_NOM)
        ]
        if existants:
            doc.Delete([e.Id for e in existants])
    except Exception:
        pass


def construire_directshape_volee(doc, faces_marches, hauteur_ft, run_id):
    """
    Construit un DirectShape groupant les volumes d'échappée de toutes les
    marches d'une volée.

    faces_marches : liste de Face triées par Z croissant
    hauteur_ft    : hauteur d'échappée en pieds
    run_id        : identifiant de la StairsRun (str ou int)
    Retourne le DirectShape créé, ou None en cas d'échec.
    """
    if not _revit_disponible or not faces_marches:
        return None

    solides = []
    for face in faces_marches:
        solide = _extruder_face_marche(face, hauteur_ft)
        if solide is not None:
            solides.append(solide)

    if not solides:
        return None

    try:
        cat_id = ElementId(BuiltInCategory.OST_GenericModel)
        shape = DirectShape.CreateElement(doc, cat_id)
        geom_list = CSharpList[GeometryObject]()
        for s in solides:
            geom_list.Add(s)
        shape.SetShape(geom_list)
        shape.Name = PREFIXE_NOM + str(run_id)
        return shape
    except Exception:
        return None


def _extruder_face_marche(face, hauteur_ft):
    """Extrude une face de marche vers le haut pour créer le volume d'échappée."""
    try:
        loops = list(face.GetEdgesAsCurveLoops())
        if not loops:
            return None
        direction = XYZ(0.0, 0.0, 1.0)
        return GeometryCreationUtilities.CreateExtrusionGeometry(
            loops, direction, hauteur_ft
        )
    except Exception:
        return None
