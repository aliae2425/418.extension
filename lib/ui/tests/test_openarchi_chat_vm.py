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
from ui.OpenArchiConfigVM import (OpenArchiConfig, OpenArchiConfigVM,
                                  PROVIDERS, AUCUN_PROJET)


class _StoreMemoire(object):
    """Double de UserConfig : rien n'est écrit sur le disque pendant les tests."""

    def __init__(self):
        self._d = {}

    def get(self, cle, defaut=None):
        return self._d.get(cle, defaut)

    def set(self, cle, valeur):
        self._d[cle] = valeur


class TestChat(unittest.TestCase):
    def setUp(self):
        self.config = OpenArchiConfig(_StoreMemoire())
        self.vm = OpenArchiChatVM(config=self.config)

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
        self.vm._envoyer()
        self.assertEqual(len(self.vm.Messages), 3)
        self.assertEqual(self.vm.Messages[1].Texte, 'bonjour')
        self.assertTrue(self.vm.Messages[1].DeUtilisateur)
        self.assertEqual(self.vm.Messages[1].Alignement, 'Right')
        self.assertEqual(self.vm.Messages[2].Alignement, 'Left')
        self.assertEqual(self.vm.Saisie, '')

    def test_references_reprises_dans_la_reponse(self):
        reponse = self.vm.repondre('compare #{Mur type A} et #Porte01')
        self.assertIn('Mur type A', reponse)
        self.assertIn('Porte01', reponse)

    def test_commande_aide_liste_les_commandes(self):
        reponse = self.vm.repondre('/aide')
        self.assertIn('/config', reponse)
        self.assertIn('/aide', reponse)

    def test_commande_inconnue_renvoie_laide(self):
        reponse = self.vm.repondre('/nimportequoi')
        self.assertIn('inconnue', reponse)
        self.assertIn('/config', reponse)

    def test_config_appelle_le_callback_et_rafraichit_le_statut(self):
        appels = []

        def _ouvrir(config):
            appels.append(config)
            config.appliquer('OpenAI', 'gpt-5', 'Tour Nord.rvt')

        vm = OpenArchiChatVM(config=self.config, ouvrir_config=_ouvrir)
        reponse = vm.repondre('/config')
        self.assertEqual(len(appels), 1)
        self.assertIn('OpenAI', reponse)
        self.assertIn('gpt-5', reponse)
        self.assertIn('Tour Nord.rvt', vm.Statut)

    def test_statut_par_defaut(self):
        self.assertIn(AUCUN_PROJET, self.vm.Statut)


class TestConfigVM(unittest.TestCase):
    def setUp(self):
        self.config = OpenArchiConfig(_StoreMemoire())
        self.vm = OpenArchiConfigVM(self.config, projets=['A.rvt', 'B.rvt'])

    def test_modele_suit_le_fournisseur(self):
        self.vm.Provider = 'OpenAI'
        self.assertEqual(list(self.vm.Modeles), PROVIDERS['OpenAI'])
        self.assertEqual(self.vm.Modele, PROVIDERS['OpenAI'][0])

    def test_valider_persiste(self):
        self.vm.Provider = 'OpenAI'
        self.vm.Projet = 'B.rvt'
        self.vm._valider()
        self.assertEqual(self.config.provider, 'OpenAI')
        self.assertEqual(self.config.projet, 'B.rvt')

    def test_sans_projet_ouvert(self):
        vm = OpenArchiConfigVM(self.config, projets=[])
        self.assertEqual(vm.Projet, AUCUN_PROJET)
        vm._valider()
        self.assertEqual(self.config.projet, '')

    def test_reglages_precedents_reconduits(self):
        self.config.appliquer('OpenAI', 'gpt-5-mini', 'A.rvt')
        vm = OpenArchiConfigVM(self.config, projets=['A.rvt', 'B.rvt'])
        self.assertEqual(vm.Provider, 'OpenAI')
        self.assertEqual(vm.Modele, 'gpt-5-mini')
        self.assertEqual(vm.Projet, 'A.rvt')


if __name__ == '__main__':
    unittest.main()
