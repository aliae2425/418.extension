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


class TestMainViewModel(unittest.TestCase):
    DESCR = [(1, u'A101', u'RDC'), (2, u'A102', u'R+1')]

    def test_decide_initial_mode(self):
        self.assertEqual(MainViewModel.decide_initial_mode(True), u'params')
        self.assertEqual(MainViewModel.decide_initial_mode(False), u'selection')

    def test_charger_avec_selection_ouvre_params(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [1])
        self.assertEqual(vm.Mode, u'params')
        self.assertTrue(vm.IsParams)
        self.assertFalse(vm.IsSelection)
        self.assertFalse(vm.IsOptions)
        self.assertEqual(vm.SelectedSheetIds, [1])

    def test_charger_sans_selection_ouvre_selection(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [])
        self.assertEqual(vm.Mode, u'selection')
        self.assertTrue(vm.IsSelection)

    def test_toggle_dans_page_met_a_jour_etat_partage(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [])
        vm.SelectionVM.FilteredItems[1].IsSelected = True  # coche A102 (id 2)
        self.assertEqual(vm.SelectedSheetIds, [2])

    def test_set_mode(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [1])
        vm.set_mode(u'selection')
        self.assertEqual(vm.Mode, u'selection')


if __name__ == '__main__':
    unittest.main()
