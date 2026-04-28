# -*- coding: utf-8 -*-
# Extraction des faces horizontales (marches) depuis la géométrie d'un StairsRun.
try:
    from Autodesk.Revit.DB import Options, PlanarFace, UV, Solid
except Exception:
    Options = None
    PlanarFace = None
    UV = None
    Solid = None

TOLERANCE_Z = 0.01  # La normale Z doit être >= 1 - TOLERANCE_Z pour une face horizontale


def extraire_faces_marches(stairs_run):
    """
    Retourne la liste des faces horizontales (marches) d'une volée,
    triées par élévation Z croissante.
    """
    if Options is None:
        return []
    opts = Options()
    opts.ComputeReferences = False
    opts.IncludeNonVisibleObjects = False

    faces = []
    try:
        geom = stairs_run.get_Geometry(opts)
        for geom_obj in geom:
            if Solid is None or not isinstance(geom_obj, Solid):
                continue
            try:
                for face in geom_obj.Faces:
                    if _est_horizontale(face):
                        faces.append(face)
            except Exception:
                continue
    except Exception:
        return []

    faces.sort(key=_z_moyen)
    return faces


def _est_horizontale(face):
    """Vérifie si une face est horizontale (normale pointant vers le haut)."""
    try:
        if isinstance(face, PlanarFace):
            return face.FaceNormal.Z >= (1.0 - TOLERANCE_Z)
        # Faces non planaires (escaliers courbes)
        uv_centre = UV(0.5, 0.5)
        return face.ComputeNormal(uv_centre).Z >= (1.0 - TOLERANCE_Z)
    except Exception:
        return False


def _z_moyen(face):
    """Retourne l'élévation Z moyenne d'une face (pour le tri)."""
    try:
        bb = face.GetBoundingBox()
        return (bb.Min.Z + bb.Max.Z) / 2.0
    except Exception:
        return 0.0
