# -*- coding: utf-8 -*-
# Service d'accès aux réglages et options d'export PDF

from __future__ import unicode_literals

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

try:
    from services.formats.base import FormatExporterService
except Exception:
    from lib.services.formats.base import FormatExporterService


class PdfExporterService(FormatExporterService):

    SETUP_KEY = 'pdf_setup_name'

    def _list_revit_setups(self, doc):
        if DB is None or doc is None:
            return []
        noms = []
        # NB : la classe API réelle est DB.ExportPDFSettings (et non
        # DB.PDFExportSettings, qui n'existe pas dans l'API Revit 2026 —
        # vérifié via RevitAPI.xml). Elle expose ExportPDFSettings.ListNames()
        # comme méthode statique dédiée, utilisée ici en priorité ; fallback
        # sur FilteredElementCollector si l'API statique n'est pas dispo.
        try:
            if hasattr(DB, 'ExportPDFSettings'):
                try:
                    noms.extend(DB.ExportPDFSettings.ListNames(doc))
                except Exception:
                    col = DB.FilteredElementCollector(doc).OfClass(DB.ExportPDFSettings).ToElements()
                    for s in col:
                        try:
                            noms.append(s.Name)
                        except Exception:
                            continue
        except Exception:
            pass
        # Fallback PrintSetting
        try:
            col = DB.FilteredElementCollector(doc).OfClass(DB.PrintSetting).ToElements()
            for s in col:
                try:
                    noms.append(s.Name)
                except Exception:
                    continue
        except Exception:
            pass
        return self._noms_tries(noms)

    def _find_revit_setup_element(self, doc, setup_name):
        # Recherche l'élément ExportPDFSettings par nom.
        # HYPOTHÈSE (RevitAPI.xml Revit 2026, non testée dans Revit) :
        # DB.ExportPDFSettings.FindByName(doc, name) est la méthode statique
        # dédiée (pendant de ExportDWGSettings mais sans FilteredElementCollector
        # direct par nom). Fallback sur un parcours manuel du collector si
        # FindByName n'existe pas ou échoue (ex. nom invalide).
        if DB is None or doc is None or not setup_name:
            return None
        try:
            if hasattr(DB, 'ExportPDFSettings'):
                try:
                    found = DB.ExportPDFSettings.FindByName(doc, setup_name)
                    if found is not None:
                        return found
                except Exception:
                    pass
                try:
                    col = DB.FilteredElementCollector(doc).OfClass(DB.ExportPDFSettings).ToElements()
                    for s in col:
                        try:
                            if s.Name == setup_name:
                                return s
                        except Exception:
                            continue
                except Exception:
                    pass
        except Exception:
            pass
        return None

    # Options API PDF
    def build_options(self, doc, setup_name=None):
        if DB is None or doc is None:
            return None

        # Base : instance vierge, retournée si rien de mieux n'est trouvé.
        options = None
        try:
            if hasattr(DB, 'PDFExportOptions'):
                options = DB.PDFExportOptions()
        except Exception:
            options = None

        name = setup_name or self.get_saved_setup()
        if not name:
            return options

        # Setup natif Revit (DB.ExportPDFSettings), sur le modèle de
        # DwgExporterService.build_options() qui utilise
        # ExportDWGSettings.GetDWGExportOptions(). HYPOTHÈSE (RevitAPI.xml,
        # non testée dans Revit) : ExportPDFSettings.GetOptions() retourne
        # une COPIE d'un DB.PDFExportOptions directement exploitable pour
        # Document.Export. À noter (doc API) : si Combine=True sur le
        # setup, FileName revient vide dans la copie — sans conséquence
        # ici car ExportOrchestrator réaffecte FileName après build_options.
        try:
            elem = self._find_revit_setup_element(doc, name)
            if elem is not None and hasattr(elem, 'GetOptions'):
                try:
                    native_opt = elem.GetOptions()
                    if native_opt is not None:
                        return native_opt
                except Exception:
                    pass
        except Exception:
            pass

        # Fallback : instance vierge (ou None si l'API est indisponible).
        return options
