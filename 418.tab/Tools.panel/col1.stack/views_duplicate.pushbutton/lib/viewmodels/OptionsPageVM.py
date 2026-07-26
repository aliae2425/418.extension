# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    class BaseViewModel(object):
        def __init__(self):
            pass

        def notify_property(self, name):
            pass

try:
    from lib.services.ViewsDuplicationOptions import ViewsDuplicationOptions
except Exception:
    from services.ViewsDuplicationOptions import ViewsDuplicationOptions


class OptionsPageVM(BaseViewModel):
    """VM de la page Options : mode de duplication et nombre de copies.

    Chaque propriété PascalCase est bindable en WPF (TwoWay). Les propriétés
    sont écrites en @property inline (getter/setter notifiant)."""

    def __init__(self):
        super(OptionsPageVM, self).__init__()
        self._ViewDuplicateOption = u'duplicate'
        self._Count = u'1'
        self._Prefixe = u''
        self._Rechercher = u''
        self._Remplacer = u''
        self._Suffixe = u''

    @property
    def ViewDuplicateOption(self):
        return self._ViewDuplicateOption

    @ViewDuplicateOption.setter
    def ViewDuplicateOption(self, value):
        if value != self._ViewDuplicateOption:
            self._ViewDuplicateOption = value
            self.notify_property('ViewDuplicateOption')

    @property
    def Count(self):
        return self._Count

    @Count.setter
    def Count(self, value):
        if value != self._Count:
            self._Count = value
            self.notify_property('Count')

    @property
    def Prefixe(self):
        return self._Prefixe

    @Prefixe.setter
    def Prefixe(self, value):
        if value != self._Prefixe:
            self._Prefixe = value
            self.notify_property('Prefixe')

    @property
    def Rechercher(self):
        return self._Rechercher

    @Rechercher.setter
    def Rechercher(self, value):
        if value != self._Rechercher:
            self._Rechercher = value
            self.notify_property('Rechercher')

    @property
    def Remplacer(self):
        return self._Remplacer

    @Remplacer.setter
    def Remplacer(self, value):
        if value != self._Remplacer:
            self._Remplacer = value
            self.notify_property('Remplacer')

    @property
    def Suffixe(self):
        return self._Suffixe

    @Suffixe.setter
    def Suffixe(self, value):
        if value != self._Suffixe:
            self._Suffixe = value
            self.notify_property('Suffixe')

    def build_options(self):
        """Construit un `ViewsDuplicationOptions` peuplé depuis l'état courant."""
        return ViewsDuplicationOptions(
            view_duplicate_option=self._ViewDuplicateOption,
            count=self._Count,
        )
