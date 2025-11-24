# -*- coding: utf-8 -*-
# Accès aux noms de paramètres Oui/Non pour feuilles/collections

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

class SheetParameterRepository(object):
    def __init__(self, config_store=None):
        self._config = config_store

    def _get_cfg(self):
        if self._config is not None:
            return self._config
        try:
            from ...core.UserConfig import UserConfig
            return UserConfig('batch_export')
        except Exception:
            return None

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

    def filter_param_names(self, param_names):
        """Filtre les noms selon règles et configuration utilisateur."""
        cfg = self._get_cfg()
        try:
            excluded_list = cfg.get('excluded_sheet_params', []) if cfg is not None else []
        except Exception:
            excluded_list = []
        excluded_set = set([str(s).lower() for s in excluded_list])
        out = []
        for pname in param_names or []:
            if not pname:
                continue
            if pname.startswith('_'):
                continue
            if pname.lower() in excluded_set:
                continue
            out.append(pname)
        return out

    # Liste de paramètres Oui/Non modifiables au niveau collection de feuilles
    def collect_for_collections(self, doc, only_boolean=True):
        collected = set()
        writable = {}
        collections = None
        try:
            collections = DB.FilteredElementCollector(doc).OfClass(DB.SheetCollection).ToElements()
        except Exception:
            collections = None
        if collections is None:
            return []
        for coll in collections:
            try:
                for param in coll.Parameters:
                    try:
                        pdef = param.Definition
                        if pdef is None:
                            continue
                        if only_boolean and not self.is_boolean_param_definition(pdef):
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
        names = self.filter_param_names(names)
        try:
            names.sort(key=lambda s: s.lower())
        except Exception:
            names.sort()
        return names

    # Paramètres projet (ProjectInformation)
    def collect_project_params(self, doc):
        out = []
        try:
            proj_info = DB.FilteredElementCollector(doc).OfClass(DB.ProjectInfo).ToElements()
            # Prendre le premier (doc.ProjectInformation aussi possible)
            if proj_info and len(proj_info) > 0:
                for param in proj_info[0].GetOrderedParameters():
                    try:
                        out.append(param.Definition.Name)
                    except Exception:
                        continue
        except Exception:
            out = []
        try:
            out.sort(key=lambda s: s.lower())
        except Exception:
            out.sort()
        return out

    # Paramètres instance de feuille (ViewSheet)
    def collect_sheet_instance_params(self, doc):
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
        out = self.filter_param_names(out)
        try:
            out.sort(key=lambda s: s.lower())
        except Exception:
            out.sort()
        return out
