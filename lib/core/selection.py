# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re as _re

try:
    from Autodesk.Revit.DB import (ViewSheet, View, ViewType, Material,
                                   ViewSheetSet, Viewport, BuiltInCategory,
                                   FilteredElementCollector)
except Exception:
    ViewSheet = None
    View = None
    ViewType = None
    Material = None
    ViewSheetSet = None
    Viewport = None
    BuiltInCategory = None
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


def cartouches(doc):
    """Les TYPES de cartouche chargés dans le projet, triés par nom.

    Ce sont des `FamilySymbol` : c'est leur `Id` que `ViewSheet.Create`
    attend, pas une instance.
    """
    if FilteredElementCollector is None or BuiltInCategory is None:
        return []
    types = list(FilteredElementCollector(doc)
                 .OfCategory(BuiltInCategory.OST_TitleBlocks)
                 .WhereElementIsElementType()
                 .ToElements())
    return sorted(types, key=lambda t: cle_naturelle(nom_de_type(t)))


def nom_de_type(symbole):
    """« Famille : Type », le libellé qu'un architecte reconnaît.

    `FamilySymbol.Name` ne rend que le type ; deux familles de cartouche
    peuvent avoir un type « A1 », et la liste deviendrait ambiguë.
    """
    try:
        return u'{0} : {1}'.format(symbole.FamilyName, symbole.Name)
    except Exception:
        try:
            return symbole.Name
        except Exception:
            return u''


def vues_par_type(doc, types):
    """Les vues duplicables dont le `ViewType` porte un de ces NOMS.

    Les noms (« Section », « Elevation », « ThreeD ») plutôt que les membres
    de l'énumération : l'appelant reste importable hors Revit, où
    `DB.ViewType` n'existe pas.
    """
    if ViewType is None or not types:
        return []
    voulus = set()
    for nom in types:
        membre = getattr(ViewType, nom, None)
        if membre is not None:
            voulus.add(membre)
    if not voulus:
        return []
    return [v for v in all_views(doc) if getattr(v, 'ViewType', None) in voulus]


def vues_placees(doc):
    """Les `ElementId` des vues déjà posées sur une feuille.

    Lu sur les `Viewport` du document : c'est le fait, pas une déduction.
    Les nomenclatures font exception (elles passent par
    `ScheduleSheetInstance`), mais aucune des vues qui nous intéressent ici
    n'en est une.
    """
    if FilteredElementCollector is None or Viewport is None:
        return set()
    return set(vp.ViewId for vp in FilteredElementCollector(doc)
               .OfClass(Viewport).ToElements())


def vues_sans_feuille(doc, vues):
    """Celles qui n'ont pas encore de feuille.

    Revit refuse de poser deux fois la même vue : ce sont donc exactement
    les vues auxquelles il manque une feuille — « le besoin » du projet.
    """
    placees = vues_placees(doc)
    return [v for v in vues if v.Id not in placees]


def jeux_de_feuilles(doc):
    """Tous les `ViewSheetSet` du document, triés par nom en ordre naturel.

    Le « jeu de feuilles » est du vocabulaire d'agence autant que de Revit :
    c'est l'unité d'export de BatchExport, et celle à laquelle PC rattache
    une pièce de dossier d'urbanisme. Deux outils le lisent, il vit donc
    ici — pas dans l'un d'eux.
    """
    if FilteredElementCollector is None or ViewSheetSet is None:
        return []
    jeux = list(FilteredElementCollector(doc)
                .OfClass(ViewSheetSet)
                .ToElements())
    return sorted(jeux, key=lambda j: cle_naturelle(j.Name))
