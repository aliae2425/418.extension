# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from models import A_REVOIR, CRITIQUE

# Les poids/points/volume viennent des règles (AuditRules), plus de constantes
# en dur ici : la source de vérité est audit_rules.json (fallback AuditRules.DEFAULTS).
from config.AuditRules import charger as _charger


def _rules(rules):
    if rules is not None:
        return rules
    return _charger()


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
