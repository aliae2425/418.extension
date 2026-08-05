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

from lib.models.Severity import OK, A_REVOIR, CRITIQUE, libelle, pire
from lib.models.AuditIssue import AuditIssue
from lib.models.ThemeResult import ThemeResult
from lib.models.AuditResult import AuditResult


class TestSeverity(unittest.TestCase):
    def test_ordre(self):
        self.assertTrue(CRITIQUE > A_REVOIR > OK)

    def test_libelle(self):
        self.assertEqual(libelle(CRITIQUE), u'Critique')
        self.assertEqual(libelle(A_REVOIR), u'À revoir')
        self.assertEqual(libelle(OK), u'Conforme')

    def test_pire_vide_est_ok(self):
        self.assertEqual(pire([]), OK)

    def test_pire_prend_le_max(self):
        self.assertEqual(pire([OK, A_REVOIR, CRITIQUE, A_REVOIR]), CRITIQUE)


class TestThemeResult(unittest.TestCase):
    def test_compte_et_pire_gravite(self):
        issues = [AuditIssue(u'a', A_REVOIR), AuditIssue(u'b', CRITIQUE)]
        tr = ThemeResult(cle=u'cad', libelle=u'CAD', issues=issues, analyses=20)
        self.assertEqual(tr.compte, 2)
        self.assertEqual(tr.pire_gravite, CRITIQUE)

    def test_theme_vide(self):
        tr = ThemeResult(cle=u'nommage', libelle=u'Nommage')
        self.assertEqual(tr.compte, 0)
        self.assertEqual(tr.pire_gravite, OK)
        self.assertTrue(tr.disponible)


class TestAuditResult(unittest.TestCase):
    def test_defauts(self):
        ar = AuditResult()
        self.assertEqual(ar.score, 100)
        self.assertEqual(ar.themes, [])
        self.assertEqual(ar.top_critiques, [])
        self.assertEqual(ar.meta, {})


if __name__ == '__main__':
    unittest.main()
