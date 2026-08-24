# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from ui.base.BaseViewModel import BaseViewModel
from models import libelle as libelle_gravite
from ui.helpers.RelayCommand import RelayCommand


class IssueRowVM(BaseViewModel):
    def __init__(self, issue, on_selectionner=None):
        try:
            super(IssueRowVM, self).__init__()
        except Exception:
            pass
        self._i = issue
        self.selectionner_cmd = (
            RelayCommand(lambda p: on_selectionner(self.ElementId))
            if (RelayCommand and on_selectionner) else None)

    @property
    def Nom(self):
        return self._i.nom

    @property
    def Emplacement(self):
        return self._i.emplacement

    @property
    def Type(self):
        return self._i.type

    @property
    def Gravite(self):
        return libelle_gravite(self._i.gravite)

    @property
    def ElementId(self):
        return self._i.element_id
