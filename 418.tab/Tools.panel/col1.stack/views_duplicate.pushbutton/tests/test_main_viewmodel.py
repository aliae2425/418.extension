# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
# Meme racine que pyRevit expose : <bouton>/lib.
_BUTTON_LIB = os.path.abspath(os.path.join(_HERE, '..', 'lib'))
if _BUTTON_LIB not in sys.path:
    sys.path.insert(0, _BUTTON_LIB)

from viewmodels.MainViewModel import MainViewModel


class FakeService(object):
    """Service factice qui enregistre les appels sans accéder à Revit."""

    def __init__(self, result=None):
        self.appels = []
        self._result = result or []

    def duplicate(self, views, options):
        self.appels.append((list(views), options))
        return self._result


class TestMainViewModel(unittest.TestCase):
    DESCR = [(1, u'Vue Plan RDC', u'FloorPlan'), (2, u'Section A', u'Section')]

    def test_decide_initial_mode(self):
        self.assertEqual(MainViewModel.decide_initial_mode(True), u'options')
        self.assertEqual(MainViewModel.decide_initial_mode(False), u'selection')

    def test_charger_avec_selection_ouvre_options(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [1])
        self.assertEqual(vm.Mode, u'options')
        self.assertTrue(vm.IsOptions)
        self.assertFalse(vm.IsSelection)
        self.assertEqual(vm.SelectedViewIds, [1])

    def test_charger_sans_selection_ouvre_selection(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [])
        self.assertEqual(vm.Mode, u'selection')
        self.assertTrue(vm.IsSelection)

    def test_toggle_dans_page_met_a_jour_etat_partage(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [])
        vm.SelectionVM.FilteredItems[1].IsSelected = True  # coche Section A (id 2)
        self.assertEqual(vm.SelectedViewIds, [2])

    def test_set_mode(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [1])
        vm.set_mode(u'selection')
        self.assertEqual(vm.Mode, u'selection')

    def test_lancer_appelle_service(self):
        svc = FakeService(result=[10, 11])
        vm = MainViewModel(service=svc)
        vm.charger(self.DESCR, [1])
        fake_view = object()
        result = vm.lancer({1: fake_view})
        self.assertEqual(result, [10, 11])
        self.assertEqual(len(svc.appels), 1)
        self.assertIn(fake_view, svc.appels[0][0])

    def test_lancer_sans_service_retourne_liste_vide(self):
        vm = MainViewModel(service=None)
        vm.charger(self.DESCR, [1])
        self.assertEqual(vm.lancer({1: object()}), [])


if __name__ == '__main__':
    unittest.main()
