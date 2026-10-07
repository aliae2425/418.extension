# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import base64
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> 418.extension/lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from ui import OpenArchiChatVM as chatvm
from ui.OpenArchiChatVM import OpenArchiChatVM
from ui.OpenArchiConfig import (OpenArchiConfig, PROVIDERS, ACTIFS,
                                CATALOGUE, connexions_de, client_de,
                                NAVIGATEUR, NAVIGATEUR_CLI, CLE_API,
                                MODELE_DEFAUT)

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
                 pret=True, modeles=(), ouverture=None, fermeture=None,
                 aboutit=None):
        # attendre_connexion est facultatif dans le contrat : on ne le pose
        # que si le test en veut un, pour couvrir aussi son absence.
        if aboutit is not None:
            self.attendre_connexion = lambda: aboutit
        self.reponse = reponse
        self.erreur = erreur
        self._pret = pret
        self._modeles = tuple(modeles)
        self._ouverture = ouverture
        self._fermeture = fermeture
        self.recus = None
        self.modele_recu = None
        self.pieces_recues = None
        # Le reste du contrat est facultatif : un client qui n'en fait rien
        # l'avale par ses **_kwargs. On le retient pour pouvoir le vérifier.
        self.kwargs = {}
        self.connexions_ouvertes = 0
        self.fermetures = 0

    def pret(self):
        return self._pret

    def raison(self):
        return 'raison de factice'

    def connecter(self):
        self.connexions_ouvertes += 1
        return self._ouverture

    def deconnecter(self):
        self.fermetures += 1
        if isinstance(self._fermeture, Exception):
            raise self._fermeture
        return self._fermeture

    def modeles(self):
        return self._modeles

    def repondre(self, messages, modele=None, pieces=None, **_kwargs):
        self.recus = messages
        self.modele_recu = modele
        self.pieces_recues = pieces
        self.kwargs = _kwargs
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
        self.assertEqual(self._libelles(),
                         ['/aide', '/connect', '/journal', '/logout',
                          '/model', '/routes', '/vider'])

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
        self.assertEqual(self._noms(),
                         [NAVIGATEUR, NAVIGATEUR_CLI, CLE_API])

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
        self.vm._choisir(self._suggestion(NAVIGATEUR))
        self.assertEqual(self.vm._client_injecte.connexions_ouvertes, 1)
        self.assertIn('navigateur', self.vm.Messages[-1].Texte)
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_connexion_aboutie_enchaine_sur_les_modeles(self):
        # Le second /connect manuel ne doit plus être nécessaire.
        self.vm._client_injecte = _ClientFactice(
            pret=False, ouverture='Connexion ouverte…',
            aboutit=True, modeles=('modele-a',))
        self._connect()
        self.vm._choisir(self._suggestion('OpenAI'))
        self.vm._choisir(self._suggestion(NAVIGATEUR))
        self.assertFalse(self.vm.EnAttente)
        self.assertIn('Connecté', self.vm.Messages[-1].Texte)
        self.assertEqual(self._noms(), ['modele-a'])

    def test_connexion_abandonnee_le_dit_et_sarrete(self):
        self.vm._client_injecte = _ClientFactice(
            pret=False, ouverture='Connexion ouverte…', aboutit=False)
        self._connect()
        self.vm._choisir(self._suggestion('OpenAI'))
        self.vm._choisir(self._suggestion(NAVIGATEUR))
        self.assertFalse(self.vm.EnAttente)
        self.assertIn('non aboutie', self.vm.Messages[-1].Texte)
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_client_sans_attente_sarrete_au_message(self):
        self.vm._client_injecte = _ClientFactice(
            pret=False, ouverture='Connexion ouverte…')
        self._connect()
        self.vm._choisir(self._suggestion('OpenAI'))
        self.vm._choisir(self._suggestion(NAVIGATEUR))
        self.assertIn('Connexion ouverte', self.vm.Messages[-1].Texte)
        self.assertFalse(self.vm.EnAttente)

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
        self.vm._choisir(self._suggestion(NAVIGATEUR))
        self.assertEqual(self._noms(), [MODELE_DEFAUT])
        self.vm._choisir(self._suggestion(MODELE_DEFAUT))
        # « Défaut » ne se persiste pas comme un nom de modèle.
        self.assertIsNone(self.config.modele)

    # --- navigation -------------------------------------------------------

    def test_echap_remonte_dune_etape_puis_ferme(self):
        self._connect()
        self.vm._choisir(self._suggestion('OpenAI'))
        self.assertEqual(self._noms(),
                         [NAVIGATEUR, NAVIGATEUR_CLI, CLE_API])
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

    def test_model_avec_un_nom_limpose_sans_liste(self):
        reponse = self.vm.repondre('/model gpt-5.1-codex')
        self.assertEqual(self.config.modele, 'gpt-5.1-codex')
        self.assertIn('gpt-5.1-codex', reponse)
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_connexion_sans_catalogue_propose_la_saisie_libre(self):
        self.vm._client_injecte = _ClientFactice(modeles=())
        reponse = self.vm.repondre('/model')
        self.assertIn('/model <nom>', reponse)

    def test_model_sans_connexion_renvoie_vers_connect(self):
        self.vm._client_injecte = _ClientFactice(pret=False)
        reponse = self.vm.repondre('/model')
        self.assertIn('/connect', reponse)
        self.assertFalse(self.vm.SuggestionsVisibles)


class TestAttente(unittest.TestCase):
    """L'appel au modèle part sur un fil ; l'animation suit EnAttente."""

    def setUp(self):
        self.client = _ClientFactice()
        self.vm = OpenArchiChatVM(config=OpenArchiConfig(_StoreMemoire()),
                                  client=self.client)

    def test_au_repos_rien_ne_sanime(self):
        self.assertFalse(self.vm.EnAttente)

    def test_lattente_retombe_apres_la_reponse(self):
        self.vm.Saisie = 'bonjour'
        self.vm._envoyer()
        self.assertFalse(self.vm.EnAttente)
        self.assertEqual(self.vm.Messages[-1].Texte, self.client.reponse)

    def test_une_commande_ne_declenche_pas_lattente(self):
        vus = []
        original = OpenArchiChatVM._en_arriere_plan
        OpenArchiChatVM._en_arriere_plan = (
            lambda soi, travail, suite: vus.append(1) or suite(travail()))
        try:
            self.vm.Saisie = '/aide'
            self.vm._envoyer()
        finally:
            OpenArchiChatVM._en_arriere_plan = original
        self.assertEqual(vus, [], 'les commandes restent sur le fil d\'interface')

    def test_pas_de_second_envoi_pendant_lattente(self):
        self.vm.EnAttente = True
        self.vm.Saisie = 'bonjour'
        self.assertFalse(self.vm._peut_envoyer())
        self.vm._envoyer()
        self.assertEqual(len(self.vm.Messages), 1)

    def test_lattente_retombe_meme_si_le_client_leve(self):
        self.vm._client_injecte = _ClientFactice(erreur=RuntimeError('boum'))
        self.vm.Saisie = 'bonjour'
        self.vm._envoyer()
        self.assertFalse(self.vm.EnAttente)
        self.assertIn('boum', self.vm.Messages[-1].Texte)


class TestLogout(unittest.TestCase):
    def setUp(self):
        self.config = OpenArchiConfig(_StoreMemoire())
        self.client = _ClientFactice(fermeture='Session fermée.')
        self.vm = OpenArchiChatVM(config=self.config, client=self.client)

    def test_logout_ferme_la_session(self):
        reponse = self.vm.repondre('/logout')
        self.assertEqual(self.client.fermetures, 1)
        self.assertIn('fermée', reponse)

    def test_logout_sans_rien_a_fermer(self):
        self.vm._client_injecte = _ClientFactice(fermeture=None)
        self.assertIn('Rien à fermer', self.vm.repondre('/logout'))

    def test_echec_du_logout_reste_dans_la_bulle(self):
        self.vm._client_injecte = _ClientFactice(
            fermeture=RuntimeError('codex absent'))
        reponse = self.vm.repondre('/logout')
        self.assertIn('codex absent', reponse)
        self.assertIn(self.config.provider, reponse)


class TestCatalogue(unittest.TestCase):
    def test_chaque_connexion_branchee_honore_le_contrat(self):
        for provider, connexions in CATALOGUE:
            for nom, _description, client in connexions:
                if client is None:
                    continue
                for membre in ('pret', 'raison', 'connecter', 'deconnecter',
                               'modeles', 'repondre'):
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


class TestHistoriqueSaisie(unittest.TestCase):
    """Flèches Haut / Bas : rappeler un message envoyé, comme un terminal."""

    def setUp(self):
        self.vm = OpenArchiChatVM(OpenArchiConfig(_StoreMemoire()),
                                  client=_ClientFactice())

    def _envoyer(self, texte):
        self.vm.Saisie = texte
        self.vm._envoyer()

    def test_rien_a_rappeler_au_depart(self):
        self.vm._precedent()
        self.assertEqual(self.vm.Saisie, '')

    def test_haut_rappelle_le_dernier_envoi(self):
        self._envoyer('bonjour')
        self.vm._precedent()
        self.assertEqual(self.vm.Saisie, 'bonjour')

    def test_haut_remonte_du_plus_recent_au_plus_ancien(self):
        self._envoyer('un')
        self._envoyer('deux')
        self.vm._precedent()
        self.assertEqual(self.vm.Saisie, 'deux')
        self.vm._precedent()
        self.assertEqual(self.vm.Saisie, 'un')

    def test_on_bute_sur_le_plus_ancien_sans_se_vider(self):
        self._envoyer('un')
        for _ in range(5):
            self.vm._precedent()
        self.assertEqual(self.vm.Saisie, 'un')

    def test_bas_redescend(self):
        self._envoyer('un')
        self._envoyer('deux')
        self.vm._precedent()
        self.vm._precedent()
        self.vm._suivant()
        self.assertEqual(self.vm.Saisie, 'deux')

    def test_le_brouillon_est_rendu_en_redescendant(self):
        # Ce qu'on était en train de taper ne doit pas être perdu parce
        # qu'on a jeté un œil à l'historique.
        self._envoyer('un')
        self.vm.Saisie = 'moitié de phra'
        self.vm._precedent()
        self.assertEqual(self.vm.Saisie, 'un')
        self.vm._suivant()
        self.assertEqual(self.vm.Saisie, 'moitié de phra')

    def test_bas_sans_navigation_en_cours_ne_fait_rien(self):
        self._envoyer('un')
        self.vm.Saisie = 'en cours'
        self.vm._suivant()
        self.assertEqual(self.vm.Saisie, 'en cours')

    def test_taper_quitte_l_historique(self):
        self._envoyer('un')
        self._envoyer('deux')
        self.vm._precedent()          # « deux »
        self.vm.Saisie = 'autre chose'
        self.vm._precedent()          # repart du plus récent
        self.assertEqual(self.vm.Saisie, 'deux')

    def test_une_commande_se_rejoue(self):
        # C'est l'usage visé : relancer /journal sans le retaper.
        self._envoyer('/aide')
        self.vm._precedent()
        self.assertEqual(self.vm.Saisie, '/aide')

    def test_pas_de_doublon_immediat(self):
        self._envoyer('/aide')
        self._envoyer('/aide')
        self.vm._precedent()
        self.vm._precedent()
        self.assertEqual(self.vm.Saisie, '/aide')
        self.assertEqual(len(self.vm._saisies), 1)

    def test_un_envoi_reinitialise_la_navigation(self):
        self._envoyer('un')
        self.vm._precedent()
        self._envoyer('deux')
        self.assertEqual(self.vm.Saisie, '')
        self.vm._precedent()
        self.assertEqual(self.vm.Saisie, 'deux')


class TestAttente(unittest.TestCase):
    """Phrases qui tournent et chronomètre. Le DispatcherTimer est absent
    hors .NET : on appelle ``_tic()`` à sa place, une seconde par appel."""

    def setUp(self):
        self.vm = OpenArchiChatVM(OpenArchiConfig(_StoreMemoire()),
                                  client=_ClientFactice())

    def test_pas_de_chrono_avant_la_premiere_seconde(self):
        self.vm.TexteAttente = None
        self.vm.EnAttente = True
        self.assertNotIn('·', self.vm.TexteAttente)

    def test_le_chrono_avance(self):
        self.vm.EnAttente = True
        self.vm._tic()
        self.assertIn('1 s', self.vm.TexteAttente)
        self.vm._tic()
        self.assertIn('2 s', self.vm.TexteAttente)

    def test_un_libelle_impose_ne_tourne_pas(self):
        # « connexion… » dit ce qui se passe ; une blague serait du bruit.
        self.vm.TexteAttente = 'connexion…'
        self.vm.EnAttente = True
        for _ in range(20):
            self.vm._tic()
        self.assertTrue(self.vm.TexteAttente.startswith('connexion…'))

    def test_la_phrase_change_en_cours_d_attente(self):
        from core import attente
        self.vm.TexteAttente = None
        self.vm.EnAttente = True
        depart = self.vm._phrase
        for _ in range(attente.TOURNE):
            self.vm._tic()
        self.assertNotEqual(self.vm._phrase, depart)

    def test_chaque_attente_repart_de_zero(self):
        # C'est le temps de CETTE réponse qui intéresse, pas le cumul.
        self.vm.EnAttente = True
        for _ in range(5):
            self.vm._tic()
        self.vm.EnAttente = False
        self.vm.EnAttente = True
        self.assertNotIn('·', self.vm.TexteAttente)

    def test_la_duree_est_posee_sous_la_reponse(self):
        self.vm.Saisie = 'bonjour'
        self.vm.EnAttente = True
        for _ in range(3):
            self.vm._tic()
        self.vm._sur_reponse('voilà')
        bulle = self.vm.Messages[-1]
        self.assertIn('3 s', bulle.Duree)
        self.assertTrue(bulle.DureeVisible)

    def test_une_reponse_instantanee_n_affiche_pas_de_duree(self):
        # « 0 s » sous une commande locale n'apprend rien.
        self.vm._sur_reponse('voilà')
        self.assertEqual(self.vm.Messages[-1].Duree, '')
        self.assertFalse(self.vm.Messages[-1].DureeVisible)

    def test_hors_wpf_la_bulle_retombe_sur_le_texte_nu(self):
        # MiseEnForme faux = le RichTextBox n'est pas construit. C'est le
        # verrou : sa propriété Document refuse null.
        from ui.OpenArchiChatVM import MessageVM
        bulle = MessageVM('OpenArchi', 'un **gras** et `du code`', False)
        self.assertFalse(bulle.MiseEnForme)
        self.assertIsNone(bulle.Document)
        self.assertNotIn('**', bulle.TexteAffiche)

    def test_le_texte_brut_survit_a_la_mise_en_forme(self):
        # C'est lui qui repart au fournisseur dans l'historique.
        from ui.OpenArchiChatVM import MessageVM
        bulle = MessageVM('OpenArchi', 'un **gras**', False)
        self.assertEqual(bulle.Texte, 'un **gras**')

    def test_l_accueil_n_a_pas_de_duree(self):
        self.assertFalse(self.vm.Messages[0].DureeVisible)

    def test_une_reponse_arrete_le_chrono(self):
        self.vm.Saisie = 'bonjour'
        self.vm._envoyer()
        self.assertFalse(self.vm.EnAttente)
        self.assertEqual(self.vm._secondes, 0)


class TestAlerteMaquette(unittest.TestCase):
    """Le bandeau en tête du chat : ce qui empêche les outils de marcher."""

    def setUp(self):
        self.vm = OpenArchiChatVM(OpenArchiConfig(_StoreMemoire()),
                                  client=_ClientFactice())

    def test_pas_de_bandeau_au_repos(self):
        self.assertEqual(self.vm.Alerte, '')
        self.assertFalse(self.vm.AlerteVisible)

    def test_une_raison_affiche_le_bandeau(self):
        self.vm.Alerte = 'Maquette injoignable : rechargez pyRevit.'
        self.assertTrue(self.vm.AlerteVisible)
        self.assertIn('injoignable', self.vm.Alerte)

    def test_le_bandeau_se_referme_quand_ca_remarche(self):
        self.vm.Alerte = 'cassé'
        self.vm.Alerte = ''
        self.assertFalse(self.vm.AlerteVisible)

    def test_un_echec_laisse_une_bulle_dans_le_fil(self):
        # Le bandeau expire et se fait ecraser : il ne peut pas etre le seul
        # canal. La bulle, elle, reste et se colle dans un rapport.
        from core import revit_outils
        revit_outils._echec['texte'] = 'revit_execute_code — AttributeError'
        avant = len(self.vm.Messages)
        try:
            self.vm._signaler_echec()
        finally:
            revit_outils._echec['texte'] = ''
        self.assertEqual(len(self.vm.Messages), avant + 1)
        self.assertIn('AttributeError', self.vm.Messages[-1].Texte)

    def test_sans_echec_aucune_bulle_n_est_ajoutee(self):
        avant = len(self.vm.Messages)
        self.vm._signaler_echec()
        self.assertEqual(len(self.vm.Messages), avant)

    def test_rafraichir_l_alerte_ne_touche_pas_au_reseau(self):
        # Le bandeau relit le dernier verdict connu. Relancer une requête
        # juste pour l'afficher, c'était une collision de plus sur le serveur
        # de routes — et un crash de Revit.
        from core import revit_outils
        appels = []
        vrai = revit_outils._appeler
        revit_outils._appeler = lambda *a, **k: appels.append(a)
        try:
            self.vm._rafraichir_alerte()
        finally:
            revit_outils._appeler = vrai
        self.assertEqual(appels, [])

    def test_un_echec_d_outil_s_affiche_en_rouge(self):
        from core import revit_outils
        revit_outils._echec['texte'] = 'revit_execute_code — AttributeError'
        try:
            self.vm._signaler_echec()
            self.assertTrue(self.vm.AlerteVisible)
            self.assertTrue(self.vm.AlerteGrave)
            self.assertIn('AttributeError', self.vm.Alerte)
        finally:
            revit_outils._echec['texte'] = ''

    def test_un_echec_prime_sur_l_etat(self):
        # L'état décrit, l'échec vient de se produire.
        from core import revit_outils
        revit_outils._echec['texte'] = 'revit_status — HTTP 500'
        revit_outils._dernier['raison'] = 'Aucun document Revit ouvert'
        try:
            self.vm._signaler_echec()
            self.assertIn('500', self.vm.Alerte)
        finally:
            revit_outils._echec['texte'] = ''
            revit_outils._dernier['raison'] = ''

    def test_un_echec_n_est_affiche_qu_une_fois(self):
        from core import revit_outils
        revit_outils._echec['texte'] = 'revit_status — cassé'
        try:
            self.vm._signaler_echec()
            self.assertTrue(self.vm.AlerteGrave)
            self.vm.Alerte = ''
            self.vm._signaler_echec()      # ne doit pas le rejouer
            self.assertFalse(self.vm.AlerteGrave)
        finally:
            revit_outils._echec['texte'] = ''

    def test_envoyer_referme_le_toast(self):
        # Il parlait du message précédent.
        self.vm._toast('revit_status — cassé')
        self.vm.Saisie = 'et maintenant ?'
        self.vm._envoyer()
        self.assertFalse(self.vm.AlerteGrave)

    def test_le_bandeau_suit_le_dernier_verdict(self):
        from core import revit_outils
        revit_outils._dernier['raison'] = 'Aucun document Revit ouvert'
        try:
            self.vm._rafraichir_alerte()
            self.assertTrue(self.vm.AlerteVisible)
        finally:
            revit_outils._dernier['raison'] = ''

    def test_une_suite_qui_leve_ne_tue_pas_le_fil_d_interface(self):
        # Sans l'enveloppe de `_en_arriere_plan`, l'exception part non
        # rattrapée sur le fil d'interface de Revit et le process meurt.
        def casse(_resultat):
            raise RuntimeError('boum dans la suite')
        self.vm._en_arriere_plan(lambda: 'ok', casse)   # ne doit pas lever


class TestPiecesJointes(unittest.TestCase):
    """Glisser-déposer : le panneau ne fait que passer les chemins ici."""

    def setUp(self):
        self.client = _ClientFactice()
        self.vm = OpenArchiChatVM(config=OpenArchiConfig(_StoreMemoire()),
                                  client=self.client)
        self.dossier = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def _ecrire(self, nom, octets):
        chemin = os.path.join(self.dossier, nom)
        with open(chemin, 'wb') as fichier:
            fichier.write(octets)
        return chemin

    def test_la_bulle_reste_courte_mais_l_historique_porte_tout(self):
        chemin = self._ecrire('plan.csv', 'niveau;surface\nR+1;42\n'.encode())
        self.vm.deposer([chemin])
        bulle = self.vm.Messages[-1]
        self.assertTrue(bulle.DeUtilisateur)
        self.assertIn('plan.csv', bulle.TexteAffiche)
        self.assertNotIn('R+1', bulle.TexteAffiche)
        self.assertIn('R+1', bulle.Texte)

    def test_deposer_n_envoie_rien(self):
        self.vm.deposer([self._ecrire('note.md', b'# titre')])
        self.assertIsNone(self.client.recus)

    def test_la_piece_repart_dans_l_historique_du_message_suivant(self):
        self.vm.deposer([self._ecrire('note.md', b'surface utile 42')])
        self.vm.Saisie = 'et donc ?'
        self.vm._envoyer()
        envoye = '\n'.join(texte for _role, texte in self.client.recus)
        self.assertIn('surface utile 42', envoye)

    def test_un_binaire_inconnu_est_refuse_sans_bulle_utilisateur(self):
        # Un .docx est bien binaire et on ne sait pas l'extraire — contrairement
        # à un PNG, que le modèle sait regarder (cf. TestImages).
        self.vm.deposer([self._ecrire('note.docx', b'PK\x03\x04\x00 zip')])
        dernier = self.vm.Messages[-1]
        self.assertFalse(dernier.DeUtilisateur)
        self.assertIn('binaire', dernier.Texte)

    def test_au_dela_du_plafond_c_est_tronque_et_annonce(self):
        self.vm.PIECE_MAX = 64
        self.vm.deposer([self._ecrire('gros.txt', b'a' * 500)])
        bulle = self.vm.Messages[-1]
        self.assertIn('tronqué', bulle.TexteAffiche)
        self.assertLess(len(bulle.Texte), 500)

    def test_un_chemin_illisible_ne_leve_pas(self):
        # Un dépôt qui lève, c'est Revit qui tombe : le fil d'UI appelle
        # deposer() directement.
        self.vm.deposer([os.path.join(self.dossier, 'absent.txt'),
                         self.dossier])
        self.assertEqual(len(self.vm.Messages), 3)


class TestPdf(TestPiecesJointes):
    """Le PDF part au fournisseur en base64 — là où c'est possible."""

    def _pdf(self, octets=b'%PDF-1.7\n\x00 faux mais binaire'):
        return self._ecrire('notice.pdf', octets)

    def test_hors_cle_api_c_est_un_refus_annonce(self):
        self.vm._config.appliquer_connexion(NAVIGATEUR)
        self.vm.deposer([self._pdf()])
        dernier = self.vm.Messages[-1]
        self.assertFalse(dernier.DeUtilisateur)
        self.assertIn(CLE_API, dernier.Texte)
        self.assertEqual(self.vm._pieces(), [])

    def test_sur_cle_api_la_piece_voyage_en_base64(self):
        self.vm._config.appliquer_connexion(CLE_API)
        self.vm.deposer([self._pdf(b'%PDF-1.7 corps')])
        piece = self.vm._pieces()[0]
        self.assertEqual(piece['nom'], 'notice.pdf')
        self.assertEqual(piece['media'], 'application/pdf')
        self.assertEqual(base64.b64decode(piece['b64']), b'%PDF-1.7 corps')

    def test_la_piece_accompagne_l_appel_au_fournisseur(self):
        self.vm._config.appliquer_connexion(CLE_API)
        self.vm.deposer([self._pdf()])
        self.vm.Saisie = 'que dit cette notice ?'
        self.vm._envoyer()
        self.assertEqual(len(self.client.pieces_recues), 1)
        # Le PDF ne doit pas AUSSI se retrouver en texte dans l'historique.
        self.assertNotIn('%PDF', '\n'.join(t for _r, t in self.client.recus))

    def test_au_dela_du_plafond_rien_n_est_joint(self):
        self.vm._config.appliquer_connexion(CLE_API)
        self.vm.PDF_MAX = 32
        self.vm.deposer([self._pdf(b'%PDF' + b'x' * 500)])
        self.assertEqual(self.vm._pieces(), [])
        self.assertIn('plafond', self.vm.Messages[-1].Texte)

    def test_un_pdf_n_est_jamais_lu_comme_du_binaire_generique(self):
        # Sans l'aiguillage par extension, il tomberait dans _joindre_texte
        # et se ferait refuser pour « format binaire » — message trompeur.
        self.vm._config.appliquer_connexion(NAVIGATEUR)
        self.vm.deposer([self._pdf()])
        self.assertNotIn('binaire', self.vm.Messages[-1].Texte)


class TestImages(TestPiecesJointes):
    """Un PNG n'est pas un binaire illisible : le modèle sait le regarder."""

    def _png(self, octets=b'\x89PNG\r\n\x1a\n faux mais binaire'):
        return self._ecrire('facade.png', octets)

    def test_sur_cle_api_l_image_voyage_en_base64(self):
        self.vm._config.appliquer_connexion(CLE_API)
        self.vm.deposer([self._png(b'\x89PNG corps')])
        piece = self.vm._pieces()[0]
        self.assertEqual(piece['media'], 'image/png')
        self.assertEqual(base64.b64decode(piece['b64']), b'\x89PNG corps')

    def test_hors_cle_api_c_est_un_refus_annonce(self):
        self.vm._config.appliquer_connexion(NAVIGATEUR)
        self.vm.deposer([self._png()])
        self.assertIn(CLE_API, self.vm.Messages[-1].Texte)
        self.assertEqual(self.vm._pieces(), [])

    def test_le_jpeg_porte_le_bon_type(self):
        self.vm._config.appliquer_connexion(CLE_API)
        self.vm.deposer([self._ecrire('coupe.jpg', b'\xff\xd8\xff corps')])
        self.assertEqual(self.vm._pieces()[0]['media'], 'image/jpeg')

    def test_au_dela_du_plafond_rien_n_est_joint(self):
        self.vm._config.appliquer_connexion(CLE_API)
        self.vm.IMAGE_MAX = 32
        self.vm.deposer([self._png(b'\x89PNG' + b'x' * 500)])
        self.assertEqual(self.vm._pieces(), [])
        self.assertIn('plafond', self.vm.Messages[-1].Texte)


class TestVider(unittest.TestCase):
    """La seule porte de sortie d'un historique qui enfle, et d'une pièce
    jointe qui repart dans chaque requête."""

    def setUp(self):
        self.client = _ClientFactice()
        self.vm = OpenArchiChatVM(config=OpenArchiConfig(_StoreMemoire()),
                                  client=self.client)
        self.dossier = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_la_conversation_repart_de_l_accueil(self):
        self.vm.Saisie = 'bonjour'
        self.vm._envoyer()
        self.vm.Saisie = '/vider'
        self.vm._envoyer()
        # L'accueil, puis le compte rendu de /vider : rien d'avant.
        self.assertEqual(len(self.vm.Messages), 2)
        self.assertIn('vidée', self.vm.Messages[-1].Texte)

    def test_l_historique_envoye_ne_porte_plus_rien(self):
        self.vm.Saisie = 'retiens ce chiffre : 1789'
        self.vm._envoyer()
        self.vm.repondre('/vider')
        self.vm.Saisie = 'et donc ?'
        self.vm._envoyer()
        self.assertNotIn('1789', '\n'.join(t for _r, t in self.client.recus))

    def test_routes_hors_revit_le_dit_au_lieu_de_lever(self):
        # La commande touche les réglages pyRevit, absents en test : elle doit
        # rendre une phrase, pas une trace.
        self.assertIn('pyRevit', self.vm.repondre('/routes'))

    def test_la_piece_jointe_est_decrochee(self):
        chemin = os.path.join(self.dossier, 'notice.pdf')
        with open(chemin, 'wb') as fichier:
            fichier.write(b'%PDF-1.7 corps')
        self.vm._config.appliquer_connexion(CLE_API)
        self.vm.deposer([chemin])
        self.assertEqual(len(self.vm._pieces()), 1)
        self.assertIn('1 pièce', self.vm.repondre('/vider'))
        self.assertEqual(self.vm._pieces(), [])


class TestAccordIrreversible(unittest.TestCase):
    """Une consigne d'invite n'est pas un garde-fou : l'interface, si."""

    def setUp(self):
        self.vm = OpenArchiChatVM(config=OpenArchiConfig(_StoreMemoire()),
                                  client=_ClientFactice())

    def test_sans_dispatcher_la_demande_se_referme_sur_un_refus(self):
        # Hors .NET, la question est posée sur le fil qui attendrait la
        # réponse : attendre serait un interblocage de cinq minutes.
        self.assertFalse(self.vm._confirmer('revit_synchroniser', {}))
        self.assertFalse(self.vm.SuggestionsVisibles)
        self.assertIn('IRRÉVERSIBLE', self.vm.Messages[-2].Texte)
        self.assertIn('Refusé', self.vm.Messages[-1].Texte)

    def test_refuser_est_la_premiere_entree(self):
        # Tab complète sur la première retenable : une frappe distraite ne
        # doit pas pousser une synchronisation sur le central.
        self.vm._ouvrir('accord')
        self.assertEqual([s.Nom for s in self.vm.Suggestions],
                         ['refuser', 'accorder'])

    def test_accorder_debloque_le_fil_de_fond(self):
        import threading
        signal = threading.Event()
        reponse = {}
        self.vm._poser_question('revit_exporter', {'format': 'pdf'},
                                reponse, signal)
        self.vm._choisir(self.vm.Suggestions[1])
        self.assertTrue(reponse['oui'])
        self.assertTrue(signal.is_set())

    def test_echap_refuse_au_lieu_de_remonter(self):
        import threading
        signal = threading.Event()
        reponse = {}
        self.vm._poser_question('revit_synchroniser', {}, reponse, signal)
        self.vm._retour()
        self.assertFalse(reponse['oui'])
        self.assertTrue(signal.is_set())
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_le_client_recoit_de_quoi_demander(self):
        # Sans ces deux rappels, la boucle d'outils n'a ni voix ni frein.
        self.vm.Saisie = 'synchronise'
        self.vm._envoyer()
        self.assertTrue(callable(self.vm._client.kwargs['confirmer']))
        self.assertTrue(callable(self.vm._client.kwargs['avancement']))


class TestDwg(TestPiecesJointes):
    """Le DWG passe par Revit, et seulement après confirmation."""

    def setUp(self):
        TestPiecesJointes.setUp(self)
        self.appels = []

        class _Pont(object):
            @staticmethod
            def executer(nom, arguments=None):
                self.appels.append((nom, arguments))
                return json.dumps({'lie': 'plan.dwg', 'vue': 'Niveau 0',
                                   'calques': ['MURS', 'COTES']})
        self._pont_sauve = chatvm.revit_outils
        chatvm.revit_outils = _Pont

    def tearDown(self):
        chatvm.revit_outils = self._pont_sauve
        TestPiecesJointes.tearDown(self)

    def _dwg(self):
        return self._ecrire('plan.dwg', b'AC1032\x00\x00 binaire')

    def test_le_depot_demande_avant_d_ecrire(self):
        self.vm.deposer([self._dwg()])
        self.assertTrue(self.vm.SuggestionsVisibles)
        self.assertEqual([s.Nom for s in self.vm.Suggestions],
                         ['lier', 'annuler'])
        self.assertEqual(self.appels, [])      # rien n'a touché la maquette

    def test_lier_appelle_l_outil_revit_et_resume(self):
        chemin = self._dwg()
        self.vm.deposer([chemin])
        self.vm._choisir(self.vm.Suggestions[0])
        self.assertEqual(self.appels, [('revit_lier_dwg', {'chemin': chemin})])
        self.assertIn('Niveau 0', self.vm.Messages[-1].Texte)
        self.assertIn('MURS', self.vm.Messages[-1].Texte)
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_annuler_n_ecrit_rien(self):
        self.vm.deposer([self._dwg()])
        self.vm._choisir(self.vm.Suggestions[1])
        self.assertEqual(self.appels, [])
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_echap_sur_un_depot_annule_au_lieu_de_remonter(self):
        # 'depot' n'est pas dans ETAPES : sans sa branche, _retour lève un
        # ValueError sur .index() — et ça part du fil d'interface.
        self.vm.deposer([self._dwg()])
        self.vm._retour()
        self.assertEqual(self.appels, [])
        self.assertFalse(self.vm.SuggestionsVisibles)

    def test_un_echec_de_l_outil_se_lit_dans_la_bulle(self):
        chatvm.revit_outils = type('P', (), {'executer': staticmethod(
            lambda nom, arguments=None: json.dumps(
                {'erreur': 'aucune vue active'}))})
        self.vm.deposer([self._dwg()])
        self.vm._choisir(self.vm.Suggestions[0])
        self.assertIn('aucune vue active', self.vm.Messages[-1].Texte)


if __name__ == '__main__':
    unittest.main()
