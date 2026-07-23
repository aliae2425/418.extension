# -*- coding: utf-8 -*-
# Service de collections de feuilles (carnets) : lecture doc + comptages.
#
# Consolide la logique historiquement répartie entre :
#   - lib/data/sheets/SheetSetRepository.py       (liste des collections + comptage)
#   - lib/data/sheets/SheetParameterRepository.py  (paramètres Oui/Non des collections)
#
# Objectif : un service unique, testable hors Revit (doc=None -> listes vides,
# jamais d'exception), sans dépendance UI.

from __future__ import unicode_literals

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

try:
    from core.UserConfig import UserConfig  # type: ignore
except Exception:
    try:
        from lib.core.UserConfig import UserConfig  # type: ignore
    except Exception:
        UserConfig = None  # type: ignore


class SheetCollectionService(object):
    """Accès en lecture aux collections de feuilles (carnets) et à leurs feuilles.

    - `list_collections()` : collections (`DB.SheetCollection`) avec comptage
      des `ViewSheet` associées.
    - `list_sheets(collection_id=None)` : feuilles du document, filtrables
      par collection.
    - `list_boolean_params()` : noms de paramètres Oui/Non modifiables au
      niveau collection (pour le mappage export -> collection).
    - `read_flag(elem, param_name)` : lit un paramètre Oui/Non sur un élément.

    Tout accès Revit est protégé par `try/except`. Si `doc is None` (ou si
    l'API Revit est indisponible), les méthodes de listing renvoient des
    listes vides sans lever.
    """

    def __init__(self, doc=None, config=None, namespace='batch_export'):
        self._doc = doc
        if config is not None:
            self._cfg = config
        elif UserConfig is not None:
            try:
                self._cfg = UserConfig(namespace)
            except Exception:
                self._cfg = None
        else:
            self._cfg = None

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def list_collections(self):
        """Retourne `[{'Titre': unicode, 'Id': ElementId, 'Feuilles': int, 'Elem': DB.SheetCollection}, ...]`.

        La clé `'Elem'` (élément Revit brut) est exposée pour permettre à
        l'appelant (ex: `MainViewModel.refresh_par_jeu`) d'appeler
        `read_flag(elem, param_name)` sans aller-retour supplémentaire par Id.
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
    # Paramètres Oui/Non des collections (pour le mappage)
    # ------------------------------------------------------------------

    def is_boolean_param_definition(self, param_def):
        """Détecte un paramètre Oui/Non (compat versions)."""
        try:
            pt = getattr(param_def, 'ParameterType', None)
            if pt is not None and DB is not None and hasattr(DB, 'ParameterType'):
                try:
                    if pt == getattr(DB.ParameterType, 'YesNo', None):
                        return True
                except Exception:
                    pass
        except Exception:
            pass
        try:
            get_dt = getattr(param_def, 'GetDataType', None)
            if callable(get_dt):
                dt = get_dt()
                type_id = getattr(dt, 'TypeId', None)
                if type_id and isinstance(type_id, str):
                    lid = type_id.lower()
                    if ('yesno' in lid) or ('boolean' in lid) or ('bool' in lid):
                        return True
        except Exception:
            pass
        return False

    def _filter_param_names(self, param_names):
        """Filtre les noms selon règles fixes et exclusions utilisateur (config)."""
        try:
            excluded_list = self._cfg.get('excluded_sheet_params', []) if self._cfg is not None else []
        except Exception:
            excluded_list = []
        try:
            excluded_set = set([str(s).lower() for s in excluded_list])
        except Exception:
            excluded_set = set()
        out = []
        for pname in param_names or []:
            if not pname:
                continue
            if pname.startswith('_'):
                continue
            try:
                if pname.lower() in excluded_set:
                    continue
            except Exception:
                pass
            out.append(pname)
        return out

    def list_boolean_params(self):
        """Retourne les noms de paramètres Oui/Non modifiables des collections, triés."""
        collected = set()
        writable = {}
        if DB is None or self._doc is None:
            return []
        try:
            collections = DB.FilteredElementCollector(self._doc).OfClass(DB.SheetCollection).ToElements()
        except Exception:
            return []
        for coll in collections:
            try:
                for param in coll.Parameters:
                    try:
                        pdef = param.Definition
                        if pdef is None:
                            continue
                        if not self.is_boolean_param_definition(pdef):
                            continue
                        pname = pdef.Name
                        if pname and pname.strip():
                            pname_clean = pname.strip()
                            collected.add(pname_clean)
                            try:
                                if hasattr(param, 'IsReadOnly') and not param.IsReadOnly:
                                    writable[pname_clean] = True
                                else:
                                    writable.setdefault(pname_clean, False)
                            except Exception:
                                writable.setdefault(pname_clean, True)
                    except Exception:
                        continue
            except Exception:
                continue
        names = [n for n in collected if writable.get(n, True)]
        names = self._filter_param_names(names)
        try:
            names.sort(key=lambda s: s.lower())
        except Exception:
            names.sort()
        return names

    # ------------------------------------------------------------------
    # Lecture d'un paramètre Oui/Non
    # ------------------------------------------------------------------

    def read_flag(self, elem, param_name):
        """Lit un paramètre Oui/Non sur `elem`. `AsInteger() == 1` -> True.

        Robuste : renvoie `False` si l'élément, le paramètre ou la valeur
        sont absents/invalides (jamais d'exception).
        """
        if elem is None or not param_name:
            return False
        param = None
        try:
            lookup = getattr(elem, 'LookupParameter', None)
            if callable(lookup):
                param = lookup(param_name)
        except Exception:
            param = None
        if param is None:
            try:
                params = getattr(elem, 'Parameters', None)
                if params:
                    for p in params:
                        try:
                            d = getattr(p, 'Definition', None)
                            if d and getattr(d, 'Name', '') == param_name:
                                param = p
                                break
                        except Exception:
                            continue
            except Exception:
                param = None
        if param is None:
            return False
        try:
            return param.AsInteger() == 1
        except Exception:
            return False
