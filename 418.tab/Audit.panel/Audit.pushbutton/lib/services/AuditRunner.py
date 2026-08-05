# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime

try:
    from models.ThemeResult import ThemeResult
    from models.AuditResult import AuditResult
except Exception:
    from lib.models.ThemeResult import ThemeResult
    from lib.models.AuditResult import AuditResult

try:
    from services import ScoreService as _score_default
except Exception:
    from lib.services import ScoreService as _score_default


def _default_checks():
    # Import tardif pour éviter les cycles ; chaque import gardé.
    checks = []
    for mod, cls in [
        (u'WarningsCheck', u'WarningsCheck'),
        (u'PurgeCheck', u'PurgeCheck'),
        (u'ViewsSheetsCheck', u'ViewsSheetsCheck'),
        (u'CadImportsCheck', u'CadImportsCheck'),
        (u'NamingCheck', u'NamingCheck'),
    ]:
        try:
            try:
                m = __import__(u'services.checks.' + mod, fromlist=[cls])
            except Exception:
                m = __import__(u'lib.services.checks.' + mod, fromlist=[cls])
            checks.append(getattr(m, cls)())
        except Exception:
            pass
    return checks


def _meta(doc):
    meta = {'horodatage': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
    try:
        if doc is not None:
            meta['fichier'] = doc.Title
    except Exception:
        pass
    return meta


def _top_critiques(themes, limite=5):
    toutes = []
    for t in themes:
        for i in t.issues:
            toutes.append(i)
    toutes.sort(key=lambda i: i.gravite, reverse=True)
    return toutes[:limite]


class AuditRunner(object):
    def __init__(self, checks=None, score_module=None):
        self._checks = checks if checks is not None else _default_checks()
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
        score = self._score.calculer(themes)
        return AuditResult(themes=themes, score=score,
                           top_critiques=_top_critiques(themes),
                           meta=_meta(doc))
