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
    DESCR = [(1, u'Béton', u'Béton coulé'), (2, u'Bois', u'Chêne')]
    PAR_ID = {1: u'materiau-1', 2: u'materiau-2'}

    def test_charger_peuple_la_page_selection(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [])
        self.assertEqual(vm.Mode, u'selection')
        self.assertEqual(len(vm.SelectionVM.AllItems), 2)
        self.assertFalse(vm.SelectionVM.HasSelection)
        self.assertEqual(vm.lancer(self.PAR_ID), [])

    def test_lancer_rend_les_materiaux_coches(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [2])
        self.assertEqual(vm.SelectedMaterialIds, [2])
        self.assertEqual(vm.lancer(self.PAR_ID), [u'materiau-2'])

    def test_selection_page_remonte_les_changements(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [])
        vm.SelectionVM.select_all()
        self.assertEqual(sorted(vm.SelectedMaterialIds), [1, 2])
        self.assertEqual(vm.lancer(self.PAR_ID), [u'materiau-1', u'materiau-2'])


if __name__ == '__main__':
    unittest.main()
