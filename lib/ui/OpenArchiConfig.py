# -*- coding: utf-8 -*-
"""Réglage OpenArchi : le fournisseur de modèle, persisté en JSON."""
from __future__ import unicode_literals

try:
    from core.UserConfig import UserConfig
except Exception:
    try:
        from lib.core.UserConfig import UserConfig
    except Exception:
        UserConfig = None

try:
    from core import chat_openai, chat_cli
except Exception:
    from lib.core import chat_openai, chat_cli

# Trois façons d'attacher un modèle : la clé API du fournisseur, un CLI déjà
# connecté dans le navigateur (l'abonnement paie, pas de clé à gérer), ou un
# serveur MCP. Une entrée sans client est listée mais grisée par /connect.
# ponytail: catalogue en dur. Le jour où l'on interroge les fournisseurs,
# remplacer cette liste par un appel réseau mis en cache.
CATALOGUE = [
    ('ChatGPT (navigateur)', 'abonnement ChatGPT, via le CLI codex', chat_cli),
    ('OpenAI (clé API)', 'facturé à l\'usage, clé OPENAI_API_KEY', chat_openai),
    ('Anthropic', 'pas encore branché', None),
    ('Ollama (local)', 'pas encore branché', None),
    ('MCP', 'pas encore branché', None),
]

PROVIDERS = [nom for nom, _description, _client in CATALOGUE]
ACTIFS = [nom for nom, _description, client in CATALOGUE if client is not None]
_CLIENTS = dict((nom, client) for nom, _description, client in CATALOGUE)


def est_actif(provider):
    return provider in ACTIFS


def client_de(provider):
    """Module de chat du fournisseur retenu. Contrat : ``pret()``, ``RAISON``,
    ``repondre(messages)`` où ``messages`` est une liste de (role, texte)."""
    return _CLIENTS.get(provider)


class OpenArchiConfig(object):
    """Fournisseur retenu. Source unique lue par le chat."""

    def __init__(self, store=None):
        if store is None and UserConfig is not None:
            store = UserConfig('openarchi')
        self._store = store
        self._memoire = ACTIFS[0]

    @property
    def provider(self):
        # Repli sur le premier fournisseur actif : un réglage persisté peut
        # référencer un fournisseur retiré, ou débranché depuis.
        if self._store is None:
            valeur = self._memoire
        else:
            valeur = self._store.get('provider', ACTIFS[0])
        return valeur if valeur in ACTIFS else ACTIFS[0]

    def appliquer(self, provider):
        if self._store is None:
            self._memoire = provider
        else:
            self._store.set('provider', provider)
