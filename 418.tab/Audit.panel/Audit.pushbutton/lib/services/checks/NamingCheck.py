# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

try:
    from services.checks.BaseCheck import BaseCheck
except Exception:
    from lib.services.checks.BaseCheck import BaseCheck

try:
    from models.Severity import A_REVOIR
    from models.AuditIssue import AuditIssue
    from models.ThemeResult import ThemeResult
except Exception:
    from lib.models.Severity import A_REVOIR
    from lib.models.AuditIssue import AuditIssue
    from lib.models.ThemeResult import ThemeResult

try:
    from core.UserConfig import UserConfig
except Exception:
    try:
        from lib.core.UserConfig import UserConfig
    except Exception:
        UserConfig = None

try:
    from Autodesk.Revit.DB import (
        FilteredElementCollector, View, Family)
except Exception:
    FilteredElementCollector = View = Family = None

# Convention par défaut : préfixe majuscules + underscore.
DEFAULT_VIEW_REGEX = r'^[A-Z]{2,4}_\d{2}_.+'
DEFAULT_FAMILY_REGEX = r'^[A-Z]{2,4}_.+'


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
        vue, fam = DEFAULT_VIEW_REGEX, DEFAULT_FAMILY_REGEX
        try:
            if UserConfig is not None:
                cfg = UserConfig('audit')
                vue = cfg.get('naming_view_regex', vue) or vue
                fam = cfg.get('naming_family_regex', fam) or fam
        except Exception:
            pass
        return vue, fam

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
