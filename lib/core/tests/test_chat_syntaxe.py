# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> 418.extension/lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.chat_syntaxe import analyser, detail_http, SYSTEME


class _FausseErreur(object):
    """Ce que urllib lève : un code, une raison, et un corps lisible une fois."""

    def __init__(self, code=400, corps=b'', reason=''):
        self.code = code
        self.reason = reason
        self._corps = corps

    def read(self):
        return self._corps


class TestInviteUnique(unittest.TestCase):
    def test_les_trois_clients_partagent_la_meme_invite(self):
        # Trois copies, c'étaient trois comportements qui divergent au premier
        # ajustement, sans que rien ne le signale.
        from core import chat_cli, chat_oauth, chat_openai
        for client in (chat_cli, chat_oauth, chat_openai):
            self.assertIs(client.SYSTEME, SYSTEME)


class TestDetailHttp(unittest.TestCase):
    def test_message_niche_sous_error(self):
        erreur = _FausseErreur(400, b'{"error": {"message": "mauvais modele"}}')
        self.assertEqual(detail_http(erreur), 'HTTP 400 — mauvais modele')

    def test_error_description_du_flux_oauth(self):
        erreur = _FausseErreur(401, b'{"error_description": "jeton expire"}')
        self.assertEqual(detail_http(erreur), 'HTTP 401 — jeton expire')

    def test_detail_nu_du_backend_codex(self):
        # La forme exacte du 400 « model is not supported ».
        erreur = _FausseErreur(400, b'{"detail": "model is not supported"}')
        self.assertEqual(detail_http(erreur),
                         'HTTP 400 — model is not supported')

    def test_error_en_chaine_plutot_quen_objet(self):
        erreur = _FausseErreur(403, b'{"error": "acces refuse"}')
        self.assertEqual(detail_http(erreur), 'HTTP 403 — acces refuse')

    def test_corps_illisible_retombe_sur_la_raison(self):
        for corps in (b'', b'<html>502</html>', b'[]'):
            erreur = _FausseErreur(502, corps, reason='Bad Gateway')
            self.assertTrue(detail_http(erreur).startswith('HTTP 502 — '))

    def test_json_valide_mais_sans_message_connu(self):
        erreur = _FausseErreur(500, b'{"autre": 1}')
        self.assertEqual(detail_http(erreur), 'HTTP 500 — sans détail')


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
