# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import shutil
import sys
import tempfile
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
        chat_cli.oublier_statut()

    def tearDown(self):
        chat_cli.chemin = self._chemin
        chat_cli.oublier_statut()

    def test_sans_cli_pas_de_sous_processus(self):
        chat_cli.chemin = lambda *a: None
        self.assertFalse(chat_cli.pret())
        try:
            chat_cli.repondre([('user', 'x')])
        except chat_cli.ErreurCLI as e:
            self.assertIn('codex', '{0}'.format(e))
        else:
            self.fail('ErreurCLI attendue')

    def test_statut_mis_en_cache(self):
        appels = []

        def _compter():
            appels.append(1)
            return True

        original = chat_cli._demander_statut
        chat_cli._demander_statut = _compter
        try:
            self.assertTrue(chat_cli.connecte())
            self.assertTrue(chat_cli.connecte())
            self.assertEqual(len(appels), 1)
            chat_cli.oublier_statut()
            self.assertTrue(chat_cli.connecte())
            self.assertEqual(len(appels), 2)
        finally:
            chat_cli._demander_statut = original


class TestChemin(unittest.TestCase):
    """CreateProcess ne résout pas PATHEXT : le nom nu ne suffit pas."""

    def setUp(self):
        self._path = os.environ.get('PATH', '')
        self._pathext = os.environ.get('PATHEXT', '')
        self._dossier = tempfile.mkdtemp()
        os.environ['PATH'] = self._dossier
        os.environ['PATHEXT'] = '.COM;.EXE;.BAT;.CMD'

    def tearDown(self):
        os.environ['PATH'] = self._path
        os.environ['PATHEXT'] = self._pathext
        shutil.rmtree(self._dossier, ignore_errors=True)

    def _poser(self, nom):
        cible = os.path.join(self._dossier, nom)
        with open(cible, 'wb') as fichier:
            fichier.write(b'')
        return cible

    def test_trouve_lextension_du_pathext(self):
        if os.name != 'nt':
            return
        attendu = self._poser('bidule.CMD')
        self.assertEqual(chat_cli.chemin('bidule'), attendu)

    def test_ignore_le_shim_sans_extension(self):
        # npm pose « codex » (script shell) à côté de « codex.CMD ». Prendre
        # le premier donne un [Errno 2] à l'exécution : c'est LE bug.
        if os.name != 'nt':
            return
        self._poser('bidule')
        attendu = self._poser('bidule.CMD')
        self.assertEqual(chat_cli.chemin('bidule'), attendu)

    def test_nom_deja_suffixe_accepte_tel_quel(self):
        if os.name != 'nt':
            return
        attendu = self._poser('bidule.exe')
        self.assertEqual(chat_cli.chemin('bidule.exe'), attendu)

    def test_introuvable_vaut_none(self):
        self.assertIsNone(chat_cli.chemin('nexiste-pas-du-tout'))

    def test_chemin_explicite_verifie_lexistence(self):
        cible = self._poser('direct.exe')
        self.assertEqual(chat_cli.chemin(cible), cible)
        self.assertIsNone(chat_cli.chemin(
            os.path.join(self._dossier, 'absent.exe')))


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
