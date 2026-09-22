# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core import chat_openai


class TestCharge(unittest.TestCase):
    def test_systeme_en_tete_puis_les_couples(self):
        corps = chat_openai.charge([('user', 'salut'), ('assistant', 'ok')])
        self.assertEqual([m['role'] for m in corps['messages']],
                         ['system', 'user', 'assistant'])
        self.assertEqual(corps['messages'][1]['content'], 'salut')

    def test_modele_explicite_prime(self):
        self.assertEqual(chat_openai.charge([], 'gpt-test')['model'],
                         'gpt-test')

    def test_accents_serialisables(self):
        # ensure_ascii=False est obligatoire sous IronPython : ce test échoue
        # côté client si quelqu'un le retire.
        brut = json.dumps(chat_openai.charge([('user', 'café éàü')]),
                          ensure_ascii=False)
        self.assertIn('café', brut)
        self.assertTrue(brut.encode('utf-8'))


class TestExtraire(unittest.TestCase):
    def test_texte_du_premier_choix(self):
        brut = json.dumps({'choices': [{'message': {'content': ' bonjour '}}]})
        self.assertEqual(chat_openai.extraire(brut), 'bonjour')

    def test_reponse_illisible(self):
        for brut in ('<html>502</html>', '{}', '{"choices": []}'):
            self.assertRaises(chat_openai.ErreurOpenAI,
                              chat_openai.extraire, brut)


class TestCle(unittest.TestCase):
    def setUp(self):
        self._sauvegarde = os.environ.pop(chat_openai.CLE_ENV, None)

    def tearDown(self):
        if self._sauvegarde is not None:
            os.environ[chat_openai.CLE_ENV] = self._sauvegarde

    def test_sans_cle_pas_dappel_reseau(self):
        self.assertFalse(chat_openai.cle_presente())
        self.assertRaises(chat_openai.ErreurOpenAI,
                          chat_openai.repondre, [('user', 'x')])


if __name__ == '__main__':
    unittest.main()
