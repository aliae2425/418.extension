# -*- coding: utf-8 -*-
"""Tests des routes propres à 418.

Les gestionnaires eux-mêmes touchent l'API Revit : ils ne se testent qu'en
vrai, dans Revit (cf. TESTS.md). Ce qui se teste ici, c'est ce qui est pur —
et surtout le fait que le module s'importe et reste inerte hors Revit, sans
quoi il ferait échouer tout le startup.
"""
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core import api418


class TestInerteHorsRevit(unittest.TestCase):
    def test_le_module_s_importe_sans_revit(self):
        # Il est importé par startup.py : lever ici casserait le chargement
        # de toute l'extension.
        self.assertIsNone(api418.routes)
        self.assertIsNone(api418.DB)

    def test_enregistrer_ne_fait_rien_et_ne_leve_pas(self):
        self.assertIsNone(api418.enregistrer())


class TestNomFiltre(unittest.TestCase):
    def test_lisible_et_prefixe(self):
        nom = api418.nom_filtre('Portes', 'Mark', 'A1')
        self.assertTrue(nom.startswith(api418.PREFIXE_FILTRE))
        for morceau in ('Portes', 'Mark', 'A1'):
            self.assertIn(morceau, nom)

    def test_stable_pour_la_meme_valeur(self):
        # C'est ce qui permet de RETROUVER un filtre au lieu d'en empiler un
        # nouveau à chaque appel.
        self.assertEqual(api418.nom_filtre('Portes', 'Mark', 'A1'),
                         api418.nom_filtre('Portes', 'Mark', 'A1'))

    def test_valeur_vide_reste_lisible(self):
        self.assertIn('(vide)', api418.nom_filtre('Portes', 'Mark', ''))

    def test_deux_valeurs_donnent_deux_noms(self):
        self.assertNotEqual(api418.nom_filtre('Portes', 'Mark', 'A1'),
                            api418.nom_filtre('Portes', 'Mark', 'A2'))


class TestCouleurs(unittest.TestCase):
    """Hors Revit, le vendor n'est pas importable : c'est le repli qui tourne."""

    def test_le_compte_demande_est_rendu(self):
        for combien in (1, 2, 5, 12, 40):
            self.assertEqual(len(api418.couleurs(combien)), combien)

    def test_composantes_dans_l_intervalle(self):
        for rouge, vert, bleu in api418.couleurs(24):
            for composante in (rouge, vert, bleu):
                self.assertIsInstance(composante, int)
                self.assertGreaterEqual(composante, 0)
                self.assertLessEqual(composante, 255)

    def test_teintes_distinctes(self):
        # Deux filtres de la même couleur ne servent à rien.
        palette = api418.couleurs(8)
        self.assertEqual(len(set(palette)), len(palette))

    def test_zero_ne_leve_pas(self):
        self.assertEqual(api418.couleurs(0), [])


class TestCharge(unittest.TestCase):
    class _Requete(object):
        def __init__(self, data):
            self.data = data

    def test_dict_passe_tel_quel(self):
        self.assertEqual(api418._charge(self._Requete({'a': 1})), {'a': 1})

    def test_chaine_json_decodee(self):
        self.assertEqual(api418._charge(self._Requete('{"a": 1}')), {'a': 1})

    def test_json_illisible_rend_un_dict_vide(self):
        self.assertEqual(api418._charge(self._Requete('pas du json')), {})

    def test_corps_absent_rend_un_dict_vide(self):
        self.assertEqual(api418._charge(self._Requete(None)), {})


if __name__ == '__main__':
    unittest.main()
