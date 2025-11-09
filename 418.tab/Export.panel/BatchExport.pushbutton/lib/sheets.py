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
    # Retourne liste triée de noms de paramètres Oui/Non modifiables des feuilles.
    names = set()
    any_writable = {}
    # Préférence: SheetCollection si dispo
    Collections = None
    try:
        Collections = DB.FilteredElementCollector(doc).OfClass(DB.SheetCollection).ToElements()
    except Exception:
        Collections = None
    for sheet in Collections:
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
    out = []
    if DB is None:
        return [{'Titre': 'Aucune donnée', 'Feuilles': 0}]
    sheet_collection = DB.FilteredElementCollector(doc).OfClass(DB.SheetCollection).ToElements()
    sheets = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).ToElements()
    # print(dir(sheet_collection[0].ID), len(sheet_collection))
    for collection_item in sheet_collection:
            titre = collection_item.Name
            sheet_count = 0
            for s in sheets:
                try:
                    parent_id = s.get_Parameter(DB.BuiltInParameter.SHEET_COLLECTION_ID).AsElementId()
                    if parent_id == collection_item.Id:
                        sheet_count += 1
                except Exception:
                    continue
            print(titre, sheet_count)
            out.append({'Titre': titre, 'Feuilles': sheet_count})
    return out
