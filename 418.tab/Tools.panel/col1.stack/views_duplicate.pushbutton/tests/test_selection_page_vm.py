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
# Ce qui reste spécifique à l'outil « vues », et que ce fichier protège :
# le script fournit ses descripteurs dans l'ordre (id, nom, type_label) — pour
# alimenter l'aperçu de nommage — alors que la page attend
# (id, colonne_gauche, nom). MainViewModel.charger fait la permutation ; s'il
# l'oubliait, la liste afficherait le nom en colonne de gauche et le type à
# droite, sans qu'aucune exception ne le signale.


class TestChargementSelectionVues(unittest.TestCase):
    def setUp(self):
        # Ordre du script : (id, nom, type_label)
        self.descripteurs = [
            (1, u'Vue Plan RDC', u'FloorPlan'),
            (2, u'Vue Plan R+1', u'FloorPlan'),
            (3, u'Section A', u'Section'),
        ]

    def _vm(self, ids_courants):
        vm = MainViewModel(doc=None, uidoc=None, service=None)
        vm.charger(self.descripteurs, ids_courants)
        return vm

    def test_colonne_gauche_est_le_type_pas_le_nom(self):
        vm = self._vm([])
        items = vm.SelectionVM.FilteredItems
        self.assertEqual([it.ColonneGauche for it in items],
                         [u'FloorPlan', u'FloorPlan', u'Section'])
        self.assertEqual([it.Nom for it in items],
                         [u'Vue Plan RDC', u'Vue Plan R+1', u'Section A'])

    def test_type_de_vue_rendu_comme_metadonnee(self):
        # est_identifiant=False -> rendu secondaire (cf. DataTrigger de
        # SelectionPage.xaml), contrairement à un numéro de feuille.
        vm = self._vm([])
        self.assertFalse(vm.SelectionVM.FilteredItems[0].EstIdentifiant)

    def test_items_precoches_selon_selection_courante(self):
        vm = self._vm([2])
        self.assertEqual([it.IsSelected for it in vm.SelectionVM.FilteredItems],
                         [False, True, False])

    def test_toggle_remonte_jusqu_au_vm_racine(self):
        vm = self._vm([])
        vm.SelectionVM.FilteredItems[0].IsSelected = True
        vm.SelectionVM.FilteredItems[2].IsSelected = True
        self.assertEqual(sorted(vm.SelectedViewIds), [1, 3])

    def test_decoche_retire_de_la_selection(self):
        vm = self._vm([1, 2])
        vm.SelectionVM.FilteredItems[0].IsSelected = False
        self.assertEqual(vm.SelectedViewIds, [2])

    def test_recherche_porte_sur_le_type_et_sur_le_nom(self):
        vm = self._vm([])
        vm.SelectionVM.FilterText = u'section'
        self.assertEqual([it.Nom for it in vm.SelectionVM.FilteredItems],
                         [u'Section A'])
        vm.SelectionVM.FilterText = u'rdc'
        self.assertEqual([it.Nom for it in vm.SelectionVM.FilteredItems],
                         [u'Vue Plan RDC'])


if __name__ == '__main__':
    unittest.main()
