# -*- coding: utf-8 -*-
# Service d'accès aux réglages et options d'export PDF

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

import json

class PdfExporterService(object):
    def __init__(self, namespace='batch_export'):
        try:
            from ...core.UserConfig import UserConfig
        except Exception:
            UserConfig = None  # type: ignore
        self._cfg = UserConfig(namespace) if UserConfig is not None else None
        self._SETUP_KEY = 'pdf_setup_name'
        self._SEPARATE_KEY = 'pdf_separate_views'
        self._CUSTOM_KEY = 'custom_pdf_setups'

    def _list_revit_setups(self, doc):
        if DB is None or doc is None:
            return []
        names = []
        # PDFExportSettings (prioritaire si disponible)
        try:
            if hasattr(DB, 'PDFExportSettings'):
                col = DB.FilteredElementCollector(doc).OfClass(DB.PDFExportSettings).ToElements()
                for s in col:
                    try:
                        nm = s.Name
                        if nm and nm not in names:
                            names.append(nm)
                    except Exception:
                        continue
        except Exception:
            pass
        # Fallback PrintSetting
        try:
            col = DB.FilteredElementCollector(doc).OfClass(DB.PrintSetting).ToElements()
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

    def _load_custom_list(self):
        if self._cfg is None:
            return []
        try:
            raw = self._cfg.get(self._CUSTOM_KEY, '')
            if not raw:
                return []
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    # Liste toutes les config PDF (Revit + customs)
    def list_all_setups(self, doc):
        revit = self._list_revit_setups(doc)
        custom = self.list_custom_setups()
        s = {n: 'revit' for n in revit}
        for n in custom:
            s[n] = 'custom'
        out = list(s.keys())
        try:
            out.sort(key=lambda x: x.lower())
        except Exception:
            out.sort()
        return out

    def list_custom_setups(self):
        lst = self._load_custom_list()
        out = []
        for it in lst:
            try:
                nm = it.get('name')
                if nm and nm not in out:
                    out.append(nm)
            except Exception:
                continue
        try:
            out.sort(key=lambda x: x.lower())
        except Exception:
            out.sort()
        return out

    def get_custom_setup_data(self, name):
        for it in self._load_custom_list():
            try:
                if it.get('name') == name:
                    d = it.get('data')
                    return d if isinstance(d, dict) else None
            except Exception:
                continue
        return None

    # Nom du setup sauvegardé
    def get_saved_setup(self, default=None):
        try:
            val = self._cfg.get(self._SETUP_KEY, '') if self._cfg is not None else None
            return val or default
        except Exception:
            return default

    # Définir le setup
    def set_saved_setup(self, name):
        if not name:
            return False
        try:
            return bool(self._cfg.set(self._SETUP_KEY, name)) if self._cfg is not None else False
        except Exception:
            return False

    # Export par vue séparée ?
    def get_separate(self, default=False):
        try:
            raw = self._cfg.get(self._SEPARATE_KEY, '') if self._cfg is not None else ''
            return True if raw == '1' else False if raw == '0' else default
        except Exception:
            return default

    def set_separate(self, flag):
        try:
            return bool(self._cfg.set(self._SEPARATE_KEY, '1' if flag else '0')) if self._cfg is not None else False
        except Exception:
            return False

    # Options API PDF
    def build_options(self, doc, setup_name=None):
        if DB is None or doc is None:
            return None
        options = None
        try:
            if hasattr(DB, 'PDFExportOptions'):
                options = DB.PDFExportOptions()
        except Exception:
            options = None
        return options
