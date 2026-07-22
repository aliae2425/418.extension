# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    RelayCommand = None

try:
    from System.Diagnostics import Process
except Exception:
    Process = None

__version__ = u'1.2.12'


class AboutViewModel(BaseViewModel):
    """Données affichées dans la fenêtre « À propos »."""

    def __init__(self):
        super(AboutViewModel, self).__init__()
        self._nom = u'418.extension'
        self._version = u'Version {0}'.format(__version__)
        self._description = (
            u'Extension pyRevit pour l\'automatisation et la gestion '
            u'dans Revit.')
        self._auteur = u'Aliae'
        self._licence = u'Licence MIT © 2025'
        self._url_depot = u'https://github.com/aliae2425/418.extension'
        self.ouvrir_depot_cmd = (
            RelayCommand(self._ouvrir_depot) if RelayCommand else None)

    def _ouvrir_depot(self, _param):
        """Ouvre le dépôt dans le navigateur par défaut."""
        if Process is None:
            return
        try:
            Process.Start(self._url_depot)
        except Exception:
            pass

    @property
    def Nom(self):
        return self._nom

    @property
    def Version(self):
        return self._version

    @property
    def Description(self):
        return self._description

    @property
    def Auteur(self):
        return self._auteur

    @property
    def Licence(self):
        return self._licence

    @property
    def UrlDepot(self):
        return self._url_depot
