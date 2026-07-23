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

    # Propriétés simples de DB.PDFExportOptions pouvant être recopiées
    # depuis un setup custom JSON (dict). Liste établie à partir de
    # RevitAPI.xml (Revit 2026) — HYPOTHÈSE NON VALIDÉE EN CONTEXTE RÉEL :
    # les noms/valeurs (enums notamment) doivent être confirmés par un
    # export réel dans Revit. Volontairement absents de cette liste :
    # 'FileName' (géré par l'appelant, ExportOrchestrator, juste avant
    # l'appel à Document.Export) et 'Combine' (idem).
    _PDF_OPTION_FIELDS = (
        'StopOnError',
        'ReplaceHalftoneWithThinLines',
        'MaskCoincidentLines',
        'HideScopeBoxes',
        'HideUnreferencedViewTags',
        'HideReferencePlane',
        'HideCropBoundaries',
        'ViewLinksInBlue',
        'OriginOffsetY',
        'OriginOffsetX',
        'PaperPlacement',
        'ColorDepth',
        'ExportQuality',
        'RasterQuality',
        'ZoomPercentage',
        'ZoomType',
        'AlwaysUseRaster',
        'PaperFormat',
        'PaperOrientation',
    )

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

    def _apply_custom_setup_data(self, options, data):
        # Recopie best-effort des champs connus d'un setup custom JSON sur
        # une instance DB.PDFExportOptions. À VALIDER DANS REVIT : les clés
        # attendues dans `data` sont supposées correspondre 1:1 aux noms de
        # propriétés de PDFExportOptions (voir _PDF_OPTION_FIELDS) ; aucun
        # éditeur de setup custom PDF n'a été trouvé dans ce repo pour
        # confirmer le schéma JSON réellement produit côté UI.
        if options is None or not isinstance(data, dict):
            return options
        for field in self._PDF_OPTION_FIELDS:
            if field not in data:
                continue
            try:
                if hasattr(options, field):
                    setattr(options, field, data[field])
            except Exception:
                continue
        return options

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

        # 1) Setup natif Revit (DB.ExportPDFSettings) — chemin prioritaire,
        # sur le modèle de DwgExporterService.build_options() qui utilise
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

        # 2) Setup custom JSON (pas d'élément Revit correspondant) —
        # recopie best-effort des champs connus sur l'instance vierge.
        try:
            custom_data = self.get_custom_setup_data(name)
            if custom_data:
                options = self._apply_custom_setup_data(options, custom_data)
        except Exception:
            pass

        # 3) Fallback : instance vierge (ou None si l'API est indisponible).
        return options
