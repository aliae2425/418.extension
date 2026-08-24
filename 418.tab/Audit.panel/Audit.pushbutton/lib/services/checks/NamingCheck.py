# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

try:
    from services.checks.BaseCheck import BaseCheck
except Exception:
    from lib.services.checks.BaseCheck import BaseCheck

try:
    from models import A_REVOIR
    from models import AuditIssue
    from models import ThemeResult
except Exception:
    from lib.models import A_REVOIR
    from lib.models import AuditIssue
    from lib.models import ThemeResult

try:
    from config.AuditRules import charger as _charger, DEFAULTS as _DEF
except Exception:
    try:
        from lib.config.AuditRules import charger as _charger, DEFAULTS as _DEF
    except Exception:
        _charger = None
        _DEF = {u'nommage': {u'vue_regex': r'^[A-Z]{2,4}_\d{2}_.+',
                             u'famille_regex': r'^[A-Z]{2,4}_.+'}}

try:
    from Autodesk.Revit.DB import (
        FilteredElementCollector, View, Family)
except Exception:
    FilteredElementCollector = View = Family = None

# Défauts ré-exportés depuis les règles (source unique : AuditRules.DEFAULTS).
DEFAULT_VIEW_REGEX = _DEF[u'nommage'][u'vue_regex']
DEFAULT_FAMILY_REGEX = _DEF[u'nommage'][u'famille_regex']


def est_conforme(nom, pattern):
    if nom is None:
        return False
    try:
        return re.match(pattern, nom) is not None
    except Exception:
        return True  # pattern cassé : on ne pénalise pas


class NamingCheck(BaseCheck):
    cle = u'nommage'
    libelle = u'Nommage'

    def _patterns(self):
        r = self._rules
        if r is None and _charger is not None:
            r = _charger()
        if r is not None:
            return r.vue_regex(), r.famille_regex()
        return DEFAULT_VIEW_REGEX, DEFAULT_FAMILY_REGEX

    def run(self, doc):
        vue_re, fam_re = self._patterns()
        issues = []
        analyses = 0
        if doc is None or FilteredElementCollector is None:
            return ThemeResult(cle=self.cle, libelle=self.libelle,
                               issues=issues, analyses=0)
        # Vues (hors gabarits)
        try:
            for v in FilteredElementCollector(doc).OfClass(View):
                if getattr(v, 'IsTemplate', False):
                    continue
                analyses += 1
                nom = v.Name
                if not est_conforme(nom, vue_re):
                    issues.append(AuditIssue(
                        nom=nom, gravite=A_REVOIR, element_id=v.Id,
                        emplacement=u'Vue', type_=u'Vue',
                        message=u'Attendu : {}'.format(vue_re)))
        except Exception:
            pass
        # Familles
        try:
            for f in FilteredElementCollector(doc).OfClass(Family):
                analyses += 1
                nom = f.Name
                if not est_conforme(nom, fam_re):
                    issues.append(AuditIssue(
                        nom=nom, gravite=A_REVOIR, element_id=f.Id,
                        emplacement=u'Famille', type_=u'Famille',
                        message=u'Attendu : {}'.format(fam_re)))
        except Exception:
            pass
        return ThemeResult(cle=self.cle, libelle=self.libelle,
                           issues=issues, analyses=analyses)
