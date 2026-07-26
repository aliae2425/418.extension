# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from Autodesk.Revit.DB import ViewSheet, View, ViewType, FilteredElementCollector
except Exception:
    ViewSheet = None
    View = None
    ViewType = None
    FilteredElementCollector = None


def _selected_elements(uidoc):
    """Éléments actuellement sélectionnés dans l'UI Revit (liste brute)."""
    doc = uidoc.Document
    return [doc.GetElement(eid) for eid in uidoc.Selection.GetElementIds()]


def get_selected_sheets(uidoc):
    """Feuilles (`ViewSheet`) actuellement sélectionnées. Liste possiblement
    vide. Aucune UI : le cas vide est traité par la page Sélection."""
    if ViewSheet is None:
        return []
    return [e for e in _selected_elements(uidoc) if isinstance(e, ViewSheet)]


def get_selected_views(uidoc):
    """Vues sélectionnées, hors feuilles et hors templates de vue."""
    if View is None:
        return []
    out = []
    for e in _selected_elements(uidoc):
        if isinstance(e, View) and not isinstance(e, ViewSheet):
            if not getattr(e, 'IsTemplate', False):
                out.append(e)
    return out


def _is_duplicable_view(view):
    """Vrai si la vue peut être dupliquée (hors feuilles et templates)."""
    if View is None:
        return False
    if not isinstance(view, View):
        return False
    if ViewSheet is not None and isinstance(view, ViewSheet):
        return False
    return not getattr(view, 'IsTemplate', False)


def all_views(doc):
    """Toutes les vues duplicables du document (hors feuilles et templates), triées par nom."""
    if FilteredElementCollector is None or View is None:
        return []
    vues = [v for v in FilteredElementCollector(doc).OfClass(View).ToElements()
            if _is_duplicable_view(v)]
    return sorted(vues, key=lambda v: v.Name)


def all_sheets(doc):
    """Toutes les `ViewSheet` du document, triées par `SheetNumber`."""
    if FilteredElementCollector is None or ViewSheet is None:
        return []
    sheets = list(FilteredElementCollector(doc)
                  .OfClass(ViewSheet)
                  .WhereElementIsNotElementType()
                  .ToElements())
    return sorted(sheets, key=lambda s: s.SheetNumber)
