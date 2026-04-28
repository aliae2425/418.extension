# -*- coding: utf-8 -*-
# Collecte des éléments Stairs depuis le document ou la sélection active.
try:
    from Autodesk.Revit.DB import FilteredElementCollector
    from Autodesk.Revit.DB.Architecture import Stairs
except Exception:
    FilteredElementCollector = None
    Stairs = None


def collect_stairs(doc):
    """Retourne tous les Stairs du document."""
    if FilteredElementCollector is None:
        return []
    return list(
        FilteredElementCollector(doc)
        .OfClass(Stairs)
        .ToElements()
    )


def collect_stairs_from_selection(uidoc, doc):
    """Retourne les Stairs parmi les éléments sélectionnés."""
    if Stairs is None:
        return []
    result = []
    for eid in uidoc.Selection.GetElementIds():
        elem = doc.GetElement(eid)
        if elem is not None and isinstance(elem, Stairs):
            result.append(elem)
    return result
