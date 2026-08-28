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


class MainViewModel(BaseViewModel):
    """VM racine (contrat RailWindow) : Titre, Mode, set_mode, un attribut par
    onglet.

    L'onglet Plans de repérage est encore une page statique — RailWindow lui
    pose un DataContext `None`, ce qui suffit tant qu'elle n'affiche rien de
    dynamique.
    """

    def __init__(self, service=None):
        super(MainViewModel, self).__init__()
        self._service = service
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
        self.CoupesVM = CoupesPageVM(coupes)
        self.notify_property('AuditVM')
        self.notify_property('CoupesVM')
