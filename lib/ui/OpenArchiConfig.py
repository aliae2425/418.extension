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

# ponytail: catalogue en dur. Le jour où l'on interroge les fournisseurs,
# remplacer cette liste par un appel réseau mis en cache.
PROVIDERS = ['Anthropic', 'OpenAI', 'Ollama (local)']


class OpenArchiConfig(object):
    """Fournisseur retenu. Source unique lue par le chat."""

    def __init__(self, store=None):
        if store is None and UserConfig is not None:
            store = UserConfig('openarchi')
        self._store = store
        self._memoire = PROVIDERS[0]

    @property
    def provider(self):
        # Repli sur le premier du catalogue : un réglage persisté peut
        # référencer un fournisseur retiré depuis.
        if self._store is None:
            valeur = self._memoire
        else:
            valeur = self._store.get('provider', PROVIDERS[0])
        return valeur if valeur in PROVIDERS else PROVIDERS[0]

    def appliquer(self, provider):
        if self._store is None:
            self._memoire = provider
        else:
            self._store.set('provider', provider)
