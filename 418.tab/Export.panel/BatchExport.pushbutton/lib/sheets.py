# -*- coding: utf-8 -*-
"""Fonctions utilitaires liées aux feuilles et jeux de feuilles Revit.

Inclut:
- collect_sheet_parameter_names(doc, config_store): noms de paramètres Oui/Non modifiables
- get_sheet_sets(doc): liste de jeux de feuilles {Titre, Feuilles}
- is_boolean_param_definition(defn): détection robuste du type Oui/Non
- filter_param_names(names, config_store): filtre noms (vides, '_'*, black-list)
"""

try:
    from Autodesk.Revit import DB
except Exception:
    DB = None  # type: ignore


def is_boolean_param_definition(defn):
    """Retourne True si la définition de paramètre correspond à un Oui/Non.

    Compat API:
      - Revit <=2021: Definition.ParameterType == DB.ParameterType.YesNo
      - Revit >=2022: Definition.GetDataType().TypeId contient 'yesno'/'boolean'/'bool'
    """
    try:
        pt = getattr(defn, 'ParameterType', None)
        if pt is not None and DB is not None and hasattr(DB, 'ParameterType'):
            try:
                if pt == getattr(DB.ParameterType, 'YesNo', None):
                    return True
            except Exception:
                pass
    except Exception:
        pass
    try:
        get_dt = getattr(defn, 'GetDataType', None)
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


def filter_param_names(names, config_store):
    """Applique des filtres simples et liste d'exclusion via config_store.
    - retire vides
    - retire ceux qui commencent par '_'
    - retire ceux présents dans 'excluded_sheet_params'
    """
    try:
        excluded = config_store.get_list('excluded_sheet_params', default=[])
    except Exception:
        excluded = []
    excl = set([s.lower() for s in excluded])
    out = []
    for n in names or []:
        if not n:
            continue
        if n.startswith('_'):
            continue
        if n.lower() in excl:
            continue
        out.append(n)
    return out


def collect_sheet_parameter_names(doc, config_store):
    """Retourne liste triée de noms de paramètres Oui/Non modifiables des feuilles.

    NOTE: Par préférence projet, tente DB.SheetCollection si disponible.
    """
    if DB is None:
        return []
    names = set()
    any_writable = {}
    # Préférence: SheetCollection si dispo
    sheets = None
    try:
        sheet_collection_type = getattr(DB, 'SheetCollection', None)
        if sheet_collection_type is not None:
            sheets = DB.FilteredElementCollector(doc).OfClass(sheet_collection_type)
    except Exception:
        sheets = None
    if sheets is None:
        # Fallback vers ViewSheet si besoin (peut être désactivé selon préférences)
        try:
            sheets = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet)
        except Exception:
            return []
    for sheet in sheets:
        try:
            for p in sheet.Parameters:
                try:
                    d = p.Definition
                    if d is None:
                        continue
                    if not is_boolean_param_definition(d):
                        continue
                    name = d.Name
                    if name and name.strip():
                        n = name.strip()
                        names.add(n)
                        try:
                            if hasattr(p, 'IsReadOnly') and not p.IsReadOnly:
                                any_writable[n] = True
                            else:
                                any_writable.setdefault(n, False)
                        except Exception:
                            any_writable.setdefault(n, True)
                except Exception:
                    continue
        except Exception:
            continue
    filtered = [n for n in names if any_writable.get(n, True)]
    filtered = filter_param_names(filtered, config_store)
    return sorted(filtered, key=lambda s: s.lower())


def get_sheet_sets(doc):
    """Retourne liste de dicts {Titre, Feuilles} représentant les jeux de feuilles.

    Tente DB.SheetCollection, sinon fallback à une ligne "Toutes les feuilles".
    """
    out = []
    if DB is None:
        return [{'Titre': 'Aucune donnée', 'Feuilles': 0}]
    try:
        sheet_collection_type = getattr(DB, 'SheetCollection', None)
        if sheet_collection_type is not None:
            try:
                coll = DB.FilteredElementCollector(doc).OfClass(sheet_collection_type)
                for sc in coll:
                    try:
                        titre = None
                        for attr in ['Title', 'Name']:
                            if hasattr(sc, attr):
                                v = getattr(sc, attr)
                                if v:
                                    titre = v
                                    break
                        if not titre:
                            titre = '(Sans titre)'
                        count = None
                        for attr in ['Count', 'SheetCount']:
                            if hasattr(sc, attr):
                                try:
                                    cv = getattr(sc, attr)
                                    if isinstance(cv, int):
                                        count = cv
                                        break
                                except Exception:
                                    pass
                        if count is None and hasattr(sc, 'Sheets'):
                            try:
                                sheets_prop = getattr(sc, 'Sheets')
                                count = len(list(sheets_prop))
                            except Exception:
                                count = 0
                        if count is None:
                            count = 0
                        out.append({'Titre': titre, 'Feuilles': count})
                    except Exception:
                        continue
            except Exception:
                pass
    except Exception:
        pass
    if not out:
        try:
            vsheets = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet)
            count = 0
            for _ in vsheets:
                count += 1
            out.append({'Titre': 'Toutes les feuilles', 'Feuilles': count})
        except Exception:
            out.append({'Titre': 'Aucune donnée', 'Feuilles': 0})
    return out
