# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from models.Severity import OK, pire
except Exception:
    try:
        from lib.models.Severity import OK, pire
    except Exception:
        OK = 0
        def pire(niveaux):
            return max(list(niveaux) + [0])


class ThemeResult(object):
    def __init__(self, cle, libelle, issues=None, analyses=None,
                 disponible=True, message=u''):
        self.cle = cle
        self.libelle = libelle
        self.issues = list(issues) if issues else []
        self.analyses = analyses
        self.disponible = disponible
        self.message = message

    @property
    def compte(self):
        return len(self.issues)

    @property
    def pire_gravite(self):
        return pire([i.gravite for i in self.issues])
