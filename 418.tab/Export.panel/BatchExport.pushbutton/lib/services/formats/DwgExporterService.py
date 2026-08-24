# -*- coding: utf-8 -*-
# Service d'accès aux réglages et options d'export DWG

from __future__ import unicode_literals

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

from services.formats.base import FormatExporterService


class DwgExporterService(FormatExporterService):

    SETUP_KEY = 'dwg_setup_name'

    def _list_revit_setups(self, doc):
        if DB is None or doc is None:
            return []
        noms = []
        try:
            col = DB.FilteredElementCollector(doc).OfClass(DB.ExportDWGSettings).ToElements()
            for s in col:
                try:
                    noms.append(s.Name)
                except Exception:
                    continue
        except Exception:
            pass
        return self._noms_tries(noms)

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
