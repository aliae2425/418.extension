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

from lib.models.Severity import A_REVOIR, CRITIQUE
from lib.models.AuditIssue import AuditIssue
from lib.models.ThemeResult import ThemeResult
from lib.services import ScoreService


def _theme(cle, gravites):
    return ThemeResult(cle=cle, libelle=cle,
                       issues=[AuditIssue(u'x', g) for g in gravites])


class TestScore(unittest.TestCase):
    def test_aucun_theme_score_100(self):
        self.assertEqual(ScoreService.calculer([]), 100)

    def test_themes_sans_probleme_score_100(self):
        self.assertEqual(ScoreService.calculer([_theme(u'cad', [])]), 100)

    def test_un_critique_cad(self):
        # poids cad 1.0 * 10 + volume min(8, 0.05*1)=0.05 -> ~10.05 -> 90
        self.assertEqual(ScoreService.calculer([_theme(u'cad', [CRITIQUE])]), 90)

    def test_purge_pese_moins(self):
        # purge poids 0.6 * 4 (a_revoir) + volume 0.05 = 2.45 -> 98 (round(97.55))
        self.assertEqual(ScoreService.calculer([_theme(u'purge', [A_REVOIR])]), 98)

    def test_score_reste_borne_sous_forte_penalite(self):
        # Sous forte pénalité (les 5 thèmes saturés de critiques), le score
        # reste dans [0, 100] et fortement réduit. La pénalité max théorique
        # (~81 sur les 5 thèmes) ne peut pas atteindre 0 : le max(0, …) est
        # une garde défensive, on vérifie ici la borne, pas un plancher exact.
        themes = [_theme(c, [CRITIQUE] * 200) for c in
                  (u'warnings', u'cad', u'vues_feuilles', u'purge', u'nommage')]
        score = ScoreService.calculer(themes)
        self.assertTrue(0 <= score <= 30)

    def test_theme_indisponible_ignore(self):
        t = ThemeResult(cle=u'cad', libelle=u'CAD', disponible=False)
        self.assertEqual(ScoreService.calculer([t]), 100)


if __name__ == '__main__':
    unittest.main()
