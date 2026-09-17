# -*- coding: utf-8 -*-
# Accès aux noms de paramètres des feuilles et du projet, pour alimenter les
# jetons {param:NOM} / {param_projet:NOM} de l'éditeur de nommage.

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
            try:
                from core.UserConfig import UserConfig
            except Exception:
                from lib.core.UserConfig import UserConfig
            return UserConfig('batch_export')
        except Exception:
            return None

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

    # Paramètres projet (ProjectInformation)
    def collect_project_params(self, doc):
        out = []
        try:
            proj_info = DB.FilteredElementCollector(doc).OfClass(DB.ProjectInfo).ToElements()
            # Prendre le premier (doc.ProjectInformation aussi possible)
            if proj_info and len(proj_info) > 0:
                for param in proj_info[0].GetOrderedParameters():
                    try:
                        pname = param.Definition.Name
                        if pname and pname.strip():
                            out.append(pname.strip())
                    except Exception:
                        continue
        except Exception:
            out = []
        
        # Apply filter like other methods
        out = self.filter_param_names(out)
        
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
