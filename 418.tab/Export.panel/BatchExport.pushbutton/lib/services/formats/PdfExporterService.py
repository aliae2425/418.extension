# -*- coding: utf-8 -*-
# Service d'accès aux réglages et options d'export PDF

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore


class PdfExporterService(object):
    def __init__(self, namespace='batch_export', config=None):
        # `config` injecté = on partage la MÊME UserConfig (socle) que le reste
        # de l'app -> les setups persistent dans data/<namespace>.json. Sinon
        # l'import relatif `...core.UserConfig` résout vers l'ANCIEN UserConfig
        # local du bouton (dépendant de pyRevit, no-op en mode admin) et les
        # setups ne se sauvegardaient jamais.
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
        self._SETUP_KEY = 'pdf_setup_name'

    def _list_revit_setups(self, doc):
        if DB is None or doc is None:
            return []
        names = []
        # NB : la classe API réelle est DB.ExportPDFSettings (et non
        # DB.PDFExportSettings, qui n'existe pas dans l'API Revit 2026 —
        # vérifié via RevitAPI.xml). Elle expose ExportPDFSettings.ListNames()
        # comme méthode statique dédiée, utilisée ici en priorité ; fallback
        # sur FilteredElementCollector si l'API statique n'est pas dispo.
        try:
            if hasattr(DB, 'ExportPDFSettings'):
                try:
                    for nm in DB.ExportPDFSettings.ListNames(doc):
                        if nm and nm not in names:
                            names.append(nm)
                except Exception:
                    col = DB.FilteredElementCollector(doc).OfClass(DB.ExportPDFSettings).ToElements()
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

    # Liste les setups PDF disponibles dans le document
    def list_all_setups(self, doc):
        return self._list_revit_setups(doc)

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
