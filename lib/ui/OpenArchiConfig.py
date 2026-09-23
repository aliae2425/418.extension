# -*- coding: utf-8 -*-
"""Réglages OpenArchi : fournisseur, connexion, modèle — persistés en JSON."""
from __future__ import unicode_literals

try:
    from core.UserConfig import UserConfig
except Exception:
    try:
        from lib.core.UserConfig import UserConfig
    except Exception:
        UserConfig = None

try:
    from core import chat_openai, chat_cli, chat_oauth
except Exception:
    from lib.core import chat_openai, chat_cli, chat_oauth

NAVIGATEUR = 'Navigateur'
NAVIGATEUR_CLI = 'Navigateur (codex)'
CLE_API = 'Clé API'

# Arbre à trois niveaux : fournisseur → connexion → modèle. Une connexion sans
# module client est listée mais grisée ; un fournisseur dont aucune connexion
# n'a de client l'est aussi. Le même champ décide de l'affichage ET de
# l'aiguillage : il n'y a pas de drapeau « actif » à tenir à jour en double.
#
# Pas de ligne MCP : on n'a rien à y brancher aujourd'hui.
# ponytail: catalogue en dur. Le jour où l'on interroge les fournisseurs,
# remplacer cette liste par un appel réseau mis en cache.
CATALOGUE = [
    ('OpenAI', [
        # En tête : c'est le défaut, et il ne demande rien à installer.
        (NAVIGATEUR, 'abonnement ChatGPT, sans rien installer', chat_oauth),
        (NAVIGATEUR_CLI, 'abonnement ChatGPT, via le CLI codex', chat_cli),
        (CLE_API, 'facturé à l\'usage, OPENAI_API_KEY', chat_openai),
    ]),
    ('Anthropic', [
        (NAVIGATEUR, 'abonnement Claude', None),
        (CLE_API, 'ANTHROPIC_API_KEY', None),
    ]),
    ('Ollama (local)', [
        (CLE_API, 'serveur local', None),
    ]),
]

MODELE_DEFAUT = 'Défaut du fournisseur'

PROVIDERS = [nom for nom, _connexions in CATALOGUE]
ACTIFS = [nom for nom, connexions in CATALOGUE
          if any(client is not None for _n, _d, client in connexions)]


def connexions_de(provider):
    """Triplets ``(nom, description, client)`` du fournisseur."""
    for nom, connexions in CATALOGUE:
        if nom == provider:
            return list(connexions)
    return []


def client_de(provider, connexion):
    """Module de chat, ``None`` si la connexion n'est pas branchée.

    Contrat d'un client : ``pret()``, ``raison()``, ``connecter()``,
    ``modeles()``, ``repondre(messages, modele=None)`` où ``messages`` est une
    liste de couples ``(role, texte)``.
    """
    for nom, _description, client in connexions_de(provider):
        if nom == connexion:
            return client
    return None


class OpenArchiConfig(object):
    """Fournisseur, connexion et modèle retenus. Source unique lue par le chat."""

    def __init__(self, store=None):
        if store is None and UserConfig is not None:
            store = UserConfig('openarchi')
        self._store = store
        self._memoire = {}

    # --- lecture ---------------------------------------------------------

    def _lire(self, cle, defaut):
        if self._store is None:
            return self._memoire.get(cle, defaut)
        return self._store.get(cle, defaut)

    @property
    def provider(self):
        # Repli sur le premier fournisseur actif : un réglage persisté peut
        # référencer un fournisseur retiré, ou débranché depuis.
        valeur = self._lire('provider', ACTIFS[0])
        return valeur if valeur in ACTIFS else ACTIFS[0]

    @property
    def connexion(self):
        # Repli sur la première connexion branchée du fournisseur courant.
        branchees = [nom for nom, _d, client in connexions_de(self.provider)
                     if client is not None]
        valeur = self._lire('connexion', None)
        return valeur if valeur in branchees else (branchees[0] if branchees
                                                   else None)

    @property
    def modele(self):
        """``None`` = laisser le fournisseur choisir."""
        return self._lire('modele', '') or None

    @property
    def client(self):
        return client_de(self.provider, self.connexion)

    # --- écriture --------------------------------------------------------

    def appliquer(self, provider):
        # Changer de fournisseur invalide la connexion et le modèle : les
        # laisser en place ferait pointer /model sur un catalogue étranger.
        self._ecrire('provider', provider)
        self._ecrire('connexion', None)
        self._ecrire('modele', None)

    def appliquer_connexion(self, connexion):
        self._ecrire('connexion', connexion)
        self._ecrire('modele', None)

    def appliquer_modele(self, modele):
        self._ecrire('modele', modele)

    def _ecrire(self, cle, valeur):
        # UserConfig est un magasin de chaînes : il sérialise None en « None ».
        # On écrit '' pour « pas de choix », jamais None.
        valeur = valeur or ''
        if self._store is None:
            self._memoire[cle] = valeur
        else:
            self._store.set(cle, valeur)
