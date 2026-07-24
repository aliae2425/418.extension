# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    class BaseViewModel(object):
        def notify_property(self, name):
            pass


class SheetItemVM(BaseViewModel):
    """Ligne de la page Sélection : une feuille cochable."""

    def __init__(self, sheet_id, numero, nom, is_selected, on_toggle):
        super(SheetItemVM, self).__init__()
        self.SheetId = sheet_id
        self._numero = numero
        self._nom = nom
        self._is_selected = is_selected
        self._on_toggle = on_toggle

    @property
    def Numero(self):
        return self._numero

    @property
    def Nom(self):
        return self._nom

    @property
    def IsSelected(self):
        return self._is_selected

    @IsSelected.setter
    def IsSelected(self, value):
        value = bool(value)
        if value != self._is_selected:
            self._is_selected = value
            self.notify_property('IsSelected')
            if self._on_toggle is not None:
                self._on_toggle(self)
