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


class _ItemNotifiant(object):
    """Un ItemVM qui prévient sa page quand sa case est écrite — le cas des
    MaterialCardVM. `_Item` ci-dessus est muet, les deux existent."""

    def __init__(self, iid, a):
        self.Id = iid
        self.A = a
        self.on_toggle = None
        self._selected = False

    @property
    def IsSelected(self):
        return self._selected

    @IsSelected.setter
    def IsSelected(self, value):
        value = bool(value)
        if value == self._selected:
            return
        self._selected = value
        if self.on_toggle is not None:
            self.on_toggle(self)


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


class TestPresets(unittest.TestCase):
    """Sélections préfabriquées : la page applique un prédicat fourni par
    l'outil, coche ce qui répond ET décoche le reste."""

    PRESETS = (
        (u'Tout', lambda it: True),
        (u'Aucun', lambda it: False),
        (u'Les A', lambda it: it.A.startswith(u'A')),
    )

    def _vm_presets(self, items=None):
        return SelectionPageVM(
            items if items is not None else _make(),
            id_getter=lambda it: it.Id,
            filter_getters=[lambda it: it.A],
            presets=self.PRESETS)

    def test_sans_presets_pas_de_menu(self):
        self.assertFalse(_vm().HasPresets)

    def test_le_libelle_neutre_ouvre_la_liste(self):
        c = self._vm_presets()
        self.assertTrue(c.HasPresets)
        self.assertEqual(c.Presets,
                         [SelectionPageVM.PLACEHOLDER, u'Tout', u'Aucun',
                          u'Les A'])

    def test_un_preset_coche_ce_qui_repond_et_decoche_le_reste(self):
        c = self._vm_presets()
        c.Preset = u'Tout'
        self.assertEqual(c.selected_ids(), [1, 2, 3])
        c.Preset = u'Les A'
        self.assertEqual(c.selected_ids(), [1, 2])
        c.Preset = u'Aucun'
        self.assertEqual(c.selected_ids(), [])

    def test_le_menu_reste_sur_le_libelle_neutre(self):
        # C'est une ACTION : re-choisir le même critère doit le rejouer.
        c = self._vm_presets()
        c.Preset = u'Les A'
        self.assertEqual(c.Preset, SelectionPageVM.PLACEHOLDER)

    def test_le_libelle_neutre_ne_touche_a_rien(self):
        c = self._vm_presets()
        c.Preset = u'Tout'
        c.Preset = SelectionPageVM.PLACEHOLDER
        c.Preset = u'inconnu'
        self.assertEqual(c.selected_ids(), [1, 2, 3])

    def test_un_preset_porte_sur_la_liste_complete(self):
        # Comme select_all : les items masqués par la recherche sont inclus.
        c = self._vm_presets()
        c.FilterText = u'B-201'
        c.Preset = u'Tout'
        self.assertEqual(c.selected_ids(), [1, 2, 3])

    def test_un_preset_n_avertit_l_hote_qu_une_fois(self):
        """Le lot doit rester UN évènement. Sinon l'hôte recalcule sa page
        une fois par item — l'aperçu de renommage de « Matériaux »."""
        vus = []
        items = [_ItemNotifiant(1, u'A-101'), _ItemNotifiant(2, u'A-102'),
                 _ItemNotifiant(3, u'B-201')]
        c = SelectionPageVM(
            items, id_getter=lambda it: it.Id,
            filter_getters=[lambda it: it.A], presets=self.PRESETS,
            on_selection_changed=lambda ids: vus.append(list(ids)))
        for item in items:
            item.on_toggle = c._on_item_toggle
        c.Preset = u'Tout'
        self.assertEqual(vus, [[1, 2, 3]])
        c.select_all()
        c.deselect_all()
        self.assertEqual(vus, [[1, 2, 3], [1, 2, 3], []])


if __name__ == '__main__':
    unittest.main()
