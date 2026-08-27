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

from lib.viewmodels import MaterialCardVM as module
from lib.viewmodels.MaterialCardVM import Couche, Motif


class _FauxHatchImage(object):
    """Remplace le vrai adaptateur WPF : on veut juste voir ce qu'il reçoit."""

    def __init__(self):
        self.recues = None

    def vignette(self, couches):
        self.recues = list(couches)
        return 'image'


class TestMotif(unittest.TestCase):
    def setUp(self):
        self.faux = _FauxHatchImage()
        self._vrai = module.hatch_image
        module.hatch_image = self.faux

    def tearDown(self):
        module.hatch_image = self._vrai

    def test_les_deux_couches_sont_empilees_fond_dabord(self):
        fond = Couche(nom='Uni', est_uni=True)
        premier = Couche(nom='Brique', grilles=[object()])
        Motif(fond=fond, premier=premier).image()
        self.assertEqual(self.faux.recues, [fond, premier])

    def test_image_construite_une_seule_fois(self):
        motif = Motif(premier=Couche(nom='Brique'))
        self.assertEqual(motif.image(), 'image')
        self.faux.recues = None
        self.assertEqual(motif.image(), 'image')
        self.assertIsNone(self.faux.recues)   # pas de reconstruction


class TestNom(unittest.TestCase):
    def test_les_deux_couches_donnent_premier_sur_fond(self):
        motif = Motif(fond=Couche(nom='Uni'), premier=Couche(nom='Brique'))
        self.assertEqual(motif.Nom, 'Brique sur Uni')

    def test_une_seule_couche_donne_son_nom(self):
        self.assertEqual(Motif(premier=Couche(nom='Brique')).Nom, 'Brique')
        self.assertEqual(Motif(fond=Couche(nom='Uni')).Nom, 'Uni')

    def test_sans_motif_aucun(self):
        self.assertEqual(Motif().Nom, 'Aucun')


if __name__ == '__main__':
    unittest.main()
