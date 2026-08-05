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
    def Analyses(self):
        # Nombre total d'éléments analysés pour ce thème (peut être None si
        # le thème ne connaît pas de dénominateur, ex. avertissements bruts).
        return self._t.analyses

    @property
    def CompteLabel(self):
        # Texte prêt à afficher : « compte / total » si le total est connu,
        # sinon le compte seul.
        analyses = self._t.analyses
        compte = self._t.compte
        if isinstance(analyses, int) and analyses > 0:
            return u'{} / {}'.format(compte, analyses)
        return u'{}'.format(compte)

    @property
    def RatioProblemePct(self):
        # Part de problèmes 0..100 pour la barre proportionnelle.
        # Robuste si analyses est None : si des problèmes existent sans
        # dénominateur, on sature à 100 %.
        analyses = self._t.analyses
        compte = self._t.compte
        if isinstance(analyses, int) and analyses > 0:
            return min(100.0, round(100.0 * compte / analyses, 1))
        if compte > 0:
            return 100.0
        return 0.0

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
