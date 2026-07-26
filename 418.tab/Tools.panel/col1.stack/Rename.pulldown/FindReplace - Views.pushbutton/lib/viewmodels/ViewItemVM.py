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


class ViewItemVM(BaseViewModel):
    """Ligne de la page Sélection : une vue cochable."""

    def __init__(self, view_id, nom, type_label, is_selected, on_toggle):
        super(ViewItemVM, self).__init__()
        self.ViewId = view_id
        self._nom = nom
        self._type_label = type_label
        self._is_selected = is_selected
        self._on_toggle = on_toggle

    @property
    def Nom(self):
        return self._nom

    @property
    def TypeLabel(self):
        return self._type_label

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
