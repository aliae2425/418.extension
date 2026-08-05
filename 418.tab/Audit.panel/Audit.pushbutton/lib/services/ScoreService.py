# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from models.Severity import A_REVOIR, CRITIQUE
except Exception:
    try:
        from lib.models.Severity import A_REVOIR, CRITIQUE
    except Exception:
        A_REVOIR, CRITIQUE = 1, 2

# Constantes v1 — réglables.
POIDS_THEME = {
    u'warnings': 1.0, u'cad': 1.0, u'vues_feuilles': 1.0,
    u'purge': 0.6, u'nommage': 0.5,
}
POINTS_CRITIQUE = 10
POINTS_A_REVOIR = 4
VOLUME_FACTEUR = 0.05
VOLUME_MAX = 8


def _severite_base(theme):
    pg = theme.pire_gravite
    if pg == CRITIQUE:
        return POINTS_CRITIQUE
    if pg == A_REVOIR:
        return POINTS_A_REVOIR
    return 0


def penalite_theme(theme):
    poids = POIDS_THEME.get(theme.cle, 1.0)
    volume = min(VOLUME_MAX, VOLUME_FACTEUR * theme.compte)
    return poids * _severite_base(theme) + volume


def calculer(themes):
    total = 0.0
    for t in themes:
        if getattr(t, 'disponible', True):
            total += penalite_theme(t)
    return int(round(max(0, 100 - total)))
