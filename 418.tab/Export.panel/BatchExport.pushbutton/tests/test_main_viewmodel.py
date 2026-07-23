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


class TestMainViewModelServicesParDefaut(unittest.TestCase):
    """Sans injection, le VM ne doit jamais lever (hors Revit -> services None ou vides)."""

    def test_construction_sans_services_ne_leve_pas(self):
        vm = MainViewModel(doc=None)
        vm.refresh_par_jeu()
        self.assertEqual(vm.Collections, [])
        self.assertEqual(vm.NbJeuxQualifies, 0)
        self.assertEqual(vm.NbFeuillesQualifiees, 0)


if __name__ == '__main__':
    unittest.main()
