# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.selection_list import SelectionListController


class _Item(object):
    def __init__(self, iid, a, b):
        self.Id = iid
        self.A = a
        self.B = b
        self.IsSelected = False


def _make():
    return [_Item(1, u'A-101', u'Plan RDC'),
            _Item(2, u'A-102', u'Plan R+1'),
            _Item(3, u'B-201', u'Coupe AA')]


def _ctrl(items):
    return SelectionListController(
        items,
        id_getter=lambda it: it.Id,
        filter_getters=[lambda it: it.A, lambda it: it.B])


class TestSelectionList(unittest.TestCase):

    def test_clic_simple_bascule_un_item(self):
        c = _ctrl(_make())
        c.handle_row_click(0)
        self.assertEqual(c.selected_ids(), [1])
        c.handle_row_click(1)              # accumule (pas d'exclusif)
        self.assertEqual(c.selected_ids(), [1, 2])

    def test_clic_simple_rebascule(self):
        c = _ctrl(_make())
        c.handle_row_click(0)
        c.handle_row_click(0)
        self.assertEqual(c.selected_ids(), [])

    def test_shift_selectionne_la_plage(self):
        c = _ctrl(_make())
        c.handle_row_click(0)             # ancre 0
        c.handle_row_click(2, shift=True)
        self.assertEqual(c.selected_ids(), [1, 2, 3])

    def test_filtre_restreint_filtered_items(self):
        c = _ctrl(_make())
        c.filter_text = u'plan'
        self.assertEqual([it.Id for it in c.filtered_items], [1, 2])

    def test_shift_agit_sur_le_sous_ensemble_filtre(self):
        c = _ctrl(_make())
        c.filter_text = u'plan'           # visibles : items 1,2
        c.handle_row_click(0)             # -> item 1
        c.handle_row_click(1, shift=True) # plage sur filtré -> 1,2
        self.assertEqual(c.selected_ids(), [1, 2])

    def test_changement_de_filtre_reset_ancre(self):
        c = _ctrl(_make())
        c.handle_row_click(0)             # ancre 0 sur liste complète
        c.filter_text = u'plan'           # reset ancre
        c.handle_row_click(1, shift=True) # ancre perdue -> clic simple sur index 1
        self.assertEqual(c.selected_ids(), [1, 2])  # item 1 restait coché + bascule item 2

    def test_select_all_agit_sur_liste_complete_meme_filtree(self):
        c = _ctrl(_make())
        c.filter_text = u'plan'           # n'affiche que 1,2
        c.select_all()
        self.assertEqual(c.selected_ids(), [1, 2, 3])  # inclut le masqué

    def test_deselect_all(self):
        c = _ctrl(_make())
        c.select_all()
        c.deselect_all()
        self.assertEqual(c.selected_ids(), [])

    def test_has_selection(self):
        c = _ctrl(_make())
        self.assertFalse(c.has_selection())
        c.handle_row_click(0)
        self.assertTrue(c.has_selection())


if __name__ == '__main__':
    unittest.main()
