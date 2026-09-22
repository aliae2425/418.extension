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

# Deux façons d'attacher un modèle : l'API du fournisseur en direct, ou un
# serveur MCP. Seul OpenAI en direct est branché ; les autres restent listés
# mais inactifs, et /connect les grise.
# ponytail: catalogue en dur. Le jour où l'on interroge les fournisseurs,
# remplacer cette liste par un appel réseau mis en cache.
CATALOGUE = [
    ('OpenAI', 'API directe, clé OPENAI_API_KEY', True),
    ('Anthropic', 'pas encore branché', False),
    ('Ollama (local)', 'pas encore branché', False),
    ('MCP', 'pas encore branché', False),
]

PROVIDERS = [nom for nom, _description, _actif in CATALOGUE]
ACTIFS = [nom for nom, _description, actif in CATALOGUE if actif]


def est_actif(provider):
    return provider in ACTIFS


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
