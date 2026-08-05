# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
import os
import unittest

# Prérequis de test: ajouter les DEUX chemins au sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
# 418.extension/lib (tests -> pushbutton -> Audit.panel -> 418.tab -> 418.extension)
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
# Dossier du bouton (pour 'from lib.models...')
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.models.Severity import CRITIQUE, A_REVOIR
from lib.models.AuditIssue import AuditIssue
from lib.models.ThemeResult import ThemeResult
from lib.models.AuditResult import AuditResult
from lib.viewmodels.ScoreVM import ScoreVM
from lib.viewmodels.ThemeCardVM import ThemeCardVM
from lib.viewmodels.IssueRowVM import IssueRowVM


class TestVM(unittest.TestCase):
    def test_score_vm(self):
        vm = ScoreVM(AuditResult(score=72, top_critiques=[AuditIssue(u'a', CRITIQUE)]))
        self.assertEqual(vm.Score, 72)
        self.assertEqual(vm.NbCritiques, 1)
        self.assertTrue(len(vm.Verdict) > 0)

    def test_issue_row_vm(self):
        row = IssueRowVM(AuditIssue(u'plan.dwg', CRITIQUE,
                                    emplacement=u'Vue', type_=u'Import'))
        self.assertEqual(row.Nom, u'plan.dwg')
        self.assertEqual(row.Gravite, u'Critique')

    def test_theme_card_vm(self):
        t = ThemeResult(cle=u'cad', libelle=u'CAD',
                        issues=[AuditIssue(u'x', A_REVOIR)], analyses=10)
        card = ThemeCardVM(t)
        self.assertEqual(card.Libelle, u'CAD')
        self.assertEqual(card.Compte, 1)
        self.assertEqual(len(card.Rows), 1)
        self.assertFalse(card.EstDeplie)


if __name__ == '__main__':
    unittest.main()
