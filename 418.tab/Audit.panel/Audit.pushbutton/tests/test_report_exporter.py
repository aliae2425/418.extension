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
# Dossier du bouton (pour 'from models...')
# Meme racine que pyRevit expose : <bouton>/lib.
_BUTTON_LIB = os.path.abspath(os.path.join(_HERE, '..', 'lib'))
if _BUTTON_LIB not in sys.path:
    sys.path.insert(0, _BUTTON_LIB)

from models import CRITIQUE, A_REVOIR
from models import AuditIssue
from models import ThemeResult
from models import AuditResult
from services.ReportExporter import construire_html


class TestReportHtml(unittest.TestCase):
    def _result(self):
        t = ThemeResult(cle=u'cad', libelle=u'Imports / Liens CAD',
                        issues=[AuditIssue(u'plan.dwg', CRITIQUE,
                                           emplacement=u'Vue : Plan RDC',
                                           type_=u'Import explosé')],
                        analyses=20)
        return AuditResult(themes=[t], score=72,
                           top_critiques=[t.issues[0]],
                           meta={'fichier': u'Test.rvt',
                                 'horodatage': u'2026-08-05 10:00'})

    def test_contient_score_et_theme(self):
        html = construire_html(self._result())
        self.assertIn(u'72', html)
        self.assertIn(u'Imports / Liens CAD', html)
        self.assertIn(u'plan.dwg', html)
        self.assertTrue(html.strip().startswith(u'<!DOCTYPE html>'))

    def test_echappe_html(self):
        t = ThemeResult(cle=u'x', libelle=u'X',
                        issues=[AuditIssue(u'<script>', A_REVOIR)])
        html = construire_html(AuditResult(themes=[t], score=50))
        self.assertNotIn(u'<script>', html)
        self.assertIn(u'&lt;script&gt;', html)


if __name__ == '__main__':
    unittest.main()
