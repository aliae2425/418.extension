# -*- coding: utf-8 -*-
"""Réglages OpenArchi : fournisseur, modèle, projet Revit ciblé."""
from __future__ import unicode_literals
from collections import OrderedDict

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        BaseViewModel = object

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    try:
        from lib.ui.helpers.RelayCommand import RelayCommand
    except Exception:
        RelayCommand = None

try:
    from core.UserConfig import UserConfig
except Exception:
    try:
        from lib.core.UserConfig import UserConfig
    except Exception:
        UserConfig = None

try:
    from System.Collections.ObjectModel import ObservableCollection
except Exception:
    ObservableCollection = None

# ponytail: catalogue en dur. Le jour où un fournisseur expose sa liste de
# modèles, remplacer ce dict par un appel réseau mis en cache.
PROVIDERS = OrderedDict([
    ('Anthropic', ['claude-opus-5', 'claude-sonnet-5', 'claude-haiku-4-5']),
    ('OpenAI', ['gpt-5', 'gpt-5-mini']),
    ('Ollama (local)', ['llama3.1', 'qwen2.5-coder']),
])

AUCUN_PROJET = '— aucun projet ouvert —'


def documents_ouverts():
    """Noms des projets Revit ouverts (liens exclus). [] hors Revit."""
    try:
        from pyrevit import HOST_APP
        noms = []
        for doc in HOST_APP.app.Documents:
            if doc.IsLinked or doc.IsFamilyDocument:
                continue
            noms.append(doc.Title)
        return noms
    except Exception:
        return []


class OpenArchiConfig(object):
    """Réglages persistés. Source unique lue par le chat ET par la modale."""

    def __init__(self, store=None):
        if store is None and UserConfig is not None:
            store = UserConfig('openarchi')
        self._store = store

    def _get(self, cle, defaut):
        if self._store is None:
            return getattr(self, '_memoire_' + cle, defaut)
        return self._store.get(cle, defaut) or defaut

    def _set(self, cle, valeur):
        if self._store is None:
            setattr(self, '_memoire_' + cle, valeur)
        else:
            self._store.set(cle, valeur)

    @property
    def provider(self):
        # Retombe sur le premier du catalogue : un réglage persisté peut
        # référencer un fournisseur retiré depuis.
        defaut = list(PROVIDERS.keys())[0]
        valeur = self._get('provider', defaut)
        return valeur if valeur in PROVIDERS else defaut

    @property
    def modele(self):
        return self._get('modele', PROVIDERS[self.provider][0])

    @property
    def projet(self):
        return self._get('projet', '')

    def appliquer(self, provider, modele, projet):
        self._set('provider', provider)
        self._set('modele', modele)
        self._set('projet', projet)

    def resume(self):
        return '{0} · {1} · {2}'.format(
            self.provider, self.modele, self.projet or AUCUN_PROJET)


class OpenArchiConfigVM(BaseViewModel):
    def __init__(self, config, projets=None):
        try:
            BaseViewModel.__init__(self)
        except Exception:
            pass
        self._config = config
        self.Providers = list(PROVIDERS.keys())
        self.Projets = projets if projets is not None else documents_ouverts()
        if not self.Projets:
            self.Projets = [AUCUN_PROJET]

        self._provider = config.provider if config.provider in PROVIDERS else self.Providers[0]
        self._modeles = self._nouvelle_liste(PROVIDERS[self._provider])
        self._modele = config.modele if config.modele in PROVIDERS[self._provider] \
            else PROVIDERS[self._provider][0]
        self._projet = config.projet if config.projet in self.Projets else self.Projets[0]

        self.ValiderCommand = RelayCommand(self._valider) if RelayCommand else None

    @staticmethod
    def _nouvelle_liste(valeurs):
        # ObservableCollection pour que le ComboBox des modèles se rafraîchisse
        # quand le fournisseur change ; simple liste hors .NET (tests).
        if ObservableCollection is None:
            return list(valeurs)
        collection = ObservableCollection[object]()
        for v in valeurs:
            collection.Add(v)
        return collection

    @property
    def Provider(self):
        return self._provider

    @Provider.setter
    def Provider(self, valeur):
        if not valeur or valeur == self._provider:
            return
        self._provider = valeur
        modeles = PROVIDERS[valeur]
        if ObservableCollection is None:
            self._modeles = list(modeles)
        else:
            self._modeles.Clear()
            for m in modeles:
                self._modeles.Add(m)
        self.notify_property('Provider')
        self.notify_property('Modeles')
        self.Modele = modeles[0]

    @property
    def Modeles(self):
        return self._modeles

    @property
    def Modele(self):
        return self._modele

    @Modele.setter
    def Modele(self, valeur):
        self._modele = valeur or ''
        self.notify_property('Modele')

    @property
    def Projet(self):
        return self._projet

    @Projet.setter
    def Projet(self, valeur):
        self._projet = valeur or ''
        self.notify_property('Projet')

    def _valider(self, _=None):
        projet = '' if self._projet == AUCUN_PROJET else self._projet
        self._config.appliquer(self._provider, self._modele, projet)
