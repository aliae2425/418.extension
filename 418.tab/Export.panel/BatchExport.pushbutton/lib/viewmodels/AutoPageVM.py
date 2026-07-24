# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# SPIKE (étape 0 du découpage main window) : sous-VM minimal de la page
# « par jeu ». But du spike : prouver qu'une page XAML chargée séparément,
# dotée de son PROPRE DataContext (cet objet, distinct du MainViewModel),
# insérée dans un ContentControl du shell, rend bien sa liste liée et
# résout les DynamicResource. Data-holder volontairement minimal.

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object


class AutoPageVM(BaseViewModel):
    def __init__(self, collections=None):
        super(AutoPageVM, self).__init__()
        self._collections = collections or []

    @property
    def Collections(self):
        return self._collections

    def set_collections(self, collections):
        self._collections = collections or []
        self.notify_property(u'Collections')
