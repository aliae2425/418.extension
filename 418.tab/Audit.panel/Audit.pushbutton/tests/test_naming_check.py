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

from services.checks.NamingCheck import (
    est_conforme, DEFAULT_VIEW_REGEX, DEFAULT_FAMILY_REGEX)


class TestNaming(unittest.TestCase):
    def test_vue_conforme(self):
        self.assertTrue(est_conforme(u'NIV_00_PLAN_RDC', DEFAULT_VIEW_REGEX))

    def test_vue_non_conforme(self):
        self.assertFalse(est_conforme(u'Sans titre 1', DEFAULT_VIEW_REGEX))

    def test_famille_conforme(self):
        self.assertTrue(est_conforme(u'MOB_Chaise', DEFAULT_FAMILY_REGEX))

    def test_famille_non_conforme(self):
        self.assertFalse(est_conforme(u'Famille2', DEFAULT_FAMILY_REGEX))

    def test_pattern_invalide_tolere(self):
        # un pattern cassé ne doit pas faire échouer l'audit
        self.assertTrue(est_conforme(u'X', u'([a-z'))

    def test_nom_none_non_conforme(self):
        self.assertFalse(est_conforme(None, DEFAULT_VIEW_REGEX))


if __name__ == '__main__':
    unittest.main()
