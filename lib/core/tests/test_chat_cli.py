# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core import chat_cli


class TestInvite(unittest.TestCase):
    def test_systeme_en_tete_puis_lechange(self):
        texte = chat_cli.invite([('user', 'salut'), ('assistant', 'ok')])
        self.assertTrue(texte.startswith(chat_cli.SYSTEME))
        self.assertIn('Utilisateur : salut', texte)
        self.assertIn('Toi : ok', texte)

    def test_accents_conserves(self):
        self.assertIn('café', chat_cli.invite([('user', 'café')]))


class TestDisponibilite(unittest.TestCase):
    def setUp(self):
        self._chemin = chat_cli.chemin

    def tearDown(self):
        chat_cli.chemin = self._chemin

    def test_sans_cli_pas_de_sous_processus(self):
        chat_cli.chemin = lambda: None
        self.assertFalse(chat_cli.pret())
        try:
            chat_cli.repondre([('user', 'x')])
        except chat_cli.ErreurCLI as e:
            self.assertIn('codex', '{0}'.format(e))
        else:
            self.fail('ErreurCLI attendue')


class TestStderr(unittest.TestCase):
    def test_derniere_ligne_utile(self):
        self.assertEqual(chat_cli._fin(b'banniere\n\nnot logged in\n'),
                         'not logged in')

    def test_stderr_vide(self):
        self.assertEqual(chat_cli._fin(b''), '')
        self.assertEqual(chat_cli._fin(None), '')


class TestArguments(unittest.TestCase):
    def test_bac_a_sable_en_lecture_seule(self):
        # Le chat ne doit jamais laisser le modèle écrire sur le disque.
        self.assertIn('read-only', chat_cli.ARGUMENTS)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',
                         chat_cli.ARGUMENTS)


if __name__ == '__main__':
    unittest.main()
