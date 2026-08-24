# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import heapq
import itertools

from models import ThemeResult
from models import AuditResult
from services import ScoreService as _score_default
from config.AuditRules import charger as _charger


from services.checks.WarningsCheck import WarningsCheck
from services.checks.PurgeCheck import PurgeCheck
from services.checks.ViewsSheetsCheck import ViewsSheetsCheck
from services.checks.CadImportsCheck import CadImportsCheck
from services.checks.NamingCheck import NamingCheck

_CHECKS = (WarningsCheck, PurgeCheck, ViewsSheetsCheck, CadImportsCheck, NamingCheck)


def _default_checks(rules=None):
    return [cls(rules) for cls in _CHECKS]


def _meta(doc):
    meta = {'horodatage': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
    try:
        if doc is not None:
            meta['fichier'] = doc.Title
    except Exception:
        pass
    return meta


def _top_critiques(themes, limite=5):
    toutes = list(itertools.chain.from_iterable(t.issues for t in themes))
    return heapq.nlargest(limite, toutes, key=lambda i: i.gravite)


class AuditRunner(object):
    def __init__(self, checks=None, score_module=None, rules=None):
        self._rules = rules if rules is not None else (
            _charger() if _charger is not None else None)
        self._checks = checks if checks is not None else _default_checks(self._rules)
        self._score = score_module or _score_default

    def run(self, doc):
        themes = []
        for chk in self._checks:
            try:
                themes.append(chk.run(doc))
            except Exception as e:
                themes.append(ThemeResult(
                    cle=getattr(chk, 'cle', u'?'),
                    libelle=getattr(chk, 'libelle', u'?'),
                    disponible=False,
                    message=u'Contrôle indisponible : {}'.format(e)))
        score = self._score.calculer(themes, self._rules)
        return AuditResult(themes=themes, score=score,
                           top_critiques=_top_critiques(themes),
                           meta=_meta(doc))
