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

    def test_charger_construit_les_quatre_onglets(self):
        _, cartes, par_id = _contexte()
        vm = MainViewModel()
        vm.charger(cartes, par_id)
        # L'audit est l'onglet ouvert par défaut.
        self.assertEqual(vm.Mode, u'audit')
        self.assertIsNotNone(vm.AuditVM)
        self.assertEqual(len(vm.SelectionVM.AllItems), 2)
        self.assertIsNotNone(vm.RemplacerVM)
        self.assertIsNotNone(vm.RenommerVM)

    def test_les_trois_onglets_partagent_les_cards_pas_la_selection(self):
        # Un seul MaterialCardVM par matériau (vignettes et usages calculés
        # une fois), mais TROIS pages de sélection, une par case.
        _, cartes, par_id = _contexte()
        vm = MainViewModel()
        vm.charger(cartes, par_id)
        pages = (vm.SelectionVM, vm.RenommerVM.SelectionVM,
                 vm.RemplacerVM.SelectionVM)
        self.assertEqual(len(set(id(p) for p in pages)), 3)
        for page in pages:
            self.assertEqual(page.AllItems, cartes)

    def test_la_cible_se_prend_dans_la_meme_liste(self):
        _, cartes, par_id = _contexte()
        vm = MainViewModel(service=object())   # présence suffit : rien n'est appelé
        vm.charger(cartes, par_id)
        vm.RemplacerVM.SelectionVM.handle_row_click(0)   # source : Béton
        vm.RemplacerVM.Cible = cartes[1]                 # cible : Chêne
        self.assertEqual(vm.RemplacerVM._sources, [1])
        self.assertTrue(cartes[1].EstCible)
        self.assertTrue(vm.RemplacerVM.PeutRemplacer)

    def test_cocher_dans_un_onglet_ne_touche_pas_aux_autres(self):
        _, cartes, par_id = _contexte()
        vm = MainViewModel()
        vm.charger(cartes, par_id)
        vm.SelectionVM.select_all()                 # onglet Matériaux
        self.assertEqual(vm.RemplacerVM._sources, [])
        vm.RenommerVM.Prefixe = u'X_'
        self.assertEqual([c.NouveauNom for c in cartes], [u'', u''])
        vm.RenommerVM.SelectionVM.handle_row_click(0)
        self.assertEqual([c.NouveauNom for c in cartes], [u'X_Béton coulé', u''])
        self.assertEqual(vm.RemplacerVM._sources, [])

    def test_decocher_vide_l_onglet_concerne(self):
        _, cartes, par_id = _contexte()
        vm = MainViewModel()
        vm.charger(cartes, par_id)
        vm.RenommerVM.SelectionVM.select_all()
        vm.RenommerVM.Prefixe = u'X_'
        self.assertEqual(vm.RenommerVM.NombreChanges, 2)
        vm.RenommerVM.SelectionVM.deselect_all()
        self.assertEqual(vm.RenommerVM.NombreChanges, 0)
        self.assertEqual([c.NouveauNom for c in cartes], [u'', u''])

    def test_chaque_onglet_a_sa_recherche(self):
        _, cartes, par_id = _contexte()
        vm = MainViewModel()
        vm.charger(cartes, par_id)
        vm.SelectionVM.FilterText = u'bois'          # classe, pas nom
        self.assertEqual([c.Nom for c in vm.SelectionVM.FilteredItems],
                         [u'Chêne'])
        self.assertEqual(len(vm.RenommerVM.SelectionVM.FilteredItems), 2)

    def test_preset_coche_les_non_utilises(self):
        # Sans comptage d'usages, tout est « non utilisé » et « sans
        # instance » : c'est le repli hors Revit.
        _, cartes, par_id = _contexte()
        vm = MainViewModel()
        vm.charger(cartes, par_id)
        vm.SelectionVM.Preset = u'Non utilisés'
        self.assertEqual(vm.SelectionVM.selected_ids(), [1, 2])
        vm.SelectionVM.Preset = u'Utilisés'
        self.assertEqual(vm.SelectionVM.selected_ids(), [])
        # Le menu reste sur son libellé neutre : c'est une action.
        self.assertEqual(vm.SelectionVM.Preset,
                         vm.SelectionVM.PLACEHOLDER)
        # Et il n'a pas touché aux autres onglets.
        self.assertEqual(vm.RemplacerVM.SelectionVM.selected_ids(), [])

    def test_set_mode_bascule_l_onglet(self):
        vm = MainViewModel()
        vm.set_mode(u'renommer')
        self.assertEqual(vm.Mode, u'renommer')


if __name__ == '__main__':
    unittest.main()
