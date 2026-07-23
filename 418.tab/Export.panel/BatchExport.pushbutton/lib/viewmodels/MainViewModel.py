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


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None, sheet_service=None, naming_service=None,
                 destination_service=None, config=None):
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
        if sheet_service is not None:
            self._sheet_service = sheet_service
        else:
            try:
                self._sheet_service = SheetCollectionService(doc) if SheetCollectionService is not None else None
            except Exception:
                self._sheet_service = None

        if naming_service is not None:
            self._naming_service = naming_service
        else:
            try:
                self._naming_service = NamingService(doc) if NamingService is not None else None
            except Exception:
                self._naming_service = None

        if destination_service is not None:
            self._destination_service = destination_service
        else:
            try:
                self._destination_service = DestinationService(doc) if DestinationService is not None else None
            except Exception:
                self._destination_service = None

        # Données « par jeu »
        self._collections = []
        self._nb_jeux_qualifies = 0
        self._nb_feuilles_qualifiees = 0

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
                     u'IsSettings', u'SurfaceTitre'):
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
        self._cfg_set(_CFG_KEY_PARAM_EXPORT, value)
        self.notify_property(u'ParamExport')

    @property
    def ParamCarnet(self):
        return self._cfg_get(_CFG_KEY_PARAM_CARNET, u'')

    @ParamCarnet.setter
    def ParamCarnet(self, value):
        self._cfg_set(_CFG_KEY_PARAM_CARNET, value)
        self.notify_property(u'ParamCarnet')

    @property
    def ParamDwg(self):
        return self._cfg_get(_CFG_KEY_PARAM_DWG, u'')

    @ParamDwg.setter
    def ParamDwg(self, value):
        self._cfg_set(_CFG_KEY_PARAM_DWG, value)
        self.notify_property(u'ParamDwg')

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

        rows_sheet = []
        if self._naming_service is not None:
            try:
                _pattern, rows_sheet = self._naming_service.load('sheet')
            except Exception:
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
                if self._naming_service is not None and sheet_elem is not None and rows_sheet:
                    try:
                        nom_projete = self._naming_service.resolve_for_element(sheet_elem, rows_sheet) or u''
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
