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

from lib.services.checks.ViewsSheetsCheck import est_nom_par_defaut


class TestNomParDefaut(unittest.TestCase):
    def test_niveau_defaut(self):
        self.assertTrue(est_nom_par_defaut(u'Niveau 4'))
        self.assertTrue(est_nom_par_defaut(u'Level 2'))
        self.assertTrue(est_nom_par_defaut(u'Quadrillage 1'))

    def test_nom_personnalise(self):
        self.assertFalse(est_nom_par_defaut(u'RDC fini'))
        self.assertFalse(est_nom_par_defaut(u'A'))


if __name__ == '__main__':
    unittest.main()
