# -*- coding: utf-8 -*-
from __future__ import unicode_literals
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

from lib.viewmodels.MainViewModel import MainViewModel


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
    """Faux UserConfig en mémoire (même contrat get/set, cf. FakeConfig de
    test_sheet_collection_service.py). Nécessaire car le vrai `UserConfig`
    est instanciable hors Revit mais son backend pyRevit est absent -> get/set
    deviennent des no-op silencieux, rendant le mapping ParamExport/Carnet/Dwg
    non testable sans injection."""

    def __init__(self):
        self._store = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value):
        self._store[key] = value
        return True


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
    """Faux SheetCollectionService : 2 collections (une qualifiée, une non)."""

    def __init__(self):
        self._elem_a = FakeCollectionElem('A')
        self._elem_b = FakeCollectionElem('B')
        self._flags = {
            (self._elem_a, 'Export'): True,
            (self._elem_a, 'Carnet'): True,
            (self._elem_a, 'Dwg'): False,
            (self._elem_b, 'Export'): False,
            (self._elem_b, 'Carnet'): False,
            (self._elem_b, 'Dwg'): False,
        }
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

    def read_flag(self, elem, param_name):
        return self._flags.get((elem, param_name), False)

    def list_boolean_params(self):
        return ['A', 'B', 'C']


class FakeNamingService(object):
    """Faux NamingService : exerce le chemin resolve_for_element (non vide)."""

    def load(self, kind):
        return ('', [{'Name': 'Numero_Feuille', 'Prefix': '', 'Suffix': '-'}])

    def resolve_for_element(self, elem, rows):
        numero = getattr(elem, 'numero', '')
        return u'PROJETE-{}'.format(numero)


class TestMainViewModelParJeu(unittest.TestCase):
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
        # Mapping paramètres attendu par FakeSheetService.read_flag
        self.vm.ParamExport = 'Export'
        self.vm.ParamCarnet = 'Carnet'
        self.vm.ParamDwg = 'Dwg'

    def test_refresh_par_jeu_construit_deux_collections(self):
        self.vm.refresh_par_jeu()
        self.assertEqual(len(self.vm.Collections), 2)

    def test_refresh_par_jeu_flags_corrects(self):
        self.vm.refresh_par_jeu()
        jeu_a = self.vm.Collections[0]
        jeu_b = self.vm.Collections[1]
        self.assertTrue(jeu_a.FlagExport)
        self.assertTrue(jeu_a.FlagCarnet)
        self.assertFalse(jeu_a.FlagDwg)
        self.assertTrue(jeu_a.Qualified)
        self.assertFalse(jeu_b.FlagExport)
        self.assertFalse(jeu_b.Qualified)

    def test_refresh_par_jeu_nb_jeux_qualifies(self):
        self.vm.refresh_par_jeu()
        self.assertEqual(self.vm.NbJeuxQualifies, 1)

    def test_refresh_par_jeu_nb_feuilles_qualifiees(self):
        self.vm.refresh_par_jeu()
        # Seul le Jeu A (qualifié) compte ses 2 feuilles.
        self.assertEqual(self.vm.NbFeuillesQualifiees, 2)

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
        self.assertTrue(jeu_a.FlagExport)
        self.assertTrue(jeu_a.Qualified)
        self.assertEqual(jeu_a.Sheets[0].Numero, '01')


class TestMainViewModelMappingParametres(unittest.TestCase):
    """Mapping paramètres : getters par défaut + setters persistants (fausse config)."""

    def setUp(self):
        self.vm = MainViewModel(doc=None, sheet_service=FakeSheetService(),
                                 naming_service=FakeNamingService(),
                                 config=FakeConfig())

    def test_param_export_par_defaut_vide(self):
        vm = MainViewModel(doc=None)
        self.assertEqual(vm.ParamExport, u'')
        self.assertEqual(vm.ParamCarnet, u'')
        self.assertEqual(vm.ParamDwg, u'')

    def test_param_export_setter_relit_la_valeur(self):
        self.vm.ParamExport = u'MonParamExport'
        self.assertEqual(self.vm.ParamExport, u'MonParamExport')

    def test_param_carnet_dwg_setters(self):
        self.vm.ParamCarnet = u'MonCarnet'
        self.vm.ParamDwg = u'MonDwg'
        self.assertEqual(self.vm.ParamCarnet, u'MonCarnet')
        self.assertEqual(self.vm.ParamDwg, u'MonDwg')


class TestMainViewModelModeParametres(unittest.TestCase):
    """Mode Paramètres (Task 4) : ParametresDisponibles + re-qualification
    déclenchée par les setters ParamExport/ParamCarnet/ParamDwg."""

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

    def test_parametres_disponibles_source_service(self):
        self.assertEqual(self.vm.ParametresDisponibles, ['A', 'B', 'C'])

    def test_parametres_disponibles_vide_sans_service(self):
        vm = MainViewModel(doc=None)
        self.assertEqual(vm.ParametresDisponibles, [])

    def test_parametres_disponibles_vide_si_service_sans_methode(self):
        class ServiceSansListBooleanParams(object):
            def list_collections(self):
                return []

            def list_sheets(self, collection_id=None):
                return []

        vm = MainViewModel(doc=None, sheet_service=ServiceSansListBooleanParams(),
                            config=FakeConfig())
        self.assertEqual(vm.ParametresDisponibles, [])

    def test_setter_param_export_declenche_requalification(self):
        # FakeSheetService qualifie Jeu A si le paramètre 'Export' est vrai.
        self.vm.ParamExport = 'Export'
        jeu_a = self.vm.Collections[0]
        self.assertTrue(jeu_a.FlagExport)
        self.assertTrue(jeu_a.Qualified)

    def test_setter_param_carnet_declenche_requalification(self):
        self.vm.ParamCarnet = 'Carnet'
        jeu_a = self.vm.Collections[0]
        self.assertTrue(jeu_a.FlagCarnet)

    def test_setter_param_dwg_declenche_requalification(self):
        self.vm.ParamExport = 'Export'
        self.vm.ParamDwg = 'Dwg'
        jeu_b = self.vm.Collections[1]
        self.assertFalse(jeu_b.FlagDwg)

    def test_setter_valeur_identique_est_idempotent(self):
        self.vm.ParamExport = 'Export'
        appels_avant = len(self.vm.Collections)
        # Réassigner la même valeur ne doit pas planter ni changer l'état.
        self.vm.ParamExport = 'Export'
        self.assertEqual(len(self.vm.Collections), appels_avant)
        self.assertEqual(self.vm.ParamExport, 'Export')

    def test_setter_ne_leve_pas_sans_service(self):
        vm = MainViewModel(doc=None, config=FakeConfig())
        vm.ParamExport = 'X'
        self.assertEqual(vm.ParamExport, 'X')


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
        """Vérifie que `from lib.services.core.ExportOrchestrator import ...`
        (chemin utilisé par `lancer_export()`) fait résoudre correctement les
        imports RELATIFS internes de l'orchestrateur (`from ...core.UserConfig`,
        `from ...data...`, `from ...services.formats...`), qui exigent que le
        package racine soit `lib` (donc `lib.services.core`).

        Importé sous `services.core.ExportOrchestrator` (package racine
        `services`), ces `...` remonteraient au-dessus de `lib` et tous les
        try/except internes retomberaient sur `None` -- l'orchestrateur
        « fonctionnerait » alors en mode dégradé silencieux (dossier courant,
        sans options de pattern/PDF/DWG). Ce test fige le chemin d'import
        correct pour que toute régression de packaging (ex: `__init__.py`
        manquant sous `lib/data/`) soit détectée hors Revit."""
        from lib.services.core.ExportOrchestrator import ExportOrchestrator
        orch = ExportOrchestrator()
        self.assertIsNotNone(orch._dest)
        self.assertIsNotNone(orch._nstore)
        self.assertIsNotNone(orch._pdf)
        self.assertIsNotNone(orch._dwg)
        self.assertIsNotNone(orch._cfg)


class FakeDestinationService(object):
    """Faux DestinationService : mêmes méthodes que le vrai (get/set/ensure),
    mais `set` enregistre l'argument reçu pour vérification (pas de disque)."""

    def __init__(self, initial=u''):
        self._path = initial
        self.set_calls = []
        self.ensure_calls = []

    def get(self, default=None):
        return self._path

    def set(self, path):
        self.set_calls.append(path)
        self._path = path
        return True

    def ensure(self, path):
        self.ensure_calls.append(path)
        return path


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


if __name__ == '__main__':
    unittest.main()
