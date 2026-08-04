# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.viewmodels.OptionsPageVM import OptionsPageVM


class TestOptionsPageVM(unittest.TestCase):
    def test_defauts_mappent_vers_options(self):
        o = OptionsPageVM().build_options()
        self.assertEqual(o.view_duplicate_option, u'duplicate')
        self.assertEqual(o.count, 1)

    def test_modif_mode_se_reflete_dans_options(self):
        vm = OptionsPageVM()
        vm.ViewDuplicateOption = u'with_detailing'
        o = vm.build_options()
        self.assertEqual(o.view_duplicate_option, u'with_detailing')

    def test_modif_count_se_reflete_dans_options(self):
        vm = OptionsPageVM()
        vm.Count = u'3'
        o = vm.build_options()
        self.assertEqual(o.count, 3)

    def test_count_invalide_donne_1(self):
        vm = OptionsPageVM()
        vm.Count = u'abc'
        o = vm.build_options()
        self.assertEqual(o.count, 1)

    def test_notify_sur_changement_mode(self):
        notifications = []
        vm = OptionsPageVM()
        # Monkey-patch notify_property pour capter les notifications
        vm.notify_property = lambda name: notifications.append(name)
        vm.ViewDuplicateOption = u'as_dependent'
        self.assertIn('ViewDuplicateOption', notifications)

    def test_pas_de_notify_si_valeur_identique(self):
        notifications = []
        vm = OptionsPageVM()
        vm.notify_property = lambda name: notifications.append(name)
        vm.ViewDuplicateOption = u'duplicate'  # identique au défaut
        self.assertEqual(notifications, [])

    def test_champs_nommage_transportes_dans_options(self):
        vm = OptionsPageVM()
        vm.Prefixe = u'PFX_'
        vm.Rechercher = u'Plan'
        vm.Remplacer = u'Vue'
        vm.Suffixe = u'_SFX'
        vm.UseRegex = False
        o = vm.build_options()
        self.assertEqual(o.prefixe, u'PFX_')
        self.assertEqual(o.rechercher, u'Plan')
        self.assertEqual(o.remplacer, u'Vue')
        self.assertEqual(o.suffixe, u'_SFX')
        self.assertEqual(o.use_regex, False)

    def test_use_regex_true_transporte(self):
        vm = OptionsPageVM()
        vm.UseRegex = True
        o = vm.build_options()
        self.assertEqual(o.use_regex, True)


if __name__ == '__main__':
    unittest.main()
