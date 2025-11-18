# -*- coding: utf-8 -*-
# Service d'options DWG (facade minimaliste)

class DwgOptionsService(object):
    def __init__(self, dwg_service=None):
        if dwg_service is None:
            try:
                from ..formats.DwgExporterService import DwgExporterService
                dwg_service = DwgExporterService()
            except Exception:
                dwg_service = None
        self._dwg = dwg_service

    def populate_combo(self, doc):
        if self._dwg is None:
            return []
        try:
            return self._dwg.list_all_setups(doc)
        except Exception:
            return []

    def get_saved(self, default=None):
        if self._dwg is None:
            return default
        return self._dwg.get_saved_setup(default)

    def set_saved(self, name):
        if self._dwg is None:
            return False
        return self._dwg.set_saved_setup(name)

    def get_separate(self, default=False):
        if self._dwg is None:
            return default
        return self._dwg.get_separate(default)

    def set_separate(self, flag):
        if self._dwg is None:
            return False
        return self._dwg.set_separate(flag)
