# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        BaseViewModel = object


def _verdict(score):
    if score >= 85:
        return u'Bon — modèle sain'
    if score >= 60:
        return u'Correct — à consolider'
    if score >= 35:
        return u'Fragile — points à traiter'
    return u'Critique — intervention requise'


class ScoreVM(BaseViewModel):
    def __init__(self, audit_result):
        try:
            super(ScoreVM, self).__init__()
        except Exception:
            pass
        self._r = audit_result

    @property
    def Score(self):
        return self._r.score

    @property
    def Verdict(self):
        return _verdict(self._r.score)

    @property
    def NbCritiques(self):
        return len(self._r.top_critiques)
