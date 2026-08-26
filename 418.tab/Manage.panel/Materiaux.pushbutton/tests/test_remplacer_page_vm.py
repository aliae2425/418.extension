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

from lib.services.MaterialService import Rapport
from lib.viewmodels.MaterialCardVM import MaterialCardVM
from lib.viewmodels.RemplacerPageVM import RemplacerPageVM


class FakeService(object):
    """Enregistre les appels et rend un rapport préparé, sans toucher Revit."""

    def __init__(self, rapport=None):
        self.analyses = []
        self.remplacements = []
        self._rapport = rapport or Rapport()

    def analyser(self, ids):
        self.analyses.append(list(ids))
        return self._rapport

    def remplacer(self, ids, id_cible):
        self.remplacements.append((list(ids), id_cible))
        return self._rapport


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
        self.vm = RemplacerPageVM(self.service, self.cartes)

    def test_sans_source_rien_n_est_possible(self):
        self.assertFalse(self.vm.PeutAnalyser)
        self.assertFalse(self.vm.PeutRemplacer)
        self.assertIn(u'Aucun matériau', self.vm.SourcesResume)

    def test_sources_sans_cible_autorise_l_analyse_seule(self):
        self.vm.set_sources([1])
        self.assertTrue(self.vm.PeutAnalyser)
        self.assertFalse(self.vm.PeutRemplacer)

    def test_sources_et_cible_autorisent_le_remplacement(self):
        self.vm.set_sources([1])
        self.vm.Cible = self.cartes[1]
        self.assertTrue(self.vm.PeutRemplacer)

    def test_resume_annonce_la_fusion_au_dela_d_une_source(self):
        self.vm.set_sources([1])
        self.assertEqual(self.vm.SourcesResume, u'1 matériau source.')
        self.vm.set_sources([1, 2])
        self.assertIn(u'fusionnés', self.vm.SourcesResume)

    def test_analyser_ne_modifie_rien_et_rend_le_rapport(self):
        self.vm.set_sources([1])
        self.vm.analyser()
        self.assertEqual(self.service.analyses, [[1]])
        self.assertEqual(self.service.remplacements, [])
        self.assertEqual(self.vm.Etat, u'4 élément(s) seraient modifiés.')
        self.assertEqual(len(self.vm.Lignes), 2)

    def test_remplacer_passe_l_id_de_la_cible(self):
        self.vm.set_sources([1])
        self.vm.Cible = self.cartes[1]
        self.vm.remplacer()
        self.assertEqual(self.service.remplacements, [([1], 2)])
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

    def test_rapport_vide_le_dit(self):
        self.vm = RemplacerPageVM(FakeService(Rapport()), self.cartes)
        self.vm.set_sources([1])
        self.vm.analyser()
        self.assertEqual(self.vm.Etat, u'Aucun élément n\'utilise ces matériaux.')

    def test_faces_peintes_signalees_sans_etre_traitees(self):
        self.vm = RemplacerPageVM(FakeService(_rapport(peints=6)), self.cartes)
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
