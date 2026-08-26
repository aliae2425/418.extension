# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Modèles de l'audit : gravités + porteurs de résultats. Regroupés ici — un
# fichier par classe de 8 à 26 lignes n'apportait rien. Import : `from models
# import OK, AuditIssue, ThemeResult, ...`.

OK = 0
A_REVOIR = 1
CRITIQUE = 2

_LIBELLES = {OK: u'Conforme', A_REVOIR: u'À revoir', CRITIQUE: u'Critique'}


def libelle(niveau):
    return _LIBELLES.get(niveau, u'Inconnu')


def pire(niveaux):
    # `default=` de max() est Python 3 seulement -> concaténation (Py2/3).
    return max(list(niveaux) + [OK])


class AuditIssue(object):
    def __init__(self, nom, gravite, element_id=None,
                 emplacement=u'', type_=u'', message=u''):
        self.nom = nom
        self.gravite = gravite
        self.element_id = element_id
        self.emplacement = emplacement
        self.type = type_
        self.message = message


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


class AuditResult(object):
    def __init__(self, themes=None, score=100, top_critiques=None, meta=None):
        self.themes = list(themes) if themes else []
        self.score = score
        self.top_critiques = list(top_critiques) if top_critiques else []
        self.meta = dict(meta) if meta else {}
