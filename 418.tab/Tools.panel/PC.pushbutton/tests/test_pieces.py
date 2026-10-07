# -*- coding: utf-8 -*-
"""Le catalogue est de la donnée réglementaire : ce test garde sa forme.

Il ne juge PAS le contenu — ni le nombre de pièces, ni leurs intitulés : ils
viennent des fiches service-public et se complètent à la main. Il garde ce
qui casserait l'outil en silence : un code en double (deux dossiers du même
nom), un type actif sans pièce, un intitulé vide.
"""
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

from lib.models import pieces as catalogue


class TestCatalogue(unittest.TestCase):

    def test_les_codes_sont_uniques_dans_un_type(self):
        # Deux pièces du même code, c'est un seul dossier sur le disque et
        # une pièce qui disparaît sans un mot.
        for dossier in catalogue.CATALOGUE:
            codes = [p.code for p in dossier.pieces]
            self.assertEqual(len(codes), len(set(codes)), dossier.code)

    def test_aucun_intitule_vide(self):
        for dossier in catalogue.CATALOGUE:
            for piece in dossier.pieces:
                self.assertTrue(piece.libelle.strip(), piece.code)

    def test_le_code_prefixe_les_pieces_de_son_type(self):
        # PC3 dans le PC, DP3 dans la DP : le bordereau se lit comme ça, et
        # c'est ce préfixe qui ordonne les dossiers.
        for dossier in catalogue.CATALOGUE:
            for piece in dossier.pieces:
                self.assertTrue(piece.code.startswith(dossier.code),
                                u'{0} dans {1}'.format(piece.code,
                                                       dossier.code))

    def test_un_type_sans_piece_est_inactif(self):
        # L'idiome du catalogue OpenArchi : un seul champ décide de
        # l'affichage ET de l'aiguillage.
        for dossier in catalogue.CATALOGUE:
            self.assertEqual(catalogue.actif(dossier.code),
                             bool(dossier.pieces), dossier.code)

    def test_les_trois_types_annonces_sont_servis(self):
        for code in (u'DP', u'PC', u'PD'):
            self.assertTrue(catalogue.actif(code), code)

    def test_pcmi_et_pa_sont_declares_mais_grises(self):
        # Déclarés pour annoncer ce qui arrive ; les retirer les ferait
        # disparaître de la fenêtre.
        for code in (u'PCMI', u'PA'):
            self.assertIsNotNone(catalogue.dossier(code), code)
            self.assertFalse(catalogue.actif(code), code)

    def test_le_premier_actif_sert_de_defaut(self):
        self.assertTrue(catalogue.actif(catalogue.premier_actif()))

    def test_les_obligatoires_sont_un_sous_ensemble(self):
        for dossier in catalogue.CATALOGUE:
            codes = set(p.code for p in dossier.pieces)
            self.assertTrue(
                set(catalogue.obligatoires(dossier.code)).issubset(codes))

    def test_les_vues_declarees_sont_des_noms_de_viewtype(self):
        # Des NOMS, pas des membres d'énumération : ce fichier doit rester
        # importable hors Revit. On garde la forme, pas la liste.
        connus = {u'Section', u'Elevation', u'ThreeD', u'FloorPlan',
                  u'CeilingPlan', u'DraftingView', u'AreaPlan', u'Detail'}
        for dossier in catalogue.CATALOGUE:
            for piece in dossier.pieces:
                for nom in piece.vues:
                    self.assertIn(nom, connus,
                                  u'{0} : {1}'.format(piece.code, nom))

    def test_aucune_piece_ne_reclame_les_plans_d_etage(self):
        # Le plan de situation et le plan de masse SONT des plans d'étage :
        # les y rattacher ferait remonter tous les niveaux du projet dans une
        # pièce qui en attend un. Ce test garde la décision.
        for dossier in catalogue.CATALOGUE:
            for piece in dossier.pieces:
                self.assertNotIn(u'FloorPlan', piece.vues, piece.code)

    def test_un_type_inconnu_ne_leve_pas(self):
        self.assertEqual(catalogue.pieces(u'XX'), ())
        self.assertEqual(catalogue.obligatoires(u'XX'), ())
        self.assertFalse(catalogue.actif(u'XX'))


if __name__ == '__main__':
    unittest.main()
