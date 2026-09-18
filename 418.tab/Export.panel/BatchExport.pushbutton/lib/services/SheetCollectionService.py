# -*- coding: utf-8 -*-
# Service de collections de feuilles (carnets) : lecture doc + comptages.
#
# Objectif : un service unique, testable hors Revit (doc=None -> listes vides,
# jamais d'exception), sans dépendance UI ni configuration.

from __future__ import unicode_literals

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore


class SheetCollectionService(object):
    """Accès en LECTURE SEULE aux collections de feuilles (carnets), aux
    feuilles et aux sets d'impression du document.

    - `list_collections()` : collections (`DB.SheetCollection`) avec comptage
      des `ViewSheet` associées.
    - `list_sheets(collection_id=None)` : feuilles du document, filtrables
      par collection.
    - `list_all_sheets()` : toutes les feuilles (mode manuel), placeholders
      exclus, triées par numéro.
    - `list_view_sheet_sets()` : sets d'impression (`DB.ViewSheetSet`).

    Tout accès Revit est protégé par `try/except`. Si `doc is None` (ou si
    l'API Revit est indisponible), les méthodes de listing renvoient des
    listes vides sans lever.
    """

    def __init__(self, doc=None):
        self._doc = doc

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def list_collections(self):
        """Retourne `[{'Titre': unicode, 'Id': ElementId, 'Feuilles': int, 'Elem': DB.SheetCollection}, ...]`.

        La clé `'Elem'` (élément Revit brut) est exposée pour permettre à
        l'appelant (ex: `MainViewModel.refresh_par_jeu`) de résoudre un motif
        de nommage sans aller-retour supplémentaire par Id.
        """
        result = []
        if DB is None or self._doc is None:
            return result
        try:
            collections = DB.FilteredElementCollector(self._doc).OfClass(DB.SheetCollection).ToElements()
            all_sheets = DB.FilteredElementCollector(self._doc).OfClass(DB.ViewSheet).ToElements()
        except Exception:
            return result
        for coll in collections:
            try:
                titre = coll.Name
            except Exception:
                titre = 'Collection'
            try:
                coll_id = coll.Id
            except Exception:
                coll_id = None
            count = 0
            for vs in all_sheets:
                try:
                    if vs.SheetCollectionId == coll_id:
                        count += 1
                except Exception:
                    continue
            result.append({'Titre': titre, 'Id': coll_id, 'Feuilles': count, 'Elem': coll})
        return result

    # ------------------------------------------------------------------
    # Feuilles
    # ------------------------------------------------------------------

    def list_sheets(self, collection_id=None):
        """Retourne `[{'Numero': unicode, 'Nom': unicode, 'CollectionId': ElementId, 'Elem': DB.ViewSheet}, ...]`.

        Si `collection_id` est `None`, retourne toutes les feuilles du document.

        La clé `'Elem'` (élément Revit brut) est exposée pour permettre à
        l'appelant de résoudre un nom projeté via `NamingService.resolve_for_element`
        sans aller-retour supplémentaire par Id.
        """
        result = []
        if DB is None or self._doc is None:
            return result
        try:
            sheets = DB.FilteredElementCollector(self._doc).OfClass(DB.ViewSheet).ToElements()
        except Exception:
            return result
        for vs in sheets:
            try:
                vs_coll_id = getattr(vs, 'SheetCollectionId', None)
            except Exception:
                vs_coll_id = None
            if collection_id is not None:
                try:
                    if vs_coll_id != collection_id:
                        continue
                except Exception:
                    continue
            try:
                numero = vs.SheetNumber
            except Exception:
                numero = ''
            try:
                nom = vs.Name
            except Exception:
                nom = ''
            result.append({'Numero': numero, 'Nom': nom, 'CollectionId': vs_coll_id, 'Elem': vs})
        return result

    # ------------------------------------------------------------------
    # Mode « feuille par feuille » (manuel) : toutes les feuilles + sets d'impression
    # ------------------------------------------------------------------

    def list_all_sheets(self):
        """Retourne `[{'Numero': unicode, 'Nom': unicode, 'CollectionId': ElementId, 'Elem': DB.ViewSheet}, ...]`
        pour TOUTES les `ViewSheet` du document (mode manuel), triées par
        `SheetNumber`.

        Exclut les feuilles placeholder (`IsPlaceholder`), qui n'ont pas de
        contenu exportable. `doc=None` (ou API Revit indisponible) -> `[]`,
        jamais d'exception.
        """
        result = []
        if DB is None or self._doc is None:
            return result
        try:
            sheets = DB.FilteredElementCollector(self._doc).OfClass(DB.ViewSheet).ToElements()
        except Exception:
            return result
        for vs in sheets:
            try:
                if getattr(vs, 'IsPlaceholder', False):
                    continue
            except Exception:
                pass
            try:
                vs_coll_id = getattr(vs, 'SheetCollectionId', None)
            except Exception:
                vs_coll_id = None
            try:
                numero = vs.SheetNumber
            except Exception:
                numero = ''
            try:
                nom = vs.Name
            except Exception:
                nom = ''
            result.append({'Numero': numero, 'Nom': nom, 'CollectionId': vs_coll_id, 'Elem': vs})
        try:
            result.sort(key=lambda s: s.get('Numero') or u'')
        except Exception:
            pass
        return result

    def list_view_sheet_sets(self):
        """Retourne `[{'Nom': unicode, 'SheetIds': set(unicode)}, ...]` pour
        les `DB.ViewSheetSet` (sets d'impression) du document.

        IMPORTANT : malgré son nom (conservé pour rester conforme au
        contrat demandé), `'SheetIds'` contient des **numéros de feuille**
        (`ViewSheet.SheetNumber`), pas des `ElementId`. Le `SheetNumber` est
        garanti unique dans un document Revit, ce qui en fait une clé de
        correspondance fiable et simple à comparer (chaînes), y compris hors
        Revit dans les tests (pas de dépendance à la représentation interne
        d'un `ElementId`).

        `doc=None` (ou API Revit indisponible) -> `[]`, jamais d'exception.
        """
        result = []
        if DB is None or self._doc is None:
            return result
        try:
            sheet_sets = DB.FilteredElementCollector(self._doc).OfClass(DB.ViewSheetSet).ToElements()
        except Exception:
            return result
        for vss in sheet_sets:
            try:
                nom = vss.Name
            except Exception:
                nom = ''
            numeros = set()
            try:
                views = vss.Views
                for v in views:
                    try:
                        if DB is not None and isinstance(v, DB.ViewSheet):
                            numeros.add(v.SheetNumber)
                    except Exception:
                        continue
            except Exception:
                pass
            result.append({'Nom': nom, 'SheetIds': numeros})
        return result
