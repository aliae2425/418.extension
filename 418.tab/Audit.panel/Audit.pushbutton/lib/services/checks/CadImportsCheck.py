# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from services.checks.BaseCheck import BaseCheck
from models import A_REVOIR, CRITIQUE
from models import AuditIssue
from models import ThemeResult

try:
    from Autodesk.Revit.DB import FilteredElementCollector, ImportInstance
except Exception:
    FilteredElementCollector = ImportInstance = None


class CadImportsCheck(BaseCheck):
    cle = u'cad'
    libelle = u'Imports / Liens CAD'

    def run(self, doc):
        if doc is None or FilteredElementCollector is None:
            return ThemeResult(cle=self.cle, libelle=self.libelle, issues=[])
        issues = []
        analyses = 0
        try:
            for inst in FilteredElementCollector(doc).OfClass(ImportInstance):
                analyses += 1
                try:
                    est_lie = bool(inst.IsLinked)
                except Exception:
                    est_lie = False
                try:
                    nom = inst.Category.Name if inst.Category else u'(CAD)'
                except Exception:
                    nom = u'(CAD)'
                # Emplacement : vue propriétaire si import spécifique à une vue.
                emplacement = u'Modèle'
                try:
                    owner = doc.GetElement(inst.OwnerViewId)
                    if owner is not None:
                        emplacement = u'Vue : {}'.format(owner.Name)
                except Exception:
                    pass
                if not est_lie:
                    issues.append(AuditIssue(
                        nom=nom, gravite=self._rules.cad_gravite_import(),
                        element_id=inst.Id,
                        emplacement=emplacement, type_=u'Import explosé',
                        message=u'Import CAD non lié (fragmente le modèle)'))
                else:
                    issues.append(AuditIssue(
                        nom=nom, gravite=self._rules.cad_gravite_lien(),
                        element_id=inst.Id,
                        emplacement=emplacement, type_=u'Lien CAD',
                        message=u'Lien CAD présent'))
        except Exception as e:
            return ThemeResult(cle=self.cle, libelle=self.libelle,
                               disponible=False,
                               message=u'Collecte CAD indisponible : {}'.format(e))
        return ThemeResult(cle=self.cle, libelle=self.libelle,
                           issues=issues, analyses=analyses)
