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

from lib.models import CRITIQUE, A_REVOIR
from lib.models import AuditIssue
from lib.models import ThemeResult
from lib.models import AuditResult
from lib.viewmodels.ScoreVM import ScoreVM
from lib.viewmodels.ThemeCardVM import ThemeCardVM
from lib.viewmodels.IssueRowVM import IssueRowVM


class TestVM(unittest.TestCase):
    def test_score_vm(self):
        # NbCritiques compte les issues CRITIQUE réelles des thèmes,
        # pas top_critiques (qui n'est qu'un top-5 toutes gravités confondues).
        themes = [ThemeResult(cle=u'x', libelle=u'X',
                              issues=[AuditIssue(u'a', CRITIQUE)])]
        vm = ScoreVM(AuditResult(score=72, themes=themes,
                                 top_critiques=[AuditIssue(u'a', CRITIQUE)]))
        self.assertEqual(vm.Score, 72)
        self.assertEqual(vm.NbCritiques, 1)
        self.assertTrue(len(vm.Verdict) > 0)

    def test_score_vm_nb_critiques_compte_les_vrais_critiques(self):
        # NbCritiques doit compter les CRITIQUE réels de tous les thèmes,
        # pas len(top_critiques) (qui est le top-5 toutes gravités confondues).
        themes = [ThemeResult(cle=u'cad', libelle=u'CAD', issues=[
            AuditIssue(u'a', CRITIQUE),
            AuditIssue(u'b', A_REVOIR),
            AuditIssue(u'c', CRITIQUE),
        ])]
        # top_critiques délibérément différent : 1 seule issue, non critique.
        result = AuditResult(score=50, themes=themes,
                             top_critiques=[AuditIssue(u'x', A_REVOIR)])
        vm = ScoreVM(result)
        self.assertEqual(vm.NbCritiques, 2)
        self.assertNotEqual(vm.NbCritiques, len(result.top_critiques))
        total_issues = sum(len(t.issues) for t in themes)
        self.assertNotEqual(vm.NbCritiques, total_issues)

    def test_score_vm_niveau_par_bandes(self):
        def niv(score):
            return ScoreVM(AuditResult(score=score)).Niveau
        self.assertEqual(niv(95), u'excellent')
        self.assertEqual(niv(80), u'bon')
        self.assertEqual(niv(60), u'correct')
        self.assertEqual(niv(30), u'critique')
        self.assertEqual(ScoreVM(AuditResult(score=60)).NiveauLibelle, u'Correct')

    def test_score_vm_donut_un_segment_par_theme_avec_probleme(self):
        themes = [
            ThemeResult(cle=u'cad', libelle=u'CAD', issues=[AuditIssue(u'a', CRITIQUE)]),
            ThemeResult(cle=u'purge', libelle=u'Purge',
                        issues=[AuditIssue(u'b', A_REVOIR), AuditIssue(u'c', A_REVOIR)]),
            ThemeResult(cle=u'vide', libelle=u'Vide', issues=[]),  # 0 problème -> pas de segment
        ]
        segs = ScoreVM(AuditResult(score=72, themes=themes)).DonutSegments
        self.assertEqual(len(segs), 2)  # seuls les thèmes avec problèmes
        for s in segs:
            self.assertTrue(s.PathData.startswith(u'M '))
            self.assertIn(u'Z', s.PathData)
        # chaque segment porte l'identité du thème (couleur + légende)
        self.assertEqual(segs[0].Cle, u'cad')
        self.assertEqual(segs[0].Libelle, u'CAD')
        self.assertEqual(segs[0].Compte, 1)
        self.assertEqual(segs[1].Cle, u'purge')
        self.assertEqual(segs[1].Compte, 2)

    def test_score_vm_donut_sans_probleme_anneau_conforme(self):
        segs = ScoreVM(AuditResult(score=100, themes=[])).DonutSegments
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].Cle, u'conforme')

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

    def test_theme_card_vm_ratio_avec_analyses(self):
        # 3 problèmes sur 10 éléments analysés -> ratio 30%, label « 3 / 10 »
        t = ThemeResult(cle=u'purge', libelle=u'À purger',
                        issues=[AuditIssue(u'a', A_REVOIR),
                                AuditIssue(u'b', A_REVOIR),
                                AuditIssue(u'c', A_REVOIR)],
                        analyses=10)
        card = ThemeCardVM(t)
        self.assertEqual(card.Analyses, 10)
        self.assertEqual(card.CompteLabel, u'3 / 10')
        self.assertEqual(card.RatioProblemePct, 30.0)

    def test_theme_card_vm_ratio_sans_analyses(self):
        # analyses inconnu (None) -> label = compte seul, ratio saturé si compte > 0
        t = ThemeResult(cle=u'warn', libelle=u'Avertissements',
                        issues=[AuditIssue(u'a', A_REVOIR),
                                AuditIssue(u'b', A_REVOIR),
                                AuditIssue(u'c', A_REVOIR)],
                        analyses=None)
        card = ThemeCardVM(t)
        self.assertIsNone(card.Analyses)
        self.assertEqual(card.CompteLabel, u'3')
        self.assertEqual(card.RatioProblemePct, 100.0)


if __name__ == '__main__':
    unittest.main()
