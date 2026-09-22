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
from ui.OpenArchiConfig import (OpenArchiConfig, PROVIDERS, ACTIFS,
                                CATALOGUE, connexions_de, client_de,
                                HARNAIS, CLE_API, MODELE_DEFAUT)

_GRISES = [nom for nom in PROVIDERS if nom not in ACTIFS]


class _StoreMemoire(object):
    """Double de UserConfig : rien n'est écrit sur le disque pendant les tests."""

    def __init__(self):
        self._d = {}

    def get(self, cle, defaut=None):
        return self._d.get(cle, defaut)

    def set(self, cle, valeur):
        self._d[cle] = valeur


class _StoreChaines(_StoreMemoire):
    """Double fidèle de UserConfig, qui sérialise TOUTE valeur en chaîne."""

    def set(self, cle, valeur):
        self._d[cle] = '{0}'.format(valeur)


class _ClientFactice(object):
    """Double d'un module de chat : ni réseau, ni sous-processus."""

    def __init__(self, reponse='réponse du modèle', erreur=None,
                 pret=True, modeles=(), ouverture=None):
        self.reponse = reponse
        self.erreur = erreur
        self._pret = pret
        self._modeles = tuple(modeles)
        self._ouverture = ouverture
        self.recus = None
        self.modele_recu = None
        self.connexions_ouvertes = 0

    def pret(self):
        return self._pret

    def raison(self):
        return 'raison de factice'

    def connecter(self):
        self.connexions_ouvertes += 1
        return self._ouverture

    def modeles(self):
        return self._modeles

    def repondre(self, messages, modele=None, **_kwargs):
        self.recus = messages
        self.modele_recu = modele
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

    def test_modele_retenu_transmis_au_client(self):
        self.config.appliquer_modele('gpt-test')
        self.vm.repondre('bonjour')
        self.assertEqual(self.client.modele_recu, 'gpt-test')

    def test_echec_du_fournisseur_affiche_en_bulle(self):
        self.vm._client_injecte = _ClientFactice(
            erreur=RuntimeError('clé absente'))
        reponse = self.vm.repondre('bonjour')
        self.assertIn('clé absente', reponse)
        self.assertIn(self.config.provider, reponse)

    def test_statut_est_un_fil_dariane(self):
        self.assertIn(self.config.provider, self.vm.Statut)
        self.assertIn(self.config.connexion, self.vm.Statut)
        self.assertIn(MODELE_DEFAUT, self.vm.Statut)

    def test_statut_signale_un_client_non_pret(self):
        self.vm._client_injecte = _ClientFactice(pret=False)
        self.assertIn('raison de factice', self.vm.Statut)
        self.assertIn(self.config.provider, self.vm.Statut)


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
        self.assertEqual(self._libelles(), ['/aide', '/connect', '/model'])

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

    def test_cliquer_execute_au_lieu_de_remplir(self):
        self.vm.Saisie = '/ai'
        self.vm._choisir(self.vm.Suggestions[0])
        self.assertEqual(self.vm.Saisie, '')
        # La commande a bien tourné : bulle utilisateur + réponse.
        self.assertEqual(self.vm.Messages[-2].Texte, '/aide')
        self.assertTrue(self.vm.Messages[-2].DeUtilisateur)
        self.assertIn('/connect', self.vm.Messages[-1].Texte)

    def test_tab_execute_la_premiere(self):
        self.vm.Saisie = '/'
        self.vm._completer()
        self.assertEqual(self.vm.Messages[-2].Texte, '/aide')

    def test_completer_sans_proposition_ne_fait_rien(self):
        self.vm.Saisie = 'bonjour'
        self.vm._completer()
        self.assertEqual(self.vm.Saisie, 'bonjour')

    def test_envoi_referme_la_liste(self):
        self.vm.Saisie = '/aide'
        self.vm._envoyer()
        self.assertFalse(self.vm.SuggestionsVisibles)


class TestAssistantConnexion(unittest.TestCase):
    """Les trois étapes de /connect : fournisseur → connexion → modèle."""

    def setUp(self):
        self.store = _StoreMemoire()
        self.config = OpenArchiConfig(self.store)
        self.client = _ClientFactice(modeles=('modele-a', 'modele-b'))
        self.vm = OpenArchiChatVM(config=self.config, client=self.client)

    def _noms(self):
        return [s.Nom for s in self.vm.Suggestions]

    def _suggestion(self, nom):
        return [s for s in self.vm.Suggestions if s.Nom == nom][0]

    def _connect(self):
        self.vm.Saisie = '/connect'
        self.vm._envoyer()

    # --- étape 1 : fournisseurs ------------------------------------------

    def test_premiere_etape_ne_montre_que_les_fournisseurs(self):
        self._connect()
        self.assertEqual(self._noms(), list(PROVIDERS))

    def test_fournisseurs_non_branches_grises(self):
        self._connect()
        self.assertEqual([s.Nom for s in self.vm.Suggestions if not s.Actif],
                         _GRISES)
        self.assertTrue(_GRISES, 'le catalogue doit garder un choix à venir')

    def test_fournisseur_grise_refuse_le_choix(self):
        self._connect()
        self.vm._choisir(self._suggestion(_GRISES[0]))
        self.assertEqual(self.config.provider, ACTIFS[0])
        self.assertEqual(self._noms(), list(PROVIDERS))  # on n'a pas avancé

    def test_la_frappe_ne_referme_pas_la_liste(self):
        self._connect()
        self.vm.Saisie = 'Anth'
        self.assertTrue(self.vm.SuggestionsVisibles)

    # --- étape 2 : connexions --------------------------------------------

    def test_choisir_un_fournisseur_montre_ses_connexions(self):
        self._connect()
        self.vm._choisir(self._suggestion('OpenAI'))
        self.assertEqual(self.config.provider, 'OpenAI')
        self.assertEqual(self._noms(), [HARNAIS, CLE_API])

    def test_connexion_prete_mene_aux_modeles(self):
        self._connect()
        self.vm._choisir(self._suggestion('OpenAI'))
        self.vm._choisir(self._suggestion(CLE_API))
        self.assertEqual(self.store.get('connexion'), CLE_API)
        self.assertEqual(self._noms(), ['modele-a', 'modele-b'])

    def test_connexion_non_prete_ouvre_le_navigateur(self):
        self.vm._client_injecte = _ClientFactice(
            pret=False, ouverture='Connexion ouverte dans le navigateur.')
        self._connect()
        self.vm._choisir(self._suggestion('OpenAI'))
        self.vm._choisir(self._suggestion(HARNAIS))
        self.assertEqual(self.vm._client_injecte.connexions_ouvertes, 1)
        self.assertIn('navigateur', self.vm.Messages[-1].Texte)
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_connexion_sans_navigateur_dit_ce_qui_manque(self):
        self.vm._client_injecte = _ClientFactice(pret=False, ouverture=None)
        self._connect()
        self.vm._choisir(self._suggestion('OpenAI'))
        self.vm._choisir(self._suggestion(CLE_API))
        self.assertIn('raison de factice', self.vm.Messages[-1].Texte)

    # --- étape 3 : modèles ------------------------------------------------

    def test_choix_du_modele_persiste_et_ferme(self):
        self._connect()
        self.vm._choisir(self._suggestion('OpenAI'))
        self.vm._choisir(self._suggestion(CLE_API))
        self.vm._choisir(self._suggestion('modele-b'))
        self.assertEqual(self.config.modele, 'modele-b')
        self.assertEqual(self.store.get('modele'), 'modele-b')
        self.assertFalse(self.vm.SuggestionsVisibles)
        self.assertIn('modele-b', self.vm.Statut)

    def test_client_sans_liste_de_modeles_propose_le_defaut(self):
        self.vm._client_injecte = _ClientFactice(modeles=())
        self._connect()
        self.vm._choisir(self._suggestion('OpenAI'))
        self.vm._choisir(self._suggestion(HARNAIS))
        self.assertEqual(self._noms(), [MODELE_DEFAUT])
        self.vm._choisir(self._suggestion(MODELE_DEFAUT))
        # « Défaut » ne se persiste pas comme un nom de modèle.
        self.assertIsNone(self.config.modele)

    # --- navigation -------------------------------------------------------

    def test_echap_remonte_dune_etape_puis_ferme(self):
        self._connect()
        self.vm._choisir(self._suggestion('OpenAI'))
        self.assertEqual(self._noms(), [HARNAIS, CLE_API])
        self.vm._retour()
        self.assertEqual(self._noms(), list(PROVIDERS))
        self.vm._retour()
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_changer_de_fournisseur_oublie_connexion_et_modele(self):
        self.config.appliquer_connexion(CLE_API)
        self.config.appliquer_modele('modele-b')
        self.config.appliquer('OpenAI')
        self.assertIsNone(self.config.modele)
        self.assertFalse(self.store.get('connexion'))

    def test_aucun_none_ecrit_dans_un_magasin_de_chaines(self):
        # UserConfig sérialise tout en chaîne : y écrire None y laisse le
        # texte « None », qui repasserait pour un nom de modèle valide.
        config = OpenArchiConfig(_StoreChaines())
        config.appliquer_modele(None)
        self.assertIsNone(config.modele)
        self.assertNotEqual(config._lire('modele', ''), 'None')


class TestCommandeModel(unittest.TestCase):
    def setUp(self):
        self.config = OpenArchiConfig(_StoreMemoire())
        self.vm = OpenArchiChatVM(
            config=self.config,
            client=_ClientFactice(modeles=('modele-a', 'modele-b')))

    def test_model_ouvre_directement_la_liste_des_modeles(self):
        self.vm.Saisie = '/model'
        self.vm._envoyer()
        self.assertEqual([s.Nom for s in self.vm.Suggestions],
                         ['modele-a', 'modele-b'])

    def test_model_sans_connexion_renvoie_vers_connect(self):
        self.vm._client_injecte = _ClientFactice(pret=False)
        reponse = self.vm.repondre('/model')
        self.assertIn('/connect', reponse)
        self.assertFalse(self.vm.SuggestionsVisibles)


class TestCatalogue(unittest.TestCase):
    def test_chaque_connexion_branchee_honore_le_contrat(self):
        for provider, connexions in CATALOGUE:
            for nom, _description, client in connexions:
                if client is None:
                    continue
                for membre in ('pret', 'raison', 'connecter', 'modeles',
                               'repondre'):
                    self.assertTrue(
                        hasattr(client, membre),
                        '{0}/{1} sans {2}'.format(provider, nom, membre))

    def test_un_fournisseur_actif_a_au_moins_une_connexion_branchee(self):
        for nom in ACTIFS:
            branchees = [c for _n, _d, c in connexions_de(nom)
                         if c is not None]
            self.assertTrue(branchees, nom)

    def test_plus_aucune_ligne_mcp(self):
        for _provider, connexions in CATALOGUE:
            self.assertNotIn('MCP', [nom for nom, _d, _c in connexions])

    def test_client_de_inconnu_vaut_none(self):
        self.assertIsNone(client_de('OpenAI', 'Pigeon voyageur'))
        self.assertIsNone(client_de('Fournisseur Fantome', CLE_API))


if __name__ == '__main__':
    unittest.main()
