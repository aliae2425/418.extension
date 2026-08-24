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
        self.assertEqual(o.view_prefix, u'')
        self.assertTrue(o.include_views)
        self.assertFalse(o.include_dimensions)
        self.assertEqual(o.view_duplicate_option, u'duplicate')

    def test_modifs_se_refletent_dans_options(self):
        vm = OptionsPageVM()
        vm.ViewPrefix = u'DUP_'
        vm.NumberSuffix = u'-b'
        vm.IncludeDimensions = True
        vm.UseExistingLegends = False
        vm.ViewDuplicateOption = u'as_dependent'
        o = vm.build_options()
        self.assertEqual(o.view_prefix, u'DUP_')
        self.assertEqual(o.number_suffix, u'-b')
        self.assertTrue(o.include_dimensions)
        self.assertFalse(o.use_existing_legends)
        self.assertEqual(o.view_duplicate_option, u'as_dependent')


if __name__ == '__main__':
    unittest.main()
