# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.viewmodels.SelectionPageVM import SelectionPageVM


class TestSelectionPageVM(unittest.TestCase):
    def setUp(self):
        self.descripteurs = [(1, u'A101', u'RDC'), (2, u'A102', u'R+1'), (3, u'A103', u'R+2')]
        self.changes = []

    def _vm(self, ids):
        return SelectionPageVM(self.descripteurs, ids,
                               on_selection_changed=lambda l: self.changes.append(list(l)))

    def test_items_precoches_selon_selection(self):
        vm = self._vm([2])
        etats = [(it.Numero, it.IsSelected) for it in vm.FilteredItems]
        self.assertEqual(etats, [(u'A101', False), (u'A102', True), (u'A103', False)])

    def test_toggle_met_a_jour_selection_et_notifie(self):
        vm = self._vm([])
        vm.FilteredItems[0].IsSelected = True
        vm.FilteredItems[2].IsSelected = True
        self.assertEqual(sorted(vm.selected_ids()), [1, 3])
        self.assertEqual(self.changes[-1], [1, 3])

    def test_decoche_retire_de_la_selection(self):
        vm = self._vm([1, 2])
        vm.FilteredItems[0].IsSelected = False
        self.assertEqual(vm.selected_ids(), [2])

    def test_has_selection_reflete_l_etat(self):
        vm = self._vm([])
        self.assertFalse(vm.HasSelection)
        vm.FilteredItems[0].IsSelected = True
        self.assertTrue(vm.HasSelection)
        vm.FilteredItems[0].IsSelected = False
        self.assertFalse(vm.HasSelection)


if __name__ == '__main__':
    unittest.main()
