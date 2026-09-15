# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> 418.extension/lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from ui.OpenArchiChatVM import OpenArchiChatVM


class TestOpenArchiChatVM(unittest.TestCase):
    def setUp(self):
        self.vm = OpenArchiChatVM()

    def test_message_accueil(self):
        self.assertEqual(len(self.vm.Messages), 1)
        self.assertFalse(self.vm.Messages[0].DeUtilisateur)

    def test_saisie_vide_bloque_envoi(self):
        self.assertFalse(self.vm._peut_envoyer())
        self.vm.Saisie = '   '
        self.assertFalse(self.vm._peut_envoyer())
        self.vm._envoyer()
        self.assertEqual(len(self.vm.Messages), 1)

    def test_envoi_ajoute_paire_et_vide_la_saisie(self):
        self.vm.Saisie = '  bonjour  '
        self.assertTrue(self.vm._peut_envoyer())
        self.vm._envoyer()
        self.assertEqual(len(self.vm.Messages), 3)
        self.assertEqual(self.vm.Messages[1].Texte, 'bonjour')
        self.assertTrue(self.vm.Messages[1].DeUtilisateur)
        self.assertIn('bonjour', self.vm.Messages[2].Texte)
        self.assertFalse(self.vm.Messages[2].DeUtilisateur)
        self.assertEqual(self.vm.Saisie, '')

    def test_alignement_par_auteur(self):
        self.vm.Saisie = 'x'
        self.vm._envoyer()
        self.assertEqual(self.vm.Messages[1].Alignement, 'Right')
        self.assertEqual(self.vm.Messages[2].Alignement, 'Left')


if __name__ == '__main__':
    unittest.main()
