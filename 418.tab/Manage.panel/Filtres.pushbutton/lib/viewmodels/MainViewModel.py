# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.viewmodels.CoupesPageVM import CoupesPageVM
except Exception:
    from viewmodels.CoupesPageVM import CoupesPageVM

try:
    from lib.viewmodels.AuditPageVM import AuditPageVM
except Exception:
    from viewmodels.AuditPageVM import AuditPageVM

try:
    from core.UserConfig import UserConfig
except Exception:
    try:
        from lib.core.UserConfig import UserConfig
    except Exception:
        UserConfig = None

#: Namespace de persistance de l'outil : 418.extension/data/filtres.json.
NAMESPACE = 'filtres'


def _config():
    """L'unique UserConfig de l'outil, ou None hors socle (tests)."""
    if UserConfig is None:
        return None
    try:
        return UserConfig(NAMESPACE)
    except Exception:
        return None


class MainViewModel(BaseViewModel):
    """VM racine (contrat RailWindow) : Titre, Mode, set_mode, un attribut par
    onglet.

    L'onglet Plans de repérage est encore une page statique — RailWindow lui
    pose un DataContext `None`, ce qui suffit tant qu'elle n'affiche rien de
    dynamique.

    C'est ICI que le service et la config sont créés puis injectés aux pages :
    une seule instance de chacun pour l'outil (règle du dépôt).
    """

    def __init__(self, service=None, config=None):
        super(MainViewModel, self).__init__()
        self._service = service
        self._config = config if config is not None else _config()
        self._mode = u'audit'
        self.AuditVM = None
        self.CoupesVM = None

    @property
    def Titre(self):
        return u'418 · Gérer les filtres'

    @property
    def Mode(self):
        return self._mode

    def set_mode(self, mode):
        if mode != self._mode:
            self._mode = mode
            self.notify_property('Mode')

    def charger(self):
        coupes = self._service.collecter_coupes() if self._service else []
        filtres = self._service.collecter_filtres() if self._service else []
        self.AuditVM = AuditPageVM(filtres)
        self.CoupesVM = CoupesPageVM(coupes, service=self._service,
                                     config=self._config)
        self.notify_property('AuditVM')
        self.notify_property('CoupesVM')

    def lancer(self, cible=None):
        """Bouton d'action de RailWindow : applique le repérage.

        `cible` est ignorée — l'onglet travaille sur les vues du document, pas
        sur une sélection passée par le script.
        """
        if self.CoupesVM is None:
            return []
        return self.CoupesVM.appliquer()
