# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

# Isole la persistance UserConfig dans un dossier temporaire (jamais le config réel).
import tempfile as _tf
os.environ['PY418_CONFIG_DIR'] = _tf.mkdtemp(prefix='418test_')

from lib.viewmodels.MainViewModel import (MainViewModel, ManualSheetVM, FiltreItemVM,
                                          CollectionItemVM, _format_duree)


class TestFormatDuree(unittest.TestCase):
    """Durée affichée dans la modale de fin d'export : toujours hh:mm:ss."""

    def test_formats(self):
        self.assertEqual(_format_duree(0), u'00:00:00')
        self.assertEqual(_format_duree(59.9), u'00:00:59')
        self.assertEqual(_format_duree(60), u'00:01:00')
        self.assertEqual(_format_duree(3661), u'01:01:01')
        self.assertEqual(_format_duree(86400), u'24:00:00')
        self.assertEqual(_format_duree(-5), u'00:00:00')

    def test_duree_renseignee_apres_export_manuel(self):
        vm = MainViewModel(
            doc=object(),
            sheet_service=FakeSheetService(),
            naming_service=FakeNamingService(),
            destination_service=FakeDestinationService(u'C:/Test'),
            config=FakeConfig(),
        )
        vm._sheets_manuel = [ManualSheetVM(u'01', u'Feuille 1', export_pdf=True)]
        vm.lancer_export_manuel()
        h, m, s = vm.DureeExport.split(u':')
        self.assertTrue(len(h) == len(m) == len(s) == 2)
        self.assertTrue((h + m + s).isdigit())


class TestMainViewModel(unittest.TestCase):
    def setUp(self):
        self.vm = MainViewModel(doc=None)

    def test_titre(self):
        self.assertEqual(self.vm.Titre, u'Exportation')

    def test_mode_par_defaut_auto(self):
        self.assertEqual(self.vm.ActiveMode, u'auto')
        self.assertTrue(self.vm.IsAuto)
        self.assertFalse(self.vm.IsManual)
        self.assertFalse(self.vm.IsSettings)

    def test_set_mode_manual(self):
        self.vm.set_mode(u'manual')
        self.assertEqual(self.vm.ActiveMode, u'manual')
        self.assertTrue(self.vm.IsManual)
        self.assertFalse(self.vm.IsAuto)

    def test_set_mode_invalide_ignore(self):
        self.vm.set_mode(u'auto')
        self.vm.set_mode(u'zzz')
        self.assertEqual(self.vm.ActiveMode, u'auto')

    def test_surface_titre_change_selon_mode(self):
        self.vm.set_mode(u'auto')
        self.assertIn(u'jeu', self.vm.SurfaceTitre.lower())
        self.vm.set_mode(u'settings')
        self.assertEqual(self.vm.SurfaceTitre, u'Paramètres')

    def test_is_not_auto(self):
        self.vm.set_mode(u'auto')
        self.assertFalse(self.vm.IsNotAuto)
        self.vm.set_mode(u'manual')
        self.assertTrue(self.vm.IsNotAuto)
        self.vm.set_mode(u'settings')
        self.assertTrue(self.vm.IsNotAuto)


# ----------------------------------------------------------------------
# Faux services (permettent de tester refresh_par_jeu() hors Revit)
# ----------------------------------------------------------------------

class FakeConfig(object):
    """Faux UserConfig en mémoire (même contrat get/set). Nécessaire car le
    vrai `UserConfig` est instanciable hors Revit mais son backend pyRevit est
    absent -> get/set deviennent des no-op silencieux, rendant la persistance
    des badges « Par jeu » non testable sans injection."""

    def __init__(self):
        self._store = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value):
        self._store[key] = value
        return True


def config_avec_badges(badges):
    """`FakeConfig` pré-alimentée avec `{titre: (export, carnet, dwg)}`, au
    format exact que `MainViewModel._enregistrer_choix()` écrit (JSON sous la
    clé `jeux_badges`) : les badges sont ainsi relus par le vrai
    `_charger_choix()`, comme à la réouverture de l'outil."""
    cfg = FakeConfig()
    cfg.set('jeux_badges',
            json.dumps(dict((t, list(v)) for t, v in badges.items())))
    return cfg


class FakeCollectionElem(object):
    """Faux élément Revit de collection : sert de clé pour FakeSheetService."""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return u'FakeCollectionElem({})'.format(self.name)


class FakeSheetElem(object):
    """Faux élément Revit de feuille (ViewSheet)."""

    def __init__(self, numero):
        self.numero = numero

    def __repr__(self):
        return u'FakeSheetElem({})'.format(self.numero)


class FakeSheetService(object):
    """Faux SheetCollectionService : 2 collections ('Jeu A' 2 feuilles,
    'Jeu B' 1 feuille). Lecture seule du « document » : aucun badge n'en
    provient, ils viennent tous de la config (cf. `config_avec_badges`)."""

    def __init__(self):
        self._elem_a = FakeCollectionElem('A')
        self._elem_b = FakeCollectionElem('B')
        self._sheets = {
            'id-A': [
                {'Numero': '01', 'Nom': 'RDC', 'CollectionId': 'id-A', 'Elem': FakeSheetElem('01')},
                {'Numero': '02', 'Nom': 'R+1', 'CollectionId': 'id-A', 'Elem': FakeSheetElem('02')},
            ],
            'id-B': [
                {'Numero': '03', 'Nom': 'Toiture', 'CollectionId': 'id-B', 'Elem': FakeSheetElem('03')},
            ],
        }

    def list_collections(self):
        return [
            {'Titre': 'Jeu A', 'Id': 'id-A', 'Feuilles': 2, 'Elem': self._elem_a},
            {'Titre': 'Jeu B', 'Id': 'id-B', 'Feuilles': 1, 'Elem': self._elem_b},
        ]

    def list_sheets(self, collection_id=None):
        return self._sheets.get(collection_id, [])

    def list_all_sheets(self):
        # Toutes les feuilles, triées par numéro (comme le vrai service).
        out = []
        for coll_id in ('id-A', 'id-B'):
            out.extend(self._sheets.get(coll_id, []))
        out.sort(key=lambda s: s.get('Numero') or u'')
        return out

    def list_view_sheet_sets(self):
        # 2 sets d'impression : 'Set 1' (feuilles 01, 03) et 'Set 2' (02 seule).
        return [
            {'Nom': 'Set 1', 'SheetIds': set(['01', '03'])},
            {'Nom': 'Set 2', 'SheetIds': set(['02'])},
        ]


class FakeNamingService(object):
    """Faux NamingService : exerce le chemin resolve_for_element (non vide)."""

    def load(self, kind):
        return ('', [{'Name': 'Numero_Feuille', 'Prefix': '', 'Suffix': '-'}])

    def resolve_for_element(self, elem, rows):
        numero = getattr(elem, 'numero', '')
        return u'PROJETE-{}'.format(numero)


class FakeNamingServicePatternSeul(object):
    """Faux NamingService, mode jetons : `load` renvoie un pattern chaîne
    NON VIDE avec des `rows` VIDES (comportement réel de
    `NamingService.save(kind, pattern)` sans rows, cf. NamingEditorViewModel
    token-based) -- exerce le correctif de `refresh_par_jeu` qui doit
    utiliser `_pattern or rows_sheet` (et non plus `rows_sheet` seul) pour
    qu'un motif à jetons pilote bien `NomProjete`."""

    def __init__(self):
        self.resolve_calls = []

    def load(self, kind):
        return ('{numero}-JETON', [])

    def resolve_for_element(self, elem, pattern_ou_rows):
        self.resolve_calls.append(pattern_ou_rows)
        numero = getattr(elem, 'numero', '')
        return u'{}-JETON'.format(numero)


class FakeNamingServiceCarnet(object):
    """Faux NamingService exerçant l'aperçu de carnet : motif `set` non vide
    résolu contre l'élément de COLLECTION (préfixe 'CARNET-' + nom du jeu),
    motif `sheet` résolu contre la feuille (préfixe 'SHEET-' + numéro).
    Distingue collection (attribut `name`) et feuille (attribut `numero`)."""

    def load(self, kind):
        if kind == 'set':
            return ('{titre}-CARNET', [])
        return ('{numero}-SHEET', [])

    def resolve_for_element(self, elem, pattern_ou_rows):
        if hasattr(elem, 'name'):
            return u'CARNET-{}'.format(elem.name)
        return u'SHEET-{}'.format(getattr(elem, 'numero', ''))


class TestMainViewModelParJeu(unittest.TestCase):
    """Document jamais configuré (config vide) : les jeux sont bien listés,
    mais AUCUN badge n'est allumé — rien n'est lu dans la maquette."""

    def setUp(self):
        self.sheet_service = FakeSheetService()
        self.naming_service = FakeNamingService()
        self.vm = MainViewModel(
            doc=None,
            sheet_service=self.sheet_service,
            naming_service=self.naming_service,
            destination_service=None,
            config=FakeConfig(),
        )

    def test_refresh_par_jeu_construit_deux_collections(self):
        self.vm.refresh_par_jeu()
        self.assertEqual(len(self.vm.Collections), 2)

    def test_refresh_par_jeu_tous_badges_eteints_sans_config(self):
        self.vm.refresh_par_jeu()
        for jeu in self.vm.Collections:
            self.assertFalse(jeu.FlagExport)
            self.assertFalse(jeu.FlagCarnet)
            self.assertFalse(jeu.FlagDwg)
            self.assertFalse(jeu.Qualified)

    def test_refresh_par_jeu_nb_jeux_qualifies(self):
        self.vm.refresh_par_jeu()
        self.assertEqual(self.vm.NbJeuxQualifies, 0)

    def test_refresh_par_jeu_nb_feuilles_qualifiees(self):
        self.vm.refresh_par_jeu()
        # Aucun jeu coché -> aucune feuille qualifiée.
        self.assertEqual(self.vm.NbFeuillesQualifiees, 0)

    def test_refresh_par_jeu_nom_projete_non_vide(self):
        self.vm.refresh_par_jeu()
        jeu_a = self.vm.Collections[0]
        for sheet in jeu_a.Sheets:
            self.assertTrue(sheet.NomProjete)
            self.assertTrue(sheet.NomProjete.startswith(u'PROJETE-'))

    def test_refresh_par_jeu_sheets_champs_attendus(self):
        self.vm.refresh_par_jeu()
        jeu_a = self.vm.Collections[0]
        self.assertEqual(len(jeu_a.Sheets), 2)
        self.assertEqual(jeu_a.Sheets[0].Numero, '01')
        self.assertEqual(jeu_a.Sheets[0].Nom, 'RDC')

    def test_refresh_par_jeu_items_exposent_attributs(self):
        """Les items produits par refresh_par_jeu() doivent exposer de
        vraies propriétés CLR (Titre/FlagExport/Qualified/Sheets[i].Numero),
        pas des clés de dict — condition nécessaire pour que le binding
        WPF {Binding Titre} fonctionne (cf. CollectionItemVM/SheetItemVM)."""
        self.vm.refresh_par_jeu()
        jeu_a = self.vm.Collections[0]
        self.assertEqual(jeu_a.Titre, u'Jeu A')
        self.assertIs(jeu_a.FlagExport, False)
        self.assertIs(jeu_a.Qualified, False)
        self.assertEqual(jeu_a.Sheets[0].Numero, '01')


class TestMainViewModelParJeuPatternJetons(unittest.TestCase):
    """Un pattern à jetons (chaîne non vide, rows vides) doit piloter
    NomProjete au même titre qu'un ancien pattern à rows -- régression
    couverte suite au correctif de `refresh_par_jeu` (voir
    FakeNamingServicePatternSeul)."""

    def setUp(self):
        self.sheet_service = FakeSheetService()
        self.naming_service = FakeNamingServicePatternSeul()
        self.vm = MainViewModel(
            doc=None,
            sheet_service=self.sheet_service,
            naming_service=self.naming_service,
            destination_service=None,
            config=FakeConfig(),
        )

    def test_nom_projete_pilote_par_le_pattern_jetons(self):
        self.vm.refresh_par_jeu()
        jeu_a = self.vm.Collections[0]
        for sheet in jeu_a.Sheets:
            self.assertTrue(sheet.NomProjete.endswith(u'-JETON'))

    def test_resolve_appele_avec_le_pattern_chaine_pas_les_rows_vides(self):
        self.vm.refresh_par_jeu()
        self.assertTrue(len(self.naming_service.resolve_calls) > 0)
        for appel in self.naming_service.resolve_calls:
            self.assertEqual(appel, u'{numero}-JETON')


class TestMainViewModelParJeuCarnetApercu(unittest.TestCase):
    """Aperçu du titre de carnet (mode « par jeu ») : `CarnetApercu`
    (motif `set` résolu contre la collection + `.pdf`) et
    `CarnetApercuVisible` (`FlagCarnet and bool(CarnetApercu)`)."""

    def setUp(self):
        self.sheet_service = FakeSheetService()
        self.naming_service = FakeNamingServiceCarnet()
        self.vm = MainViewModel(
            doc=None,
            sheet_service=self.sheet_service,
            naming_service=self.naming_service,
            destination_service=None,
            config=config_avec_badges({u'Jeu A': (True, True, False)}),
        )

    def test_carnet_apercu_resolu_avec_extension_pdf(self):
        self.vm.refresh_par_jeu()
        jeu_a = self.vm.Collections[0]  # Jeu A qualifié + FlagCarnet
        self.assertEqual(jeu_a.CarnetApercu, u'CARNET-A.pdf')

    def test_carnet_apercu_visible_si_flag_carnet_et_apercu(self):
        self.vm.refresh_par_jeu()
        jeu_a = self.vm.Collections[0]
        self.assertTrue(jeu_a.FlagCarnet)
        self.assertTrue(jeu_a.CarnetApercuVisible)

    def test_carnet_apercu_non_visible_sans_flag_carnet(self):
        self.vm.refresh_par_jeu()
        jeu_b = self.vm.Collections[1]  # Jeu B : pas de FlagCarnet
        self.assertFalse(jeu_b.FlagCarnet)
        self.assertFalse(jeu_b.CarnetApercuVisible)

    def test_carnet_apercu_vide_et_non_visible_si_motif_set_vide(self):
        class FakeNamingServiceSetVide(FakeNamingServiceCarnet):
            def load(self, kind):
                if kind == 'set':
                    return ('', [])
                return ('{numero}-SHEET', [])

        vm = MainViewModel(
            doc=None,
            sheet_service=FakeSheetService(),
            naming_service=FakeNamingServiceSetVide(),
            destination_service=None,
            config=config_avec_badges({u'Jeu A': (True, True, False)}),
        )
        vm.refresh_par_jeu()
        jeu_a = vm.Collections[0]
        self.assertTrue(jeu_a.FlagCarnet)
        self.assertEqual(jeu_a.CarnetApercu, u'')
        self.assertFalse(jeu_a.CarnetApercuVisible)


class TestMainViewModelBadgesJeuxPersistance(unittest.TestCase):
    """Persistance des badges « Par jeu » (clé `jeux_badges` d'UserConfig).

    C'est LE contrat de la fonctionnalité : un badge cliqué est écrit dans la
    config, et une nouvelle session (nouveau `MainViewModel` sur la même
    config) le retrouve coché."""

    def _vm(self, cfg):
        return MainViewModel(
            doc=None,
            sheet_service=FakeSheetService(),
            naming_service=FakeNamingService(),
            destination_service=None,
            config=cfg,
        )

    def test_clic_sur_un_badge_ecrit_dans_la_config(self):
        cfg = FakeConfig()
        vm = self._vm(cfg)
        vm.refresh_par_jeu()
        vm.Collections[0].FlagExport = True
        self.assertEqual(json.loads(cfg.get('jeux_badges')),
                         {u'Jeu A': [True, False, False]})

    def test_une_nouvelle_session_retrouve_les_badges_coches(self):
        cfg = FakeConfig()
        vm1 = self._vm(cfg)
        vm1.refresh_par_jeu()
        jeu_b = next(c for c in vm1.Collections if c.Titre == u'Jeu B')
        jeu_b.FlagExport = True
        jeu_b.FlagDwg = True

        vm2 = self._vm(cfg)  # même magasin de config, VM neuf
        vm2.refresh_par_jeu()
        apres = next(c for c in vm2.Collections if c.Titre == u'Jeu B')
        self.assertTrue(apres.FlagExport)
        self.assertFalse(apres.FlagCarnet)
        self.assertTrue(apres.FlagDwg)
        # Le jeu jamais cliqué reste éteint.
        self.assertFalse(
            next(c for c in vm2.Collections if c.Titre == u'Jeu A').FlagExport)

    def test_decocher_un_badge_est_aussi_persiste(self):
        cfg = config_avec_badges({u'Jeu A': (True, True, True)})
        vm1 = self._vm(cfg)
        vm1.refresh_par_jeu()
        vm1.Collections[0].FlagCarnet = False

        vm2 = self._vm(cfg)
        vm2.refresh_par_jeu()
        jeu_a = next(c for c in vm2.Collections if c.Titre == u'Jeu A')
        self.assertTrue(jeu_a.FlagExport)
        self.assertFalse(jeu_a.FlagCarnet)
        self.assertTrue(jeu_a.FlagDwg)

    def test_titre_accentue_ecrit_sans_echappement(self):
        """Régression : un jeu au titre accentué doit être persisté.

        Sous IronPython 2.7 (moteur pyRevit), `str is unicode` : l'encodeur
        ASCII de `json` prend toujours la branche « octets » et lève sur tout
        accent. Le seul remède est `ensure_ascii=False` -- vérifiable ici par
        l'ABSENCE d'échappement `\\uXXXX` dans ce qui est écrit en config.
        C'est le bug qui empêchait les badges de persister : seuls les jeux au
        titre purement ASCII survivaient."""
        cfg = FakeConfig()
        vm = self._vm(cfg)
        vm.refresh_par_jeu()
        jeu = vm.Collections[0]
        jeu._titre = u'1.06_D\xe9tails'  # titre accentué, comme dans Revit
        jeu.FlagExport = True

        brut = cfg.get('jeux_badges')
        self.assertIn(u'1.06_D\xe9tails', brut)
        self.assertNotIn(u'\\u', brut)
        self.assertEqual(json.loads(brut),
                         {u'1.06_D\xe9tails': [True, False, False]})

    def test_echec_decriture_est_signale_pas_avale(self):
        """Une config qui refuse d'écrire (set -> False) ou qui lève DOIT
        produire un AVERT. Sans ça, l'utilisateur voit « ça ne persiste pas »
        sans aucune trace de la cause -- c'est exactement le symptôme qui a
        motivé ce garde-fou."""
        class CfgKo(FakeConfig):
            def set(self, key, value):
                return False

        class CfgQuiLeve(FakeConfig):
            def set(self, key, value):
                raise IOError(u'disque plein')

        for cfg in (CfgKo(), CfgQuiLeve()):
            vm = self._vm(cfg)
            alertes = []
            vm._log = lambda cat, msg: alertes.append((cat, msg))
            vm.refresh_par_jeu()
            vm.Collections[0].FlagExport = True  # ne doit pas lever
            self.assertTrue([a for a in alertes if a[0] == u'AVERT'],
                            u'aucun AVERT pour {}'.format(type(cfg).__name__))

    def test_config_absente_ne_leve_pas(self):
        # `config=None` -> le VM tente le vrai UserConfig (no-op hors Revit).
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                           naming_service=FakeNamingService())
        vm.refresh_par_jeu()
        vm.Collections[0].FlagExport = True  # ne doit pas lever
        self.assertTrue(vm.Collections[0].FlagExport)


class TestMainViewModelChargerChoixRobustesse(unittest.TestCase):
    """`_charger_choix()` est best-effort : une config illisible ne doit
    JAMAIS empêcher l'ouverture de l'outil, seulement repartir éteint."""

    def _badges(self, valeur_brute):
        cfg = FakeConfig()
        if valeur_brute is not None:
            cfg.set('jeux_badges', valeur_brute)
        return MainViewModel(doc=None, sheet_service=FakeSheetService(),
                             naming_service=FakeNamingService(),
                             config=cfg)._badges_jeux

    def test_cle_absente_donne_dict_vide(self):
        self.assertEqual(self._badges(None), {})

    def test_json_corrompu_donne_dict_vide(self):
        self.assertEqual(self._badges(u'{ceci nest pas du json'), {})

    def test_json_qui_nest_pas_un_dict_donne_dict_vide(self):
        self.assertEqual(self._badges(u'[1, 2, 3]'), {})

    def test_entree_malformee_ignoree_sans_perdre_les_autres(self):
        brut = json.dumps({u'Jeu A': [True, False],          # longueur != 3
                           u'Jeu B': [True, True, False]})
        self.assertEqual(self._badges(brut), {u'Jeu B': (True, True, False)})


class TestMainViewModelModeManuel(unittest.TestCase):
    """Mode « feuille par feuille » : refresh_manuel(), recherche, filtre
    (par jeu / par set d'impression), toggles PDF/DWG, compteurs et
    selection_manuelle(). Utilise le FakeSheetService étendu (3 feuilles :
    01/RDC, 02/R+1 dans Jeu A ; 03/Toiture dans Jeu B) + 2 sets factices
    ('Set 1' = 01+03, 'Set 2' = 02 seule)."""

    def setUp(self):
        self.sheet_service = FakeSheetService()
        self.vm = MainViewModel(
            doc=None,
            sheet_service=self.sheet_service,
            naming_service=FakeNamingService(),
            destination_service=None,
            config=FakeConfig(),
        )

    def test_refresh_manuel_construit_toutes_les_feuilles(self):
        self.vm.refresh_manuel()
        self.assertEqual(len(self.vm.SheetsManuel), 3)
        numeros = [s.Numero for s in self.vm.SheetsManuel]
        self.assertEqual(numeros, ['01', '02', '03'])

    def test_refresh_manuel_items_sont_de_vraies_instances(self):
        self.vm.refresh_manuel()
        for s in self.vm.SheetsManuel:
            self.assertIsInstance(s, ManualSheetVM)

    def test_defaut_aucun_format_coche(self):
        self.vm.refresh_manuel()
        for s in self.vm.SheetsManuel:
            self.assertFalse(s.ExportPdf)
            self.assertFalse(s.ExportDwg)

    def test_filtres_manuel_contient_jeux_et_sets_sans_toutes_les_feuilles(self):
        self.vm.refresh_manuel()
        labels = [f.Label for f in self.vm.FiltresManuel]
        self.assertNotIn(u'Toutes les feuilles', labels)
        self.assertIn(u'Jeu : Jeu A', labels)
        self.assertIn(u'Jeu : Jeu B', labels)
        self.assertIn(u'Impression : Set 1', labels)
        self.assertIn(u'Impression : Set 2', labels)
        for f in self.vm.FiltresManuel:
            self.assertIsInstance(f, FiltreItemVM)

    def test_filtres_manuel_tous_inactifs_par_defaut(self):
        self.vm.refresh_manuel()
        for f in self.vm.FiltresManuel:
            self.assertFalse(f.IsActif)

    def test_sheets_manuel_filtrees_sans_filtre_actif_ni_recherche(self):
        # Aucun filtre actif -> toutes les feuilles passent (sémantique
        # multi-filtre OU : liste vide de filtres actifs = pas de restriction).
        self.vm.refresh_manuel()
        self.assertEqual(len(self.vm.SheetsManuelFiltrees), 3)

    def test_recherche_filtre_par_numero(self):
        self.vm.refresh_manuel()
        self.vm.RechercheManuel = u'02'
        filtrees = self.vm.SheetsManuelFiltrees
        self.assertEqual(len(filtrees), 1)
        self.assertEqual(filtrees[0].Numero, '02')

    def test_recherche_filtre_par_nom_insensible_a_la_casse(self):
        self.vm.refresh_manuel()
        self.vm.RechercheManuel = u'toiture'
        filtrees = self.vm.SheetsManuelFiltrees
        self.assertEqual(len(filtrees), 1)
        self.assertEqual(filtrees[0].Nom, 'Toiture')

    def test_recherche_vide_ne_filtre_rien(self):
        self.vm.refresh_manuel()
        self.vm.RechercheManuel = u''
        self.assertEqual(len(self.vm.SheetsManuelFiltrees), 3)

    def test_filtre_par_collection_restreint_correctement(self):
        self.vm.refresh_manuel()
        filtre_jeu_a = next(f for f in self.vm.FiltresManuel if f.Label == u'Jeu : Jeu A')
        filtre_jeu_a.IsActif = True
        filtrees = self.vm.SheetsManuelFiltrees
        numeros = sorted([s.Numero for s in filtrees])
        self.assertEqual(numeros, ['01', '02'])

    def test_filtre_par_set_impression_restreint_correctement(self):
        self.vm.refresh_manuel()
        filtre_set1 = next(f for f in self.vm.FiltresManuel if f.Label == u'Impression : Set 1')
        filtre_set1.IsActif = True
        filtrees = self.vm.SheetsManuelFiltrees
        numeros = sorted([s.Numero for s in filtrees])
        self.assertEqual(numeros, ['01', '03'])

    def test_filtre_set_et_recherche_combines(self):
        self.vm.refresh_manuel()
        filtre_set1 = next(f for f in self.vm.FiltresManuel if f.Label == u'Impression : Set 1')
        filtre_set1.IsActif = True
        self.vm.RechercheManuel = u'toiture'
        filtrees = self.vm.SheetsManuelFiltrees
        self.assertEqual(len(filtrees), 1)
        self.assertEqual(filtrees[0].Numero, '03')

    def test_multi_filtre_ou_union_de_deux_filtres_actifs(self):
        """2 filtres actifs -> union OU (pas intersection) : Jeu B (feuille
        '03') + Set 2 (feuille '02') actifs ensemble doivent renvoyer
        {'02', '03'}."""
        self.vm.refresh_manuel()
        filtre_jeu_b = next(f for f in self.vm.FiltresManuel if f.Label == u'Jeu : Jeu B')
        filtre_set2 = next(f for f in self.vm.FiltresManuel if f.Label == u'Impression : Set 2')
        filtre_jeu_b.IsActif = True
        filtre_set2.IsActif = True
        filtrees = self.vm.SheetsManuelFiltrees
        numeros = sorted([s.Numero for s in filtrees])
        self.assertEqual(numeros, ['02', '03'])

    def test_multi_filtre_desactivation_retire_de_lunion(self):
        self.vm.refresh_manuel()
        filtre_jeu_a = next(f for f in self.vm.FiltresManuel if f.Label == u'Jeu : Jeu A')
        filtre_jeu_b = next(f for f in self.vm.FiltresManuel if f.Label == u'Jeu : Jeu B')
        filtre_jeu_a.IsActif = True
        filtre_jeu_b.IsActif = True
        self.assertEqual(len(self.vm.SheetsManuelFiltrees), 3)
        filtre_jeu_b.IsActif = False
        numeros = sorted([s.Numero for s in self.vm.SheetsManuelFiltrees])
        self.assertEqual(numeros, ['01', '02'])

    def test_toggle_export_pdf_met_a_jour_nb_pdf(self):
        self.vm.refresh_manuel()
        self.assertEqual(self.vm.NbPdf, 0)  # défaut : rien de coché
        self.vm.SheetsManuel[0].ExportPdf = True
        self.assertEqual(self.vm.NbPdf, 1)

    def test_toggle_export_dwg_met_a_jour_nb_dwg(self):
        self.vm.refresh_manuel()
        self.assertEqual(self.vm.NbDwg, 0)  # défaut DWG=False pour toutes
        self.vm.SheetsManuel[0].ExportDwg = True
        self.assertEqual(self.vm.NbDwg, 1)

    def test_nb_feuilles_manuel_reflete_le_filtre(self):
        self.vm.refresh_manuel()
        self.assertEqual(self.vm.NbFeuillesManuel, 3)
        self.vm.RechercheManuel = u'01'
        self.assertEqual(self.vm.NbFeuillesManuel, 1)

    def test_compteurs_pdf_dwg_portent_sur_les_feuilles_filtrees(self):
        self.vm.refresh_manuel()
        self.vm.SheetsManuel[2].ExportDwg = True  # feuille '03' (Toiture)
        filtre_jeu_a = next(f for f in self.vm.FiltresManuel if f.Label == u'Jeu : Jeu A')
        filtre_jeu_a.IsActif = True
        # Feuille '03' est hors Jeu A -> ne doit plus compter dans NbDwg.
        self.assertEqual(self.vm.NbDwg, 0)

    def test_selection_manuelle_retourne_les_feuilles_cochees(self):
        self.vm.refresh_manuel()
        self.vm.SheetsManuel[0].ExportDwg = True  # '01' : seule feuille cochée
        self.vm.SheetsManuel[1].ExportPdf = False  # '02' : ni PDF ni DWG
        self.vm.SheetsManuel[2].ExportPdf = False
        self.vm.SheetsManuel[2].ExportDwg = False
        selection = self.vm.selection_manuelle()
        numeros = sorted([s.Numero for s in selection])
        self.assertEqual(numeros, ['01'])

    def test_selection_manuelle_ignore_les_feuilles_masquees(self):
        """Une feuille masquée par un filtre ne doit PAS être exportée, même
        cochée : porter sur la liste entière exportait des feuilles invisibles."""
        self.vm.refresh_manuel()
        for s in self.vm.SheetsManuel:
            s.ExportPdf = True
        self.vm.SheetsManuel[2].ExportDwg = True  # '03' (Jeu B)
        filtre_jeu_a = next(f for f in self.vm.FiltresManuel if f.Label == u'Jeu : Jeu A')
        filtre_jeu_a.IsActif = True  # masque '03'
        numeros = sorted([s.Numero for s in self.vm.selection_manuelle()])
        self.assertEqual(numeros, ['01', '02'])

    def test_masquer_non_selectionnees(self):
        self.vm.refresh_manuel()
        for s in self.vm.SheetsManuel:
            s.ExportPdf = True
        self.vm.MasquerNonSelectionnees = True
        self.assertEqual(self.vm.NbFeuillesManuel, 3)
        self.vm.SheetsManuel[1].ExportPdf = False  # '02' : plus aucun format
        numeros = [s.Numero for s in self.vm.SheetsManuelFiltrees]
        self.assertEqual(numeros, ['01', '03'])
        self.vm.MasquerNonSelectionnees = False
        self.assertEqual(self.vm.NbFeuillesManuel, 3)

    def test_selection_manuelle_ignore_les_feuilles_hors_recherche(self):
        self.vm.refresh_manuel()
        for s in self.vm.SheetsManuel:
            s.ExportPdf = True
        self.vm.RechercheManuel = u'01'
        numeros = [s.Numero for s in self.vm.selection_manuelle()]
        self.assertEqual(numeros, ['01'])

    def test_refresh_manuel_reinitialise_la_selection(self):
        self.vm.refresh_manuel()
        self.vm.SheetsManuel[0].ExportDwg = True
        self.vm.SheetsManuel[1].ExportPdf = True
        self.vm.refresh_manuel()
        for s in self.vm.SheetsManuel:
            self.assertFalse(s.ExportPdf)
            self.assertFalse(s.ExportDwg)

    def test_jeu_nom_renseigne_depuis_la_collection(self):
        self.vm.refresh_manuel()
        sheets_by_numero = {s.Numero: s for s in self.vm.SheetsManuel}
        self.assertEqual(sheets_by_numero['01'].JeuNom, u'Jeu A')
        self.assertEqual(sheets_by_numero['02'].JeuNom, u'Jeu A')
        self.assertEqual(sheets_by_numero['03'].JeuNom, u'Jeu B')

    def test_nom_projete_resolu_via_naming_service(self):
        # FakeNamingService.resolve_for_element -> 'PROJETE-{numero}'.
        self.vm.refresh_manuel()
        for s in self.vm.SheetsManuel:
            self.assertEqual(s.NomProjete, u'PROJETE-{}'.format(s.Numero))

    def test_refresh_manuel_sans_service_ne_leve_pas(self):
        vm = MainViewModel(doc=None)
        vm.refresh_manuel()
        self.assertEqual(vm.SheetsManuel, [])
        self.assertEqual(vm.FiltresManuel, [])  # aucune collection/set -> aucun filtre
        self.assertEqual(vm.NbFeuillesManuel, 0)
        self.assertEqual(vm.NbPdf, 0)
        self.assertEqual(vm.NbDwg, 0)
        self.assertEqual(vm.selection_manuelle(), [])


class TestManualSheetVM(unittest.TestCase):
    """`ManualSheetVM` isolé : défauts, notify + callback on_change,
    idempotence des setters."""

    def test_defauts(self):
        item = ManualSheetVM('01', 'RDC')
        self.assertTrue(item.ExportPdf)
        self.assertFalse(item.ExportDwg)
        self.assertEqual(item.JeuNom, u'')
        self.assertEqual(item.NomProjete, u'')

    def test_jeu_nom_et_nom_projete_lecture_seule_depuis_constructeur(self):
        item = ManualSheetVM('01', 'RDC', jeu_nom=u'Jeu A', nom_projete=u'01_RDC')
        self.assertEqual(item.JeuNom, u'Jeu A')
        self.assertEqual(item.NomProjete, u'01_RDC')

    def test_toggle_appelle_on_change(self):
        calls = []
        item = ManualSheetVM('01', 'RDC', on_change=lambda: calls.append(1))
        item.ExportPdf = False
        self.assertEqual(len(calls), 1)
        item.ExportDwg = True
        self.assertEqual(len(calls), 2)

    def test_setter_idempotent_ne_rappelle_pas_on_change(self):
        calls = []
        item = ManualSheetVM('01', 'RDC', on_change=lambda: calls.append(1))
        item.ExportPdf = True  # déjà True par défaut
        self.assertEqual(len(calls), 0)

    def test_sans_on_change_ne_leve_pas(self):
        item = ManualSheetVM('01', 'RDC')
        item.ExportPdf = False  # ne doit pas lever
        self.assertFalse(item.ExportPdf)


class TestMainViewModelServicesParDefaut(unittest.TestCase):
    """Sans injection, le VM ne doit jamais lever (hors Revit -> services None ou vides)."""

    def test_construction_sans_services_ne_leve_pas(self):
        vm = MainViewModel(doc=None)
        vm.refresh_par_jeu()
        self.assertEqual(vm.Collections, [])
        self.assertEqual(vm.NbJeuxQualifies, 0)
        self.assertEqual(vm.NbFeuillesQualifiees, 0)


class TestMainViewModelLancerExport(unittest.TestCase):
    """`lancer_export()` (Task 3) : ne doit jamais lever hors Revit, quels que
    soient les services injectés (réels absents ou faux/factices)."""

    def test_lancer_export_doc_none_ne_leve_pas(self):
        vm = MainViewModel(doc=None)
        vm.lancer_export()
        self.assertIn(u'indisponible', vm.StatusText.lower())

    def test_lancer_export_avec_services_factices_doc_none_ne_leve_pas(self):
        vm = MainViewModel(
            doc=None,
            sheet_service=FakeSheetService(),
            naming_service=FakeNamingService(),
            destination_service=None,
            config=FakeConfig(),
        )
        vm.lancer_export()
        self.assertIn(u'indisponible', vm.StatusText.lower())

    def test_status_text_et_progress_value_par_defaut(self):
        vm = MainViewModel(doc=None)
        self.assertEqual(vm.StatusText, u'')
        self.assertEqual(vm.ProgressValue, 0)

    def test_progress_value_setter_borne_0_100(self):
        vm = MainViewModel(doc=None)
        vm.ProgressValue = 150
        self.assertEqual(vm.ProgressValue, 100)
        vm.ProgressValue = -5
        self.assertEqual(vm.ProgressValue, 0)

    def test_on_export_progress_met_a_jour_status_et_progress(self):
        vm = MainViewModel(doc=None)
        vm._on_export_progress(2, 4, u'Collection: Jeu A')
        self.assertEqual(vm.ProgressValue, 50)
        self.assertEqual(vm.StatusText, u'Collection: Jeu A')

    def test_on_export_log_met_a_jour_status(self):
        vm = MainViewModel(doc=None)
        vm._on_export_log(u'Erreur export PDF: 01_RDC')
        self.assertEqual(vm.StatusText, u'Erreur export PDF: 01_RDC')

    def test_import_lib_services_core_resout_les_dependances_internes(self):
        """Vérifie que `from lib.services.ExportOrchestrator import ...`
        (chemin utilisé par `lancer_export()`) fait résoudre correctement les
        imports internes de l'orchestrateur.

        Si l'un d'eux retombait sur `None`, l'orchestrateur « fonctionnerait »
        en mode dégradé silencieux (dossier courant, sans options PDF/DWG ni
        motif de nommage). Ce test fige donc le fait que TOUTES ses
        dépendances sont bien résolues, pour que la moindre régression de
        packaging soit détectée hors Revit."""
        from lib.services.ExportOrchestrator import ExportOrchestrator
        orch = ExportOrchestrator()
        self.assertIsNone(orch.erreur_dependances())
        self.assertIsNotNone(orch._pdf)
        self.assertIsNotNone(orch._dwg)
        self.assertIsNotNone(orch._cfg)
        self.assertIsNotNone(orch._NamingService_cls)

    def test_erreur_dependances_signale_le_mode_degrade(self):
        """`erreur_dependances()` est le seul garde-fou : `__init__` ne lève
        jamais, il met `_dest` à None. Sans ce test, la suppression du garde
        passerait inaperçue et l'export tournerait en mode dégradé."""
        from lib.services.ExportOrchestrator import ExportOrchestrator
        orch = ExportOrchestrator()
        orch._dest = None
        orch._erreurs_import = [u'DestinationService : boum']
        self.assertIn(u'boum', orch.erreur_dependances())
        orch._erreurs_import = []
        self.assertIn(u'indisponible', orch.erreur_dependances().lower())


class FakeDestinationService(object):
    """Faux DestinationService : mêmes méthodes que le vrai (get/set/ensure),
    mais `set` enregistre l'argument reçu pour vérification (pas de disque).

    Étendu (toggles Paramètres) avec get_create_subfolders/set_create_subfolders
    et get_separate_formats/set_separate_formats, stockage en mémoire, même
    contrat que le vrai DestinationService (booléens)."""

    def __init__(self, initial=u''):
        self._path = initial
        self.set_calls = []
        self.ensure_calls = []
        self._create_subfolders = False
        self._separate_formats = False

    def get(self, default=None):
        return self._path

    def set(self, path):
        self.set_calls.append(path)
        self._path = path
        return True

    def ensure(self, path):
        self.ensure_calls.append(path)
        return path

    def get_create_subfolders(self):
        return self._create_subfolders

    def set_create_subfolders(self, val):
        self._create_subfolders = bool(val)

    def get_separate_formats(self):
        return self._separate_formats

    def set_separate_formats(self, val):
        self._separate_formats = bool(val)


class FakePdfService(object):
    """Faux PdfExporterService minimal : list_all_setups/get_saved_setup/
    set_saved_setup, stockage en mémoire, ignore `doc`."""

    def __init__(self, setups=None, saved=u''):
        self._setups = list(setups or [])
        self._saved = saved
        self.set_calls = []

    def list_all_setups(self, doc):
        return list(self._setups)

    def get_saved_setup(self, default=None):
        return self._saved or default

    def set_saved_setup(self, name):
        self.set_calls.append(name)
        self._saved = name
        return True


class FakeDwgService(object):
    """Faux DwgExporterService minimal, même contrat que FakePdfService."""

    def __init__(self, setups=None, saved=u''):
        self._setups = list(setups or [])
        self._saved = saved
        self.set_calls = []

    def list_all_setups(self, doc):
        return list(self._setups)

    def get_saved_setup(self, default=None):
        return self._saved or default

    def set_saved_setup(self, name):
        self.set_calls.append(name)
        self._saved = name
        return True


class TestMainViewModelDestination(unittest.TestCase):
    """`DestinationPath` (Task « Parcourir ») : reflète un faux
    destination_service ; `definir_destination` appelle bien set()/ensure()
    sur le service et notifie la propriété bindable."""

    def test_destination_path_reflete_le_service(self):
        vm = MainViewModel(doc=None, destination_service=FakeDestinationService(u'C:/Export'))
        self.assertEqual(vm.DestinationPath, u'C:/Export')

    def test_destination_path_vide_si_service_absent(self):
        # `destination_service=None` ne suffit pas à simuler l'absence de
        # service : le VM instancie alors le VRAI `DestinationService`
        # (importable hors Revit, avec repli ~/Documents/Exports). Pour
        # exercer la branche "service absent" du getter (cf.
        # `DestinationPath`), on force `_destination_service` à None
        # après construction plutôt qu'à l'injection.
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=FakeNamingService(),
                            config=FakeConfig())
        vm._destination_service = None
        self.assertEqual(vm.DestinationPath, u'')

    def test_definir_destination_appelle_set_sur_le_service(self):
        fake = FakeDestinationService(u'')
        vm = MainViewModel(doc=None, destination_service=fake)
        vm.definir_destination(u'X')
        self.assertEqual(fake.set_calls, [u'X'])
        self.assertEqual(vm.DestinationPath, u'X')

    def test_definir_destination_appelle_ensure_sur_le_service(self):
        fake = FakeDestinationService(u'')
        vm = MainViewModel(doc=None, destination_service=fake)
        vm.definir_destination(u'X')
        self.assertEqual(fake.ensure_calls, [u'X'])

    def test_definir_destination_chemin_vide_ignore(self):
        fake = FakeDestinationService(u'C:/Existant')
        vm = MainViewModel(doc=None, destination_service=fake)
        vm.definir_destination(u'')
        self.assertEqual(fake.set_calls, [])
        self.assertEqual(vm.DestinationPath, u'C:/Existant')

    def test_definir_destination_sans_service_ne_leve_pas(self):
        vm = MainViewModel(doc=None, destination_service=None,
                            sheet_service=FakeSheetService(),
                            naming_service=FakeNamingService(),
                            config=FakeConfig())
        vm.definir_destination(u'X')  # ne doit pas lever

    def test_definir_destination_fonctionne_sans_methode_ensure(self):
        """Le service peut ne pas exposer `ensure` (mock minimal) -> `set`
        doit tout de même être appelé, sans lever."""
        class ServiceSansEnsure(object):
            def __init__(self):
                self.set_calls = []

            def get(self, default=None):
                return u''

            def set(self, path):
                self.set_calls.append(path)
                return True

        fake = ServiceSansEnsure()
        vm = MainViewModel(doc=None, destination_service=fake)
        vm.definir_destination(u'X')
        self.assertEqual(fake.set_calls, [u'X'])


class TestMainViewModelTogglesParametres(unittest.TestCase):
    """`CreerSousDossiers`/`SeparerFormats` (page Paramètres) : reflètent un
    faux DestinationService étendu, round-trip set/get, et ne lèvent jamais
    si le service est absent."""

    def test_creer_sous_dossiers_reflete_le_service_et_persiste(self):
        fake = FakeDestinationService()
        vm = MainViewModel(doc=None, destination_service=fake)
        self.assertFalse(vm.CreerSousDossiers)
        vm.CreerSousDossiers = True
        self.assertTrue(vm.CreerSousDossiers)
        self.assertTrue(fake.get_create_subfolders())

    def test_separer_formats_reflete_le_service_et_persiste(self):
        fake = FakeDestinationService()
        vm = MainViewModel(doc=None, destination_service=fake)
        self.assertFalse(vm.SeparerFormats)
        vm.SeparerFormats = True
        self.assertTrue(vm.SeparerFormats)
        self.assertTrue(fake.get_separate_formats())

    def test_creer_sous_dossiers_setter_idempotent(self):
        fake = FakeDestinationService()
        vm = MainViewModel(doc=None, destination_service=fake)
        vm.CreerSousDossiers = True
        vm.CreerSousDossiers = True  # ne doit pas lever ni changer l'état
        self.assertTrue(vm.CreerSousDossiers)

    def test_creer_sous_dossiers_defaut_false_sans_service(self):
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=FakeNamingService(),
                            config=FakeConfig())
        vm._destination_service = None
        self.assertFalse(vm.CreerSousDossiers)

    def test_separer_formats_defaut_false_sans_service(self):
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=FakeNamingService(),
                            config=FakeConfig())
        vm._destination_service = None
        self.assertFalse(vm.SeparerFormats)

    def test_creer_sous_dossiers_setter_ne_leve_pas_sans_service(self):
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=FakeNamingService(),
                            config=FakeConfig())
        vm._destination_service = None
        vm.CreerSousDossiers = True  # ne doit pas lever
        self.assertFalse(vm.CreerSousDossiers)

    def test_separer_formats_setter_ne_leve_pas_sans_service(self):
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=FakeNamingService(),
                            config=FakeConfig())
        vm._destination_service = None
        vm.SeparerFormats = True  # ne doit pas lever
        self.assertFalse(vm.SeparerFormats)


class TestMainViewModelSetupsPdfDwg(unittest.TestCase):
    """`SetupsPdf`/`SetupPdf`/`SetupsDwg`/`SetupDwg` (page Paramètres) :
    reflètent de faux services PDF/DWG, tolèrent un service absent."""

    def test_setups_pdf_reflete_le_service(self):
        fake = FakePdfService(setups=[u'A', u'B'])
        vm = MainViewModel(doc=None, pdf_service=fake)
        self.assertEqual(vm.SetupsPdf, [u'A', u'B'])

    def test_setups_pdf_vide_si_service_absent_apres_construction(self):
        fake = FakePdfService(setups=[u'A', u'B'])
        vm = MainViewModel(doc=None, pdf_service=fake)
        self.assertEqual(vm.SetupsPdf, [u'A', u'B'])
        vm._pdf_service = None
        self.assertEqual(vm.SetupsPdf, [])

    def test_setups_dwg_reflete_le_service(self):
        fake = FakeDwgService(setups=[u'X', u'Y'])
        vm = MainViewModel(doc=None, dwg_service=fake)
        self.assertEqual(vm.SetupsDwg, [u'X', u'Y'])

    def test_setups_dwg_vide_si_service_absent_apres_construction(self):
        fake = FakeDwgService(setups=[u'X', u'Y'])
        vm = MainViewModel(doc=None, dwg_service=fake)
        self.assertEqual(vm.SetupsDwg, [u'X', u'Y'])
        vm._dwg_service = None
        self.assertEqual(vm.SetupsDwg, [])

    def test_setup_pdf_reflete_le_service_et_persiste(self):
        fake = FakePdfService(setups=[u'A', u'B'])
        vm = MainViewModel(doc=None, pdf_service=fake)
        self.assertEqual(vm.SetupPdf, u'')
        vm.SetupPdf = u'A'
        self.assertEqual(vm.SetupPdf, u'A')
        self.assertEqual(fake.set_calls, [u'A'])

    def test_setup_dwg_reflete_le_service_et_persiste(self):
        fake = FakeDwgService(setups=[u'X', u'Y'])
        vm = MainViewModel(doc=None, dwg_service=fake)
        self.assertEqual(vm.SetupDwg, u'')
        vm.SetupDwg = u'Y'
        self.assertEqual(vm.SetupDwg, u'Y')
        self.assertEqual(fake.set_calls, [u'Y'])

    def test_setup_pdf_setter_idempotent(self):
        fake = FakePdfService(setups=[u'A'])
        vm = MainViewModel(doc=None, pdf_service=fake)
        vm.SetupPdf = u'A'
        vm.SetupPdf = u'A'  # ne doit pas rappeler set_saved_setup
        self.assertEqual(fake.set_calls, [u'A'])

    def test_setup_pdf_defaut_vide_sans_service(self):
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=FakeNamingService(),
                            config=FakeConfig())
        vm._pdf_service = None
        self.assertEqual(vm.SetupPdf, u'')

    def test_setup_dwg_defaut_vide_sans_service(self):
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=FakeNamingService(),
                            config=FakeConfig())
        vm._dwg_service = None
        self.assertEqual(vm.SetupDwg, u'')

    def test_setup_pdf_setter_ne_leve_pas_sans_service(self):
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=FakeNamingService(),
                            config=FakeConfig())
        vm._pdf_service = None
        vm.SetupPdf = u'X'  # ne doit pas lever
        self.assertEqual(vm.SetupPdf, u'')

    def test_setup_dwg_setter_ne_leve_pas_sans_service(self):
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=FakeNamingService(),
                            config=FakeConfig())
        vm._dwg_service = None
        vm.SetupDwg = u'X'  # ne doit pas lever
        self.assertEqual(vm.SetupDwg, u'')


class TestMainViewModelServicesPdfDwgParDefaut(unittest.TestCase):
    """Construction sans aucun service PDF/DWG injecté : le VM doit pouvoir
    instancier les vrais services hors Revit sans jamais lever."""

    def test_construction_sans_pdf_dwg_service_ne_leve_pas(self):
        vm = MainViewModel(doc=None)
        # Vérifie que les VRAIS services ont bien été instanciés (et non
        # `None` suite à un import silencieusement en échec) -- sinon les
        # assertions [] / u'' ci-dessous passeraient aussi dans le cas d'une
        # régression de packaging, sans jamais la détecter (cf. le même
        # garde-fou pour ExportOrchestrator dans
        # test_import_lib_services_core_resout_les_dependances_internes).
        self.assertIsNotNone(vm._pdf_service)
        self.assertIsNotNone(vm._dwg_service)
        self.assertEqual(vm.SetupsPdf, [])
        self.assertEqual(vm.SetupsDwg, [])
        self.assertEqual(vm.SetupPdf, u'')
        self.assertEqual(vm.SetupDwg, u'')
        vm.SetupPdf = u'X'
        vm.SetupDwg = u'Y'


class TestMainViewModelGetNamingParams(unittest.TestCase):
    """`get_naming_params()` (page Paramètres -> modale NamingEditorView) :
    best-effort, ne doit jamais lever, retourne `[]` hors Revit (doc=None)."""

    def test_get_naming_params_vide_sans_doc(self):
        vm = MainViewModel(doc=None)
        self.assertEqual(vm.get_naming_params(), [])

    def test_get_naming_params_ne_leve_pas_meme_avec_doc_factice(self):
        # doc factice sans rapport avec Autodesk.Revit.DB -- la collecte
        # réelle (SheetParameterRepository) échoue silencieusement à chaque
        # étape (FilteredElementCollector etc.) et doit retourner [].
        vm = MainViewModel(doc=object())
        self.assertEqual(vm.get_naming_params(), [])


class TestFiltreItemVM(unittest.TestCase):
    """`FiltreItemVM` isolé : défaut `IsActif=False`, notify + callback
    on_change, idempotence du setter (miroir de TestManualSheetVM)."""

    def test_defaut_is_actif_false(self):
        item = FiltreItemVM(u'Jeu : A', u'collection', coll_id='id-A')
        self.assertFalse(item.IsActif)

    def test_toggle_is_actif_appelle_on_change(self):
        calls = []
        item = FiltreItemVM(u'Jeu : A', u'collection', coll_id='id-A',
                             on_change=lambda: calls.append(1))
        item.IsActif = True
        self.assertTrue(item.IsActif)
        self.assertEqual(len(calls), 1)

    def test_setter_idempotent_ne_rappelle_pas_on_change(self):
        calls = []
        item = FiltreItemVM(u'Jeu : A', u'collection', coll_id='id-A',
                             on_change=lambda: calls.append(1))
        item.IsActif = False  # déjà False par défaut
        self.assertEqual(len(calls), 0)

    def test_sans_on_change_ne_leve_pas(self):
        item = FiltreItemVM(u'Jeu : A', u'collection', coll_id='id-A')
        item.IsActif = True  # ne doit pas lever
        self.assertTrue(item.IsActif)


class FakeSheetServiceTriMixte(object):
    """Faux SheetCollectionService dédié au test de tri : 4 collections
    ('Abc', 'Nord', 'Sud', 'Zeb') listées par ordre alphabétique.

    Le test coche 'Sud' et 'Zeb' pour que l'ordre alphabétique brut NE
    corresponde PAS à l'ordre qualifié-d'abord attendu -- nécessaire pour
    discriminer un tri par groupe d'un simple tri alpha global.
    """

    def __init__(self):
        self._defs = [
            ('Abc', 'id-abc'),
            ('Nord', 'id-nord'),
            ('Sud', 'id-sud'),
            ('Zeb', 'id-zeb'),
        ]

    def list_collections(self):
        return [{'Titre': titre, 'Id': cid, 'Elem': FakeCollectionElem(titre)}
                for (titre, cid) in self._defs]

    def list_sheets(self, collection_id=None):
        return []


class TestMainViewModelParJeuTri(unittest.TestCase):
    """Tri de `Collections` (mode « par jeu ») : qualifiées (FlagExport=True)
    d'abord, puis alphabétique du Titre (insensible à la casse) au sein de
    chaque groupe."""

    def setUp(self):
        self.vm = MainViewModel(
            doc=None,
            sheet_service=FakeSheetServiceTriMixte(),
            naming_service=FakeNamingService(),
            destination_service=None,
            config=config_avec_badges({u'Sud': (True, False, False),
                                       u'Zeb': (True, False, False)}),
        )

    def test_qualifiees_avant_non_qualifiees_puis_alpha(self):
        self.vm.refresh_par_jeu()
        titres = [c.Titre for c in self.vm.Collections]
        self.assertEqual(titres, ['Sud', 'Zeb', 'Abc', 'Nord'])

    def test_toutes_qualifiees_sont_groupees_en_tete(self):
        self.vm.refresh_par_jeu()
        qualifs = [c.Qualified for c in self.vm.Collections]
        # Les True doivent précéder tous les False (groupement, pas
        # d'entrelacement).
        self.assertEqual(qualifs, sorted(qualifs, reverse=True))


class TestMainViewModelPatternsApercu(unittest.TestCase):
    """`PatternFeuilleApercu`/`PatternCarnetApercu` (page Réglages) :
    lecture du motif brut via `_naming_service.load(kind)[0]`."""

    class FakeNamingServiceMotifs(object):
        def __init__(self, sheet_pattern=u'', set_pattern=u''):
            self._sheet_pattern = sheet_pattern
            self._set_pattern = set_pattern

        def load(self, kind):
            if kind == 'sheet':
                return (self._sheet_pattern, [])
            if kind == 'set':
                return (self._set_pattern, [])
            return (u'', [])

        def resolve_for_element(self, elem, pattern):
            return u''

    def test_pattern_feuille_apercu_lit_le_motif_brut(self):
        naming = self.FakeNamingServiceMotifs(sheet_pattern=u'{numero}-{nom}')
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=naming, config=FakeConfig())
        self.assertEqual(vm.PatternFeuilleApercu, u'{numero}-{nom}')

    def test_pattern_carnet_apercu_lit_le_motif_brut(self):
        naming = self.FakeNamingServiceMotifs(set_pattern=u'{nom_carnet}')
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=naming, config=FakeConfig())
        self.assertEqual(vm.PatternCarnetApercu, u'{nom_carnet}')

    def test_patterns_apercu_vides_sans_naming_service(self):
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=None, config=FakeConfig())
        self.assertEqual(vm.PatternFeuilleApercu, u'')
        self.assertEqual(vm.PatternCarnetApercu, u'')

    def test_refresh_patterns_apercu_relit_apres_changement(self):
        naming = self.FakeNamingServiceMotifs(sheet_pattern=u'V1')
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=naming, config=FakeConfig())
        self.assertEqual(vm.PatternFeuilleApercu, u'V1')
        naming._sheet_pattern = u'V2'
        vm.refresh_patterns_apercu()
        self.assertEqual(vm.PatternFeuilleApercu, u'V2')

    def test_refresh_manuel_relit_les_patterns_apercu(self):
        naming = self.FakeNamingServiceMotifs(sheet_pattern=u'V1')
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                            naming_service=naming, config=FakeConfig())
        naming._sheet_pattern = u'V2'
        vm.refresh_manuel()
        self.assertEqual(vm.PatternFeuilleApercu, u'V2')


class TestMainViewModelCombinerPdf(unittest.TestCase):
    """Mode « feuille par feuille » : PDF combiné + titre (UI + persistance).
    Vérifie les valeurs par défaut, le round-trip via UserConfig injecté, et
    l'indépendance des deux propriétés. Le branchement moteur n'est PAS testé
    ici (non implémenté à ce stade)."""

    def setUp(self):
        self.cfg = FakeConfig()
        self.vm = MainViewModel(doc=None, config=self.cfg)

    def test_defauts(self):
        self.assertFalse(self.vm.CombinerPdf)
        self.assertEqual(self.vm.TitrePdfCombine, u'')

    def test_combiner_pdf_round_trip(self):
        self.vm.CombinerPdf = True
        self.assertTrue(self.vm.CombinerPdf)
        # persisté dans la config injectée
        self.assertEqual(self.cfg.get('manual_combine_pdf'), u'1')
        self.vm.CombinerPdf = False
        self.assertFalse(self.vm.CombinerPdf)
        self.assertEqual(self.cfg.get('manual_combine_pdf'), u'0')

    def test_titre_round_trip(self):
        self.vm.TitrePdfCombine = u'Carnet complet'
        self.assertEqual(self.vm.TitrePdfCombine, u'Carnet complet')
        self.assertEqual(self.cfg.get('manual_pdf_combine_title'), u'Carnet complet')

    def test_proprietes_independantes(self):
        self.vm.TitrePdfCombine = u'Titre'
        self.assertFalse(self.vm.CombinerPdf)  # titre défini n'active pas le combiné
        self.vm.CombinerPdf = True
        self.assertEqual(self.vm.TitrePdfCombine, u'Titre')  # combiné n'efface pas le titre

    def test_setter_idempotent(self):
        self.vm.CombinerPdf = True
        self.vm.CombinerPdf = True  # ne doit pas lever ni changer
        self.assertTrue(self.vm.CombinerPdf)


class TestMainViewModelLancerExportManuel(unittest.TestCase):
    """`lancer_export_manuel()` : chemins hors Revit (doc=None, sélection vide,
    orchestrateur indisponible). Ne doit jamais lever.

    Le branchement moteur réel (doc non-None + Revit API) n'est pas testable
    hors Revit ; ces tests couvrent les gardes et la logique de dispatch."""

    def test_lancer_export_manuel_doc_none_ne_leve_pas(self):
        vm = MainViewModel(doc=None)
        vm.lancer_export_manuel()
        self.assertIn(u'indisponible', vm.StatusText.lower())

    def test_lancer_export_manuel_selection_vide_ne_leve_pas(self):
        vm = MainViewModel(
            doc=object(),  # doc non-None pour passer le premier garde
            sheet_service=FakeSheetService(),
            naming_service=FakeNamingService(),
            config=FakeConfig(),
        )
        # _sheets_manuel vide par défaut (pas de refresh_manuel)
        vm.lancer_export_manuel()
        self.assertIn(u'sélectionnée', vm.StatusText.lower())

    def test_lancer_export_mode_manual_dispatche_vers_lancer_export_manuel(self):
        """lancer_export() en mode 'manual' appelle lancer_export_manuel() :
        le statut doit refléter l'appel (ici 'indisponible' car doc=None)."""
        vm = MainViewModel(doc=None)
        vm.set_mode(u'manual')
        vm.lancer_export()
        self.assertIn(u'indisponible', vm.StatusText.lower())

    def test_lancer_export_mode_auto_ne_dispatche_pas_vers_manuel(self):
        """lancer_export() en mode 'auto' reste sur le chemin auto (ne passe
        PAS par lancer_export_manuel). Résultat attendu : 'indisponible'
        (doc=None) mais le chemin code n'est pas celui de la sélection vide."""
        vm = MainViewModel(doc=None)
        vm.set_mode(u'auto')
        vm.lancer_export()
        # Le garde auto (doc=None) écrit 'indisponible' — pas 'sélectionnée'
        self.assertIn(u'indisponible', vm.StatusText.lower())
        self.assertNotIn(u'sélectionnée', vm.StatusText.lower())

    def test_lancer_export_manuel_orchestre_ne_leve_pas_si_dependances_manquantes(self):
        """Si l'orchestrateur est instanciable mais _dest=None (mode dégradé),
        lancer_export_manuel() signale l'indisponibilité sans lever."""
        vm = MainViewModel(doc=object(), sheet_service=FakeSheetService(),
                           naming_service=FakeNamingService(), config=FakeConfig())
        # Injecter une feuille cochée pour dépasser le garde sélection vide
        from lib.viewmodels.MainViewModel import ManualSheetVM
        svm = ManualSheetVM(u'01', u'Feuille 1', export_pdf=True, export_dwg=False)
        vm._sheets_manuel = [svm]
        # L'orchestrateur réel (importable hors Revit) a _dest non-None →
        # la méthode avancera jusqu'au run_manual, qui échouera silencieusement
        # car DB est None (pas de Revit). Ne doit pas lever.
        try:
            vm.lancer_export_manuel()
        except Exception as exc:
            self.fail(u"lancer_export_manuel() a levé une exception : {}".format(exc))


class TestListSelectionService(unittest.TestCase):
    """Tests unitaires pour `ListSelectionService` (service pur Python)."""

    def setUp(self):
        from core.list_selection import ListSelectionService
        self.svc = ListSelectionService(prop=u'Selected')

    def _items(self, n):
        from lib.viewmodels.MainViewModel import ManualSheetVM
        return [ManualSheetVM(str(i), u'Feuille {}'.format(i)) for i in range(n)]

    def test_clic_simple_selectionne_uniquement_cet_index(self):
        items = self._items(5)
        self.svc.handle_click(items, 2)
        selected = [i.Selected for i in items]
        self.assertEqual(selected, [False, False, True, False, False])

    def test_clic_simple_deselectionne_les_autres(self):
        items = self._items(3)
        items[0].Selected = True
        items[1].Selected = True
        self.svc.handle_click(items, 2)
        self.assertFalse(items[0].Selected)
        self.assertFalse(items[1].Selected)
        self.assertTrue(items[2].Selected)

    def test_ctrl_clic_bascule_sans_toucher_les_autres(self):
        items = self._items(3)
        self.svc.handle_click(items, 0)         # sélectionne 0, ancre=0
        self.svc.handle_click(items, 1, ctrl=True)  # toggle 1 sans toucher 0
        self.assertTrue(items[0].Selected)   # inchangé
        self.assertTrue(items[1].Selected)   # togglé ON
        self.assertFalse(items[2].Selected)

    def test_shift_clic_selectionne_plage_inclusive(self):
        items = self._items(5)
        self.svc.handle_click(items, 1)          # ancre = 1
        self.svc.handle_click(items, 4, shift=True)  # plage 1..4
        selected = [i.Selected for i in items]
        self.assertEqual(selected, [False, True, True, True, True])

    def test_shift_clic_ne_deplace_pas_ancre(self):
        items = self._items(5)
        self.svc.handle_click(items, 2)
        self.svc.handle_click(items, 4, shift=True)
        self.svc.handle_click(items, 0, shift=True)  # ancre toujours = 2 → plage 0..2
        selected = [i.Selected for i in items]
        self.assertEqual(selected, [True, True, True, False, False])

    def test_shift_sans_ancre_agit_comme_clic_simple(self):
        items = self._items(4)
        items[1].Selected = True
        self.svc.handle_click(items, 3, shift=True)
        selected = [i.Selected for i in items]
        self.assertEqual(selected, [False, False, False, True])

    def test_reset_reinitialise_ancre(self):
        items = self._items(4)
        self.svc.handle_click(items, 1)   # ancre = 1
        self.svc.reset()
        self.svc.handle_click(items, 3, shift=True)  # shift sans ancre → clic simple
        selected = [i.Selected for i in items]
        self.assertEqual(selected, [False, False, False, True])


class TestFormatPropagate(unittest.TestCase):
    """Propagation PDF/DWG à la sélection lors du toggle d'un item sélectionné."""

    def _sheets(self, n):
        return [ManualSheetVM(str(i), u'F{}'.format(i)) for i in range(n)]

    def _make_propagate(self, sheets_ref, bulk):
        def propagate(source, prop, value):
            if not getattr(source, u'Selected', False):
                return
            selected = bulk.get_selected(sheets_ref[0])
            for item in selected:
                if item is not source:
                    try:
                        setattr(item, prop, value)
                    except Exception:
                        pass
        return propagate

    def setUp(self):
        from core import bulk_edit
        self.bulk = bulk_edit

    def test_toggle_pdf_propage_a_toute_la_selection(self):
        sheets = self._sheets(3)
        ref = [sheets]
        propagate = self._make_propagate(ref, self.bulk)
        for s in sheets:
            s._on_format_change = propagate
            s.Selected = True
        sheets[0].ExportPdf = False
        self.assertFalse(sheets[1].ExportPdf)
        self.assertFalse(sheets[2].ExportPdf)

    def test_toggle_dwg_propage_a_toute_la_selection(self):
        sheets = self._sheets(3)
        ref = [sheets]
        propagate = self._make_propagate(ref, self.bulk)
        for s in sheets:
            s._on_format_change = propagate
            s.Selected = True
        sheets[1].ExportDwg = True
        self.assertTrue(sheets[0].ExportDwg)
        self.assertTrue(sheets[2].ExportDwg)

    def test_toggle_ne_propage_pas_si_non_selectionne(self):
        sheets = self._sheets(3)
        ref = [sheets]
        propagate = self._make_propagate(ref, self.bulk)
        for s in sheets:
            s._on_format_change = propagate
        # Seul sheets[0] est sélectionné
        sheets[0].Selected = True
        sheets[0].ExportPdf = False
        self.assertTrue(sheets[1].ExportPdf)   # inchangé
        self.assertTrue(sheets[2].ExportPdf)   # inchangé


class TestMainViewModelToggleAll(unittest.TestCase):
    """Tests pour `toggle_all_pdf` / `toggle_all_dwg` et `handle_row_click`."""

    def _make_vm(self):
        from tests.test_main_viewmodel import (FakeSheetService,
                                               FakeNamingService, FakeConfig)
        vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                           naming_service=FakeNamingService(), config=FakeConfig())
        vm.refresh_manuel()
        return vm

    def test_toggle_all_pdf_active_tous_si_au_moins_un_off(self):
        vm = self._make_vm()
        sheets = vm.SheetsManuelFiltrees
        if not sheets:
            return
        sheets[0].ExportPdf = False   # au moins un off
        vm.toggle_all_pdf()
        self.assertTrue(all(s.ExportPdf for s in sheets))

    def test_toggle_all_pdf_desactive_tous_si_tous_on(self):
        vm = self._make_vm()
        sheets = vm.SheetsManuelFiltrees
        if not sheets:
            return
        for s in sheets:
            s._export_pdf = True   # force sans callback
        vm.toggle_all_pdf()
        self.assertTrue(all(not s.ExportPdf for s in sheets))

    def test_handle_row_click_selectionne_feuille(self):
        vm = self._make_vm()
        sheets = vm.SheetsManuelFiltrees
        if not sheets:
            return
        vm.handle_row_click(0)
        self.assertTrue(sheets[0].Selected)
        if len(sheets) > 1:
            self.assertFalse(sheets[1].Selected)

    def test_handle_row_click_shift_selectionne_plage(self):
        vm = self._make_vm()
        sheets = vm.SheetsManuelFiltrees
        if len(sheets) < 3:
            return
        vm.handle_row_click(0)
        vm.handle_row_click(2, shift=True)
        self.assertTrue(sheets[0].Selected)
        self.assertTrue(sheets[1].Selected)
        self.assertTrue(sheets[2].Selected)


class TestExportDoneCallback(unittest.TestCase):
    """_on_export_done_cb : déclenché après export réussi, absent ou ignoré
    sur les chemins d'échec (doc=None, sélection vide, exception)."""

    def test_callback_absent_par_defaut(self):
        vm = MainViewModel(doc=None)
        self.assertIsNone(vm._on_export_done_cb)

    def test_callback_non_appele_si_doc_none_auto(self):
        calls = []
        vm = MainViewModel(doc=None)
        vm._on_export_done_cb = lambda dest: calls.append(dest)
        vm.lancer_export()
        self.assertEqual(len(calls), 0)

    def test_callback_non_appele_si_doc_none_manuel(self):
        calls = []
        vm = MainViewModel(doc=None)
        vm._on_export_done_cb = lambda dest: calls.append(dest)
        vm.lancer_export_manuel()
        self.assertEqual(len(calls), 0)

    def test_callback_appele_apres_export_manuel_avec_doc_factice(self):
        calls = []
        dest_svc = FakeDestinationService(u'C:/Test/Export')
        vm = MainViewModel(
            doc=object(),
            sheet_service=FakeSheetService(),
            naming_service=FakeNamingService(),
            destination_service=dest_svc,
            config=FakeConfig(),
        )
        vm._on_export_done_cb = lambda dest: calls.append(dest)
        svm = ManualSheetVM(u'01', u'Feuille 1', export_pdf=True, export_dwg=False)
        vm._sheets_manuel = [svm]
        vm.lancer_export_manuel()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], u'C:/Test/Export')

    def test_status_text_vide_apres_export_manuel_reussi(self):
        dest_svc = FakeDestinationService(u'C:/Test')
        vm = MainViewModel(
            doc=object(),
            sheet_service=FakeSheetService(),
            naming_service=FakeNamingService(),
            destination_service=dest_svc,
            config=FakeConfig(),
        )
        svm = ManualSheetVM(u'01', u'Feuille 1', export_pdf=True)
        vm._sheets_manuel = [svm]
        vm.lancer_export_manuel()
        self.assertNotIn(u'Termin', vm.StatusText)
        self.assertNotIn(u'Log', vm.StatusText)

    def test_callback_non_appele_si_exception_dans_orchestrateur(self):
        calls = []

        class OrchestrateurtQuiLeve(object):
            def __init__(self, namespace='batch_export', config=None):
                pass

            def erreur_dependances(self):
                return None

            def run_manual(self, *a, **kw):
                raise RuntimeError(u'échec simulé')

        vm = MainViewModel(
            doc=object(),
            sheet_service=FakeSheetService(),
            naming_service=FakeNamingService(),
            destination_service=FakeDestinationService(u'C:/Test'),
            config=FakeConfig(),
        )
        vm._on_export_done_cb = lambda dest: calls.append(dest)
        svm = ManualSheetVM(u'01', u'Feuille 1', export_pdf=True)
        vm._sheets_manuel = [svm]

        import lib.services.ExportOrchestrator as _eo_mod
        _orig = _eo_mod.ExportOrchestrator
        _eo_mod.ExportOrchestrator = OrchestrateurtQuiLeve
        try:
            vm.lancer_export_manuel()
        finally:
            _eo_mod.ExportOrchestrator = _orig

        self.assertEqual(len(calls), 0)
        self.assertIn(u'erreur', vm.StatusText.lower())


class TestCollectionItemVMSetters(unittest.TestCase):
    """Setters des trois flags (badges cliquables du mode « par jeu ») :
    chacun notifie ses propriétés dérivées et rappelle `on_change`, et le
    garde « même valeur » coupe court avant toute notification."""

    def setUp(self):
        self.appels = []
        self.notifs = []
        self.item = CollectionItemVM(
            u'Jeu A', u'id-A', False, False, False, [],
            carnet_apercu=u'CARNET-A.pdf',
            on_change=lambda source: self.appels.append(source),
        )
        # Hors Revit `notify_property` est un no-op (BaseViewModel sans WPF) :
        # on le shadow au niveau de l'instance pour observer les notifications.
        self.item.notify_property = lambda nom: self.notifs.append(nom)

    def test_flag_export_bascule_aussi_qualified(self):
        self.assertFalse(self.item.Qualified)
        self.item.FlagExport = True
        self.assertTrue(self.item.FlagExport)
        self.assertTrue(self.item.Qualified)
        self.assertEqual(self.notifs, [u'FlagExport', u'Qualified'])
        self.assertEqual(len(self.appels), 1)

    def test_flag_carnet_bascule_carnet_apercu_visible(self):
        self.assertFalse(self.item.CarnetApercuVisible)
        self.item.FlagCarnet = True
        self.assertTrue(self.item.CarnetApercuVisible)
        self.assertEqual(self.notifs, [u'FlagCarnet', u'CarnetApercuVisible'])
        self.assertEqual(len(self.appels), 1)

    def test_flag_dwg_notifie_et_rappelle_on_change(self):
        self.item.FlagDwg = True
        self.assertTrue(self.item.FlagDwg)
        self.assertEqual(self.notifs, [u'FlagDwg'])
        self.assertEqual(len(self.appels), 1)

    def test_meme_valeur_ne_notifie_ni_ne_rappelle(self):
        self.item.FlagExport = False  # déjà False
        self.item.FlagCarnet = False
        self.item.FlagDwg = False
        self.assertEqual(self.notifs, [])
        self.assertEqual(self.appels, [])

    def test_valeur_non_booleenne_normalisee(self):
        self.item.FlagExport = 1
        self.assertIs(self.item.FlagExport, True)
        self.item.FlagExport = 1  # même valeur après normalisation -> garde
        self.assertEqual(len(self.appels), 1)


class TestMainViewModelCollectionsEditables(unittest.TestCase):
    """`Collections` : liste UNIQUE et éditable. Les flags viennent des
    badges mémorisés (config) puis suivent les clics de l'utilisateur."""

    def setUp(self):
        self.sheet_service = FakeSheetService()
        self.vm = MainViewModel(
            doc=None,
            sheet_service=self.sheet_service,
            naming_service=FakeNamingServiceCarnet(),
            destination_service=None,
            config=config_avec_badges({u'Jeu A': (True, True, False)}),
        )
        self.vm.refresh_par_jeu()

    def _jeu(self, titre):
        return next(c for c in self.vm.Collections if c.Titre == titre)

    def test_flags_repris_des_badges_memorises(self):
        jeu_a = self._jeu(u'Jeu A')
        self.assertTrue(jeu_a.FlagExport)
        self.assertTrue(jeu_a.FlagCarnet)
        self.assertFalse(jeu_a.FlagDwg)
        # Jeu B absent de la config -> tout éteint.
        self.assertFalse(self._jeu(u'Jeu B').FlagExport)

    def test_chaque_item_porte_le_callback_du_vm(self):
        # Badges cliquables : sans `on_change`, ni les compteurs ni la
        # persistance des choix (cf. `_badges_jeux`) ne fonctionneraient.
        for c in self.vm.Collections:
            self.assertTrue(callable(c._on_change))

    def test_les_choix_survivent_a_un_refresh_en_cours_de_session(self):
        """`refresh_par_jeu()` est ré-appelé en cours de session (retour de la
        modale de nommage) : les badges cliqués doivent être reportés."""
        jeu_a = self._jeu(u'Jeu A')
        jeu_a.FlagExport = False
        jeu_a.FlagDwg = True

        self.vm.refresh_par_jeu()

        apres = self._jeu(u'Jeu A')
        self.assertFalse(apres.FlagExport)
        self.assertTrue(apres.FlagDwg)


class TestMainViewModelCompteurs(unittest.TestCase):
    """`NbJeuxQualifies`/`NbFeuillesQualifiees` : calculés sur `Collections`,
    donc sensibles aux clics sur les badges et INDÉPENDANTS du mode."""

    def setUp(self):
        self.vm = MainViewModel(
            doc=None,
            sheet_service=FakeSheetService(),
            naming_service=FakeNamingService(),
            destination_service=None,
            config=config_avec_badges({u'Jeu A': (True, True, False)}),
        )
        self.vm.refresh_par_jeu()

    def test_compteurs_refletent_les_badges_memorises(self):
        # Jeu A seul coché, avec ses 2 feuilles.
        self.assertEqual(self.vm.NbJeuxQualifies, 1)
        self.assertEqual(self.vm.NbFeuillesQualifiees, 2)

    def test_clic_sur_un_badge_met_a_jour_les_compteurs(self):
        # Jeu A (2 feuilles) décoché, Jeu B (1 feuille) coché.
        self.vm.Collections[0].FlagExport = False
        self.vm.Collections[1].FlagExport = True
        self.assertEqual(self.vm.NbJeuxQualifies, 1)
        self.assertEqual(self.vm.NbFeuillesQualifiees, 1)

    def test_compteurs_identiques_quel_que_soit_le_mode(self):
        for mode in (u'auto', u'manual', u'settings'):
            self.vm.set_mode(mode)
            self.assertEqual(self.vm.NbJeuxQualifies, 1)
            self.assertEqual(self.vm.NbFeuillesQualifiees, 2)


class OrchestrateurEspion(object):
    """Faux ExportOrchestrator : retient les arguments reçus par `run()` et
    rend True comme un export réussi. `run` ne nomme que `doc` afin que le
    test puisse vérifier que `flags` arrive bien en 2e POSITIONNEL."""

    appels = []

    def __init__(self, namespace='batch_export', config=None):
        pass

    def erreur_dependances(self):
        return None

    def run(self, doc, *args, **kw):
        OrchestrateurEspion.appels.append({'args': args, 'kw': kw})
        return True


class TestMainViewModelLancerExportParJeu(unittest.TestCase):
    """`lancer_export()` (mode « par jeu ») : les badges cochés partent en
    `flags=[(titre, export, carnet, dwg), ...]`, 2e argument POSITIONNEL de
    `run()`. Seule source de qualification de l'export."""

    def setUp(self):
        OrchestrateurEspion.appels = []
        self.vm = MainViewModel(
            doc=object(),
            sheet_service=FakeSheetService(),
            naming_service=FakeNamingService(),
            destination_service=FakeDestinationService(u'C:/Test'),
            config=config_avec_badges({u'Jeu A': (True, True, False)}),
        )
        self.vm.refresh_par_jeu()

    def _lancer(self):
        import lib.services.ExportOrchestrator as _eo_mod
        _orig = _eo_mod.ExportOrchestrator
        _eo_mod.ExportOrchestrator = OrchestrateurEspion
        try:
            self.vm.lancer_export()
        finally:
            _eo_mod.ExportOrchestrator = _orig
        self.assertEqual(len(OrchestrateurEspion.appels), 1)
        return OrchestrateurEspion.appels[0]

    def test_flags_transmis_en_deuxieme_positionnel(self):
        appel = self._lancer()
        self.assertEqual(len(appel['args']), 1)
        self.assertNotIn('flags', appel['kw'])
        self.assertEqual(appel['args'][0], [(u'Jeu A', True, True, False),
                                            (u'Jeu B', False, False, False)])

    def test_flags_refletent_les_badges_cliques(self):
        self.vm.Collections[0].FlagCarnet = False
        self.vm.Collections[1].FlagExport = True
        self.vm.Collections[1].FlagDwg = True
        appel = self._lancer()
        self.assertEqual(appel['args'][0], [(u'Jeu A', True, False, False),
                                            (u'Jeu B', True, False, True)])

    def test_flags_portent_des_booleens_pas_des_noms_de_parametres(self):
        appel = self._lancer()
        for titre, export, carnet, dwg in appel['args'][0]:
            self.assertIsInstance(titre, type(u''))
            for valeur in (export, carnet, dwg):
                self.assertIsInstance(valeur, bool)

    def test_destination_transmise_a_l_orchestrateur(self):
        appel = self._lancer()
        self.assertEqual(appel['kw']['destination'], u'C:/Test')


if __name__ == '__main__':
    unittest.main()
