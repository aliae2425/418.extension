# -*- coding: utf-8 -*-
# Construction et insertion des DirectShape de contrôle d'échappée.
# Pour chaque paire (marche n, marche n+1) : prisme oblique de la contre-marche n
# à la contre-marche n+1, hauteur h mesurée verticalement à chaque contre-marche.
# La dernière marche utilise une extrusion verticale simple (vers palier).

PREFIXE_NOM = "418_EchappeeEscalier_"

try:
    from Autodesk.Revit.DB import (
        DirectShape, GeometryCreationUtilities, GeometryObject,
        FilteredElementCollector, ElementId, BuiltInCategory, XYZ,
        Line, CurveLoop, Curve
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
            ids = CSharpList[ElementId]()
            for e in existants:
                ids.Add(e.Id)
            doc.Delete(ids)
    except Exception:
        pass


def construire_directshape_volee(doc, faces_marches, hauteur_ft, run_id):
    """
    Construit un DirectShape groupant les volumes d'échappée d'une volée.

    faces_marches : liste de Face horizontales triées par Z croissant
    hauteur_ft    : hauteur d'échappée en pieds
    run_id        : identifiant de la StairsRun (str ou int)
    """
    if not _revit_disponible or not faces_marches:
        return None

    solides = []

    # Paires consécutives → prisme oblique
    for i in range(len(faces_marches) - 1):
        solide = _construire_prisme_paire(faces_marches[i], faces_marches[i + 1], hauteur_ft)
        if solide is not None:
            solides.append(solide)
        else:
            # Fallback si la géométrie oblique ne peut être construite
            solide = _extruder_verticalement(faces_marches[i], hauteur_ft)
            if solide is not None:
                solides.append(solide)

    # Dernière marche → extrusion verticale (vers palier)
    if faces_marches:
        solide = _extruder_verticalement(faces_marches[-1], hauteur_ft)
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


def _construire_prisme_paire(face_n, face_n1, hauteur_ft):
    """
    Prisme oblique pour la marche n : de la contre-marche n à la contre-marche n+1.
    Section en L dans le plan (direction escalier, Z), extrudée sur la largeur.
    """
    try:
        verts_n = _sommets_face(face_n)
        verts_n1 = _sommets_face(face_n1)
        if not verts_n or not verts_n1:
            return None

        z_n = verts_n[0].Z
        z_n1 = verts_n1[0].Z

        # Pas de contre-marche (marches au même niveau) → fallback
        if abs(z_n1 - z_n) < 1e-6:
            return None

        # Direction horizontale de l'escalier (de la marche n vers n+1)
        c_n = _centroide(verts_n)
        c_n1 = _centroide(verts_n1)
        dx = c_n1.X - c_n.X
        dy = c_n1.Y - c_n.Y
        d_len = (dx * dx + dy * dy) ** 0.5
        if d_len < 1e-6:
            return None
        d = XYZ(dx / d_len, dy / d_len, 0.0)

        # Direction de largeur : perpendiculaire à d dans XY
        w_vec = XYZ(-d.Y, d.X, 0.0)

        # Emprise de la marche n dans le repère local (d, w_vec)
        projs_d = [v.X * d.X + v.Y * d.Y for v in verts_n]
        projs_w = [v.X * w_vec.X + v.Y * w_vec.Y for v in verts_n]
        s_min = min(projs_d)
        s_max = max(projs_d)
        w_min = min(projs_w)
        w_max = max(projs_w)
        stair_width = abs(w_max - w_min)
        if stair_width < 1e-6 or abs(s_max - s_min) < 1e-6:
            return None

        # Convertit coord locale (s, z) → XYZ global au côté w_min
        def pt(s, z):
            return XYZ(
                d.X * s + w_vec.X * w_min,
                d.Y * s + w_vec.Y * w_min,
                z
            )

        # Profil en L : 5 sommets
        A = pt(s_min, z_n)
        B = pt(s_max, z_n)
        C = pt(s_max, z_n1)
        D = pt(s_max, z_n1 + hauteur_ft)
        E = pt(s_min, z_n + hauteur_ft)

        # CurveLoop du profil en L
        curves = CSharpList[Curve]()
        curves.Add(Line.CreateBound(A, B))
        curves.Add(Line.CreateBound(B, C))
        curves.Add(Line.CreateBound(C, D))
        curves.Add(Line.CreateBound(D, E))
        curves.Add(Line.CreateBound(E, A))
        loop = CurveLoop.Create(curves)

        loops_cs = CSharpList[CurveLoop]()
        loops_cs.Add(loop)

        return GeometryCreationUtilities.CreateExtrusionGeometry(
            loops_cs, w_vec, stair_width
        )
    except Exception:
        return None


def _extruder_verticalement(face, hauteur_ft):
    """Extrusion verticale simple (dernière marche d'une volée ou fallback)."""
    try:
        loops = face.GetEdgesAsCurveLoops()
        if not loops:
            return None
        return GeometryCreationUtilities.CreateExtrusionGeometry(
            loops, XYZ(0.0, 0.0, 1.0), hauteur_ft
        )
    except Exception:
        return None


def _sommets_face(face):
    """Retourne les sommets du contour extérieur d'une face."""
    try:
        outer = list(face.GetEdgesAsCurveLoops())[0]
        return [curve.GetEndPoint(0) for curve in outer]
    except Exception:
        return []


def _centroide(vertices):
    """Retourne le centroïde d'une liste de sommets XYZ."""
    if not vertices:
        return XYZ(0.0, 0.0, 0.0)
    n = float(len(vertices))
    return XYZ(
        sum(v.X for v in vertices) / n,
        sum(v.Y for v in vertices) / n,
        sum(v.Z for v in vertices) / n
    )
