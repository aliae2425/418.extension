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

from core import chat_boucle
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


class TestPiecesJointes(unittest.TestCase):
    PIECE = {'nom': 'notice.pdf', 'media': 'application/pdf', 'b64': 'QUJD'}

    def test_sans_piece_le_contenu_reste_une_chaine(self):
        # Basculer tout l'historique en blocs sans raison, c'est changer la
        # forme d'un corps qui marche.
        corps = chat_openai.charge([('user', 'salut')])
        self.assertEqual(corps['messages'][1]['content'], 'salut')

    def test_la_piece_se_pose_sur_le_dernier_tour_utilisateur(self):
        corps = chat_openai.charge(
            [('user', 'premier'), ('assistant', 'ok'), ('user', 'et ça ?')],
            pieces=[self.PIECE])
        self.assertEqual(corps['messages'][1]['content'], 'premier')
        dernier = corps['messages'][3]['content']
        self.assertEqual([bloc['type'] for bloc in dernier], ['text', 'file'])
        self.assertEqual(dernier[0]['text'], 'et ça ?')
        self.assertEqual(dernier[1]['file']['filename'], 'notice.pdf')
        self.assertEqual(dernier[1]['file']['file_data'],
                         'data:application/pdf;base64,QUJD')

    def test_un_historique_sans_tour_utilisateur_ne_leve_pas(self):
        chat_openai.charge([('assistant', 'ok')], pieces=[self.PIECE])


class TestImages(unittest.TestCase):
    """Une image ne se décrit pas, elle se regarde — et pas dans un bloc file."""

    IMAGE = {'nom': 'facade.png', 'media': 'image/png', 'b64': 'QUJD'}

    def test_l_image_part_en_bloc_image_url(self):
        corps = chat_openai.charge([('user', 'que vois-tu ?')],
                                   pieces=[self.IMAGE])
        bloc = corps['messages'][1]['content'][1]
        self.assertEqual(bloc['type'], 'image_url')
        self.assertEqual(bloc['image_url']['url'],
                         'data:image/png;base64,QUJD')

    def test_le_pdf_garde_sa_forme_a_lui(self):
        corps = chat_openai.charge(
            [('user', 'x')],
            pieces=[{'nom': 'n.pdf', 'media': 'application/pdf', 'b64': 'Qg=='}])
        self.assertEqual(corps['messages'][1]['content'][1]['type'], 'file')


class TestBoucleOutils(unittest.TestCase):
    """La connexion qui porte les PDF ne doit plus être l'aveugle du lot."""

    OUTIL = {'nom': 'revit_vues', 'description': 'les vues',
             'parametres': {'type': 'object', 'properties': {}}}

    def setUp(self):
        self.envois = []
        self.executes = []
        self._vrais = (chat_openai._poster, chat_boucle.revit_outils)
        chat_openai._poster = self._poster
        chat_boucle.revit_outils = self
        os.environ[chat_openai.CLE_ENV] = 'cle-de-test'

    def tearDown(self):
        (chat_openai._poster, chat_boucle.revit_outils) = self._vrais
        os.environ.pop(chat_openai.CLE_ENV, None)

    # --- double de revit_outils ---
    TOURS_MAX = 3

    def disponible(self):
        return True, ''

    def outils(self):
        return [self.OUTIL]

    def irreversibles(self):
        return ('revit_exporter',)

    def executer(self, nom, arguments=None):
        self.executes.append((nom, arguments))
        return json.dumps({'vues': 12})

    # --- double du réseau ---
    def _poster(self, charge_utile, _cle, _timeout):
        self.envois.append(charge_utile)
        return json.dumps(self.reponses.pop(0))

    @staticmethod
    def _appel(nom='revit_vues'):
        return {'choices': [{'message': {
            'role': 'assistant', 'content': None,
            'tool_calls': [{'id': 'call_1', 'type': 'function',
                            'function': {'name': nom, 'arguments': '{}'}}]}}]}

    @staticmethod
    def _texte(texte):
        return {'choices': [{'message': {'role': 'assistant',
                                         'content': texte}}]}

    def test_les_outils_sont_imbriques_sous_function(self):
        # Le backend Responses les pose à plat ; celui-ci non. Inverser les
        # deux rend un 400 sur le corps entier.
        self.reponses = [self._texte('ok')]
        chat_openai.repondre([('user', 'x')])
        outil = self.envois[0]['tools'][0]
        self.assertEqual(outil['type'], 'function')
        self.assertEqual(outil['function']['name'], 'revit_vues')

    def test_un_appel_puis_la_reponse(self):
        self.reponses = [self._appel(), self._texte('Douze vues.')]
        self.assertEqual(chat_openai.repondre([('user', 'combien ?')]),
                         'Douze vues.')
        self.assertEqual(self.executes, [('revit_vues', {})])
        # L'API est sans mémoire : son propre appel ET le résultat.
        envoyes = self.envois[1]['messages']
        self.assertEqual(envoyes[-2]['tool_calls'][0]['id'], 'call_1')
        self.assertEqual(envoyes[-1]['role'], 'tool')
        self.assertEqual(envoyes[-1]['tool_call_id'], 'call_1')

    def test_sans_outils_aucune_promesse_dans_la_consigne(self):
        self.disponible = lambda: (False, 'Maquette injoignable')
        self.reponses = [self._texte('sans les yeux')]
        chat_openai.repondre([('user', 'x')])
        self.assertNotIn('tools', self.envois[0])
        self.assertEqual(self.envois[0]['messages'][0]['content'],
                         chat_openai.systeme(False))

    def test_plafond_de_tours_puis_reponse_forcee_sans_outils(self):
        self.reponses = ([self._appel()] * self.TOURS_MAX +
                         [self._texte('assez lu')])
        self.assertEqual(chat_openai.repondre([('user', 'x')]), 'assez lu')
        self.assertEqual(len(self.executes), self.TOURS_MAX)
        self.assertNotIn('tools', self.envois[-1])

    def test_un_irreversible_sans_accord_ne_part_pas(self):
        self.reponses = [self._appel('revit_exporter'), self._texte('bon')]
        chat_openai.repondre([('user', 'x')], confirmer=lambda _n, _a: False)
        self.assertEqual(self.executes, [])

    def test_la_piece_jointe_survit_a_la_boucle(self):
        # C'est tout l'intérêt : des PDF ET des outils sur la même connexion.
        self.reponses = [self._appel(), self._texte('vu')]
        chat_openai.repondre(
            [('user', 'et ce plan ?')],
            pieces=[{'nom': 'p.pdf', 'media': 'application/pdf',
                     'b64': 'QUJD'}])
        blocs = self.envois[1]['messages'][1]['content']
        self.assertEqual([b['type'] for b in blocs], ['text', 'file'])


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
        self.assertFalse(chat_openai.pret())
        self.assertRaises(chat_openai.ErreurOpenAI,
                          chat_openai.repondre, [('user', 'x')])


if __name__ == '__main__':
    unittest.main()
