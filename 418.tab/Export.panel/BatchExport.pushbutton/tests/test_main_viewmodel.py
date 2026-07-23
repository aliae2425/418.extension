# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.viewmodels.MainViewModel import MainViewModel


class TestMainViewModel(unittest.TestCase):
    def setUp(self):
        self.vm = MainViewModel(doc=None)

    def test_titre(self):
        self.assertEqual(self.vm.Titre, u'Exportation')

    def test_mode_par_defaut_auto(self):
        self.assertEqual(self.vm.ActiveMode, u'auto')
        self.assertTrue(self.vm.IsAuto)
        self.assertFalse(self.vm.IsManual)
        self.assertFalse(self.vm.IsSettings)

    def test_set_mode_manual(self):
        self.vm.set_mode(u'manual')
        self.assertEqual(self.vm.ActiveMode, u'manual')
        self.assertTrue(self.vm.IsManual)
        self.assertFalse(self.vm.IsAuto)

    def test_set_mode_invalide_ignore(self):
        self.vm.set_mode(u'auto')
        self.vm.set_mode(u'zzz')
        self.assertEqual(self.vm.ActiveMode, u'auto')

    def test_surface_titre_change_selon_mode(self):
        self.vm.set_mode(u'auto')
        self.assertIn(u'jeu', self.vm.SurfaceTitre.lower())
        self.vm.set_mode(u'settings')
        self.assertEqual(self.vm.SurfaceTitre, u'Paramètres')


if __name__ == '__main__':
    unittest.main()
