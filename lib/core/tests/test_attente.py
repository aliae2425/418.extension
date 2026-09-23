# -*- coding: utf-8 -*-
"""Tests des phrases d'attente et du chronomètre."""
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core import attente


class TestPhrases(unittest.TestCase):
    def test_il_y_en_a_assez_pour_ne_pas_tourner_en_rond(self):
        # Une attente d'une minute en montre 12 : moins de dix, ça se répète.
        self.assertGreaterEqual(len(attente.PHRASES), 10)

    def test_aucun_doublon(self):
        self.assertEqual(len(attente.PHRASES), len(set(attente.PHRASES)))

    def test_assez_courtes_pour_la_bulle(self):
        # La bulle fait 340 px : au-delà, la blague passe sur deux lignes.
        for phrase in attente.PHRASES:
            self.assertLessEqual(len(phrase), 48, phrase)

    def test_jamais_deux_fois_la_meme_d_affilee(self):
        precedente = attente.PHRASES[0]
        for _ in range(200):
            suivante = attente.autre(precedente)
            self.assertNotEqual(suivante, precedente)
            precedente = suivante

    def test_une_phrase_inconnue_ne_bloque_pas_le_tirage(self):
        self.assertIn(attente.autre('phrase qui n\'existe pas'),
                      attente.PHRASES)


class TestDuree(unittest.TestCase):
    def test_secondes(self):
        self.assertEqual(attente.duree(0), '0 s')
        self.assertEqual(attente.duree(8), '8 s')
        self.assertEqual(attente.duree(59), '59 s')

    def test_minutes(self):
        self.assertEqual(attente.duree(60), '1 min 00 s')
        self.assertEqual(attente.duree(72), '1 min 12 s')
        self.assertEqual(attente.duree(605), '10 min 05 s')

    def test_les_secondes_sont_sur_deux_chiffres_apres_la_minute(self):
        # « 1 min 5 s » se lit mal à côté de « 1 min 45 s ».
        self.assertIn('00', attente.duree(60))


class TestLibelle(unittest.TestCase):
    def test_avant_la_premiere_seconde_la_phrase_seule(self):
        self.assertEqual(attente.libelle('je cherche…', 0), 'je cherche…')
        self.assertEqual(attente.libelle('je cherche…'), 'je cherche…')

    def test_ensuite_la_phrase_et_le_chrono(self):
        self.assertEqual(attente.libelle('je cherche…', 3),
                         'je cherche…  ·  3 s')


if __name__ == '__main__':
    unittest.main()
