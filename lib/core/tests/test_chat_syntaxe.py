# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> 418.extension/lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.chat_syntaxe import analyser


class TestCommandes(unittest.TestCase):
    def test_commande_seule(self):
        a = analyser('/config')
        self.assertTrue(a.est_commande)
        self.assertEqual(a.commande, 'config')
        self.assertEqual(a.arguments, '')

    def test_commande_avec_arguments(self):
        a = analyser('  /Aide  les modeles  ')
        self.assertEqual(a.commande, 'aide')  # insensible à la casse
        self.assertEqual(a.arguments, 'les modeles')

    def test_barre_oblique_au_milieu_nest_pas_une_commande(self):
        for texte in ('echelle 1/200', 'voir https://x.y/z', 'a /b'):
            self.assertFalse(analyser(texte).est_commande, texte)

    def test_texte_simple(self):
        a = analyser('bonjour')
        self.assertFalse(a.est_commande)
        self.assertEqual(a.texte, 'bonjour')


class TestReferences(unittest.TestCase):
    def test_reference_simple(self):
        self.assertEqual(analyser('regarde #Mur_01').references, ['Mur_01'])

    def test_reference_entre_accolades(self):
        a = analyser('compare #{Porte simple 90} et #{Porte double}')
        self.assertEqual(a.references, ['Porte simple 90', 'Porte double'])

    def test_doublons_ecartes(self):
        self.assertEqual(analyser('#M1 puis #M1').references, ['M1'])

    def test_aucune_reference(self):
        self.assertEqual(analyser('rien a signaler').references, [])

    def test_commande_et_references_cohabitent(self):
        a = analyser('/config #{Projet A}')
        self.assertEqual(a.commande, 'config')
        self.assertEqual(a.references, ['Projet A'])


if __name__ == '__main__':
    unittest.main()
