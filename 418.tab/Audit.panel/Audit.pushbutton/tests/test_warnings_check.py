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
from services.checks.WarningsCheck import gravite_pour


class TestWarningsGravite(unittest.TestCase):
    def test_doublon_est_critique(self):
        self.assertEqual(
            gravite_pour(u'There are identical instances in the same place'),
            CRITIQUE)
        self.assertEqual(gravite_pour(u'Éléments dupliqués au même endroit'),
                         CRITIQUE)

    def test_autre_est_a_revoir(self):
        self.assertEqual(gravite_pour(u'Les murs se chevauchent'), A_REVOIR)


if __name__ == '__main__':
    unittest.main()
