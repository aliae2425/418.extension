# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
# Meme racine que pyRevit expose : <bouton>/lib.
_BUTTON_LIB = os.path.abspath(os.path.join(_HERE, '..', 'lib'))
if _BUTTON_LIB not in sys.path:
    sys.path.insert(0, _BUTTON_LIB)

from config.AuditRules import AuditRules
from models import A_REVOIR, CRITIQUE
from models import AuditIssue
from models import ThemeResult
from services import ScoreService
from services.checks.WarningsCheck import gravite_pour
from services.checks.ViewsSheetsCheck import est_nom_par_defaut
from services.checks.NamingCheck import NamingCheck


def _theme(cle, gravites):
    return ThemeResult(cle=cle, libelle=cle,
                       issues=[AuditIssue(u'x', g) for g in gravites])


class TestReglesInjectees(unittest.TestCase):
    """Prouve que des règles injectées (venant du JSON) changent bien le
    comportement de chaque consommateur, vs les défauts."""

    def test_score_suit_les_poids_custom(self):
        defaut = ScoreService.calculer([_theme(u'cad', [CRITIQUE])])  # 90 par défaut
        custom = AuditRules(data={u'score': {
            u'poids_theme': {u'cad': 2.0}, u'points_critique': 10,
            u'points_a_revoir': 4, u'volume_facteur': 0.0, u'volume_max': 0}})
        score = ScoreService.calculer([_theme(u'cad', [CRITIQUE])], custom)
        self.assertEqual(defaut, 90)
        self.assertEqual(score, 80)   # 2.0 * 10 + 0 -> 80

    def test_warnings_mots_critiques_custom(self):
        # 'overlap' n'est pas critique par défaut...
        self.assertEqual(gravite_pour(u'walls overlap'), A_REVOIR)
        # ...mais le devient si on l'ajoute aux règles.
        r = AuditRules(data={u'avertissements': {u'mots_critiques': [u'overlap']}})
        self.assertEqual(gravite_pour(u'walls overlap', r), CRITIQUE)

    def test_nom_defaut_regex_custom(self):
        self.assertFalse(est_nom_par_defaut(u'ZoneA'))
        r = AuditRules(data={u'vues_feuilles': {u'nom_defaut_regex': u'^Zone'}})
        self.assertTrue(est_nom_par_defaut(u'ZoneA', r))

    def test_naming_patterns_custom(self):
        r = AuditRules(data={u'nommage': {u'vue_regex': u'^ZZ_',
                                          u'famille_regex': u'^FF_'}})
        chk = NamingCheck(r)
        self.assertEqual(chk._patterns(), (u'^ZZ_', u'^FF_'))


if __name__ == '__main__':
    unittest.main()
