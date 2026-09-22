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
from ui.OpenArchiConfig import OpenArchiConfig, PROVIDERS, ACTIFS, client_de


class _StoreMemoire(object):
    """Double de UserConfig : rien n'est écrit sur le disque pendant les tests."""

    def __init__(self):
        self._d = {}

    def get(self, cle, defaut=None):
        return self._d.get(cle, defaut)

    def set(self, cle, valeur):
        self._d[cle] = valeur


class _ClientFactice(object):
    """Double de core.chat_openai : aucun appel réseau pendant les tests."""

    RAISON = 'raison de factice'

    def __init__(self, reponse='réponse du modèle', erreur=None):
        self.reponse = reponse
        self.erreur = erreur
        self.recus = None

    def pret(self):
        return True

    def repondre(self, messages, **_kwargs):
        self.recus = messages
        if self.erreur is not None:
            raise self.erreur
        return self.reponse


class TestChat(unittest.TestCase):
    def setUp(self):
        self.config = OpenArchiConfig(_StoreMemoire())
        self.client = _ClientFactice()
        self.vm = OpenArchiChatVM(config=self.config, client=self.client)

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

    def test_message_libre_part_au_fournisseur(self):
        reponse = self.vm.repondre('compare #{Mur type A} et #Porte01')
        self.assertEqual(reponse, self.client.reponse)
        self.assertEqual(self.client.recus[-1],
                         ('user', 'compare #{Mur type A} et #Porte01'))

    def test_historique_alterne_et_exclut_laccueil(self):
        self.vm.Saisie = 'bonjour'
        self.vm._envoyer()
        self.vm.Saisie = 'et ensuite ?'
        self.vm._envoyer()
        self.assertEqual([role for role, _ in self.client.recus],
                         ['user', 'assistant', 'user'])
        self.assertNotIn(self.vm.ACCUEIL,
                         [texte for _, texte in self.client.recus])

    def test_echec_du_fournisseur_affiche_en_bulle(self):
        self.vm._client_injecte = _ClientFactice(
            erreur=RuntimeError('clé absente'))
        reponse = self.vm.repondre('bonjour')
        self.assertIn('clé absente', reponse)
        self.assertIn(self.config.provider, reponse)

    def test_statut_signale_un_client_non_pret(self):
        muet = _ClientFactice()
        muet.pret = lambda: False
        self.vm._client_injecte = muet
        self.assertIn(_ClientFactice.RAISON, self.vm.Statut)
        self.assertIn(self.config.provider, self.vm.Statut)

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
        self.vm = OpenArchiChatVM(config=OpenArchiConfig(_StoreMemoire()),
                                  client=_ClientFactice())

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
        self.vm = OpenArchiChatVM(config=self.config, client=_ClientFactice())

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

    def _suggestion(self, nom):
        return [s for s in self.vm.Suggestions if s.Nom == nom][0]

    def test_choix_persiste_et_met_le_statut_a_jour(self):
        self._ouvrir_la_liste()
        # Le dernier actif, pour ne pas confondre avec le repli par défaut.
        cible = ACTIFS[-1]
        self.vm._choisir(self._suggestion(cible))
        self.assertEqual(self.config.provider, cible)
        self.assertIn(cible, self.vm.Statut)
        # Écrit dans le store, pas seulement le repli du getter.
        self.assertEqual(self.store.get('provider'), cible)

    def test_chaque_fournisseur_actif_a_un_client(self):
        for nom in ACTIFS:
            client = client_de(nom)
            self.assertIsNotNone(client, nom)
            for membre in ('pret', 'repondre', 'RAISON'):
                self.assertTrue(hasattr(client, membre),
                                '{0} sans {1}'.format(nom, membre))

    def test_fournisseurs_non_branches_grises(self):
        self._ouvrir_la_liste()
        grises = [s.Nom for s in self.vm.Suggestions if not s.Actif]
        self.assertEqual(grises, [n for n in PROVIDERS if n not in ACTIFS])
        self.assertTrue(grises, 'le catalogue doit rester un choix à venir')

    def test_choix_dun_fournisseur_grise_refuse(self):
        self._ouvrir_la_liste()
        grise = [s for s in self.vm.Suggestions if not s.Actif][0]
        avant = len(self.vm.Messages)
        self.vm._choisir(grise)
        self.assertEqual(self.config.provider, ACTIFS[0])
        self.assertEqual(len(self.vm.Messages), avant)
        # La liste reste ouverte : le clic n'est pas un choix.
        self.assertTrue(self.vm.SuggestionsVisibles)

    def test_choix_referme_la_liste_et_rend_les_commandes(self):
        self._ouvrir_la_liste()
        avant = len(self.vm.Messages)
        self.vm._choisir(self.vm.Suggestions[0])
        self.assertFalse(self.vm.SuggestionsVisibles)
        self.assertEqual(len(self.vm.Messages), avant + 1)
        self.vm.Saisie = '/'
        self.assertEqual([s.Libelle for s in self.vm.Suggestions],
                         ['/aide', '/connect'])

    def test_tab_choisit_le_premier_fournisseur_actif(self):
        self._ouvrir_la_liste()
        self.vm._completer()
        self.assertEqual(self.config.provider, ACTIFS[0])

    def test_fournisseur_inconnu_ou_debranche_retombe_sur_un_actif(self):
        for valeur in ('Fournisseur Fantome',
                       [n for n in PROVIDERS if n not in ACTIFS][0]):
            store = _StoreMemoire()
            store.set('provider', valeur)
            self.assertEqual(OpenArchiConfig(store).provider, ACTIFS[0])


if __name__ == '__main__':
    unittest.main()
