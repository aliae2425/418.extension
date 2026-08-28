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


class MainViewModel(BaseViewModel):
    """VM racine (contrat RailWindow) : Titre, Mode, set_mode, un attribut par
    onglet.

    Scaffold : seul l'onglet Coupes a un ViewModel. Audit et Plans de repérage
    sont des pages statiques — RailWindow leur pose un DataContext `None`, ce
    qui suffit tant qu'elles n'affichent rien de dynamique.
    """

    def __init__(self, service=None):
        super(MainViewModel, self).__init__()
        self._service = service
        self._mode = u'audit'
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
        self.CoupesVM = CoupesPageVM(coupes)
        self.notify_property('CoupesVM')
