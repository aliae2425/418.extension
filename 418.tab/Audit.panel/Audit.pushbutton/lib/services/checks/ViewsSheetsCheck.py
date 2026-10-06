# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

try:
    from services.checks.BaseCheck import BaseCheck
except Exception:
    from lib.services.checks.BaseCheck import BaseCheck
try:
    from models import A_REVOIR, CRITIQUE
    from models import AuditIssue
    from models import ThemeResult
except Exception:
    from lib.models import A_REVOIR, CRITIQUE
    from lib.models import AuditIssue
    from lib.models import ThemeResult
try:
    from config.AuditRules import charger as _charger, DEFAULTS as _DEF
except Exception:
    try:
        from lib.config.AuditRules import charger as _charger, DEFAULTS as _DEF
    except Exception:
        _charger = None
        _DEF = {u'vues_feuilles': {u'nom_defaut_regex': r'^(Niveau|Level|Quadrillage|Grid)\s*\d+$'}}

try:
    from Autodesk.Revit.DB import (
        FilteredElementCollector, View, ViewType, ElementId)
except Exception:
    FilteredElementCollector = View = ViewType = ElementId = None

DEFAULT_NOM_DEFAUT_REGEX = _DEF[u'vues_feuilles'][u'nom_defaut_regex']


def _regex_nom_defaut(rules):
    r = rules if rules is not None else (_charger() if _charger is not None else None)
    pat = r.nom_defaut_regex() if r is not None else DEFAULT_NOM_DEFAUT_REGEX
    try:
        return re.compile(pat)
    except Exception:
        return re.compile(DEFAULT_NOM_DEFAUT_REGEX)


def est_nom_par_defaut(nom, rules=None):
    if not nom:
        return False
    try:
        return _regex_nom_defaut(rules).match(nom) is not None
    except Exception:
        return False


class ViewsSheetsCheck(BaseCheck):
    cle = u'vues_feuilles'
    libelle = u'Vues & Feuilles'

    def run(self, doc):
        if doc is None or FilteredElementCollector is None:
            return ThemeResult(cle=self.cle, libelle=self.libelle, issues=[])
        issues = []
        analyses = 0
        rgx_defaut = _regex_nom_defaut(self._rules)
        # Ids de vues placées sur une feuille (via Viewports).
        placees = set()
        try:
            from Autodesk.Revit.DB import Viewport
            for vp in FilteredElementCollector(doc).OfClass(Viewport):
                try:
                    placees.add(vp.ViewId.IntegerValue)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            for v in FilteredElementCollector(doc).OfClass(View):
                if getattr(v, 'IsTemplate', False):
                    continue
                # Ignorer feuilles et vues systèmes non plaçables.
                try:
                    if v.ViewType in (ViewType.DrawingSheet, ViewType.ProjectBrowser,
                                      ViewType.SystemBrowser, ViewType.Schedule):
                        continue
                except Exception:
                    pass
                analyses += 1
                non_placee = v.Id.IntegerValue not in placees
                try:
                    sans_gabarit = (v.ViewTemplateId == ElementId.InvalidElementId)
                except Exception:
                    sans_gabarit = False
                if non_placee and sans_gabarit:
                    issues.append(AuditIssue(
                        nom=v.Name, gravite=CRITIQUE, element_id=v.Id,
                        emplacement=u'Vue', type_=u'Non placée + sans gabarit',
                        message=u'Non placée sur feuille et sans gabarit'))
                elif non_placee:
                    issues.append(AuditIssue(
                        nom=v.Name, gravite=A_REVOIR, element_id=v.Id,
                        emplacement=u'Vue', type_=u'Non placée',
                        message=u'Non placée sur feuille'))
                elif sans_gabarit:
                    issues.append(AuditIssue(
                        nom=v.Name, gravite=A_REVOIR, element_id=v.Id,
                        emplacement=u'Vue', type_=u'Sans gabarit',
                        message=u'Aucun gabarit de vue appliqué'))
                try:
                    est_defaut = rgx_defaut.match(v.Name or u'') is not None
                except Exception:
                    est_defaut = False
                if est_defaut:
                    issues.append(AuditIssue(
                        nom=v.Name, gravite=A_REVOIR, element_id=v.Id,
                        emplacement=u'Vue', type_=u'Nom par défaut',
                        message=u'Nom générique non renommé'))
        except Exception:
            pass
        return ThemeResult(cle=self.cle, libelle=self.libelle,
                           issues=issues, analyses=analyses)
