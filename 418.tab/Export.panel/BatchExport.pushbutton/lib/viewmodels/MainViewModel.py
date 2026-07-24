# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

# ----------------------------------------------------------------------
# Imports des services (Phase 2). Double forme pour supporter :
#   - le régime pyRevit (sys.path = .../BatchExport.pushbutton/lib)
#   - le régime tests standalone (sys.path = .../BatchExport.pushbutton,
#     imports préfixés par `lib.`)
# ----------------------------------------------------------------------
try:
    from services.SheetCollectionService import SheetCollectionService
except Exception:
    try:
        from lib.services.SheetCollectionService import SheetCollectionService
    except Exception:
        SheetCollectionService = None  # type: ignore

try:
    from services.NamingService import NamingService
except Exception:
    try:
        from lib.services.NamingService import NamingService
    except Exception:
        NamingService = None  # type: ignore

try:
    from services.DestinationService import DestinationService
except Exception:
    try:
        from lib.services.DestinationService import DestinationService
    except Exception:
        DestinationService = None  # type: ignore

try:
    from core.UserConfig import UserConfig
except Exception:
    try:
        from lib.core.UserConfig import UserConfig
    except Exception:
        UserConfig = None  # type: ignore

# Répertoire (legacy) des paramètres de nommage disponibles (feuilles +
# projet). Utilisé uniquement par `get_naming_params()` pour alimenter la
# modale NamingEditorView -- double forme d'import comme les autres services
# de ce fichier.
try:
    from data.sheets.SheetParameterRepository import SheetParameterRepository
except Exception:
    try:
        from lib.data.sheets.SheetParameterRepository import SheetParameterRepository
    except Exception:
        SheetParameterRepository = None  # type: ignore

# ATTENTION -- ordre d'import INVERSE des autres services de ce fichier
# (`lib.` d'abord). PdfExporterService/DwgExporterService utilisent des
# imports RELATIFS internes (`from ...core.UserConfig import UserConfig`) qui
# ne résolvent correctement QUE si leur package racine est `lib`
# (donc `lib.services.formats.X`). Importés comme `services.formats.X`
# (racine = `services`), les `...` remontent au-dessus de `lib` et l'import
# interne de UserConfig retombe sur None sans lever -> `self._cfg = None`
# côté service -> get/set_saved_setup deviennent des no-op silencieux et les
# setups PDF/DWG choisis ne persisteraient JAMAIS (les listes, elles,
# continueraient de se peupler car list_all_setups n'a besoin que de DB/doc :
# bug invisible « les setups ne se sauvegardent pas »). Même raison que pour
# l'import de ExportOrchestrator dans lancer_export().
try:
    from lib.services.formats.PdfExporterService import PdfExporterService
except Exception:
    try:
        from services.formats.PdfExporterService import PdfExporterService
    except Exception:
        PdfExporterService = None  # type: ignore

try:
    from lib.services.formats.DwgExporterService import DwgExporterService
except Exception:
    try:
        from services.formats.DwgExporterService import DwgExporterService
    except Exception:
        DwgExporterService = None  # type: ignore


_MODES = (u'auto', u'manual', u'settings')
_SURFACE_TITRES = {
    u'auto': u'Jeux qualifiés à l\'export',
    u'manual': u'Sélection manuelle',
    u'settings': u'Paramètres',
}

# Clés UserConfig (namespace 'batch_export') pour le mappage des paramètres
# Oui/Non de collection -> rôle (export / carnet / dwg).
#
# `sheet_param_carnetcombo` et `sheet_param_dwgcombo` reprennent les clés
# legacy déjà utilisées par ConfigManagerService.KEYS (profils/CSV).
# `sheet_param_exportationcombo` est une clé NOUVELLE : le legacy
# (lib/services/core/ExportOrchestrator._get_ui_selected_param_names) lisait
# le nom du paramètre "Export" directement depuis le contrôle UI
# (ComboBox 'ExportationCombo') sans jamais le persister. On l'ajoute ici en
# suivant la même convention de nommage (`sheet_param_` + nom du combo en
# minuscules) pour permettre au VM de fonctionner sans UI. À reporter dans
# `ConfigManagerService.KEYS` (profils/CSV) dans une tâche ultérieure.
_CFG_KEY_PARAM_EXPORT = 'sheet_param_exportationcombo'
_CFG_KEY_PARAM_CARNET = 'sheet_param_carnetcombo'
_CFG_KEY_PARAM_DWG = 'sheet_param_dwgcombo'


class SheetItemVM(BaseViewModel):
    """Item bindable pour une feuille au sein d'une collection (mode « par
    jeu »). Dérive de `BaseViewModel` (comme le reste du projet) pour que
    `{Binding Numero}` etc. résolvent via de vraies propriétés CLR — un
    `dict` Python n'expose pas ces propriétés et ne bind pas de façon
    fiable via `{Binding [Cle]}`."""

    def __init__(self, numero, nom, nom_projete):
        super(SheetItemVM, self).__init__()
        self._numero = numero
        self._nom = nom
        self._nom_projete = nom_projete

    @property
    def Numero(self):
        return self._numero

    @property
    def Nom(self):
        return self._nom

    @property
    def NomProjete(self):
        return self._nom_projete


class CollectionItemVM(BaseViewModel):
    """Item bindable pour une collection (jeu) au sein du mode « par jeu »."""

    def __init__(self, titre, cid, flag_export, flag_carnet, flag_dwg, sheets):
        super(CollectionItemVM, self).__init__()
        self._titre = titre
        self._id = cid
        self._flag_export = bool(flag_export)
        self._flag_carnet = bool(flag_carnet)
        self._flag_dwg = bool(flag_dwg)
        self._sheets = sheets  # list[SheetItemVM]

    @property
    def Titre(self):
        return self._titre

    @property
    def Id(self):
        return self._id

    @property
    def FlagExport(self):
        return self._flag_export

    @property
    def FlagCarnet(self):
        return self._flag_carnet

    @property
    def FlagDwg(self):
        return self._flag_dwg

    @property
    def Qualified(self):
        return self._flag_export

    @property
    def Sheets(self):
        return self._sheets


class ManualSheetVM(BaseViewModel):
    """Item bindable pour une feuille en mode « feuille par feuille »
    (sélection manuelle). `ExportPdf`/`ExportDwg`/`Selected` sont TWO-WAY
    (cases à cocher) ; chaque toggle notifie sa propriété puis appelle
    `on_change` (callback fourni par le VM parent) pour permettre la
    recomputation des compteurs `NbPdf`/`NbDwg`/`NbSelected` sans que ce VM
    connaisse `MainViewModel`.

    `JeuNom`/`NomProjete` sont en LECTURE SEULE : calculés une fois par
    `refresh_manuel()` (mapping CollectionId->Titre et résolution du
    pattern de nommage FEUILLE), jamais recalculés à la volée par ce VM.

    Sémantique de `Selected` (proposition, voir docstring de
    `selection_manuelle`) : coche d'inclusion de la ligne dans l'export,
    INDÉPENDANTE des cases de format `ExportPdf`/`ExportDwg`. Ce draft
    n'unifie pas encore les deux notions -- `selection_manuelle()` continue
    de se baser uniquement sur ExportPdf/ExportDwg (comportement inchangé,
    couvert par les tests existants) ; `Selected`/`NbSelected` sont exposés
    en plus pour que l'UI/orchestrateur décide plus tard comment les
    combiner (ex: une ligne cochée sans aucun format actif ne serait pas
    exportée malgré `Selected=True`).
    """

    def __init__(self, numero, nom, collection_id=None, elem=None,
                 export_pdf=True, export_dwg=False, selected=False,
                 jeu_nom=u'', nom_projete=u'', on_change=None):
        super(ManualSheetVM, self).__init__()
        self._numero = numero
        self._nom = nom
        self._collection_id = collection_id
        self._elem = elem
        self._export_pdf = bool(export_pdf)
        self._export_dwg = bool(export_dwg)
        self._selected = bool(selected)
        self._jeu_nom = jeu_nom or u''
        self._nom_projete = nom_projete or u''
        self._on_change = on_change

    @property
    def Numero(self):
        return self._numero

    @property
    def Nom(self):
        return self._nom

    @property
    def CollectionId(self):
        return self._collection_id

    @property
    def Elem(self):
        return self._elem

    @property
    def JeuNom(self):
        return self._jeu_nom

    @property
    def NomProjete(self):
        return self._nom_projete

    @property
    def ExportPdf(self):
        return self._export_pdf

    @ExportPdf.setter
    def ExportPdf(self, value):
        value = bool(value)
        if value == self._export_pdf:
            return
        self._export_pdf = value
        self.notify_property(u'ExportPdf')
        if callable(self._on_change):
            self._on_change()

    @property
    def ExportDwg(self):
        return self._export_dwg

    @ExportDwg.setter
    def ExportDwg(self, value):
        value = bool(value)
        if value == self._export_dwg:
            return
        self._export_dwg = value
        self.notify_property(u'ExportDwg')
        if callable(self._on_change):
            self._on_change()

    @property
    def Selected(self):
        return self._selected

    @Selected.setter
    def Selected(self, value):
        value = bool(value)
        if value == self._selected:
            return
        self._selected = value
        self.notify_property(u'Selected')
        if callable(self._on_change):
            self._on_change()


class FiltreItemVM(BaseViewModel):
    """Item bindable pour le sélecteur de filtre du mode manuel (un par
    collection/jeu, un par set d'impression -- PLUS d'item « Toutes les
    feuilles » pseudo, cf. sémantique multi-filtre de
    `MainViewModel.SheetsManuelFiltrees`).

    `.Label` et `.IsActif` sont bindés côté WPF (case à cocher par filtre).
    `kind`/`coll_id`/`sheet_ids` sont des attributs internes lus uniquement
    par `MainViewModel.SheetsManuelFiltrees`. `kind` vaut `'collection'` ou
    `'set'`. `on_change` (callback du VM parent) est appelé à chaque
    toggle de `IsActif`, comme pour `ManualSheetVM.ExportPdf`/`ExportDwg`.
    """

    def __init__(self, label, kind, coll_id=None, sheet_ids=None,
                 is_actif=False, on_change=None):
        super(FiltreItemVM, self).__init__()
        self._label = label
        self.kind = kind
        self.coll_id = coll_id
        self.sheet_ids = sheet_ids or set()
        self._is_actif = bool(is_actif)
        self._on_change = on_change

    @property
    def Label(self):
        return self._label

    @property
    def IsActif(self):
        return self._is_actif

    @IsActif.setter
    def IsActif(self, value):
        value = bool(value)
        if value == self._is_actif:
            return
        self._is_actif = value
        self.notify_property(u'IsActif')
        if callable(self._on_change):
            self._on_change()


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None, sheet_service=None, naming_service=None,
                 destination_service=None, config=None,
                 pdf_service=None, dwg_service=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._titre = u'Exportation'
        self._mode = u'auto'

        # Config (namespace fixe 'batch_export'). Injectable pour les tests
        # hors Revit : `UserConfig` reste instanciable sans pyRevit mais son
        # backend (`pyrevit.userconfig`) est alors indisponible -> get/set
        # deviennent des no-op silencieux. `config` permet d'injecter un
        # faux magasin en mémoire (même contrat get/set que UserConfig) pour
        # tester le mapping ParamExport/ParamCarnet/ParamDwg sans Revit.
        if config is not None:
            self._cfg = config
        else:
            try:
                self._cfg = UserConfig('batch_export') if UserConfig is not None else None
            except Exception:
                self._cfg = None

        # Services injectables : si absents, instancier les vrais sous
        # try/except -> None (permet l'usage hors Revit / dans les tests).
        # On INJECTE self._cfg (config partagée du VM) : ainsi tous les services
        # écrivent via la MÊME instance UserConfig que le mapping (qui, lui,
        # persiste). Sinon chaque service crée sa propre UserConfig via son
        # propre import (`core.UserConfig` vs `lib.core.UserConfig` = modules
        # distincts) et la destination ne partageait pas le chemin de config.
        if sheet_service is not None:
            self._sheet_service = sheet_service
        else:
            try:
                self._sheet_service = SheetCollectionService(doc, config=self._cfg) if SheetCollectionService is not None else None
            except Exception:
                self._sheet_service = None

        if naming_service is not None:
            self._naming_service = naming_service
        else:
            try:
                self._naming_service = NamingService(doc, config=self._cfg) if NamingService is not None else None
            except Exception:
                self._naming_service = None

        if destination_service is not None:
            self._destination_service = destination_service
        else:
            try:
                self._destination_service = DestinationService(doc, config=self._cfg) if DestinationService is not None else None
            except Exception:
                self._destination_service = None

        # Services PDF/DWG (setups + options d'export). Contrairement aux
        # autres services, PdfExporterService/DwgExporterService n'acceptent
        # PAS de paramètre `config=`/`doc=` dans leur constructeur (signature
        # figée : `__init__(self, namespace='batch_export')`). Ils créent
        # donc leur propre instance UserConfig plutôt que de partager
        # `self._cfg` -- pas d'injection possible par construction. Ce n'est
        # toutefois pas un problème de partage de données : `UserConfig`
        # (lib/core/UserConfig.py) ignore le `namespace` reçu et opère
        # toujours sur la MÊME section pyRevit `uc.batch_export`, donc ces
        # services persistent bien dans la même config que le reste du VM,
        # simplement via une instance Python distincte.
        if pdf_service is not None:
            self._pdf_service = pdf_service
        else:
            try:
                self._pdf_service = PdfExporterService(config=self._cfg) if PdfExporterService is not None else None
            except Exception:
                self._pdf_service = None

        if dwg_service is not None:
            self._dwg_service = dwg_service
        else:
            try:
                self._dwg_service = DwgExporterService(config=self._cfg) if DwgExporterService is not None else None
            except Exception:
                self._dwg_service = None

        # Données « par jeu »
        self._collections = []
        self._nb_jeux_qualifies = 0
        self._nb_feuilles_qualifiees = 0

        # Export (Task 3) : retour visuel (progress_cb/log_cb de l'orchestrateur)
        self._status_text = u''
        self._progress_value = 0

        # Mode Paramètres (Task 4) : liste des paramètres Oui/Non disponibles
        # pour le mappage Export/Carnet/DWG. Calculée une fois à la
        # construction (voir `_refresh_parametres_disponibles`) plutôt qu'à
        # chaque `refresh_par_jeu()` -- ce dernier est appelé par les setters
        # ParamExport/ParamCarnet/ParamDwg, et `list_boolean_params()` n'a
        # aucun rapport avec la (re)qualification des jeux.
        self._parametres_disponibles = []
        self._refresh_parametres_disponibles()

        # Données « feuille par feuille » (mode manuel). Sélection ÉPHÉMÈRE :
        # reconstruite à chaque refresh_manuel(), jamais persistée.
        self._sheets_manuel = []
        self._filtres_manuel = []
        # `FiltreManuelSelectionne` (sélection UNIQUE) est DÉPRÉCIÉ depuis le
        # passage au multi-filtre à cases `IsActif` (voir `FiltreItemVM`) --
        # conservé INERTE (getter/setter no-op côté recalcul) uniquement en
        # filet de sécurité si un binding XAML résiduel y fait encore
        # référence ; `SheetsManuelFiltrees` ne le lit plus jamais.
        self._filtre_manuel_selectionne = None
        self._recherche_manuel = u''

        # Aperçu des conventions de nommage (page Réglages) : motifs bruts
        # (chaînes à jetons ou anciens templates), recalculés par
        # `refresh_patterns_apercu()`.
        self._pattern_feuille_apercu = u''
        self._pattern_carnet_apercu = u''

        # Cache CollectionId -> Titre, recalculé par `refresh_manuel()` --
        # sert uniquement à peupler `ManualSheetVM.JeuNom`.
        self._collections_titres = {}

        # Aperçu initial (avant tout refresh_manuel()) -- best-effort,
        # cf. refresh_patterns_apercu().
        self.refresh_patterns_apercu()

    # ------------------------------------------------------------------
    # Mode / titre (existant)
    # ------------------------------------------------------------------

    @property
    def Titre(self):
        return self._titre

    @property
    def ActiveMode(self):
        return self._mode

    @ActiveMode.setter
    def ActiveMode(self, value):
        if value not in _MODES:
            return
        self._mode = value
        for name in (u'ActiveMode', u'IsAuto', u'IsNotAuto', u'IsManual',
                     u'IsSettings', u'IsNotSettings', u'SurfaceTitre'):
            self.notify_property(name)

    def set_mode(self, mode):
        self.ActiveMode = mode

    @property
    def IsAuto(self):
        return self._mode == u'auto'

    @property
    def IsNotAuto(self):
        return self._mode != u'auto'

    @property
    def IsManual(self):
        return self._mode == u'manual'

    @property
    def IsSettings(self):
        return self._mode == u'settings'

    @property
    def IsNotSettings(self):
        return self._mode != u'settings'

    @property
    def SurfaceTitre(self):
        return _SURFACE_TITRES.get(self._mode, u'')

    # ------------------------------------------------------------------
    # Mapping paramètres (persistant via UserConfig)
    # ------------------------------------------------------------------

    def _cfg_get(self, key, default=u''):
        try:
            return self._cfg.get(key, default) if self._cfg is not None else default
        except Exception:
            return default

    def _cfg_set(self, key, value):
        try:
            if self._cfg is not None:
                self._cfg.set(key, value or u'')
        except Exception:
            pass

    @property
    def ParamExport(self):
        return self._cfg_get(_CFG_KEY_PARAM_EXPORT, u'')

    @ParamExport.setter
    def ParamExport(self, value):
        value = value or u''
        if value == self.ParamExport:
            return
        self._cfg_set(_CFG_KEY_PARAM_EXPORT, value)
        self.notify_property(u'ParamExport')
        self.refresh_par_jeu()

    @property
    def ParamCarnet(self):
        return self._cfg_get(_CFG_KEY_PARAM_CARNET, u'')

    @ParamCarnet.setter
    def ParamCarnet(self, value):
        value = value or u''
        if value == self.ParamCarnet:
            return
        self._cfg_set(_CFG_KEY_PARAM_CARNET, value)
        self.notify_property(u'ParamCarnet')
        self.refresh_par_jeu()

    @property
    def ParamDwg(self):
        return self._cfg_get(_CFG_KEY_PARAM_DWG, u'')

    @ParamDwg.setter
    def ParamDwg(self, value):
        value = value or u''
        if value == self.ParamDwg:
            return
        self._cfg_set(_CFG_KEY_PARAM_DWG, value)
        self.notify_property(u'ParamDwg')
        self.refresh_par_jeu()

    def _refresh_parametres_disponibles(self):
        """(Re)calcule `ParametresDisponibles` depuis `_sheet_service`.

        Best-effort : `list_boolean_params()` peut être absent (faux
        service dans certains tests) ou lever (hors Revit) -> `[]`.
        """
        noms = []
        if self._sheet_service is not None:
            try:
                lister = getattr(self._sheet_service, 'list_boolean_params', None)
                if callable(lister):
                    noms = list(lister() or [])
            except Exception:
                noms = []
        self._parametres_disponibles = noms
        self.notify_property(u'ParametresDisponibles')

    @property
    def ParametresDisponibles(self):
        return self._parametres_disponibles

    def get_naming_params(self):
        """Liste des noms de paramètres utilisables pour le nommage des
        fichiers exportés (modale NamingEditorView), best-effort.

        Combine les paramètres d'instance de feuille (`ViewSheet`) et les
        paramètres projet (`ProjectInfo`) via `SheetParameterRepository`
        (legacy), dédoublonnés en conservant l'ordre d'apparition
        (feuilles d'abord, puis projet). Injecte `self._cfg` (config
        partagée du VM) au repository -- `SheetParameterRepository._get_cfg`
        retourne alors directement cette instance sans dépendre de son
        import relatif interne (`from ...core.UserConfig import UserConfig`),
        qui ne résolvent correctement que si le package racine du module est
        `lib` (cf. notes d'import plus haut dans ce fichier).

        Ne lève jamais : retourne `[]` si `self._doc` est absent, si
        `SheetParameterRepository` n'a pas pu être importé, ou si la
        collecte échoue pour toute autre raison.
        """
        if self._doc is None or SheetParameterRepository is None:
            return []
        try:
            repo = SheetParameterRepository(config_store=self._cfg)
        except Exception:
            return []

        noms = []
        vus = set()

        try:
            for n in (repo.collect_sheet_instance_params(self._doc) or []):
                if n not in vus:
                    vus.add(n)
                    noms.append(n)
        except Exception:
            pass

        try:
            for n in (repo.collect_project_params(self._doc) or []):
                if n not in vus:
                    vus.add(n)
                    noms.append(n)
        except Exception:
            pass

        return noms

    # ------------------------------------------------------------------
    # Page Réglages : aperçu des conventions de nommage (motifs bruts)
    # ------------------------------------------------------------------

    def refresh_patterns_apercu(self):
        """(Re)calcule `PatternFeuilleApercu`/`PatternCarnetApercu` depuis
        `_naming_service.load('sheet')`/`load('set')` (le motif brut
        uniquement -- `[0]` du tuple `(pattern, rows)`, pour affichage dans
        la page Réglages).

        Best-effort : ne lève jamais. Repli `u''` si `_naming_service` est
        absent ou si `load()` échoue."""
        pattern_feuille = u''
        pattern_carnet = u''
        if self._naming_service is not None:
            try:
                pattern_feuille = self._naming_service.load('sheet')[0] or u''
            except Exception:
                pattern_feuille = u''
            try:
                pattern_carnet = self._naming_service.load('set')[0] or u''
            except Exception:
                pattern_carnet = u''
        self._pattern_feuille_apercu = pattern_feuille
        self._pattern_carnet_apercu = pattern_carnet
        for name in (u'PatternFeuilleApercu', u'PatternCarnetApercu'):
            self.notify_property(name)

    @property
    def PatternFeuilleApercu(self):
        return self._pattern_feuille_apercu

    @property
    def PatternCarnetApercu(self):
        return self._pattern_carnet_apercu

    # ------------------------------------------------------------------
    # Mode « par jeu »
    # ------------------------------------------------------------------

    def refresh_par_jeu(self):
        """Construit `self._collections` à partir des services injectés.

        Contrat attendu pour `sheet_service` (réel ou faux, pour tests
        hors Revit) :
          - `list_collections()` -> liste de dicts contenant au moins
            `'Titre'`, `'Id'`, et **`'Elem'`** (élément Revit brut, ou tout
            objet substitut dans les tests) permettant `read_flag(elem, ...)`.
            NB: `SheetCollectionService.list_collections()` (Phase 2) ne
            renvoie pas nativement cette clé -> à compléter côté service
            réel (ajout non invasif d'une clé `'Elem': coll` dans la boucle
            existante) pour que ce VM fonctionne dans Revit. C'est la voie
            choisie plutôt qu'un accès par Id séparé, car elle évite un
            aller-retour supplémentaire et reste cohérente avec le même
            besoin côté feuilles (`list_sheets`).
          - `list_sheets(collection_id)` -> liste de dicts contenant au
            moins `'Numero'`, `'Nom'`, et **`'Elem'`** (élément `ViewSheet`
            brut) pour permettre `naming_service.resolve_for_element`.
          - `read_flag(elem, param_name)` -> bool.

        `naming_service` : `load('sheet')` -> `(pattern, rows)` ;
        `resolve_for_element(elem, rows)` -> unicode.
        """
        collections_out = []
        nb_jeux_qualifies = 0
        nb_feuilles_qualifiees = 0

        _pattern = u''
        rows_sheet = []
        if self._naming_service is not None:
            try:
                _pattern, rows_sheet = self._naming_service.load('sheet')
            except Exception:
                _pattern = u''
                rows_sheet = []

        raw_collections = []
        if self._sheet_service is not None:
            try:
                raw_collections = self._sheet_service.list_collections() or []
            except Exception:
                raw_collections = []

        param_export = self.ParamExport
        param_carnet = self.ParamCarnet
        param_dwg = self.ParamDwg

        for coll in raw_collections:
            titre = coll.get('Titre', u'') if isinstance(coll, dict) else u''
            coll_id = coll.get('Id') if isinstance(coll, dict) else None
            coll_elem = coll.get('Elem') if isinstance(coll, dict) else None

            flag_export = False
            flag_carnet = False
            flag_dwg = False
            if self._sheet_service is not None and coll_elem is not None:
                try:
                    flag_export = bool(self._sheet_service.read_flag(coll_elem, param_export)) if param_export else False
                except Exception:
                    flag_export = False
                try:
                    flag_carnet = bool(self._sheet_service.read_flag(coll_elem, param_carnet)) if param_carnet else False
                except Exception:
                    flag_carnet = False
                try:
                    flag_dwg = bool(self._sheet_service.read_flag(coll_elem, param_dwg)) if param_dwg else False
                except Exception:
                    flag_dwg = False

            qualified = bool(flag_export)
            if qualified:
                nb_jeux_qualifies += 1

            sheets_out = []
            raw_sheets = []
            if self._sheet_service is not None:
                try:
                    raw_sheets = self._sheet_service.list_sheets(coll_id) or []
                except Exception:
                    raw_sheets = []

            for sheet in raw_sheets:
                numero = sheet.get('Numero', u'') if isinstance(sheet, dict) else u''
                nom = sheet.get('Nom', u'') if isinstance(sheet, dict) else u''
                sheet_elem = sheet.get('Elem') if isinstance(sheet, dict) else None

                nom_projete = u''
                if self._naming_service is not None and sheet_elem is not None and (_pattern or rows_sheet):
                    try:
                        nom_projete = self._naming_service.resolve_for_element(sheet_elem, _pattern or rows_sheet) or u''
                    except Exception:
                        nom_projete = u''
                if not nom_projete:
                    nom_projete = u"{}{}".format(numero, nom)

                sheets_out.append(SheetItemVM(numero, nom, nom_projete))

            if qualified:
                nb_feuilles_qualifiees += len(sheets_out)

            collections_out.append(CollectionItemVM(
                titre, coll_id, flag_export, flag_carnet, flag_dwg, sheets_out
            ))

        # Tri (stable) : collections QUALIFIÉES (FlagExport=True) d'abord,
        # puis alphabétique du Titre (insensible à la casse) au sein de
        # chaque groupe. `sorted()` est stable en Python -> l'ordre relatif
        # d'items à clé égale (même Qualified, même Titre) est préservé.
        collections_out = sorted(
            collections_out,
            key=lambda c: (not c.Qualified, (c.Titre or u'').lower()),
        )

        self._collections = collections_out
        self._nb_jeux_qualifies = nb_jeux_qualifies
        self._nb_feuilles_qualifiees = nb_feuilles_qualifiees

        for name in (u'Collections', u'NbJeuxQualifies', u'NbFeuillesQualifiees'):
            self.notify_property(name)

    @property
    def Collections(self):
        return self._collections

    @property
    def NbJeuxQualifies(self):
        return self._nb_jeux_qualifies

    @property
    def NbFeuillesQualifiees(self):
        return self._nb_feuilles_qualifiees

    # ------------------------------------------------------------------
    # Mode « feuille par feuille » (manuel)
    # ------------------------------------------------------------------

    def refresh_manuel(self):
        """Construit `self._sheets_manuel` (toutes les feuilles du doc) et
        `self._filtres_manuel` (un par collection/jeu + un par set
        d'impression -- PLUS d'item « Toutes les feuilles » pseudo, cf.
        sémantique multi-filtre de `SheetsManuelFiltrees`) depuis
        `_sheet_service`.

        Sélection ÉPHÉMÈRE : chaque appel reconstruit entièrement les
        `ManualSheetVM` (défauts `ExportPdf=True`/`ExportDwg=False`/
        `Selected=False`) et les `FiltreItemVM` (défaut `IsActif=False` :
        aucun filtre actif -> toutes les feuilles visibles), sans tenter de
        préserver l'état précédent.

        `JeuNom` (par feuille) est renseigné via un mapping
        CollectionId->Titre construit depuis `list_collections()` (déjà
        appelée par `refresh_par_jeu`, ré-appelée ici pour ne pas coupler
        les deux refresh). `NomProjete` est calculé en résolvant le pattern
        de nommage FEUILLE (chargé UNE SEULE FOIS via `_naming_service.load
        ('sheet')`) contre chaque élément -- même stratégie de repli
        `pattern or rows` que `refresh_par_jeu` (un pattern à jetons vide
        avec des rows renseignées, ou l'inverse, doit tout de même piloter
        la résolution ; cf. TestMainViewModelParJeuPatternJetons).

        Contrat attendu pour `sheet_service` :
          - `list_all_sheets()` -> liste de dicts `'Numero'`/`'Nom'`/
            `'CollectionId'`/`'Elem'`.
          - `list_collections()` -> liste de dicts `'Titre'`/`'Id'` (déjà
            utilisée par `refresh_par_jeu`).
          - `list_view_sheet_sets()` -> liste de dicts `'Nom'`/`'SheetIds'`
            (numéros de feuille, PAS des ElementId -- cf. docstring de
            `SheetCollectionService.list_view_sheet_sets`).
        """
        raw_collections = []
        if self._sheet_service is not None:
            try:
                raw_collections = self._sheet_service.list_collections() or []
            except Exception:
                raw_collections = []

        collections_titres = {}
        for coll in raw_collections:
            titre = coll.get('Titre', u'') if isinstance(coll, dict) else u''
            coll_id = coll.get('Id') if isinstance(coll, dict) else None
            collections_titres[coll_id] = titre or u''
        self._collections_titres = collections_titres

        _pattern = u''
        rows_sheet = []
        if self._naming_service is not None:
            try:
                _pattern, rows_sheet = self._naming_service.load('sheet')
            except Exception:
                _pattern = u''
                rows_sheet = []

        raw_sheets = []
        if self._sheet_service is not None:
            try:
                raw_sheets = self._sheet_service.list_all_sheets() or []
            except Exception:
                raw_sheets = []

        sheets_out = []
        for sheet in raw_sheets:
            numero = sheet.get('Numero', u'') if isinstance(sheet, dict) else u''
            nom = sheet.get('Nom', u'') if isinstance(sheet, dict) else u''
            coll_id = sheet.get('CollectionId') if isinstance(sheet, dict) else None
            elem = sheet.get('Elem') if isinstance(sheet, dict) else None

            jeu_nom = collections_titres.get(coll_id, u'') or u''

            nom_projete = u''
            if self._naming_service is not None and elem is not None and (_pattern or rows_sheet):
                try:
                    nom_projete = self._naming_service.resolve_for_element(elem, _pattern or rows_sheet) or u''
                except Exception:
                    nom_projete = u''

            sheets_out.append(ManualSheetVM(
                numero, nom, collection_id=coll_id, elem=elem,
                export_pdf=True, export_dwg=False, selected=False,
                jeu_nom=jeu_nom, nom_projete=nom_projete,
                on_change=self._on_manual_sheet_change,
            ))
        self._sheets_manuel = sheets_out

        filtres_out = []
        for coll in raw_collections:
            titre = coll.get('Titre', u'') if isinstance(coll, dict) else u''
            coll_id = coll.get('Id') if isinstance(coll, dict) else None
            filtres_out.append(FiltreItemVM(
                u'Jeu : ' + (titre or u''), u'collection', coll_id=coll_id,
                on_change=self._on_filtre_change,
            ))

        raw_sets = []
        if self._sheet_service is not None:
            try:
                raw_sets = self._sheet_service.list_view_sheet_sets() or []
            except Exception:
                raw_sets = []
        for vss in raw_sets:
            nom = vss.get('Nom', u'') if isinstance(vss, dict) else u''
            sheet_ids = vss.get('SheetIds') if isinstance(vss, dict) else None
            filtres_out.append(FiltreItemVM(
                u'Impression : ' + (nom or u''), u'set', sheet_ids=sheet_ids,
                on_change=self._on_filtre_change,
            ))

        self._filtres_manuel = filtres_out
        self._filtre_manuel_selectionne = None

        self.refresh_patterns_apercu()

        for name in (u'SheetsManuel', u'FiltresManuel', u'FiltreManuelSelectionne',
                     u'SheetsManuelFiltrees', u'NbFeuillesManuel', u'NbPdf',
                     u'NbDwg', u'NbSelected'):
            self.notify_property(name)

    def _on_manual_sheet_change(self):
        """Callback passé à chaque `ManualSheetVM` : un toggle ExportPdf/
        ExportDwg/Selected impacte les compteurs (calculés à la volée sur
        les feuilles FILTRÉES), jamais la liste ni les filtres eux-mêmes."""
        for name in (u'NbPdf', u'NbDwg', u'NbSelected'):
            self.notify_property(name)

    def _on_filtre_change(self):
        """Callback passé à chaque `FiltreItemVM` : un toggle `IsActif`
        recalcule `SheetsManuelFiltrees` et les compteurs (union OU sur les
        filtres actifs -- voir `SheetsManuelFiltrees`)."""
        for name in (u'SheetsManuelFiltrees', u'NbFeuillesManuel', u'NbPdf',
                     u'NbDwg', u'NbSelected'):
            self.notify_property(name)

    @property
    def SheetsManuel(self):
        return self._sheets_manuel

    @property
    def FiltresManuel(self):
        return self._filtres_manuel

    @property
    def FiltreManuelSelectionne(self):
        """DÉPRÉCIÉ (sélection UNIQUE, remplacée par le multi-filtre à
        cases `FiltreItemVM.IsActif`). Conservé INERTE : le setter ne
        recalcule plus `SheetsManuelFiltrees` (qui n'en dépend plus) --
        gardé uniquement en filet de sécurité pour un éventuel binding XAML
        résiduel, afin qu'une affectation ne lève pas d'erreur."""
        return self._filtre_manuel_selectionne

    @FiltreManuelSelectionne.setter
    def FiltreManuelSelectionne(self, value):
        self._filtre_manuel_selectionne = value
        self.notify_property(u'FiltreManuelSelectionne')

    @property
    def RechercheManuel(self):
        return self._recherche_manuel

    @RechercheManuel.setter
    def RechercheManuel(self, value):
        value = value or u''
        if value == self._recherche_manuel:
            return
        self._recherche_manuel = value
        for name in (u'RechercheManuel', u'SheetsManuelFiltrees',
                     u'NbFeuillesManuel', u'NbPdf', u'NbDwg', u'NbSelected'):
            self.notify_property(name)

    def _sheet_matches_filtre(self, sheet, filtre):
        """Applique le critère de correspondance feuille <-> UN filtre.

        - kind 'collection' : `sheet.CollectionId == filtre.coll_id`.
        - kind 'set' : `sheet.Numero in filtre.sheet_ids` -- le
          `SheetNumber` est la clé de correspondance choisie pour les sets
          d'impression (cf. `SheetCollectionService.list_view_sheet_sets`),
          car unique dans le document et trivialement comparable hors
          Revit, contrairement à un `ElementId`.
        """
        if filtre is None:
            return False
        if filtre.kind == u'collection':
            return sheet.CollectionId == filtre.coll_id
        if filtre.kind == u'set':
            try:
                return sheet.Numero in (filtre.sheet_ids or set())
            except Exception:
                return False
        return False

    @property
    def SheetsManuelFiltrees(self):
        """Feuilles du mode manuel après application de la recherche
        (Numero OU Nom, insensible à la casse) ET du multi-filtre.

        Sémantique multi-filtre OU : si AUCUN filtre n'est actif
        (`FiltreItemVM.IsActif`), TOUTES les feuilles passent le filtre ;
        sinon une feuille passe si elle correspond à AU MOINS UN filtre
        actif (union OU), via `_sheet_matches_filtre`."""
        recherche = (self._recherche_manuel or u'').strip().lower()
        filtres_actifs = [f for f in self._filtres_manuel if f.IsActif]
        out = []
        for sheet in self._sheets_manuel:
            if filtres_actifs:
                if not any(self._sheet_matches_filtre(sheet, f) for f in filtres_actifs):
                    continue
            if recherche:
                try:
                    numero = (sheet.Numero or u'').lower()
                except Exception:
                    numero = u''
                try:
                    nom = (sheet.Nom or u'').lower()
                except Exception:
                    nom = u''
                if recherche not in numero and recherche not in nom:
                    continue
            out.append(sheet)
        return out

    @property
    def NbFeuillesManuel(self):
        return len(self.SheetsManuelFiltrees)

    @property
    def NbPdf(self):
        return len([s for s in self.SheetsManuelFiltrees if s.ExportPdf])

    @property
    def NbDwg(self):
        return len([s for s in self.SheetsManuelFiltrees if s.ExportDwg])

    @property
    def NbSelected(self):
        """Nombre de feuilles `Selected=True` parmi les feuilles FILTRÉES
        (même périmètre que `NbPdf`/`NbDwg`)."""
        return len([s for s in self.SheetsManuelFiltrees if s.Selected])

    def selection_manuelle(self):
        """Retourne les `ManualSheetVM` cochées (ExportPdf OU ExportDwg),
        pour un futur export.

        Porte sur `self._sheets_manuel` EN ENTIER (pas sur
        `SheetsManuelFiltrees`) : une feuille cochée puis masquée par un
        changement de filtre/recherche doit rester dans la sélection --
        seul `refresh_manuel()` réinitialise l'état des cases.

        Choix (draft) : `Selected` (case d'inclusion de ligne, cf.
        `ManualSheetVM`) N'EST PAS pris en compte ici -- le critère reste
        UNIQUEMENT les cases de format ExportPdf/ExportDwg, comme avant
        l'ajout de `Selected`. `Selected`/`NbSelected` sont exposés en plus
        (pas encore consommés par l'export) pour laisser l'UI/orchestrateur
        décider plus tard de la combinaison exacte des deux notions."""
        return [s for s in self._sheets_manuel if s.ExportPdf or s.ExportDwg]

    # ------------------------------------------------------------------
    # Destination (Task « Parcourir ») : coordination VM -> DestinationService
    # ------------------------------------------------------------------

    @property
    def DestinationPath(self):
        """Chemin de destination courant.

        Best-effort : `_destination_service.get()` peut lever (hors Revit,
        backend UserConfig absent) -> repli `u''`. Si le service lui-même
        est absent (None), retourne directement `u''` sans appel.
        """
        try:
            if self._destination_service is not None:
                return self._destination_service.get() or u''
        except Exception:
            pass
        return u''

    @DestinationPath.setter
    def DestinationPath(self, value):
        """Setter TWO-WAY (footer : TextBox destination éditable).

        Délègue à `definir_destination` (persistance + notification déjà
        gérées là-bas). Ignore une valeur vide ou inchangée pour éviter une
        boucle de notification (LostFocus -> setter -> notify_property ->
        binding relit la même valeur -> ...).
        """
        if not value or value == self.DestinationPath:
            return
        self.definir_destination(value)

    def definir_destination(self, path):
        """Enregistre `path` comme dossier de destination et notifie la vue.

        Ne lève jamais : chaque étape (set/ensure) est protégée
        individuellement afin que l'échec de l'une n'empêche pas l'autre
        ni la notification de la propriété bindable.
        """
        if not path:
            return
        if self._destination_service is None:
            return
        try:
            self._destination_service.set(path)
        except Exception:
            pass
        try:
            ensure = getattr(self._destination_service, 'ensure', None)
            if callable(ensure):
                ensure(path)
        except Exception:
            pass
        self.notify_property(u'DestinationPath')

    # ------------------------------------------------------------------
    # Page Paramètres : toggles destination (sous-dossiers / formats séparés)
    # ------------------------------------------------------------------

    @property
    def CreerSousDossiers(self):
        """Reflète `DestinationService.get_create_subfolders()`.

        Best-effort : `False` si le service est absent ou lève (hors Revit
        sans injection, ou service factice minimal dans les tests)."""
        try:
            if self._destination_service is not None:
                return bool(self._destination_service.get_create_subfolders())
        except Exception:
            pass
        return False

    @CreerSousDossiers.setter
    def CreerSousDossiers(self, value):
        value = bool(value)
        if value == self.CreerSousDossiers:
            return
        try:
            if self._destination_service is not None:
                self._destination_service.set_create_subfolders(value)
        except Exception:
            pass
        self.notify_property(u'CreerSousDossiers')

    @property
    def SeparerFormats(self):
        """Reflète `DestinationService.get_separate_formats()` (dossiers
        distincts PDF/DWG à l'export) -- sans rapport avec les options
        `get_separate`/`pdf_separate_views` propres à PdfExporterService/
        DwgExporterService (export par vue séparée), volontairement non
        touchées ici."""
        try:
            if self._destination_service is not None:
                return bool(self._destination_service.get_separate_formats())
        except Exception:
            pass
        return False

    @SeparerFormats.setter
    def SeparerFormats(self, value):
        value = bool(value)
        if value == self.SeparerFormats:
            return
        try:
            if self._destination_service is not None:
                self._destination_service.set_separate_formats(value)
        except Exception:
            pass
        self.notify_property(u'SeparerFormats')

    # ------------------------------------------------------------------
    # Page Paramètres : sélecteurs de setup PDF / DWG
    # ------------------------------------------------------------------

    @property
    def SetupsPdf(self):
        """Liste des setups PDF disponibles (Revit + customs).

        Calculée À LA DEMANDE (pas de cache construit dans `__init__`,
        contrairement à `ParametresDisponibles`) : `list_all_setups(doc)`
        dépend potentiellement de l'état courant du document Revit, et le
        coût d'un appel API au moment du binding WPF est négligeable (pas
        de sondage répété). Ce choix permet aussi de refléter fidèlement
        un service devenu `None` en cours de vie (cf. tests)."""
        try:
            if self._pdf_service is not None:
                return list(self._pdf_service.list_all_setups(self._doc) or [])
        except Exception:
            pass
        return []

    @property
    def SetupPdf(self):
        try:
            if self._pdf_service is not None:
                return self._pdf_service.get_saved_setup(default=u'') or u''
        except Exception:
            pass
        return u''

    @SetupPdf.setter
    def SetupPdf(self, value):
        value = value or u''
        if value == self.SetupPdf:
            return
        try:
            if self._pdf_service is not None:
                self._pdf_service.set_saved_setup(value)
        except Exception:
            pass
        self.notify_property(u'SetupPdf')

    @property
    def SetupsDwg(self):
        """Cf. `SetupsPdf` : même choix (à la demande, non caché)."""
        try:
            if self._dwg_service is not None:
                return list(self._dwg_service.list_all_setups(self._doc) or [])
        except Exception:
            pass
        return []

    @property
    def SetupDwg(self):
        try:
            if self._dwg_service is not None:
                return self._dwg_service.get_saved_setup(default=u'') or u''
        except Exception:
            pass
        return u''

    @SetupDwg.setter
    def SetupDwg(self, value):
        value = value or u''
        if value == self.SetupDwg:
            return
        try:
            if self._dwg_service is not None:
                self._dwg_service.set_saved_setup(value)
        except Exception:
            pass
        self.notify_property(u'SetupDwg')

    # ------------------------------------------------------------------
    # Export (Task 3) : coordination VM -> ExportOrchestrator
    # ------------------------------------------------------------------

    @property
    def StatusText(self):
        return self._status_text

    @StatusText.setter
    def StatusText(self, value):
        self._status_text = value if value is not None else u''
        self.notify_property(u'StatusText')

    @property
    def ProgressValue(self):
        return self._progress_value

    @ProgressValue.setter
    def ProgressValue(self, value):
        try:
            v = int(value)
        except Exception:
            v = 0
        v = max(0, min(100, v))
        self._progress_value = v
        self.notify_property(u'ProgressValue')

    class _ComboShim(object):
        """Faux contrôle UI minimal : expose seulement `.SelectedItem`.

        `ExportOrchestrator._get_ui_selected_param_names` fait
        `str(getattr(ctrl, 'SelectedItem', None))` sur ce que renvoie
        `get_ctrl(name)`. Historiquement `get_ctrl` retournait une vraie
        ComboBox WPF (`.SelectedItem` = nom du paramètre choisi par
        l'utilisateur). Ce shim reproduit uniquement l'attribut consommé,
        sans dépendance WPF, pour que l'orchestrateur (non modifié) puisse
        lire le mapping paramètres depuis le VM.
        """

        def __init__(self, value):
            self.SelectedItem = value if value else u''

    def _get_ctrl_adapter(self):
        """Construit `get_ctrl(name)` à partir du mapping VM (ParamExport/
        ParamCarnet/ParamDwg), sans passer par des contrôles WPF réels.

        Adaptation choisie (la moins invasive après lecture de
        `ExportOrchestrator`) : l'orchestrateur n'a besoin, en dehors de
        `doc`, que des TROIS noms de paramètres Oui/Non (Export/Carnet/DWG)
        via `get_ctrl(name).SelectedItem`. Tout le reste (destination,
        patterns de nommage, setups PDF/DWG) est lu par l'orchestrateur
        lui-même depuis `UserConfig('batch_export')` — le MÊME namespace et
        les MÊMES clés que `DestinationService`/`NamingService` (Phase 2)
        utilisent pour persister (`PathDossier`, `pattern_sheet[_rows]`,
        `pattern_set[_rows]`, `create_subfolders`, `separate_format_folders`,
        etc.). Il n'y a donc pas besoin d'injecter `_destination_service`
        ni `_naming_service` dans l'orchestrateur : la configuration est
        déjà partagée de façon transparente via le namespace commun. Un
        adaptateur plus large (dict de config direct) aurait nécessité de
        modifier `ExportOrchestrator.run()` -- écarté au profit de ce petit
        shim purement local au VM.
        """
        mapping = {
            u'ExportationCombo': self.ParamExport,
            u'CarnetCombo': self.ParamCarnet,
            u'DWGCombo': self.ParamDwg,
        }

        def get_ctrl(name):
            return MainViewModel._ComboShim(mapping.get(name, u''))

        return get_ctrl

    def _on_export_progress(self, current, total, message=u''):
        try:
            total = max(int(total), 1)
        except Exception:
            total = 1
        try:
            current = int(current)
        except Exception:
            current = 0
        self.ProgressValue = int(100 * current / total)
        self.StatusText = message or u''

    def _on_export_log(self, message):
        self.StatusText = message or u''

    def lancer_export(self):
        """Lance l'export du mode « par jeu » via `ExportOrchestrator`.

        Hors Revit (`doc is None`) ou si l'orchestrateur est indisponible,
        ne lève jamais : `StatusText` reflète l'indisponibilité et la
        méthode retourne silencieusement. Toute exception levée pendant la
        construction/l'exécution de l'orchestrateur est absorbée (try/except)
        conformément aux conventions du projet (accès Revit protégé).
        """
        if self._doc is None:
            self.StatusText = u"Export indisponible (hors Revit)."
            return

        try:
            try:
                # Ordre d'import : `lib.services.core...` d'abord. Le module
                # `ExportOrchestrator` utilise des imports relatifs (`from
                # ...core.UserConfig`, `from ...data...`) qui ne résolvent
                # correctement QUE si son package est `lib.services.core`
                # (racine de package = `lib`). Importé comme
                # `services.core.ExportOrchestrator` (package racine =
                # `services`), les `...` remontent au-dessus de `lib` et
                # tous les try/except internes retombent sur None
                # (DestinationStore/NamingPatternStore/NamingResolver/
                # PdfExporterService = None) sans lever -- l'export
                # « fonctionnerait » silencieusement en mode dégradé
                # (dossier courant, sans options). D'où l'ordre inverse de
                # celui utilisé pour les autres services de ce fichier.
                from lib.services.core.ExportOrchestrator import ExportOrchestrator
            except Exception:
                from services.core.ExportOrchestrator import ExportOrchestrator
        except Exception:
            self.StatusText = u"Export indisponible (orchestrateur introuvable)."
            return

        try:
            orch = ExportOrchestrator()
        except Exception:
            self.StatusText = u"Export indisponible (initialisation impossible)."
            return

        # Détection best-effort du mode dégradé (imports internes retombés
        # sur None) : on prévient plutôt que d'exporter silencieusement
        # dans de mauvaises conditions.
        try:
            if getattr(orch, '_dest', None) is None:
                self.StatusText = u"Export indisponible (dépendances internes manquantes)."
                return
        except Exception:
            pass

        self.StatusText = u"Préparation de l'export..."
        self.ProgressValue = 0

        try:
            orch.run(
                self._doc,
                self._get_ctrl_adapter(),
                progress_cb=self._on_export_progress,
                log_cb=self._on_export_log,
            )
        except Exception as exc:
            try:
                self.StatusText = u"Erreur pendant l'export : {}".format(exc)
            except Exception:
                self.StatusText = u"Erreur pendant l'export."
            return
