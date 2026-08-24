# -*- coding: utf-8 -*-
# Service d'accès aux réglages et options d'export DWG

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore


class DwgExporterService(object):
    def __init__(self, namespace='batch_export', config=None):
        # `config` injecté = même UserConfig (socle) que le reste de l'app ->
        # setups persistés dans data/<namespace>.json (cf. PdfExporterService).
        if config is not None:
            self._cfg = config
        else:
            UserConfig = None  # type: ignore
            try:
                from core.UserConfig import UserConfig  # socle en priorité
            except Exception:
                try:
                    from lib.core.UserConfig import UserConfig
                except Exception:
                    UserConfig = None  # type: ignore
            self._cfg = UserConfig(namespace) if UserConfig is not None else None
        self._SETUP_KEY = 'dwg_setup_name'

    def _list_revit_setups(self, doc):
        if DB is None or doc is None:
            return []
        names = []
        try:
            col = DB.FilteredElementCollector(doc).OfClass(DB.ExportDWGSettings).ToElements()
            for s in col:
                try:
                    nm = s.Name
                    if nm and nm not in names:
                        names.append(nm)
                except Exception:
                    continue
        except Exception:
            pass
        try:
            names.sort(key=lambda x: x.lower())
        except Exception:
            names.sort()
        return names

    def list_all_setups(self, doc):
        return self._list_revit_setups(doc)

    def get_saved_setup(self, default=None):
        try:
            val = self._cfg.get(self._SETUP_KEY, '') if self._cfg is not None else None
            return val or default
        except Exception:
            return default

    def set_saved_setup(self, name):
        if not name:
            return False
        try:
            return bool(self._cfg.set(self._SETUP_KEY, name)) if self._cfg is not None else False
        except Exception:
            return False

    def build_options(self, doc, setup_name=None):
        if DB is None or doc is None:
            return None
        try:
            options = DB.DWGExportOptions()
        except Exception:
            return None
        if setup_name:
            try:
                col = DB.FilteredElementCollector(doc).OfClass(DB.ExportDWGSettings).ToElements()
                for s in col:
                    if s.Name == setup_name:
                        try:
                            opt = s.GetDWGExportOptions()
                            if opt is not None:
                                options = opt
                        except Exception:
                            pass
                        break
            except Exception:
                pass
        return options
