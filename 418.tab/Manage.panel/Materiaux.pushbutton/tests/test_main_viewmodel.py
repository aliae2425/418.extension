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
from lib.viewmodels.MaterialCardVM import MaterialCardVM


class FakeMateriau(object):
    def __init__(self, item_id, nom):
        self.Id = item_id
        self.Name = nom


def _contexte():
    """Deux matériaux, leurs cards, et la table id -> matériau."""
    materiaux = [FakeMateriau(1, u'Béton coulé'), FakeMateriau(2, u'Chêne')]
    cartes = [MaterialCardVM(1, u'Béton coulé', classe=u'Béton'),
              MaterialCardVM(2, u'Chêne', classe=u'Bois')]
    return materiaux, cartes, dict((m.Id, m) for m in materiaux)


class TestMainViewModel(unittest.TestCase):

    def test_charger_construit_les_trois_onglets(self):
        _, cartes, par_id = _contexte()
        vm = MainViewModel()
        vm.charger(cartes, par_id)
        self.assertEqual(vm.Mode, u'selection')
        self.assertEqual(len(vm.SelectionVM.AllItems), 2)
        self.assertIsNotNone(vm.RemplacerVM)
        self.assertIsNotNone(vm.RenommerVM)

    def test_les_deux_onglets_partagent_une_seule_liste(self):
        # Le tableau de la page Remplacer affiche la MÊME SelectionPageVM que
        # les cards : une seule sélection, pas deux listes à synchroniser.
        _, cartes, par_id = _contexte()
        vm = MainViewModel()
        vm.charger(cartes, par_id)
        self.assertIs(vm.RemplacerVM.SelectionVM, vm.SelectionVM)
        self.assertEqual([c.Nom for c in vm.RemplacerVM.SelectionVM.AllItems],
                         [u'Béton coulé', u'Chêne'])

    def test_la_cible_se_prend_dans_la_meme_liste(self):
        _, cartes, par_id = _contexte()
        vm = MainViewModel(service=object())   # présence suffit : rien n'est appelé
        vm.charger(cartes, par_id)
        vm.SelectionVM.handle_row_click(0)          # source : Béton
        vm.RemplacerVM.Cible = cartes[1]            # cible : Chêne
        self.assertEqual(vm.RemplacerVM._sources, [1])
        self.assertTrue(cartes[1].EstCible)
        self.assertTrue(vm.RemplacerVM.PeutRemplacer)

    def test_cocher_une_card_alimente_les_deux_autres_onglets(self):
        _, cartes, par_id = _contexte()
        vm = MainViewModel()
        vm.charger(cartes, par_id)
        vm.SelectionVM.handle_row_click(0)          # coche la 1re card
        self.assertEqual(vm.RemplacerVM._sources, [1])
        # L'onglet Renommer n'a pas de liste à lui : l'aperçu s'écrit sur la
        # card, et seulement sur celles qui sont cochées.
        vm.RenommerVM.Prefixe = u'X_'
        self.assertEqual([c.NouveauNom for c in cartes], [u'X_Béton coulé', u''])

    def test_decocher_vide_les_deux_autres_onglets(self):
        _, cartes, par_id = _contexte()
        vm = MainViewModel()
        vm.charger(cartes, par_id)
        vm.SelectionVM.select_all()
        vm.RenommerVM.Prefixe = u'X_'
        self.assertEqual(vm.RenommerVM.NombreChanges, 2)
        vm.SelectionVM.deselect_all()
        self.assertEqual(vm.RemplacerVM._sources, [])
        self.assertEqual(vm.RenommerVM.NombreChanges, 0)
        self.assertEqual([c.NouveauNom for c in cartes], [u'', u''])

    def test_recherche_filtre_sur_le_nom_et_la_classe(self):
        _, cartes, par_id = _contexte()
        vm = MainViewModel()
        vm.charger(cartes, par_id)
        vm.SelectionVM.FilterText = u'bois'          # classe, pas nom
        self.assertEqual([c.Nom for c in vm.SelectionVM.FilteredItems],
                         [u'Chêne'])

    def test_set_mode_bascule_l_onglet(self):
        vm = MainViewModel()
        vm.set_mode(u'renommer')
        self.assertEqual(vm.Mode, u'renommer')


if __name__ == '__main__':
    unittest.main()
