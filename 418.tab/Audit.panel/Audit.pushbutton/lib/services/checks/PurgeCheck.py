# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from services.checks.BaseCheck import BaseCheck
from models import A_REVOIR
from models import AuditIssue
from models import ThemeResult

try:
    from Autodesk.Revit.DB import ElementId, Category
except Exception:
    ElementId = Category = None

try:
    from System.Collections.Generic import HashSet
except Exception:
    HashSet = None


class PurgeCheck(BaseCheck):
    cle = u'purge'
    libelle = u'À purger'

    def run(self, doc):
        if doc is None or ElementId is None or HashSet is None:
            return ThemeResult(cle=self.cle, libelle=self.libelle, issues=[])
        try:
            ids = doc.GetUnusedElements(HashSet[ElementId]())
        except Exception as e:
            return ThemeResult(cle=self.cle, libelle=self.libelle,
                               disponible=False,
                               message=u'GetUnusedElements indisponible : {}'.format(e))
        # Regrouper par nom de catégorie.
        par_cat = {}
        total = 0
        for eid in ids:
            total += 1
            nom_cat = u'Autres'
            try:
                el = doc.GetElement(eid)
                if el is not None and el.Category is not None:
                    nom_cat = el.Category.Name
            except Exception:
                pass
            par_cat.setdefault(nom_cat, 0)
            par_cat[nom_cat] += 1
        issues = []
        gravite = self._rules.purge_gravite()
        for cat, n in sorted(par_cat.items(), key=lambda kv: kv[1], reverse=True):
            issues.append(AuditIssue(
                nom=cat, gravite=gravite,
                emplacement=u'Projet', type_=u'Non utilisé',
                message=u'{} élément(s) purgeable(s)'.format(n)))
        # analyses laissé à None : le nombre total d'éléments inutilisés n'est
        # pas une population comparable au compte groupé (issues par
        # catégorie) ; analyses=None fait afficher une barre 100% problème.
        return ThemeResult(cle=self.cle, libelle=self.libelle,
                           issues=issues)
