# -*- coding: utf-8 -*-
"""Scaffold : le VM tient le titre, rien d'autre.

Les services viendront ici — instanciés par le VM et INJECTÉS aux couches
basses, jamais créés par elles.
"""
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    RelayCommand = None


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None, uidoc=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._uidoc = uidoc
        self._titre = u'Permis de construire'
        self.fermer_cmd = RelayCommand(lambda p: None) if RelayCommand else None

    @property
    def Titre(self):
        return self._titre

    @Titre.setter
    def Titre(self, value):
        self._titre = value
        self.notify_property('Titre')
