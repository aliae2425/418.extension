# -*- coding: utf-8 -*-
"""L'état de la session, éprouvé sans navigateur ni réseau.

Le flux OAuth lui-même ne se teste pas ici — il demande un navigateur et un
compte. Ce qui se teste, c'est tout ce qui décide SI la session tient : la
lecture des jetons, l'échéance, et le verdict rendu à l'interface.
"""
from __future__ import unicode_literals
import os
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from harnais import oauth, secrets                              # noqa: E402


class _Bac(unittest.TestCase):
    """Détourne LOCALAPPDATA : sans ça les tests liraient la vraie session."""

    def setUp(self):
        self._bac = tempfile.mkdtemp()
        self._avant = os.environ.get('LOCALAPPDATA')
        os.environ['LOCALAPPDATA'] = self._bac

    def tearDown(self):
        if self._avant is None:
            os.environ.pop('LOCALAPPDATA', None)
        else:
            os.environ['LOCALAPPDATA'] = self._avant
        shutil.rmtree(self._bac, ignore_errors=True)

    def poser(self, **champs):
        jetons = {'access_token': 'a', 'refresh_token': 'r',
                  'expire': time.time() + 3600}
        jetons.update(champs)
        secrets.poser_jetons(jetons)


class TestEtat(_Bac):
    """`etat()` ne touche PAS au réseau — l'interface s'en sert pour se
    dessiner avant qu'une requête ait répondu."""

    def test_sans_jeton_aucune_session(self):
        self.assertEqual({'session': False, 'expire': False, 'raison': ''},
                         oauth.etat())

    def test_jeton_frais(self):
        self.poser()
        self.assertEqual({'session': True, 'expire': False, 'raison': ''},
                         oauth.etat())

    def test_expire_mais_rafraichissable_reste_une_session(self):
        # Dire non ici renverrait l'architecte au navigateur pour rien.
        self.poser(expire=time.time() - 10)
        self.assertEqual({'session': True, 'expire': True, 'raison': ''},
                         oauth.etat())

    def test_expire_sans_refresh_cest_fini(self):
        self.poser(expire=time.time() - 10, refresh_token='')
        lu = oauth.etat()
        self.assertFalse(lu['session'])
        self.assertIn('/connect', lu['raison'])

    def test_la_marge_fait_expirer_avant_l_heure(self):
        # Un jeton qui expire PENDANT l'appel rend un 401 au milieu d'un
        # flux ; une marge coûte une requête.
        self.poser(expire=time.time() + oauth.MARGE / 2)
        self.assertTrue(oauth.etat()['expire'])

    def test_pret_suit_letat(self):
        self.assertFalse(oauth.pret())
        self.poser()
        self.assertTrue(oauth.pret())


class TestVerifier(_Bac):
    """`verifier()` est la différence entre « un jeton existe » et « un jeton
    marche ». Le réseau est remplacé."""

    def setUp(self):
        _Bac.setUp(self)
        self._vrai = oauth._demander_jetons

    def tearDown(self):
        oauth._demander_jetons = self._vrai
        _Bac.tearDown(self)

    def test_sans_session_rien_a_verifier(self):
        oauth._demander_jetons = self._interdit
        self.assertFalse(oauth.verifier()['session'])

    def test_un_jeton_frais_ne_declenche_aucun_appel(self):
        # Vérifier ne doit pas coûter une requête à chaque ouverture du volet.
        self.poser()
        oauth._demander_jetons = self._interdit
        self.assertTrue(oauth.verifier()['session'])

    def test_un_jeton_expire_est_rafraichi(self):
        self.poser(expire=time.time() - 10)
        oauth._demander_jetons = lambda corps: {
            'access_token': 'neuf', 'refresh_token': 'r2',
            'expires_in': 3600, 'id_token': ''}
        lu = oauth.verifier()
        self.assertTrue(lu['session'])
        self.assertFalse(lu['expire'])
        self.assertEqual('neuf', secrets.jetons()['access_token'])

    def test_un_refresh_refuse_efface_et_le_dit(self):
        # opencode laisse le disque périmé et l'utilisateur deviner. Ici la
        # session morte est effacée, et la raison remonte à l'interface.
        self.poser(expire=time.time() - 10)

        def casse(_corps):
            raise oauth.ErreurOAuth('HTTP 400 — invalid_grant')

        oauth._demander_jetons = casse
        lu = oauth.verifier()
        self.assertFalse(lu['session'])
        self.assertIn('/connect', lu['raison'])
        self.assertEqual({}, secrets.jetons())

    def test_le_refresh_token_survit_s_il_n_est_pas_renvoye(self):
        # Le backend ne le renvoie pas toujours ; perdre l'ancien tuerait la
        # session au rafraîchissement suivant.
        self.poser(expire=time.time() - 10)
        oauth._demander_jetons = lambda corps: {
            'access_token': 'neuf', 'expires_in': 3600}
        oauth.verifier()
        self.assertEqual('r', secrets.jetons()['refresh_token'])

    @staticmethod
    def _interdit(_corps):
        raise AssertionError('aucun appel réseau ne devait partir')


class TestPKCE(unittest.TestCase):
    """Ce qui part au navigateur. Aucun réseau."""

    def test_le_defi_est_du_base64url_sans_remplissage(self):
        defi = oauth.defi(oauth._b64(b'x' * 64))
        self.assertEqual(43, len(defi))
        self.assertNotIn('=', defi)
        self.assertNotIn('+', defi)
        self.assertNotIn('/', defi)

    def test_l_url_porte_ce_qu_il_faut(self):
        url = oauth.url_autorisation(oauth._b64(b'y' * 64), 'etat-abc')
        for attendu in ('code_challenge_method=S256', 'client_id=app_EMoam',
                        'state=etat-abc', 'response_type=code'):
            self.assertIn(attendu, url)

    def test_on_se_nomme_au_lieu_de_se_faire_passer_pour_codex(self):
        # L'ancien code envoyait `codex_cli_rs`. Le client_id reste emprunté,
        # la zone grise reste — se faire passer pour un autre n'y ajoutait rien.
        self.assertEqual('418', oauth.ORIGINATEUR)
        self.assertIn('originator=418',
                      oauth.url_autorisation(oauth._b64(b'z' * 64), 'e'))

    def test_un_id_token_illisible_ne_leve_pas(self):
        self.assertEqual('', oauth.compte(''))
        self.assertEqual('', oauth.compte('pas.un.jwt'))


if __name__ == '__main__':
    unittest.main()
