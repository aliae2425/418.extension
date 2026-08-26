# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from models import A_REVOIR, CRITIQUE
except Exception:
    try:
        from lib.models import A_REVOIR, CRITIQUE
    except Exception:
        A_REVOIR, CRITIQUE = 1, 2

# Les poids/points/volume viennent des règles (AuditRules), plus de constantes
# en dur ici : la source de vérité est audit_rules.json (fallback AuditRules.DEFAULTS).
try:
    from config.AuditRules import charger as _charger
except Exception:
    try:
        from lib.config.AuditRules import charger as _charger
    except Exception:
        _charger = None


def _rules(rules):
    if rules is not None:
        return rules
    return _charger() if _charger is not None else None


def _severite_base(theme, points):
    pg = theme.pire_gravite
    if pg == CRITIQUE:
        return points[u'critique']
    if pg == A_REVOIR:
        return points[u'a_revoir']
    return 0


def penalite_theme(theme, rules=None):
    r = _rules(rules)
    poids = r.score_poids().get(theme.cle, 1.0)
    vol = r.score_volume()
    volume = min(vol[u'max'], vol[u'facteur'] * theme.compte)
    return poids * _severite_base(theme, r.score_points()) + volume


def calculer(themes, rules=None):
    r = _rules(rules)
    total = 0.0
    for t in themes:
        if getattr(t, 'disponible', True):
            total += penalite_theme(t, r)
    return int(round(max(0, 100 - total)))
