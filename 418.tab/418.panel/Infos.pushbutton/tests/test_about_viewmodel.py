# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

# Rendre importable le lib partagé (418.extension/lib) comme le fait pyRevit.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(
    _HERE, '..', '..', '..', '..', 'lib'))  # -> 418.extension/lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
# Rendre importable le lib local du bouton (pour 'from lib.viewmodels...').
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.viewmodels.AboutViewModel import AboutViewModel, __version__


class TestAboutViewModel(unittest.TestCase):
    def setUp(self):
        self.vm = AboutViewModel()

    def test_nom(self):
        self.assertEqual(self.vm.Nom, u'418.extension')

    def test_version_contient_numero(self):
        self.assertEqual(self.vm.Version, u'Version 1.2.12')
        self.assertEqual(__version__, u'1.2.12')

    def test_description_non_vide(self):
        self.assertTrue(len(self.vm.Description) > 0)

    def test_auteur_et_licence(self):
        self.assertEqual(self.vm.Auteur, u'Aliae')
        self.assertEqual(self.vm.Licence, u'Licence MIT © 2025')

    def test_url_depot(self):
        self.assertEqual(
            self.vm.UrlDepot,
            u'https://github.com/aliae2425/418.extension')

    def test_ouvrir_depot_ne_leve_pas(self):
        # Hors Revit, Process.Start est indisponible : ne doit pas lever.
        cmd = self.vm.ouvrir_depot_cmd
        if cmd is not None:
            cmd.Execute(None)  # RelayCommand.Execute


if __name__ == '__main__':
    unittest.main()
