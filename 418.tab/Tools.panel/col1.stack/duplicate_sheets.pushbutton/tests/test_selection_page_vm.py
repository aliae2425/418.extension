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

# La page Sélection elle-même est couverte par lib/ui/tests/test_selection_page_vm.py.
# Ici on vérifie le raccordement propre à l'outil « feuilles » : les
# descripteurs arrivent déjà dans l'ordre attendu (id, numéro, nom), et le
# numéro de feuille doit être rendu comme un IDENTIFIANT (gras) et non comme
# une métadonnée.


class TestChargementSelectionFeuilles(unittest.TestCase):
    def setUp(self):
        self.descripteurs = [(1, u'A101', u'RDC'),
                             (2, u'A102', u'R+1'),
                             (3, u'A103', u'R+2')]

    def _vm(self, ids_courants):
        vm = MainViewModel(doc=None, uidoc=None, service=None)
        vm.charger(self.descripteurs, ids_courants)
        return vm

    def test_colonne_gauche_est_le_numero(self):
        vm = self._vm([])
        items = vm.SelectionVM.FilteredItems
        self.assertEqual([it.ColonneGauche for it in items],
                         [u'A101', u'A102', u'A103'])
        self.assertEqual([it.Nom for it in items], [u'RDC', u'R+1', u'R+2'])

    def test_numero_rendu_comme_identifiant(self):
        vm = self._vm([])
        self.assertTrue(vm.SelectionVM.FilteredItems[0].EstIdentifiant)

    def test_items_precoches_selon_selection_courante(self):
        vm = self._vm([2])
        self.assertEqual([it.IsSelected for it in vm.SelectionVM.FilteredItems],
                         [False, True, False])

    def test_toggle_remonte_jusqu_au_vm_racine(self):
        vm = self._vm([])
        vm.SelectionVM.FilteredItems[0].IsSelected = True
        vm.SelectionVM.FilteredItems[2].IsSelected = True
        self.assertEqual(sorted(vm.SelectedSheetIds), [1, 3])

    def test_decoche_retire_de_la_selection(self):
        vm = self._vm([1, 2])
        vm.SelectionVM.FilteredItems[0].IsSelected = False
        self.assertEqual(vm.SelectedSheetIds, [2])

    def test_recherche_porte_sur_le_numero_et_sur_le_nom(self):
        vm = self._vm([])
        vm.SelectionVM.FilterText = u'a102'
        self.assertEqual([it.Nom for it in vm.SelectionVM.FilteredItems], [u'R+1'])
        vm.SelectionVM.FilterText = u'rdc'
        self.assertEqual([it.ColonneGauche for it in vm.SelectionVM.FilteredItems],
                         [u'A101'])


if __name__ == '__main__':
    unittest.main()
