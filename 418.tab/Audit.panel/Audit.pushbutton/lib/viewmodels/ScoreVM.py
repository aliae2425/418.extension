# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import math

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        BaseViewModel = object

try:
    from models.Severity import OK, CRITIQUE, libelle as _libelle
except Exception:
    try:
        from lib.models.Severity import OK, CRITIQUE, libelle as _libelle
    except Exception:
        OK, CRITIQUE = 0, 2
        def _libelle(n):
            return {0: u'Conforme', 1: u'À revoir', 2: u'Critique'}.get(n, u'Inconnu')

# Géométrie du donut (repère 176x176, centre 88, anneau R=84 / IR=58).
_CX = _CY = 88.0
_R = 84.0
_IR = 58.0

_NIVEAU_LIB = {
    u'excellent': u'Excellent', u'bon': u'Bon',
    u'correct': u'Correct', u'critique': u'Critique',
}


def _niveau(score):
    if score >= 90:
        return u'excellent'
    if score >= 75:
        return u'bon'
    if score >= 55:
        return u'correct'
    return u'critique'


def _verdict(score):
    if score >= 85:
        return u'Bon — modèle sain'
    if score >= 60:
        return u'Correct — à consolider'
    if score >= 35:
        return u'Fragile — points à traiter'
    return u'Critique — intervention requise'


def _pt(r, deg):
    a = math.radians(deg - 90.0)  # -90 : le 0° démarre en haut
    return _CX + r * math.cos(a), _CY + r * math.sin(a)


def _fmt(v):
    return u'{:.2f}'.format(v)


def _sector_path(start_deg, end_deg):
    """Chemin (mini-langage Geometry WPF) d'un secteur annulaire."""
    large = 1 if (end_deg - start_deg) > 180.0 else 0
    ox1, oy1 = _pt(_R, start_deg)
    ox2, oy2 = _pt(_R, end_deg)
    ix2, iy2 = _pt(_IR, end_deg)
    ix1, iy1 = _pt(_IR, start_deg)
    return (u'M {},{} A {},{} 0 {} 1 {},{} L {},{} '
            u'A {},{} 0 {} 0 {},{} Z').format(
        _fmt(ox1), _fmt(oy1), _fmt(_R), _fmt(_R), large, _fmt(ox2), _fmt(oy2),
        _fmt(ix2), _fmt(iy2), _fmt(_IR), _fmt(_IR), large, _fmt(ix1), _fmt(iy1))


class DonutSegment(object):
    """Un segment du donut : géométrie + identité du thème (couleur + légende).
    `Cle` pilote la couleur (palette par thème) ; `Libelle`/`Compte` la légende."""

    def __init__(self, path_data, cle, libelle, compte):
        self._path = path_data
        self._cle = cle
        self._lib = libelle
        self._compte = compte

    @property
    def PathData(self):
        return self._path

    @property
    def Cle(self):
        return self._cle

    @property
    def Libelle(self):
        return self._lib

    @property
    def Compte(self):
        return self._compte


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
    def Niveau(self):
        # Clé de niveau pour la couleur du tag (excellent/bon/correct/critique).
        return _niveau(self._r.score)

    @property
    def NiveauLibelle(self):
        return _NIVEAU_LIB[self.Niveau]

    @property
    def NbProblemes(self):
        # Total des problèmes sur les thèmes disponibles (ligne de synthèse).
        total = 0
        for t in (getattr(self._r, 'themes', None) or []):
            if getattr(t, 'disponible', True):
                total += getattr(t, 'compte', 0) or 0
        return total

    @property
    def NbCritiques(self):
        # Compte les vraies issues de gravité CRITIQUE sur tous les thèmes
        # (top_critiques n'est que le top-5 toutes gravités confondues).
        total = 0
        for t in (getattr(self._r, 'themes', None) or []):
            for i in (getattr(t, 'issues', None) or []):
                if getattr(i, 'gravite', None) == CRITIQUE:
                    total += 1
        return total

    @property
    def DonutSegments(self):
        """Répartition des problèmes par thème en secteurs annulaires.
        Segment = un thème ayant des problèmes, taille = nombre de problèmes,
        couleur = pire gravité du thème. Aucun problème -> anneau conforme."""
        parts = []
        total = 0
        for t in (getattr(self._r, 'themes', None) or []):
            if not getattr(t, 'disponible', True):
                continue
            c = getattr(t, 'compte', 0) or 0
            if c > 0:
                parts.append((c, getattr(t, 'cle', u'?'),
                              getattr(t, 'libelle', u'?')))
                total += c
        if total <= 0:
            return [DonutSegment(_sector_path(0.0, 359.9),
                                 u'conforme', u'Aucun problème', 0)]
        segs = []
        cursor = 0.0
        for c, cle, lib in parts:
            frac = float(c) / total
            start = cursor * 360.0
            end = (cursor + frac) * 360.0
            if end - start >= 359.9:
                end = start + 359.9
            segs.append(DonutSegment(_sector_path(start, end), cle, lib, c))
            cursor += frac
        return segs
