# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.models.pieces import Piece
from lib.services import ArborescenceService as arbo


def _piece(code, libelle):
    return Piece(code, libelle, False)


class TestNomDossier(unittest.TestCase):

    def test_le_code_vient_en_tete(self):
        self.assertEqual(arbo.nom_dossier(_piece(u'PC3', u'Plan en coupe')),
                         u'PC3 - Plan en coupe')

    def test_les_caracteres_interdits_sont_retires(self):
        # Un intitulé du CERFA peut porter un « : » ou un « / » ; le système
        # de fichiers, non.
        nom = arbo.nom_dossier(_piece(u'PC4', u'Notice : terrain / projet'))
        for interdit in u'\\/:*?"<>|':
            self.assertNotIn(interdit, nom)


class TestChemins(unittest.TestCase):

    PIECES = (_piece(u'PC1', u'Plan de situation'),
              _piece(u'PC2', u'Plan de masse'))

    def test_la_racine_vient_en_premier(self):
        chemins = arbo.chemins(u'C:\\p\\2431 - PC', self.PIECES)
        self.assertEqual(chemins[0], u'C:\\p\\2431 - PC')
        self.assertEqual(len(chemins), 3)

    def test_sans_racine_il_n_y_a_rien_a_creer(self):
        self.assertEqual(arbo.chemins(u'', self.PIECES), [])

    def test_sans_piece_la_racine_seule(self):
        self.assertEqual(len(arbo.chemins(u'C:\\p\\x', ())), 1)

    def test_l_ordre_du_bordereau_est_conserve(self):
        chemins = arbo.chemins(u'R', self.PIECES)
        self.assertIn(u'PC1', chemins[1])
        self.assertIn(u'PC2', chemins[2])


class TestCreer(unittest.TestCase):

    PIECES = (_piece(u'PC1', u'Plan de situation'),
              _piece(u'PC2', u'Plan de masse'))

    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.racine = os.path.join(self.dossier, u'2431 - Essai - PC')

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_cree_la_racine_et_les_pieces(self):
        crees, existants, echecs = arbo.creer(self.racine, self.PIECES)
        self.assertEqual(len(crees), 3)
        self.assertEqual(existants, [])
        self.assertEqual(echecs, [])
        for chemin in arbo.chemins(self.racine, self.PIECES):
            self.assertTrue(os.path.isdir(chemin))

    def test_relancer_n_ecrase_rien_et_le_dit(self):
        # Un dossier se monte par morceaux : relancer l'outil dessus ne doit
        # rien perdre, et doit dire ce qui était déjà là.
        arbo.creer(self.racine, self.PIECES)
        temoin = os.path.join(self.racine, u'PC1 - Plan de situation',
                              u'planche.txt')
        with open(temoin, 'wb') as fichier:
            fichier.write(b'dessin')
        crees, existants, echecs = arbo.creer(self.racine, self.PIECES)
        self.assertEqual(crees, [])
        self.assertEqual(len(existants), 3)
        self.assertEqual(echecs, [])
        self.assertTrue(os.path.exists(temoin))

    def test_une_piece_ajoutee_apres_coup_se_cree_seule(self):
        arbo.creer(self.racine, self.PIECES[:1])
        crees, existants, _ = arbo.creer(self.racine, self.PIECES)
        self.assertEqual(len(crees), 1)
        self.assertEqual(len(existants), 2)

    def test_le_resume_dit_ce_qui_a_manque(self):
        self.assertIn(u'2', arbo.resume([1, 2], [], []))
        self.assertIn(u'échec', arbo.resume([], [], [(u'x', u'accès refusé')]))
        self.assertIn(u'accès refusé',
                      arbo.resume([], [], [(u'x', u'accès refusé')]))
        self.assertEqual(arbo.resume([], [], []), u'Rien à créer.')


if __name__ == '__main__':
    unittest.main()
