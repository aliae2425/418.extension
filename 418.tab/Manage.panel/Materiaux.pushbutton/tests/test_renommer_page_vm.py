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

from lib.viewmodels.RenommerPageVM import RenommerPageVM


class FakeMateriau(object):
    def __init__(self, nom):
        self.Name = nom


class FakeService(object):
    """Applique vraiment le renommage sur les faux matériaux, comme le
    ferait `MaterialService.renommer` dans sa transaction."""

    def __init__(self):
        self.appels = []

    def renommer(self, materiaux, rename_service):
        self.appels.append(list(materiaux))
        changes = 0
        for index, materiau in enumerate(materiaux, start=1):
            nouveau = rename_service.apply(materiau.Name, index=index)
            if nouveau != materiau.Name:
                materiau.Name = nouveau
                changes += 1
        return changes


def _vm(noms=(u'Béton coulé', u'Béton banché')):
    service = FakeService()
    vm = RenommerPageVM(service)
    vm.set_sources([FakeMateriau(n) for n in noms])
    return vm, service


class TestApercu(unittest.TestCase):

    def test_sans_regle_l_apercu_reproduit_les_noms(self):
        vm, _ = _vm()
        self.assertEqual([a.Nouveau for a in vm.Apercus],
                         [u'Béton coulé', u'Béton banché'])
        self.assertFalse(any(a.Change for a in vm.Apercus))

    def test_rechercher_remplacer_met_l_apercu_a_jour(self):
        vm, _ = _vm()
        vm.Rechercher = u'Béton'
        vm.Remplacer = u'BA'
        self.assertEqual([a.Nouveau for a in vm.Apercus],
                         [u'BA coulé', u'BA banché'])
        self.assertTrue(all(a.Change for a in vm.Apercus))

    def test_prefixe_et_suffixe_encadrent_le_nom(self):
        vm, _ = _vm([u'Chêne'])
        vm.Prefixe = u'BOIS_'
        vm.Suffixe = u'_v2'
        self.assertEqual(vm.Apercus[0].Nouveau, u'BOIS_Chêne_v2')

    def test_le_jeton_n_numerote_les_lignes(self):
        vm, _ = _vm()
        vm.Suffixe = u'_{n}'
        self.assertEqual([a.Nouveau for a in vm.Apercus],
                         [u'Béton coulé_1', u'Béton banché_2'])

    def test_sans_regex_le_motif_est_litteral(self):
        vm, _ = _vm([u'Béton (ext)'])
        vm.Rechercher = u'(ext)'
        vm.Remplacer = u'EXT'
        self.assertEqual(vm.Apercus[0].Nouveau, u'Béton EXT')

    def test_avec_regex_le_motif_est_une_expression(self):
        vm, _ = _vm([u'Béton 25', u'Béton 30'])
        vm.UseRegex = True
        vm.Rechercher = u'\\d+'
        vm.Remplacer = u'XX'
        self.assertEqual([a.Nouveau for a in vm.Apercus],
                         [u'Béton XX', u'Béton XX'])

    def test_regex_invalide_signale_sans_planter(self):
        vm, _ = _vm()
        vm.UseRegex = True
        vm.Rechercher = u'([Béton'
        self.assertTrue(vm.HasRegexError)
        self.assertFalse(vm.PeutRenommer)
        self.assertEqual([a.Nouveau for a in vm.Apercus],
                         [u'Béton coulé', u'Béton banché'])

    def test_regex_corrigee_efface_l_erreur(self):
        vm, _ = _vm()
        vm.UseRegex = True
        vm.Rechercher = u'([Béton'
        vm.Rechercher = u'Béton'
        self.assertFalse(vm.HasRegexError)


class TestRenommer(unittest.TestCase):

    def test_sans_changement_le_bouton_reste_inactif(self):
        vm, _ = _vm()
        self.assertFalse(vm.PeutRenommer)

    def test_sans_source_le_bouton_reste_inactif(self):
        vm, _ = _vm([])
        vm.Prefixe = u'X_'
        self.assertFalse(vm.PeutRenommer)

    def test_renommer_applique_et_compte(self):
        vm, service = _vm()
        vm.Rechercher = u'Béton'
        vm.Remplacer = u'BA'
        self.assertTrue(vm.PeutRenommer)
        vm.renommer()
        self.assertEqual(vm.Etat, u'2 matériau(x) renommé(s).')
        self.assertEqual([m.Name for m in service.appels[0]],
                         [u'BA coulé', u'BA banché'])

    def test_apres_renommage_l_apercu_repart_des_nouveaux_noms(self):
        vm, _ = _vm()
        vm.Rechercher = u'Béton'
        vm.Remplacer = u'BA'
        vm.renommer()
        self.assertEqual([a.Ancien for a in vm.Apercus],
                         [u'BA coulé', u'BA banché'])
        # La règle ne mord plus : plus rien à renommer.
        self.assertFalse(vm.PeutRenommer)

    def test_renommer_inactif_ne_fait_rien(self):
        vm, service = _vm()
        vm.renommer()
        self.assertEqual(service.appels, [])
        self.assertEqual(vm.Etat, u'')


if __name__ == '__main__':
    unittest.main()
