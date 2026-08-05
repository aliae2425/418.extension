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
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    try:
        from lib.ui.helpers.RelayCommand import RelayCommand
    except Exception:
        RelayCommand = None
try:
    from services.AuditRunner import AuditRunner
except Exception:
    from lib.services.AuditRunner import AuditRunner
try:
    from viewmodels.ScoreVM import ScoreVM
    from viewmodels.ThemeCardVM import ThemeCardVM
    from viewmodels.IssueRowVM import IssueRowVM
except Exception:
    from lib.viewmodels.ScoreVM import ScoreVM
    from lib.viewmodels.ThemeCardVM import ThemeCardVM
    from lib.viewmodels.IssueRowVM import IssueRowVM


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None, runner=None):
        try:
            super(MainViewModel, self).__init__()
        except Exception:
            pass
        self._doc = doc
        self._runner = runner or AuditRunner()
        self.Titre = u'Audit — Santé du modèle'
        self.ScoreVM = None
        self.Cartes = []
        self.TopCritiques = []
        self.Meta = {}
        self.relancer_cmd = RelayCommand(lambda p: self.lancer_audit()) if RelayCommand else None
        self.exporter_cmd = None  # câblé Task 13
        self.lancer_audit()

    def lancer_audit(self):
        res = self._runner.run(self._doc)
        self._appliquer(res)

    def _appliquer(self, res):
        self._resultat = res
        self.ScoreVM = ScoreVM(res)
        self.Cartes = [ThemeCardVM(t) for t in res.themes]
        self.TopCritiques = [IssueRowVM(i) for i in res.top_critiques]
        self.Meta = res.meta
        for prop in ('ScoreVM', 'Cartes', 'TopCritiques', 'Meta'):
            try:
                self.notify_property(prop)
            except Exception:
                pass
