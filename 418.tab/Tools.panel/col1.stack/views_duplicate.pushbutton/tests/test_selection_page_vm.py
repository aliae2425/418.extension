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
        self.descripteurs = [
            (1, u'Vue Plan RDC', u'FloorPlan'),
            (2, u'Vue Plan R+1', u'FloorPlan'),
            (3, u'Section A', u'Section'),
        ]
        self.changes = []

    def _vm(self, ids):
        return SelectionPageVM(self.descripteurs, ids,
                               on_selection_changed=lambda l: self.changes.append(list(l)))

    def test_items_precoches_selon_selection(self):
        vm = self._vm([2])
        etats = [(it.Nom, it.IsSelected) for it in vm.Items]
        self.assertEqual(etats, [
            (u'Vue Plan RDC', False),
            (u'Vue Plan R+1', True),
            (u'Section A', False),
        ])

    def test_toggle_met_a_jour_selection_et_notifie(self):
        vm = self._vm([])
        vm.Items[0].IsSelected = True
        vm.Items[2].IsSelected = True
        self.assertEqual(sorted(vm.selected_ids()), [1, 3])
        self.assertEqual(sorted(self.changes[-1]), [1, 3])

    def test_decoche_retire_de_la_selection(self):
        vm = self._vm([1, 2])
        vm.Items[0].IsSelected = False
        self.assertEqual(vm.selected_ids(), [2])

    def test_has_selection_reflete_l_etat(self):
        vm = self._vm([])
        self.assertFalse(vm.HasSelection)
        vm.Items[0].IsSelected = True
        self.assertTrue(vm.HasSelection)
        vm.Items[0].IsSelected = False
        self.assertFalse(vm.HasSelection)

    def test_type_label_accessible(self):
        vm = self._vm([])
        self.assertEqual(vm.Items[2].TypeLabel, u'Section')


if __name__ == '__main__':
    unittest.main()
