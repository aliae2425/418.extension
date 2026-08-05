# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

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

try:
    from Autodesk.Revit.DB import (
        FilteredElementCollector, View, ViewType, ElementId)
except Exception:
    FilteredElementCollector = View = ViewType = ElementId = None

_RE_DEFAUT = re.compile(r'^(Niveau|Level|Quadrillage|Grid)\s*\d+$')


def est_nom_par_defaut(nom):
    if not nom:
        return False
    return _RE_DEFAUT.match(nom) is not None


class ViewsSheetsCheck(BaseCheck):
    cle = u'vues_feuilles'
    libelle = u'Vues & Feuilles'

    def run(self, doc):
        if doc is None or FilteredElementCollector is None:
            return ThemeResult(cle=self.cle, libelle=self.libelle, issues=[])
        issues = []
        analyses = 0
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
                if est_nom_par_defaut(v.Name):
                    issues.append(AuditIssue(
                        nom=v.Name, gravite=A_REVOIR, element_id=v.Id,
                        emplacement=u'Vue', type_=u'Nom par défaut',
                        message=u'Nom générique non renommé'))
        except Exception:
            pass
        return ThemeResult(cle=self.cle, libelle=self.libelle,
                           issues=issues, analyses=analyses)
