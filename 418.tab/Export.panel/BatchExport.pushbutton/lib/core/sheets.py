# -*- coding: utf-8 -*-
"""Core utilities for Revit sheets and sheet collections."""

try:
    from Autodesk.Revit import DB
except Exception:
    DB = None  # type: ignore


def is_boolean_param_definition(param_def):
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
        result_sets.append({'Titre': coll_title, 'Feuilles': count_in_coll})
    return result_sets


def picker_collect_project_parameter_names(doc, config_store):
    out = []
    proj_info= DB.FilteredElementCollector(doc).OfClass(DB.ProjectInfo).ToElements()
    for param in proj_info[0].GetOrderedParameters():
        out.append(param.Definition.Name)
    try:
        out.sort(key=lambda s: s.lower())
    except Exception:
        out.sort()
    return out


def picker_collect_sheet_instance_parameter_names(doc, config_store):
    names = set()
    writable = {}
    try:
        sheets = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).ToElements()
    except Exception:
        sheets = []
    for vs in sheets:
        try:
            for param in vs.Parameters:
                try:
                    pdef = param.Definition
                    pname = pdef.Name
                    if pname and pname.strip():
                        pname_clean = pname.strip()
                        names.add(pname_clean)
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
    out = [n for n in names if writable.get(n, True)]
    out = filter_param_names(out, config_store)
    try:
        out.sort(key=lambda s: s.lower())
    except Exception:
        out.sort()
    return out


def picker_collect_sheet_parameter_names(doc, config_store):
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


__all__ = [
    'is_boolean_param_definition',
    'filter_param_names',
    'collect_sheet_parameter_names',
    'get_sheet_sets',
    'picker_collect_project_parameter_names',
    'picker_collect_sheet_instance_parameter_names',
    'picker_collect_sheet_parameter_names',
]
