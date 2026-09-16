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
from ui.OpenArchiConfig import OpenArchiConfig, PROVIDERS


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
        self.assertIn('/connect', reponse)
        self.assertIn('/aide', reponse)

    def test_commande_inconnue_renvoie_laide(self):
        reponse = self.vm.repondre('/nimportequoi')
        self.assertIn('inconnue', reponse)
        self.assertIn('/connect', reponse)

    def test_statut_est_le_fournisseur(self):
        self.assertEqual(self.vm.Statut, self.config.provider)


class TestAutocomplete(unittest.TestCase):
    def setUp(self):
        self.vm = OpenArchiChatVM(config=OpenArchiConfig(_StoreMemoire()))

    def _libelles(self):
        return [s.Libelle for s in self.vm.Suggestions]

    def test_rien_sans_barre_oblique(self):
        self.vm.Saisie = 'bonjour'
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_barre_oblique_seule_propose_tout(self):
        self.vm.Saisie = '/'
        self.assertTrue(self.vm.SuggestionsVisibles)
        self.assertEqual(self._libelles(), ['/aide', '/connect'])

    def test_filtre_sur_le_prefixe(self):
        self.vm.Saisie = '/co'
        self.assertEqual(self._libelles(), ['/connect'])

    def test_prefixe_insensible_a_la_casse(self):
        self.vm.Saisie = '/CO'
        self.assertEqual(self._libelles(), ['/connect'])

    def test_prefixe_sans_correspondance(self):
        self.vm.Saisie = '/zzz'
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_liste_fermee_une_fois_la_commande_ecrite(self):
        self.vm.Saisie = '/connect '
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_choisir_remplit_la_saisie_et_ferme(self):
        self.vm.Saisie = '/co'
        self.vm._choisir(self.vm.Suggestions[0])
        self.assertEqual(self.vm.Saisie, '/connect ')
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_completer_prend_la_premiere(self):
        self.vm.Saisie = '/'
        self.vm._completer()
        self.assertEqual(self.vm.Saisie, '/aide ')

    def test_completer_sans_proposition_ne_fait_rien(self):
        self.vm.Saisie = 'bonjour'
        self.vm._completer()
        self.assertEqual(self.vm.Saisie, 'bonjour')

    def test_envoi_referme_la_liste(self):
        self.vm.Saisie = '/aide'
        self.vm._envoyer()
        self.assertFalse(self.vm.SuggestionsVisibles)


class TestConnect(unittest.TestCase):
    def setUp(self):
        self.store = _StoreMemoire()
        self.config = OpenArchiConfig(self.store)
        self.vm = OpenArchiChatVM(config=self.config)

    def _ouvrir_la_liste(self):
        """Envoie /connect : la liste des fournisseurs remplace les commandes."""
        self.vm.Saisie = '/connect'
        self.vm._envoyer()

    def test_connect_ouvre_la_liste_des_fournisseurs(self):
        self._ouvrir_la_liste()
        self.assertEqual([s.Nom for s in self.vm.Suggestions], list(PROVIDERS))

    def test_libelles_des_fournisseurs_sans_barre_oblique(self):
        self._ouvrir_la_liste()
        self.assertEqual([s.Libelle for s in self.vm.Suggestions],
                         list(PROVIDERS))

    def test_la_frappe_ne_referme_pas_la_liste(self):
        self._ouvrir_la_liste()
        self.vm.Saisie = 'Anth'
        self.assertTrue(self.vm.SuggestionsVisibles)

    def test_choix_persiste_et_met_le_statut_a_jour(self):
        self._ouvrir_la_liste()
        cible = PROVIDERS[1]
        self.vm._choisir([s for s in self.vm.Suggestions
                          if s.Nom == cible][0])
        self.assertEqual(self.config.provider, cible)
        self.assertEqual(self.vm.Statut, cible)
        # Relu depuis le même store : la valeur a bien été persistée.
        self.assertEqual(OpenArchiConfig(self.store).provider, cible)

    def test_choix_referme_la_liste_et_rend_les_commandes(self):
        self._ouvrir_la_liste()
        avant = len(self.vm.Messages)
        self.vm._choisir(self.vm.Suggestions[0])
        self.assertFalse(self.vm.SuggestionsVisibles)
        self.assertEqual(len(self.vm.Messages), avant + 1)
        self.vm.Saisie = '/'
        self.assertEqual([s.Libelle for s in self.vm.Suggestions],
                         ['/aide', '/connect'])

    def test_tab_choisit_le_premier_fournisseur(self):
        self._ouvrir_la_liste()
        self.vm._completer()
        self.assertEqual(self.config.provider, PROVIDERS[0])

    def test_fournisseur_inconnu_retombe_sur_le_premier(self):
        store = _StoreMemoire()
        store.set('provider', 'Fournisseur Fantome')
        self.assertEqual(OpenArchiConfig(store).provider, PROVIDERS[0])


if __name__ == '__main__':
    unittest.main()
