# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        BaseViewModel = object
try:
    from models.Severity import libelle as libelle_gravite
except Exception:
    from lib.models.Severity import libelle as libelle_gravite
try:
    from viewmodels.IssueRowVM import IssueRowVM
except Exception:
    from lib.viewmodels.IssueRowVM import IssueRowVM


class ThemeCardVM(BaseViewModel):
    def __init__(self, theme_result, on_selectionner=None):
        try:
            super(ThemeCardVM, self).__init__()
        except Exception:
            pass
        self._t = theme_result
        self._deplie = False
        self.Rows = [IssueRowVM(i, on_selectionner) for i in theme_result.issues]

    @property
    def Libelle(self):
        return self._t.libelle

    @property
    def Compte(self):
        return self._t.compte

    @property
    def PireGravite(self):
        return libelle_gravite(self._t.pire_gravite)

    @property
    def Disponible(self):
        return self._t.disponible

    @property
    def EstDeplie(self):
        return self._deplie

    @EstDeplie.setter
    def EstDeplie(self, value):
        self._deplie = bool(value)
        try:
            self.notify_property('EstDeplie')
        except Exception:
            pass
