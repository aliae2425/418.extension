# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
# 418.extension/lib (tests -> ui -> lib)
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from ui.base.SelectionPageVM import SelectionPageVM


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


def _vm(items=None, on_selection_changed=None):
    return SelectionPageVM(
        items if items is not None else _make(),
        id_getter=lambda it: it.Id,
        filter_getters=[lambda it: it.A, lambda it: it.B],
        on_selection_changed=on_selection_changed)


class TestSelectionPageVM(unittest.TestCase):

    def test_clic_simple_bascule_un_item(self):
        c = _vm()
        c.handle_row_click(0)
        self.assertEqual(c.selected_ids(), [1])
        c.handle_row_click(1)              # accumule (pas d'exclusif)
        self.assertEqual(c.selected_ids(), [1, 2])

    def test_clic_simple_rebascule(self):
        c = _vm()
        c.handle_row_click(0)
        c.handle_row_click(0)
        self.assertEqual(c.selected_ids(), [])

    def test_shift_selectionne_la_plage(self):
        c = _vm()
        c.handle_row_click(0)             # ancre 0
        c.handle_row_click(2, shift=True)
        self.assertEqual(c.selected_ids(), [1, 2, 3])

    def test_filtre_restreint_filtered_items(self):
        c = _vm()
        c.FilterText = u'plan'
        self.assertEqual([it.Id for it in c.FilteredItems], [1, 2])

    def test_shift_agit_sur_le_sous_ensemble_filtre(self):
        c = _vm()
        c.FilterText = u'plan'            # visibles : items 1,2
        c.handle_row_click(0)             # -> item 1
        c.handle_row_click(1, shift=True) # plage sur filtré -> 1,2
        self.assertEqual(c.selected_ids(), [1, 2])

    def test_changement_de_filtre_reset_ancre(self):
        c = _vm()
        c.handle_row_click(0)             # ancre 0 sur liste complète
        c.FilterText = u'plan'            # reset ancre
        c.handle_row_click(1, shift=True) # ancre perdue -> clic simple index 1
        self.assertEqual(c.selected_ids(), [1, 2])  # 1 restait coché + bascule 2

    def test_select_all_agit_sur_liste_complete_meme_filtree(self):
        c = _vm()
        c.FilterText = u'plan'            # n'affiche que 1,2
        c.select_all()
        self.assertEqual(c.selected_ids(), [1, 2, 3])  # inclut le masqué

    def test_deselect_all(self):
        c = _vm()
        c.select_all()
        c.deselect_all()
        self.assertEqual(c.selected_ids(), [])

    def test_has_selection(self):
        c = _vm()
        self.assertFalse(c.HasSelection)
        c.handle_row_click(0)
        self.assertTrue(c.HasSelection)

    def test_callback_recoit_les_ids_selectionnes(self):
        vus = []
        c = _vm(on_selection_changed=lambda ids: vus.append(list(ids)))
        c.handle_row_click(0)
        c.select_all()
        c.deselect_all()
        self.assertEqual(vus, [[1], [1, 2, 3], []])

    def test_item_toggle_direct_notifie_l_hote(self):
        # Une case cochée directement sur l'ItemVM passe par _on_item_toggle.
        vus = []
        items = _make()
        c = _vm(items=items, on_selection_changed=lambda ids: vus.append(list(ids)))
        items[2].IsSelected = True
        c._on_item_toggle(items[2])
        self.assertEqual(vus, [[3]])


if __name__ == '__main__':
    unittest.main()
