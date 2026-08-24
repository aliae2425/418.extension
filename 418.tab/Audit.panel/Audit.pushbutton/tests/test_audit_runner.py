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

from models import A_REVOIR, CRITIQUE
from models import AuditIssue
from models import ThemeResult
from services.AuditRunner import AuditRunner


class _FakeCheck(object):
    def __init__(self, cle, issues):
        self.cle = cle
        self.libelle = cle
        self._issues = issues

    def run(self, doc):
        return ThemeResult(cle=self.cle, libelle=self.libelle, issues=self._issues)


class _CheckQuiLeve(object):
    cle = u'cad'
    libelle = u'CAD'

    def run(self, doc):
        raise ValueError(u'boom')


class TestAuditRunner(unittest.TestCase):
    def test_agrege_themes_et_score(self):
        checks = [_FakeCheck(u'cad', [AuditIssue(u'a', CRITIQUE)]),
                  _FakeCheck(u'purge', [AuditIssue(u'b', A_REVOIR)])]
        res = AuditRunner(checks=checks).run(doc=None)
        self.assertEqual(len(res.themes), 2)
        self.assertTrue(0 <= res.score <= 100)

    def test_top_critiques_trie_et_limite(self):
        issues = [AuditIssue(u'w%d' % i, A_REVOIR) for i in range(10)]
        issues.append(AuditIssue(u'grave', CRITIQUE))
        res = AuditRunner(checks=[_FakeCheck(u'warnings', issues)]).run(doc=None)
        self.assertEqual(len(res.top_critiques), 5)
        self.assertEqual(res.top_critiques[0].nom, u'grave')  # critique en tête

    def test_check_qui_leve_devient_indisponible(self):
        res = AuditRunner(checks=[_CheckQuiLeve()]).run(doc=None)
        self.assertEqual(len(res.themes), 1)
        self.assertFalse(res.themes[0].disponible)

    def test_meta_sans_doc(self):
        res = AuditRunner(checks=[_FakeCheck(u'cad', [])]).run(doc=None)
        self.assertIn('horodatage', res.meta)


if __name__ == '__main__':
    unittest.main()
