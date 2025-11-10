# -*- coding: utf-8 -*-
"""Fonctions utilitaires liées aux feuilles et jeux de feuilles Revit.

Thématiques:
- Détection de type Oui/Non (booléen) pour paramètres -> is_boolean_param_definition
- Filtrage de noms de paramètres selon règles/config -> filter_param_names
- Collecte des paramètres pertinents au niveau des collections de feuilles -> collect_sheet_parameter_names
- Agrégation des jeux de feuilles et comptage -> get_sheet_sets

Contrat: ne modifie pas la logique existante; uniquement réorganisation et noms explicites.
"""

try:
    from Autodesk.Revit import DB
except Exception:
    DB = None  # type: ignore


def is_boolean_param_definition(param_def):
    """Vérifie si "param_def" décrit un paramètre Oui/Non (booléen).

    Compat API:
      - Revit <=2021: Definition.ParameterType == DB.ParameterType.YesNo
      - Revit >=2022: Definition.GetDataType().TypeId contient 'yesno'/'boolean'/'bool'
    """
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


def filter_param_names(param_names, config_store):
    """Filtre les noms de paramètres selon règles simples et configuration.

    Règles:
    - retirer les vides
    - retirer ceux qui commencent par '_'
    - retirer ceux présents dans la liste "excluded_sheet_params" de la config
    """
    try:
        excluded_list = config_store.get_list('excluded_sheet_params', default=[])
    except Exception:
        excluded_list = []
    excluded_set = set([s.lower() for s in excluded_list])
    filtered_names = []
    for pname in param_names or []:
        if not pname:
            continue
        if pname.startswith('_'):
            continue
        if pname.lower() in excluded_set:
            continue
        filtered_names.append(pname)
    return filtered_names


def collect_sheet_parameter_names(doc, config_store):
    """Retourne liste triée de noms de paramètres Oui/Non modifiables (au niveau SheetCollection).

    Logique d'origine conservée; seulement variables clarifiées.
    """
    collected_names = set()
    writable_flags = {}
    collections = None
    try:
        collections = DB.FilteredElementCollector(doc).OfClass(DB.SheetCollection).ToElements()
    except Exception:
        collections = None
    for coll in collections:
        try:
            for param in coll.Parameters:
                try:
                    pdef = param.Definition
                    if pdef is None:
                        continue
                    if not is_boolean_param_definition(pdef):
                        continue
                    pname = pdef.Name
                    if pname and pname.strip():
                        pname_clean = pname.strip()
                        collected_names.add(pname_clean)
                        try:
                            if hasattr(param, 'IsReadOnly') and not param.IsReadOnly:
                                writable_flags[pname_clean] = True
                            else:
                                writable_flags.setdefault(pname_clean, False)
                        except Exception:
                            writable_flags.setdefault(pname_clean, True)
                except Exception:
                    continue
        except Exception:
            continue
    filtered_names = [n for n in collected_names if writable_flags.get(n, True)]
    filtered_names = filter_param_names(filtered_names, config_store)
    return sorted(filtered_names, key=lambda s: s.lower())


def get_sheet_sets(doc):
    """Retourne la liste des jeux de feuilles avec nombre de feuilles par jeu.

    Structure: [{'Titre': <str>, 'Feuilles': <int>}]
    Logique intacte, variables rendues explicites.
    """
    result_sets = []
    if DB is None:
        return [{'Titre': 'Aucune donnée', 'Feuilles': 0}]
    collections = DB.FilteredElementCollector(doc).OfClass(DB.SheetCollection).ToElements()
    all_sheets = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).ToElements()
    for coll in collections:
        coll_title = coll.Name
        count_in_coll = 0
        for vs in all_sheets:
            try:
                if vs.SheetCollectionId == coll.Id:
                    count_in_coll += 1
            except Exception:
                continue
        # print(coll_title, count_in_coll)
        result_sets.append({'Titre': coll_title, 'Feuilles': count_in_coll})
    return result_sets
