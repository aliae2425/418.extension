# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import time

# Journal de diagnostic : le logger pyRevit écrit dans la fenêtre de sortie
# du script (et respecte le niveau de verbosité choisi par l'utilisateur).
# Hors Revit (tests standalone), `get_logger` est indisponible -> no-op.
try:
    from pyrevit import script as _pyrevit_script
    _LOGGER = _pyrevit_script.get_logger()
except Exception:
    _LOGGER = None

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

try:
    from services.formats.PdfExporterService import PdfExporterService
except Exception:
    try:
        from lib.services.formats.PdfExporterService import PdfExporterService
    except Exception:
        PdfExporterService = None  # type: ignore

try:
    from services.formats.DwgExporterService import DwgExporterService
except Exception:
    try:
        from lib.services.formats.DwgExporterService import DwgExporterService
    except Exception:
        DwgExporterService = None  # type: ignore

try:
    from core import bulk_edit
except Exception:
    try:
        from lib.core import bulk_edit
    except Exception:
        bulk_edit = None  # type: ignore

try:
    from core.list_selection import ListSelectionService
except Exception:
    try:
        from lib.core.list_selection import ListSelectionService
    except Exception:
        ListSelectionService = None  # type: ignore

# Items bindables (extraits dans viewmodels/items.py). Réexportés de fait par
# ce module : les tests les importent depuis MainViewModel de longue date.
try:
    from viewmodels.items import (SheetItemVM, CollectionItemVM,
                                  ManualSheetVM, FiltreItemVM)
except Exception:
    from lib.viewmodels.items import (SheetItemVM, CollectionItemVM,
                                      ManualSheetVM, FiltreItemVM)


_MODES = (u'auto', u'manual', u'settings')
_SURFACE_TITRES = {
    u'auto': u'Jeux à l\'export',
    u'manual': u'Sélection manuelle',
    u'settings': u'Paramètres',
}

# Badges « Par jeu » (export / carnet / dwg) persistés par titre de jeu, en
# JSON : {titre: [export, carnet, dwg]}. Une seule clé -- cf.
# `_charger_choix`/`_enregistrer_choix`.
_CFG_KEY_BADGES_JEUX = 'jeux_badges'

# Mode « feuille par feuille » : export combiné en un seul PDF + titre de ce
# PDF. Persistés via UserConfig (namespace 'batch_export'). Transmis à
# ExportOrchestrator.run_manual() par lancer_export_manuel().
_CFG_KEY_COMBINE_PDF = 'manual_combine_pdf'
_CFG_KEY_PDF_COMBINE_TITLE = 'manual_pdf_combine_title'


def _champ(source, cle, defaut=None):
    """Champ d'un descripteur de service, tolérant au non-dict.

    Les services rendent des dicts, mais les faux services des tests et les
    versions plus anciennes peuvent rendre autre chose : ce qui n'est pas un
    dict vaut `defaut` plutôt que de lever.
    """
    if isinstance(source, dict):
        return source.get(cle, defaut)
    return defaut


def _format_duree(secondes):
    """Secondes -> 'hh:mm:ss'. Au-delà de 24 h, les heures débordent (99:00:00)."""
    s = int(max(0, secondes))
    return u'{:02d}:{:02d}:{:02d}'.format(s // 3600, (s // 60) % 60, s % 60)


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
        # tester la persistance sans Revit.
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
        # écrivent via la MÊME instance UserConfig que le VM. Sinon chaque
        # service crée sa propre UserConfig via son propre import
        # (`core.UserConfig` vs `lib.core.UserConfig` = modules distincts) et
        # la destination ne partageait pas le chemin de config.
        # `SheetCollectionService` fait exception : purement en lecture du
        # document, il n'a aucune config à lire ni à écrire.
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

        # Données « par jeu » : liste unique, éditable (badges cliquables).
        # Les flags viennent UNIQUEMENT des clics de l'utilisateur, jamais du
        # document Revit.
        self._collections = []
        # Badges cochés, indexés par TITRE de jeu : {titre: (export, carnet,
        # dwg)}. Alimenté par `_on_collection_change`, relu par
        # `refresh_par_jeu`, persisté dans UserConfig (clé `jeux_badges`) donc
        # restauré à la réouverture de l'outil. Rien n'est jamais écrit dans
        # la maquette. Limite assumée de l'indexation par titre : un jeu
        # renommé dans Revit n'est plus reconnu et repart éteint.
        self._badges_jeux = self._charger_choix()

        # Export (Task 3) : retour visuel (progress_cb/log_cb de l'orchestrateur)
        self._status_text = u''
        self._progress_value = 0

        # Données « feuille par feuille » (mode manuel). Sélection ÉPHÉMÈRE :
        # reconstruite à chaque refresh_manuel(), jamais persistée.
        self._sheets_manuel = []
        self._selection_svc = (ListSelectionService(prop=u'Selected')
                               if ListSelectionService is not None else None)
        self._filtres_manuel = []
        self._recherche_manuel = u''
        # Préférence d'affichage (pas un état de sélection) : ne montrer que
        # les feuilles cochées PDF ou DWG. Survit à refresh_manuel().
        self._masquer_non_selectionnees = False
        self._on_export_done_cb = None
        # Durée du dernier export réussi, format hh:mm:ss (lue par la modale
        # de fin via le VM -- garde le callback à un seul argument).
        self.DureeExport = u'00:00:00'

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

        self._log_init_context()

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
        self._log(u'MODE', u'{} → {}'.format(self._mode, mode))
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
    # Persistance (UserConfig)
    # ------------------------------------------------------------------

    def _cfg_get(self, key, default=u''):
        try:
            return self._cfg.get(key, default) if self._cfg is not None else default
        except Exception:
            return default

    def _cfg_set(self, key, value):
        """Écrit une clé de config. Un échec est LOGGÉ, jamais avalé : une
        perte de réglage silencieuse est indiscernable d'un bug d'UI côté
        utilisateur (cf. « les badges ne persistent pas »). Ne lève toujours
        pas -- un réglage non sauvé ne doit pas casser l'outil."""
        try:
            if self._cfg is None:
                self._log(u'AVERT',
                    u'Config indisponible : "{}" non persisté'.format(key))
                return
            # `UserConfig.set` rend False quand l'écriture du fichier échoue
            # (les faux magasins des tests rendent None -> pas d'alerte).
            if self._cfg.set(key, value or u'') is False:
                self._log(u'AVERT',
                    u'Échec d\'écriture de la config : "{}"'.format(key))
        except Exception as exc:
            self._log(u'AVERT',
                u'Config "{}" non persistée : {}'.format(key, exc))

    def _charger_choix(self):
        """Relit les badges « Par jeu » persistés -> `{titre: (e, c, d)}`.

        `UserConfig.set` stringifie ce qu'on lui donne : la valeur est donc
        stockée en JSON explicite. Best-effort absolu -- clé absente, JSON
        corrompu, config absente ou entrée malformée (non itérable, longueur
        != 3) sont ignorés silencieusement, jamais d'exception à l'ouverture.
        """
        try:
            brut = self._cfg_get(_CFG_KEY_BADGES_JEUX, u'')
            charge = json.loads(brut) if brut else None
        except Exception:
            charge = None
        if not isinstance(charge, dict):
            return {}

        out = {}
        for titre, flags in charge.items():
            try:
                export, carnet, dwg = flags
            except Exception:
                continue
            out[titre] = (bool(export), bool(carnet), bool(dwg))
        return out

    def _enregistrer_choix(self):
        """Persiste `self._badges_jeux` en JSON. Ne lève jamais, mais logge.

        `ensure_ascii=False` est OBLIGATOIRE, pas cosmétique : sous IronPython
        2.7 (le moteur pyRevit), `str is unicode`, donc l'encodeur ASCII de
        `json` prend systématiquement la branche « octets » et tente un
        `.decode('utf-8')` sur la chaîne -- qui lève sur le moindre accent
        (« 0xE9 ... from specified code page »). Tout jeu au titre accentué
        (« 1.06_Détails ») faisait donc échouer la sauvegarde des badges.
        `UserConfig` écrit déjà le fichier en UTF-8 avec `ensure_ascii=False` :
        les accents y sont stockés littéralement, c'est la même convention.
        """
        try:
            self._cfg_set(_CFG_KEY_BADGES_JEUX,
                          json.dumps(dict(
                              (t, list(v)) for t, v in self._badges_jeux.items()),
                              ensure_ascii=False))
        except Exception as exc:
            self._log(u'AVERT', u'Badges non persistés : {}'.format(exc))

    def get_naming_params(self):
        """Liste des noms de paramètres utilisables pour le nommage des
        fichiers exportés (modale NamingEditorView), best-effort.

        Combine les paramètres d'instance de feuille (`ViewSheet`) et les
        paramètres projet (`ProjectInfo`) via `SheetParameterRepository`
        (legacy), dédoublonnés en conservant l'ordre d'apparition
        (feuilles d'abord, puis projet). Injecte `self._cfg` (config
        partagée du VM) au repository -- `SheetParameterRepository._get_cfg`
        retourne alors directement cette instance au lieu d'en créer une.

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

    def _charger_motif(self, genre):
        """Motif de nommage `(pattern, rows)` d'un genre, ('', []) si échec."""
        if self._naming_service is None:
            return u'', []
        try:
            return self._naming_service.load(genre)
        except Exception:
            return u'', []

    def _resoudre_nom(self, elem, motif):
        """Nom projeté d'un élément selon `motif`, vide si non résolvable."""
        if self._naming_service is None or elem is None or not motif:
            return u''
        try:
            return self._naming_service.resolve_for_element(elem, motif) or u''
        except Exception:
            return u''

    def refresh_par_jeu(self):
        """Construit `self._collections` à partir des services injectés.

        Contrat attendu pour `sheet_service` (réel ou faux, pour tests
        hors Revit) :
          - `list_collections()` -> liste de dicts contenant au moins
            `'Titre'`, `'Id'`, et **`'Elem'`** (élément Revit brut, ou tout
            objet substitut dans les tests) permettant de résoudre le motif
            de nommage du carnet.
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

        Les badges (export / carnet / DWG) ne sont PAS lus dans le document :
        ils viennent de `self._badges_jeux` (persisté par titre de jeu), et un
        jeu inconnu part donc tout éteint.

        `naming_service` : `load('sheet')` -> `(pattern, rows)` ;
        `resolve_for_element(elem, rows)` -> unicode.
        """
        collections_out = []

        _pattern, rows_sheet = self._charger_motif('sheet')

        # Motif carnet ('set') hissé une fois (comme _pattern/rows_sheet pour
        # les feuilles), résolu par collection pour l'aperçu du titre de carnet.
        _set_pattern, set_rows = self._charger_motif('set')

        raw_collections = []
        if self._sheet_service is not None:
            try:
                raw_collections = self._sheet_service.list_collections() or []
            except Exception:
                raw_collections = []

        for coll in raw_collections:
            titre = _champ(coll, 'Titre', u'')
            coll_id = _champ(coll, 'Id')
            coll_elem = _champ(coll, 'Elem')

            sheets_out = []
            raw_sheets = []
            if self._sheet_service is not None:
                try:
                    raw_sheets = self._sheet_service.list_sheets(coll_id) or []
                except Exception:
                    raw_sheets = []

            for sheet in raw_sheets:
                numero = _champ(sheet, 'Numero', u'')
                nom = _champ(sheet, 'Nom', u'')
                sheet_elem = _champ(sheet, 'Elem')

                nom_projete = self._resoudre_nom(sheet_elem,
                                                 _pattern or rows_sheet)
                if not nom_projete:
                    nom_projete = u"{}{}".format(numero, nom)

                sheets_out.append(SheetItemVM(numero, nom, nom_projete))

            # Aperçu du titre de carnet : motif `set` résolu contre l'élément
            # de collection + `.pdf` (extension du fichier produit à l'export).
            resolved = self._resoudre_nom(coll_elem, _set_pattern or set_rows)
            carnet_apercu = (resolved + u'.pdf') if resolved else u''

            # Badges : uniquement ce que l'utilisateur a coché (persisté par
            # titre de jeu, cf. `_badges_jeux`). `refresh_par_jeu()` est
            # ré-appelé en cours de session (retour de la modale de nommage) et
            # doit donc reporter ces choix. Jeu inconnu -> tout éteint.
            flag_export, flag_carnet, flag_dwg = self._badges_jeux.get(
                titre, (False, False, False))

            collections_out.append(CollectionItemVM(
                titre, coll_id, flag_export, flag_carnet, flag_dwg, sheets_out,
                carnet_apercu=carnet_apercu,
                on_change=self._on_collection_change,
            ))

        # Tri (stable) : collections QUALIFIÉES (FlagExport=True) d'abord,
        # puis alphabétique du Titre (insensible à la casse) au sein de
        # chaque groupe. `sorted()` est stable en Python -> l'ordre relatif
        # d'items à clé égale (même Qualified, même Titre) est préservé.
        collections_out = sorted(
            collections_out,
            key=lambda c: (not c.Qualified, (c.Titre or u'').lower()))

        self._collections = collections_out

        # Chiffres du LOG : état courant des badges.
        nb_jeux_qualifies = len([c for c in collections_out if c.Qualified])
        nb_feuilles_qualifiees = sum(
            len(c.Sheets) for c in collections_out if c.Qualified)

        # Log du résultat du refresh
        self._log(u'AUTO',
            u'refresh_par_jeu : {} jeux trouvés, {} qualifiés, {} feuilles qualifiées'.format(
                len(collections_out), nb_jeux_qualifies, nb_feuilles_qualifiees))
        for c in collections_out:
            etat = u'QUALIFIE' if c.Qualified else u'ignoré  '
            self._log(u'AUTO',
                u'  [{}] "{}" → Export={} Carnet={} DWG={} ({} feuilles)'.format(
                    etat, c.Titre, c.FlagExport, c.FlagCarnet, c.FlagDwg,
                    len(c.Sheets)))
        # Seul le document SANS aucun jeu de feuilles est une anomalie. « 0 jeu
        # coché » est l'état normal d'une première ouverture (les badges sont
        # persistés, pas déduits du document) : le signaler en AVERT affichait
        # un rouge dans la sortie pyRevit à chaque lancement.
        if not collections_out:
            self._log(u'AVERT',
                u'  Aucune SheetCollection dans ce document '
                u'(vérifiez que le projet utilise des Jeux de feuilles Revit)')

        # Les badges sont mémorisés par TITRE de jeu, dans une config commune à
        # tous les documents. Des badges mémorisés dont aucun titre n'existe ici
        # = autre projet, ou jeu renommé : le dire, sinon l'utilisateur ne voit
        # qu'un « ça ne persiste pas » sans cause.
        titres_doc = [c.Titre for c in collections_out]
        if collections_out and self._badges_jeux and not any(
                t in self._badges_jeux for t in titres_doc):
            self._log(u'AVERT',
                u'  Badges mémorisés pour {} : aucun jeu de ce document ne '
                u'correspond (jeux ici : {}). Renommage de jeu ou autre projet '
                u'-> les badges repartent éteints.'.format(
                    u', '.join(sorted(self._badges_jeux)),
                    u', '.join(titres_doc)))

        for name in (u'Collections', u'NbJeuxQualifies',
                     u'NbFeuillesQualifiees'):
            self.notify_property(name)

    def _on_collection_change(self, item):
        """Callback passé à chaque `CollectionItemVM` : un clic sur un badge
        change la qualification, donc les deux compteurs de l'en-tête.

        Mémorise aussi le choix, par titre de jeu, pour que `refresh_par_jeu()`
        le reporte, et le persiste aussitôt (UserConfig) : les badges cochés
        reviennent à la réouverture de l'outil."""
        try:
            self._badges_jeux[item.Titre] = (
                item.FlagExport, item.FlagCarnet, item.FlagDwg)
            self._log(u'CONFIG', u'Badge "{}" -> Export={} Carnet={} DWG={}'.format(
                item.Titre, item.FlagExport, item.FlagCarnet, item.FlagDwg))
        except Exception as exc:
            self._log(u'AVERT', u'Badge non mémorisé : {}'.format(exc))
        self._enregistrer_choix()
        for name in (u'NbJeuxQualifies', u'NbFeuillesQualifiees'):
            self.notify_property(name)

    @property
    def Collections(self):
        return self._collections

    @property
    def NbJeuxQualifies(self):
        return len([c for c in self._collections if c.Qualified])

    @property
    def NbFeuillesQualifiees(self):
        return sum(len(c.Sheets) for c in self._collections if c.Qualified)

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
        `ManualSheetVM` (défauts `ExportPdf=False`/`ExportDwg=False` : rien
        n'est coché à l'ouverture, l'utilisateur choisit ; « Tout PDF »
        reste là pour tout activer d'un clic) et les
        `FiltreItemVM` (défaut `IsActif=False` : aucun filtre actif ->
        toutes les feuilles visibles), sans tenter de préserver l'état
        précédent.

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
            titre = _champ(coll, 'Titre', u'')
            coll_id = _champ(coll, 'Id')
            collections_titres[coll_id] = titre or u''
        self._collections_titres = collections_titres

        _pattern, rows_sheet = self._charger_motif('sheet')

        raw_sheets = []
        if self._sheet_service is not None:
            try:
                raw_sheets = self._sheet_service.list_all_sheets() or []
            except Exception:
                raw_sheets = []

        sheets_out = []
        for sheet in raw_sheets:
            numero = _champ(sheet, 'Numero', u'')
            nom = _champ(sheet, 'Nom', u'')
            coll_id = _champ(sheet, 'CollectionId')
            elem = _champ(sheet, 'Elem')

            jeu_nom = collections_titres.get(coll_id, u'') or u''

            nom_projete = self._resoudre_nom(elem, _pattern or rows_sheet)

            sheets_out.append(ManualSheetVM(
                numero, nom, collection_id=coll_id, elem=elem,
                export_pdf=False, export_dwg=False,
                jeu_nom=jeu_nom, nom_projete=nom_projete,
                on_change=self._on_manual_sheet_change,
                on_format_change=self._on_format_propagate,
            ))
        self._sheets_manuel = sheets_out

        filtres_out = []
        for coll in raw_collections:
            titre = _champ(coll, 'Titre', u'')
            coll_id = _champ(coll, 'Id')
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
            nom = _champ(vss, 'Nom', u'')
            sheet_ids = _champ(vss, 'SheetIds')
            filtres_out.append(FiltreItemVM(
                u'Impression : ' + (nom or u''), u'set', sheet_ids=sheet_ids,
                on_change=self._on_filtre_change,
            ))

        self._filtres_manuel = filtres_out

        if self._selection_svc is not None:
            try:
                self._selection_svc.reset()
            except Exception:
                pass

        self.refresh_patterns_apercu()

        self._log(u'MANUEL',
            u'refresh_manuel : {} feuilles, {} filtres ({} jeux + {} sets impression)'.format(
                len(sheets_out), len(filtres_out), len(raw_collections), len(raw_sets)))
        if not sheets_out:
            self._log(u'AVERT', u'  Aucune feuille trouvée dans le document')

        for name in (u'SheetsManuel', u'FiltresManuel',
                     u'SheetsManuelFiltrees', u'NbFeuillesManuel', u'NbPdf',
                     u'NbDwg', u'FiltresResume'):
            self.notify_property(name)

    def _on_manual_sheet_change(self):
        """Callback passé à chaque `ManualSheetVM` : un toggle ExportPdf/
        ExportDwg/Selected impacte les compteurs (calculés à la volée sur
        les feuilles FILTRÉES), jamais la liste ni les filtres eux-mêmes.

        Exception : si `MasquerNonSelectionnees` est actif, décocher le
        dernier format d'une ligne la fait sortir de la liste visible -> il
        faut aussi notifier celle-ci."""
        noms = [u'NbPdf', u'NbDwg', u'NbSelected']
        if self._masquer_non_selectionnees:
            noms += [u'SheetsManuelFiltrees', u'NbFeuillesManuel']
        for name in noms:
            self.notify_property(name)

    def _on_format_propagate(self, source, prop, value):
        """Propage `prop=value` à toute la sélection si `source` est sélectionné.

        Déclenché par `ManualSheetVM.on_format_change` (ExportPdf/ExportDwg
        uniquement). Le guard dans chaque setter (``if value == self._xxx: return``)
        assure la convergence et évite les boucles infinies.
        """
        if not getattr(source, u'Selected', False):
            return
        if bulk_edit is None:
            return
        selected = bulk_edit.get_selected(self.SheetsManuelFiltrees)
        for item in selected:
            if item is not source:
                try:
                    setattr(item, prop, value)
                except Exception:
                    pass

    def _on_filtre_change(self):
        """Callback passé à chaque `FiltreItemVM` : un toggle `IsActif`
        recalcule `SheetsManuelFiltrees` et les compteurs (union OU sur les
        filtres actifs -- voir `SheetsManuelFiltrees`), ainsi que le résumé
        affiché sur le ToggleButton du menu déroulant (`FiltresResume`)."""
        if self._selection_svc is not None:
            try:
                self._selection_svc.reset()
            except Exception:
                pass
        for name in (u'SheetsManuelFiltrees', u'NbFeuillesManuel', u'NbPdf',
                     u'NbDwg', u'FiltresResume'):
            self.notify_property(name)

    @property
    def SheetsManuel(self):
        return self._sheets_manuel

    @property
    def FiltresManuel(self):
        return self._filtres_manuel

    @property
    def FiltresResume(self):
        """Texte de résumé affiché dans le ToggleButton du menu déroulant de
        filtres (mode manuel) : nombre de filtres actifs, ou un texte
        générique si aucun -- il n'y a pas de sélection UNIQUE à refléter
        (multi-filtre, cf. `SheetsManuelFiltrees`)."""
        n = len([f for f in self._filtres_manuel if f.IsActif])
        if n <= 0:
            return u'Filtres'
        if n == 1:
            return u'1 filtre actif'
        return u'{} filtres actifs'.format(n)

    @property
    def RechercheManuel(self):
        return self._recherche_manuel

    @RechercheManuel.setter
    def RechercheManuel(self, value):
        value = value or u''
        if value == self._recherche_manuel:
            return
        self._recherche_manuel = value
        if self._selection_svc is not None:
            try:
                self._selection_svc.reset()
            except Exception:
                pass
        for name in (u'RechercheManuel', u'SheetsManuelFiltrees',
                     u'NbFeuillesManuel', u'NbPdf', u'NbDwg'):
            self.notify_property(name)

    @property
    def MasquerNonSelectionnees(self):
        """N'afficher que les feuilles cochées PDF ou DWG (case de la barre
        d'état, mode manuel). Éphémère comme le reste de l'état manuel."""
        return self._masquer_non_selectionnees

    @MasquerNonSelectionnees.setter
    def MasquerNonSelectionnees(self, value):
        value = bool(value)
        if value == self._masquer_non_selectionnees:
            return
        self._masquer_non_selectionnees = value
        if self._selection_svc is not None:
            try:
                self._selection_svc.reset()
            except Exception:
                pass
        for name in (u'MasquerNonSelectionnees', u'SheetsManuelFiltrees',
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
        actif (union OU), via `_sheet_matches_filtre`.

        `MasquerNonSelectionnees` retire en plus les feuilles sans aucun
        format coché."""
        recherche = (self._recherche_manuel or u'').strip().lower()
        filtres_actifs = [f for f in self._filtres_manuel if f.IsActif]
        out = []
        for sheet in self._sheets_manuel:
            if self._masquer_non_selectionnees and not (sheet.ExportPdf or sheet.ExportDwg):
                continue
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
        """Nombre de feuilles sélectionnées (Selected=True) parmi les feuilles filtrées."""
        return len([s for s in self.SheetsManuelFiltrees if s.Selected])

    def selection_manuelle(self):
        """Retourne les `ManualSheetVM` cochées (ExportPdf OU ExportDwg),
        pour un futur export.

        Porte sur `SheetsManuelFiltrees` (feuilles VISIBLES), pas sur
        `self._sheets_manuel` : balayer la liste entière exporterait des
        feuilles masquées par le filtre/la recherche affichés (typiquement
        après un « Tout PDF » puis un changement de filtre). Ce qui est à
        l'écran est ce qui est exporté.

        Le critère reste UNIQUEMENT les cases de format ExportPdf/ExportDwg
        (pas de case de sélection de ligne dédiée -- retirée car redondante,
        cf. docstring de `ManualSheetVM`)."""
        return [s for s in self.SheetsManuelFiltrees if s.ExportPdf or s.ExportDwg]

    # ------------------------------------------------------------------
    # Édition en masse (boutons « Tout PDF » / « Tout DWG »)
    # ------------------------------------------------------------------

    def toggle_all_pdf(self):
        """Bascule ExportPdf sur TOUTES les feuilles filtrées (tout ON → OFF, sinon → ON)."""
        if bulk_edit is None:
            return
        bulk_edit.toggle(self.SheetsManuelFiltrees, u'ExportPdf')

    def toggle_all_dwg(self):
        """Bascule ExportDwg sur TOUTES les feuilles filtrées (tout ON → OFF, sinon → ON)."""
        if bulk_edit is None:
            return
        bulk_edit.toggle(self.SheetsManuelFiltrees, u'ExportDwg')

    def handle_row_click(self, index, shift=False, ctrl=False):
        """Délègue la sélection multi-items à `ListSelectionService`."""
        if self._selection_svc is None:
            return
        self._selection_svc.handle_click(
            self.SheetsManuelFiltrees, index, shift=shift, ctrl=ctrl)

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
        self._log(u'CONFIG', u'Destination : "{}" → "{}"'.format(self.DestinationPath, path))
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
    # Mode « feuille par feuille » : PDF combiné (UI + persistance seulement)
    # ------------------------------------------------------------------

    @property
    def CombinerPdf(self):
        """Mode manuel : fusionner les feuilles sélectionnées en un seul PDF.

        Persisté via UserConfig. Transmis à `ExportOrchestrator.run_manual()`
        par `lancer_export_manuel()` pour piloter l'export combiné."""
        return self._cfg_get(_CFG_KEY_COMBINE_PDF, u'0') == u'1'

    @CombinerPdf.setter
    def CombinerPdf(self, value):
        value = bool(value)
        if value == self.CombinerPdf:
            return
        self._cfg_set(_CFG_KEY_COMBINE_PDF, u'1' if value else u'0')
        self.notify_property(u'CombinerPdf')

    @property
    def TitrePdfCombine(self):
        """Titre du PDF combiné (mode manuel). Pertinent uniquement si
        `CombinerPdf` est vrai ; le champ est désactivé sinon côté UI
        (IsEnabled lié à `CombinerPdf`)."""
        return self._cfg_get(_CFG_KEY_PDF_COMBINE_TITLE, u'')

    @TitrePdfCombine.setter
    def TitrePdfCombine(self, value):
        value = value or u''
        if value == self.TitrePdfCombine:
            return
        self._cfg_set(_CFG_KEY_PDF_COMBINE_TITLE, value)
        self.notify_property(u'TitrePdfCombine')

    # ------------------------------------------------------------------
    # Page Paramètres : sélecteurs de setup PDF / DWG
    # ------------------------------------------------------------------

    @property
    def SetupsPdf(self):
        """Liste des setups PDF disponibles (Revit + customs).

        Calculée À LA DEMANDE (pas de cache construit dans `__init__`) :
        `list_all_setups(doc)`
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
        self._log(u'CONFIG', u'SetupPdf : "{}" → "{}"'.format(self.SetupPdf, value))
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
        self._log(u'CONFIG', u'SetupDwg : "{}" → "{}"'.format(self.SetupDwg, value))
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

    # ------------------------------------------------------------------
    # Log de session (diagnostic complet : actions UI + export)
    # ------------------------------------------------------------------

    def _log(self, category, message):
        """Journalise `[CATEGORIE] message` via le logger pyRevit.

        AVERT/ERREUR passent en warning/error pour ressortir dans la fenêtre
        de sortie ; le reste est du debug (masqué sauf mode verbeux).
        """
        if _LOGGER is None:
            return
        try:
            ligne = u'[{}] {}'.format(category, message or u'')
            if category == u'ERREUR':
                _LOGGER.error(ligne)
            elif category == u'AVERT':
                _LOGGER.warning(ligne)
            elif category in (u'INIT', u'CONFIG'):
                # Contexte d'ouverture et changements de réglage : les seuls
                # diagnostics utiles sans mode verbeux (p.ex. « les badges ne
                # reviennent pas ») -> info, visible dans la sortie pyRevit.
                _LOGGER.info(ligne)
            else:
                _LOGGER.debug(ligne)
        except Exception:
            pass

    def _log_init_context(self):
        """Log le contexte complet au démarrage de la session."""
        try:
            doc_title = u'(aucun doc)'
            if self._doc is not None:
                try:
                    doc_title = self._doc.Title
                except Exception:
                    doc_title = u'(doc inconnu)'
            self._log(u'INIT', u'Document   : "{}"'.format(doc_title))
            self._log(u'INIT', u'Mode       : {}'.format(self._mode))
            self._log(u'INIT', u'BadgesJeux : {} jeu(x) mémorisé(s) -> {}'.format(
                len(self._badges_jeux),
                u', '.join(sorted(self._badges_jeux)) or u'(aucun)'))
            self._log(u'INIT', u'Destination: "{}"'.format(self.DestinationPath))
            self._log(u'INIT', u'SetupPdf   : "{}" | SetupDwg: "{}"'.format(
                self.SetupPdf, self.SetupDwg))
            self._log(u'INIT', u'CombinerPdf: {} | TitrePdf: "{}"'.format(
                self.CombinerPdf, self.TitrePdfCombine))
            self._log(u'INIT', u'SousDossiers: {} | FormatsSepar: {}'.format(
                self.CreerSousDossiers, self.SeparerFormats))
        except Exception:
            pass

    def _make_export_callbacks_with_log(self):
        """Retourne (progress_cb, log_cb) qui alimentent StatusText ET le log de session."""
        def progress_cb(current, total, message=u''):
            self._on_export_progress(current, total, message)
            self._log(u'PROGRESS', u'[{}/{}] {}'.format(current, total, message or u''))

        def log_cb(message):
            self._on_export_log(message)
            self._log(u'LOG', message)

        return progress_cb, log_cb

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

    def _creer_orchestrateur(self):
        """Retourne un `ExportOrchestrator` prêt à l'emploi, ou None si
        indisponible (StatusText renseigné, jamais d'exception).

        La config partagée du VM est INJECTÉE : l'orchestrateur doit lire les
        MÊMES flags de séparation et motifs de nommage que ceux persistés par
        le VM/la modale (sinon il lit sa propre config '<absent>').
        """
        try:
            from services.ExportOrchestrator import ExportOrchestrator
        except Exception:
            try:
                from lib.services.ExportOrchestrator import ExportOrchestrator
            except Exception:
                self.StatusText = u"Export indisponible (orchestrateur introuvable)."
                return None

        try:
            orch = ExportOrchestrator(config=self._cfg)
        except Exception:
            self.StatusText = u"Export indisponible (initialisation impossible)."
            return None

        erreur = orch.erreur_dependances()
        if erreur:
            self.StatusText = erreur
            self._log(u'ERREUR', erreur)
            return None
        return orch

    def lancer_export(self):
        """Dispatch par mode : délègue à `lancer_export_manuel()` en mode
        manuel, ou lance l'export « par jeu » via `ExportOrchestrator.run()`.

        Les plans viennent TOUJOURS des badges cochés dans l'UI (`flags`),
        jamais d'une relecture des paramètres Revit.

        Ne lève jamais hors Revit : `StatusText` reflète l'indisponibilité.
        """
        if self._mode == u'manual':
            self.lancer_export_manuel()
            return

        if self._doc is None:
            self.StatusText = u"Export indisponible (hors Revit)."
            return

        orch = self._creer_orchestrateur()
        if orch is None:
            return

        self.StatusText = u"Préparation de l'export..."
        self.ProgressValue = 0

        # Badges cochés dans l'onglet « Par jeu » : (titre, export, carnet,
        # dwg) par jeu. Seule source de qualification de l'export.
        flags = [(c.Titre, c.FlagExport, c.FlagCarnet, c.FlagDwg)
                 for c in self._collections]

        # --- Log config complète avant lancement ---
        self._log(u'EXPORT', u'--- Export PAR JEU lancé ---')
        self._log(u'EXPORT',
            u'Seuls les badges cochés pilotent l\'export '
            u'(aucune lecture ni écriture de paramètres dans la maquette).')
        self._log(u'EXPORT', u'Destination="{}" | SousDossiers={} | FormatsSepar={}'.format(
            self.DestinationPath, self.CreerSousDossiers, self.SeparerFormats))
        self._log(u'EXPORT', u'SetupPdf="{}" | SetupDwg="{}"'.format(
            self.SetupPdf, self.SetupDwg))

        # --- Plan prévisionnel : ce que le programme va faire ---
        try:
            self._log(u'PLAN', u'{} jeux analysés :'.format(len(flags)))
            for titre, f_export, f_carnet, f_dwg in flags:
                etat = u'EXPORT' if f_export else u'IGNORE'
                self._log(u'PLAN',
                    u'  [{}] "{}" → PDF={} DWG={} par_feuille={}'.format(
                        etat, titre, bool(f_export), bool(f_dwg),
                        not bool(f_carnet)))
            if not any(f[1] for f in flags):
                self._log(u'AVERT', u'  → Aucun jeu coché dans l\'onglet Par jeu'
                          if flags else u'  → Aucun jeu dans le document')
        except Exception as _pe:
            self._log(u'PLAN', u'Erreur calcul plan : {}'.format(_pe))

        progress_cb, log_cb = self._make_export_callbacks_with_log()

        _t0 = time.time()
        _export_ok = False
        try:
            # `run()` rend False si l'utilisateur a arrêté l'export sur un
            # fichier existant -> pas de modale de fin, StatusText conserve
            # le message posé par log_cb.
            _export_ok = orch.run(
                self._doc,
                flags,
                progress_cb=progress_cb,
                log_cb=log_cb,
                destination=self.DestinationPath,
            ) is not False
        except Exception as exc:
            try:
                msg = u"Erreur pendant l'export : {}".format(exc)
            except Exception:
                msg = u"Erreur pendant l'export."
            self.StatusText = msg
            self._log(u'ERREUR', msg)

        self.DureeExport = _format_duree(time.time() - _t0)
        self._log(u'EXPORT', u'--- Fin export PAR JEU ({}) ---'.format(
            self.DureeExport))
        if _export_ok:
            self.StatusText = u''
            if callable(self._on_export_done_cb):
                try:
                    self._on_export_done_cb(self.DestinationPath)
                except Exception:
                    pass

    def lancer_export_manuel(self):
        """Lance l'export « feuille par feuille » via `ExportOrchestrator.run_manual()`.

        Lit `selection_manuelle()` (feuilles cochées ExportPdf ou ExportDwg),
        transmet `CombinerPdf` et `TitrePdfCombine` à l'orchestrateur.
        Ne lève jamais : StatusText reflète toute indisponibilité ou erreur.
        """
        if self._doc is None:
            self.StatusText = u"Export indisponible (hors Revit)."
            return

        selection = self.selection_manuelle()
        if not selection:
            self.StatusText = u"Aucune feuille sélectionnée."
            return

        orch = self._creer_orchestrateur()
        if orch is None:
            return

        self.StatusText = u"Préparation de l'export..."
        self.ProgressValue = 0

        # --- Log config + sélection complète avant lancement ---
        n_pdf = len([s for s in selection if s.ExportPdf])
        n_dwg = len([s for s in selection if s.ExportDwg])
        self._log(u'EXPORT', u'--- Export MANUEL lancé ---')
        self._log(u'EXPORT', u'{} feuilles sélectionnées : {} PDF, {} DWG'.format(
            len(selection), n_pdf, n_dwg))
        self._log(u'EXPORT', u'CombinerPdf={} | TitrePdf="{}"'.format(
            self.CombinerPdf, self.TitrePdfCombine))
        self._log(u'EXPORT', u'Destination="{}" | SetupPdf="{}" | SetupDwg="{}"'.format(
            self.DestinationPath, self.SetupPdf, self.SetupDwg))
        for s in selection:
            elem_ok = u'Elem=OK' if s.Elem is not None else u'Elem=NULL!'
            self._log(u'SÉLECT',
                u'  {} | "{}" | Jeu:"{}" | PDF:{} DWG:{} | {}'.format(
                    s.Numero, s.Nom, s.JeuNom, s.ExportPdf, s.ExportDwg, elem_ok))

        progress_cb, log_cb = self._make_export_callbacks_with_log()

        _t0 = time.time()
        _export_ok = False
        try:
            # Cf. lancer_export() : False = arrêté sur un fichier existant.
            _export_ok = orch.run_manual(
                self._doc,
                selection,
                combine_pdf=self.CombinerPdf,
                pdf_title=self.TitrePdfCombine,
                progress_cb=progress_cb,
                log_cb=log_cb,
                destination=self.DestinationPath,
            ) is not False
        except Exception as exc:
            try:
                msg = u"Erreur pendant l'export : {}".format(exc)
            except Exception:
                msg = u"Erreur pendant l'export."
            self.StatusText = msg
            self._log(u'ERREUR', msg)

        self.DureeExport = _format_duree(time.time() - _t0)
        self._log(u'EXPORT', u'--- Fin export MANUEL ({}) ---'.format(self.DureeExport))
        if _export_ok:
            self.StatusText = u''
            if callable(self._on_export_done_cb):
                try:
                    self._on_export_done_cb(self.DestinationPath)
                except Exception:
                    pass
