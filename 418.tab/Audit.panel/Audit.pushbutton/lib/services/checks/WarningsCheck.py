# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from services.checks.BaseCheck import BaseCheck
except Exception:
    from lib.services.checks.BaseCheck import BaseCheck
try:
    from models.Severity import A_REVOIR, CRITIQUE
    from models.AuditIssue import AuditIssue
    from models.ThemeResult import ThemeResult
except Exception:
    from lib.models.Severity import A_REVOIR, CRITIQUE
    from lib.models.AuditIssue import AuditIssue
    from lib.models.ThemeResult import ThemeResult

_MOTS_CRITIQUES = (u'dupliqu', u'identical', u'same place',
                   u'même endroit', u'meme endroit', u'même place')


def gravite_pour(description):
    d = (description or u'').lower()
    for mot in _MOTS_CRITIQUES:
        if mot in d:
            return CRITIQUE
    return A_REVOIR


class WarningsCheck(BaseCheck):
    cle = u'warnings'
    libelle = u'Avertissements'

    def run(self, doc):
        issues = []
        if doc is None:
            return ThemeResult(cle=self.cle, libelle=self.libelle, issues=issues)
        try:
            warnings = list(doc.GetWarnings())
        except Exception as e:
            return ThemeResult(cle=self.cle, libelle=self.libelle,
                               disponible=False,
                               message=u'GetWarnings indisponible : {}'.format(e))
        # Regrouper par description.
        groupes = {}
        for w in warnings:
            try:
                desc = w.GetDescriptionText()
            except Exception:
                desc = u'(avertissement)'
            groupes.setdefault(desc, 0)
            groupes[desc] += 1
        for desc, n in groupes.items():
            issues.append(AuditIssue(
                nom=desc, gravite=gravite_pour(desc),
                emplacement=u'Modèle', type_=u'Avertissement',
                message=u'{} occurrence(s)'.format(n)))
        # analyses laissé à None : le nombre total d'avertissements n'est pas
        # une population comparable au compte groupé (issues distinctes par
        # description) ; analyses=None fait afficher une barre 100% problème.
        return ThemeResult(cle=self.cle, libelle=self.libelle,
                           issues=issues)
