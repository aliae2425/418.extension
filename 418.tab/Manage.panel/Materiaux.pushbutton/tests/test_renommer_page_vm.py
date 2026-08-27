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


class FakeService(object):
    """Applique vraiment le renommage sur les faux matériaux, comme le
    ferait `MaterialService.renommer` dans sa transaction."""

    def __init__(self):
        self.appels = []

    def renommer(self, materiaux, rename_service):
        self.appels.append([m.Name for m in materiaux])
        changes = 0
        for index, materiau in enumerate(materiaux, start=1):
            nouveau = rename_service.apply(materiau.Name, index=index)
            if nouveau != materiau.Name:
                materiau.Name = nouveau
                changes += 1
        return changes


def _vm(noms=(u'Béton coulé', u'Béton banché'), cocher=None):
    """Le VM racine câblé comme en production : la page Renommer a SA page de
    sélection sur la case `IsSelectedRenommer`. `cocher` : indices cochés,
    tous par défaut."""
    service = FakeService()
    materiaux = [FakeMateriau(i, nom) for i, nom in enumerate(noms)]
    cartes = [MaterialCardVM(m.Id, m.Name) for m in materiaux]
    racine = MainViewModel(service=service)
    racine.charger(cartes, dict((m.Id, m) for m in materiaux))
    indices = range(len(cartes)) if cocher is None else cocher
    for index in indices:
        cartes[index].IsSelectedRenommer = True
    return racine.RenommerVM, service, cartes


def _apercu(cartes):
    return [carte.NouveauNom for carte in cartes]


class TestApercu(unittest.TestCase):

    def test_sans_regle_l_apercu_reproduit_les_noms(self):
        vm, _, cartes = _vm()
        self.assertEqual(_apercu(cartes), [u'Béton coulé', u'Béton banché'])
        self.assertFalse(any(c.NomChange for c in cartes))

    def test_rechercher_remplacer_met_l_apercu_a_jour(self):
        vm, _, cartes = _vm()
        vm.Rechercher = u'Béton'
        vm.Remplacer = u'BA'
        self.assertEqual(_apercu(cartes), [u'BA coulé', u'BA banché'])
        self.assertTrue(all(c.NomChange for c in cartes))

    def test_prefixe_et_suffixe_encadrent_le_nom(self):
        vm, _, cartes = _vm([u'Chêne'])
        vm.Prefixe = u'BOIS_'
        vm.Suffixe = u'_v2'
        self.assertEqual(cartes[0].NouveauNom, u'BOIS_Chêne_v2')

    def test_sans_regex_le_motif_est_litteral(self):
        vm, _, cartes = _vm([u'Béton (ext)'])
        vm.Rechercher = u'(ext)'
        vm.Remplacer = u'EXT'
        self.assertEqual(cartes[0].NouveauNom, u'Béton EXT')

    def test_avec_regex_le_motif_est_une_expression(self):
        vm, _, cartes = _vm([u'Béton 25', u'Béton 30'])
        vm.UseRegex = True
        vm.Rechercher = u'\\d+'
        vm.Remplacer = u'XX'
        self.assertEqual(_apercu(cartes), [u'Béton XX', u'Béton XX'])

    def test_regex_invalide_signale_sans_planter(self):
        vm, _, cartes = _vm()
        vm.UseRegex = True
        vm.Rechercher = u'([Béton'
        self.assertTrue(vm.HasRegexError)
        self.assertFalse(vm.PeutRenommer)
        self.assertEqual(_apercu(cartes), [u'Béton coulé', u'Béton banché'])

    def test_regex_corrigee_efface_l_erreur(self):
        vm, _, _ = _vm()
        vm.UseRegex = True
        vm.Rechercher = u'([Béton'
        vm.Rechercher = u'Béton'
        self.assertFalse(vm.HasRegexError)


class TestSelection(unittest.TestCase):
    """Seules les lignes cochées DANS CET ONGLET ont un aperçu, et ce sont
    les seules renommées."""

    def test_cocher_ailleurs_ne_change_rien_ici(self):
        vm, _, cartes = _vm(cocher=[])
        cartes[0].IsSelected = True             # onglet Matériaux
        cartes[1].IsSelectedRemplacer = True    # onglet Remplacer
        vm.Prefixe = u'X_'
        self.assertEqual([c.NouveauNom for c in cartes], [u'', u''])
        self.assertFalse(vm.PeutRenommer)

    def test_ligne_decochee_na_pas_d_apercu(self):
        vm, _, cartes = _vm(cocher=[0])
        vm.Prefixe = u'X_'
        self.assertEqual(cartes[0].NouveauNom, u'X_Béton coulé')
        self.assertEqual(cartes[1].NouveauNom, u'')
        self.assertFalse(cartes[1].NomChange)

    def test_le_jeton_n_ne_numerote_que_les_cochees(self):
        vm, _, cartes = _vm((u'A', u'B', u'C'), cocher=[0, 2])
        vm.Suffixe = u'_{n}'
        self.assertEqual(_apercu(cartes), [u'A_1', u'', u'C_2'])

    def test_decocher_apres_coup_retire_l_apercu(self):
        vm, _, cartes = _vm()
        vm.Prefixe = u'X_'
        cartes[1].IsSelectedRenommer = False
        self.assertEqual(_apercu(cartes), [u'X_Béton coulé', u''])
        self.assertEqual(vm.NombreChanges, 1)

    def test_seules_les_cochees_partent_au_service(self):
        vm, service, cartes = _vm(cocher=[1])
        vm.Prefixe = u'X_'
        vm.renommer()
        self.assertEqual(service.appels, [[u'Béton banché']])
        self.assertEqual(cartes[0].Nom, u'Béton coulé')


class TestRenommer(unittest.TestCase):

    def test_sans_changement_le_bouton_reste_inactif(self):
        vm, _, _ = _vm()
        self.assertFalse(vm.PeutRenommer)

    def test_sans_source_le_bouton_reste_inactif(self):
        vm, _, _ = _vm(cocher=[])
        vm.Prefixe = u'X_'
        self.assertFalse(vm.PeutRenommer)

    def test_renommer_applique_et_compte(self):
        vm, service, _ = _vm()
        vm.Rechercher = u'Béton'
        vm.Remplacer = u'BA'
        self.assertTrue(vm.PeutRenommer)
        vm.renommer()
        self.assertEqual(vm.Etat, u'2 matériau(x) renommé(s).')
        self.assertEqual(service.appels, [[u'Béton coulé', u'Béton banché']])

    def test_les_cards_suivent_les_nouveaux_noms(self):
        """Le nom affiché sur les cards de l'onglet 1 doit être celui que
        Revit a accepté, sinon l'aperçu repart d'un nom périmé."""
        vm, _, cartes = _vm()
        vm.Rechercher = u'Béton'
        vm.Remplacer = u'BA'
        vm.renommer()
        self.assertEqual([c.Nom for c in cartes], [u'BA coulé', u'BA banché'])
        # La règle ne mord plus : plus rien à renommer.
        self.assertFalse(vm.PeutRenommer)
        self.assertEqual(vm.NombreChanges, 0)

    def test_renommer_inactif_ne_fait_rien(self):
        vm, service, _ = _vm()
        vm.renommer()
        self.assertEqual(service.appels, [])
        self.assertEqual(vm.Etat, u'')

    def test_recapitulatif_compte_coches_et_changements(self):
        vm, _, _ = _vm((u'A', u'B', u'C'), cocher=[0, 1])
        self.assertEqual(vm.Recapitulatif,
                         u'2 matériau(x) coché(s) · aucun changement de nom.')
        vm.Prefixe = u'X_'
        self.assertEqual(vm.Recapitulatif,
                         u'2 matériau(x) coché(s) · 2 renommage(s).')


if __name__ == '__main__':
    unittest.main(verbosity=2)
