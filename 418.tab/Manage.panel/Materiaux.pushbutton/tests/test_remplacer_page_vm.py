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

from ui.base.SelectionPageVM import SelectionPageVM

from lib.services.MaterialService import Rapport
from lib.viewmodels.MaterialCardVM import MaterialCardVM
from lib.viewmodels.RemplacerPageVM import CategorieVM, RemplacerPageVM


class FakeService(object):
    """Enregistre les appels et rend un rapport préparé, sans toucher Revit."""

    def __init__(self, rapport=None):
        self.analyses = []
        self.remplacements = []
        self._rapport = rapport or Rapport()

    def analyser(self, ids, categorie_id=None):
        self.analyses.append((list(ids), categorie_id))
        return self._rapport

    def remplacer(self, ids, id_cible, categorie_id=None):
        self.remplacements.append((list(ids), id_cible, categorie_id))
        return self._rapport


def _selection(cartes):
    """La MÊME page de sélection que l'onglet Matériaux — le tableau de la
    page Remplacer s'y branche au lieu d'avoir sa propre liste."""
    return SelectionPageVM(cartes,
                           id_getter=lambda carte: carte.Id,
                           filter_getters=[lambda carte: carte.Nom],
                           titre=u'Matériaux')


def _rapport(peints=0):
    rapport = Rapport()
    rapport.ajouter(u'Murs', est_type=True)
    rapport.ajouter(u'Murs', est_type=True)
    rapport.ajouter(u'Murs', est_type=False)
    rapport.ajouter(u'Sols', est_type=True)
    rapport.Peints = peints
    return rapport


class TestRapport(unittest.TestCase):

    def test_agrege_types_et_instances_par_categorie(self):
        lignes = _rapport().Lignes
        self.assertEqual([l.Categorie for l in lignes], [u'Murs', u'Sols'])
        self.assertEqual((lignes[0].Types, lignes[0].Instances), (2, 1))
        self.assertEqual(lignes[0].Total, 3)

    def test_total_et_vide(self):
        self.assertEqual(_rapport().Total, 4)
        self.assertTrue(Rapport().EstVide)
        self.assertFalse(_rapport().EstVide)

    def test_detail_accorde_le_pluriel(self):
        lignes = _rapport().Lignes
        self.assertEqual(lignes[0].Detail, u'2 types · 1 instance')
        self.assertEqual(lignes[1].Detail, u'1 type')

    def test_lignes_triees_par_volume_decroissant(self):
        rapport = Rapport()
        rapport.ajouter(u'Sols', est_type=True)
        rapport.ajouter(u'Murs', est_type=True)
        rapport.ajouter(u'Murs', est_type=True)
        self.assertEqual([l.Categorie for l in rapport.Lignes], [u'Murs', u'Sols'])


class TestRemplacerPageVM(unittest.TestCase):

    def setUp(self):
        self.cartes = [MaterialCardVM(1, u'Béton'), MaterialCardVM(2, u'BA25')]
        self.service = FakeService(_rapport())
        self.vm = RemplacerPageVM(self.service, _selection(self.cartes))

    def test_sans_source_rien_n_est_possible(self):
        self.assertFalse(self.vm.PeutAnalyser)
        self.assertFalse(self.vm.PeutRemplacer)
        self.assertEqual(self.vm.Recapitulatif, u'Aucune source cochée.')

    def test_sources_sans_cible_autorise_l_analyse_seule(self):
        self.vm.set_sources([1])
        self.assertTrue(self.vm.PeutAnalyser)
        self.assertFalse(self.vm.PeutRemplacer)

    def test_sources_et_cible_autorisent_le_remplacement(self):
        self.vm.set_sources([1])
        self.vm.Cible = self.cartes[1]
        self.assertTrue(self.vm.PeutRemplacer)

    def test_recapitulatif_annonce_la_fusion_au_dela_d_une_source(self):
        self.vm.set_sources([1])
        self.assertEqual(self.vm.Recapitulatif, u'1 source → aucune cible')
        self.vm.set_sources([1, 2])
        self.assertIn(u'2 sources fusionnées', self.vm.Recapitulatif)

    def test_recapitulatif_nomme_la_cible(self):
        self.vm.set_sources([1])
        self.vm.Cible = self.cartes[1]
        self.assertEqual(self.vm.Recapitulatif, u'1 source → BA25')

    def test_analyser_ne_modifie_rien_et_rend_le_rapport(self):
        self.vm.set_sources([1])
        self.vm.analyser()
        self.assertEqual(self.service.analyses, [([1], None)])
        self.assertEqual(self.service.remplacements, [])
        self.assertEqual(self.vm.Etat, u'4 élément(s) seraient modifiés.')
        self.assertEqual(len(self.vm.Lignes), 2)

    def test_remplacer_passe_l_id_de_la_cible(self):
        self.vm.set_sources([1])
        self.vm.Cible = self.cartes[1]
        self.vm.remplacer()
        self.assertEqual(self.service.remplacements, [([1], 2, None)])
        self.assertEqual(self.vm.Etat, u'4 élément(s) modifié(s).')

    def test_remplacer_ne_s_applique_pas_deux_fois(self):
        self.vm.set_sources([1])
        self.vm.Cible = self.cartes[1]
        self.vm.remplacer()
        self.vm.remplacer()
        self.assertEqual(len(self.service.remplacements), 1)

    def test_changer_la_selection_oublie_le_rapport(self):
        self.vm.set_sources([1])
        self.vm.analyser()
        self.assertTrue(self.vm.HasRapport)
        self.vm.set_sources([1, 2])
        self.assertFalse(self.vm.HasRapport)
        self.assertEqual(self.vm.Etat, u'')

    def test_changer_la_cible_oublie_le_rapport(self):
        self.vm.set_sources([1])
        self.vm.analyser()
        self.vm.Cible = self.cartes[1]
        self.assertFalse(self.vm.HasRapport)

    def test_designer_une_cible_eteint_la_precedente(self):
        self.vm.Cible = self.cartes[0]
        self.assertTrue(self.cartes[0].EstCible)
        self.vm.Cible = self.cartes[1]
        self.assertFalse(self.cartes[0].EstCible)
        self.assertTrue(self.cartes[1].EstCible)

    def _avec_categories(self):
        """VM avec deux catégories cochables, toutes décochées au départ."""
        murs = CategorieVM(42, u'Murs')
        sols = CategorieVM(43, u'Sols')
        vm = RemplacerPageVM(self.service, _selection(self.cartes),
                             [murs, sols])
        return vm, murs, sols

    def test_portee_par_defaut_tout_le_modele(self):
        vm, _, _ = self._avec_categories()
        self.assertEqual(vm.PorteeResume, u'Appliquer à toutes les catégories')
        vm.set_sources([1])
        vm.analyser()
        # None, pas une liste vide : le service balaie tout.
        self.assertEqual(self.service.analyses, [([1], None)])

    def test_les_categories_cochees_sont_transmises_au_service(self):
        vm, murs, sols = self._avec_categories()
        vm.set_sources([1])
        vm.Cible = self.cartes[1]
        murs.EstCochee = True
        sols.EstCochee = True
        vm.analyser()
        self.assertEqual(self.service.analyses, [([1], [42, 43])])
        vm.remplacer()
        self.assertEqual(self.service.remplacements, [([1], 2, [42, 43])])

    def test_decocher_la_derniere_categorie_revient_a_tout(self):
        vm, murs, _ = self._avec_categories()
        vm.set_sources([1])
        murs.EstCochee = True
        murs.EstCochee = False
        vm.analyser()
        self.assertEqual(self.service.analyses, [([1], None)])

    def test_changer_de_portee_oublie_le_rapport(self):
        vm, murs, _ = self._avec_categories()
        vm.set_sources([1])
        vm.analyser()
        self.assertTrue(vm.HasRapport)
        murs.EstCochee = True
        self.assertFalse(vm.HasRapport)

    def test_resume_de_portee_compte_les_cochees(self):
        vm, murs, sols = self._avec_categories()
        murs.EstCochee = True
        self.assertEqual(vm.PorteeResume, u'Appliquer à : Murs')
        sols.EstCochee = True
        self.assertEqual(vm.PorteeResume, u'Appliquer à 2 catégories')

    def test_reinitialiser_decoche_tout(self):
        vm, murs, sols = self._avec_categories()
        murs.EstCochee = True
        sols.EstCochee = True
        vm.reinitialiser_portee()
        self.assertFalse(murs.EstCochee)
        self.assertFalse(sols.EstCochee)
        self.assertEqual(vm.PorteeResume, u'Appliquer à toutes les catégories')

    def test_recapitulatif_mentionne_la_portee(self):
        vm, murs, sols = self._avec_categories()
        vm.set_sources([1])
        vm.Cible = self.cartes[1]
        self.assertEqual(vm.Recapitulatif, u'1 source → BA25')
        murs.EstCochee = True
        self.assertEqual(vm.Recapitulatif, u'1 source → BA25 · Murs')
        sols.EstCochee = True
        self.assertEqual(vm.Recapitulatif, u'1 source → BA25 · 2 catégories')

    def test_la_colonne_cible_a_son_propre_filtre(self):
        # Filtrer la cible ne touche pas la colonne des sources.
        self.assertEqual(len(self.vm.CiblesFiltrees), 2)
        self.vm.CibleFilterText = u'ba'
        self.assertEqual([c.Nom for c in self.vm.CiblesFiltrees], [u'BA25'])
        self.assertEqual(len(self.vm.SelectionVM.FilteredItems), 2)

    def test_filtrer_la_cible_ne_la_deselectionne_pas(self):
        self.vm.Cible = self.cartes[1]
        self.vm.CibleFilterText = u'béton'
        self.assertEqual(self.vm.CiblesFiltrees, [self.cartes[0]])
        self.assertIs(self.vm.Cible, self.cartes[1])
        self.assertTrue(self.cartes[1].EstCible)

    def test_une_card_peut_etre_source_et_cible_le_service_tranche(self):
        # Cocher aussi la cible ne doit pas bloquer l'interface : c'est
        # MaterialService.remplacer qui écarte la cible des sources.
        self.vm.set_sources([1, 2])
        self.vm.Cible = self.cartes[1]
        self.assertTrue(self.vm.PeutRemplacer)
        self.vm.remplacer()
        self.assertEqual(self.service.remplacements, [([1, 2], 2, None)])

    def test_rapport_vide_le_dit(self):
        self.vm = RemplacerPageVM(FakeService(Rapport()), _selection(self.cartes))
        self.vm.set_sources([1])
        self.vm.analyser()
        self.assertEqual(self.vm.Etat, u'Aucun élément n\'utilise ces matériaux.')

    def test_faces_peintes_signalees_sans_etre_traitees(self):
        self.vm = RemplacerPageVM(FakeService(_rapport(peints=6)),
                                  _selection(self.cartes))
        self.vm.set_sources([1])
        self.vm.analyser()
        self.assertTrue(self.vm.HasPeints)
        self.assertIn(u'6 éléments', self.vm.AvertissementPeints)
        self.assertIn(u'pas modifiée', self.vm.AvertissementPeints)

    def test_sans_face_peinte_aucun_avertissement(self):
        self.vm.set_sources([1])
        self.vm.analyser()
        self.assertFalse(self.vm.HasPeints)
        self.assertEqual(self.vm.AvertissementPeints, u'')


if __name__ == '__main__':
    unittest.main()
