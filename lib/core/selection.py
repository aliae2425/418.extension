# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re as _re

try:
    from Autodesk.Revit.DB import (ViewSheet, View, ViewType, Material,
                                   FilteredElementCollector)
except Exception:
    ViewSheet = None
    View = None
    ViewType = None
    Material = None
    FilteredElementCollector = None


def cle_naturelle(texte):
    """Clé de tri « naturelle » : les blocs de chiffres comparés en NOMBRE.

    A9 passe donc avant A10, là où un tri de chaînes place A10 avant A9.
    C'est l'ordre attendu sur des numéros de feuille et des noms de vue."""
    return [(0, int(p), u'') if p.isdigit() else (1, 0, p.lower())
            for p in _re.split(r'(\d+)', texte or u'')]


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
    """Toutes les vues duplicables du document (hors feuilles et templates),
    triées par nom en ordre naturel croissant."""
    if FilteredElementCollector is None or View is None:
        return []
    vues = [v for v in FilteredElementCollector(doc).OfClass(View).ToElements()
            if _is_duplicable_view(v)]
    return sorted(vues, key=lambda v: cle_naturelle(v.Name))


def all_materials(doc):
    """Tous les `Material` du document, triés par nom."""
    if FilteredElementCollector is None or Material is None:
        return []
    materiaux = list(FilteredElementCollector(doc)
                     .OfClass(Material)
                     .WhereElementIsNotElementType()
                     .ToElements())
    return sorted(materiaux, key=lambda m: m.Name)


def all_sheets(doc):
    """Toutes les `ViewSheet` du document, triées par `SheetNumber` en ordre
    naturel croissant."""
    if FilteredElementCollector is None or ViewSheet is None:
        return []
    sheets = list(FilteredElementCollector(doc)
                  .OfClass(ViewSheet)
                  .WhereElementIsNotElementType()
                  .ToElements())
    return sorted(sheets, key=lambda s: cle_naturelle(s.SheetNumber))
