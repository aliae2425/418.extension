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

    def test_count_multiplie_les_lignes_d_apercu(self):
        vm = OptionsPageVM()
        vm.set_source_items([(u'A101', u'Plan RDC'), (u'A102', u'Plan R+1')])
        self.assertEqual(len(vm.PreviewGroups), 2)
        vm.Count = u'3'
        self.assertEqual(len(vm.PreviewGroups), 6)
        self.assertEqual(vm.build_options().count, 3)

    def test_count_invalide_retombe_sur_une_ligne_par_feuille(self):
        vm = OptionsPageVM()
        vm.set_source_items([(u'A101', u'Plan RDC')])
        vm.Count = u''
        self.assertEqual(len(vm.PreviewGroups), 1)

    def test_token_n_numerote_les_copies_dans_l_apercu(self):
        vm = OptionsPageVM()
        vm.NumberSuffix = u'_{n}'
        vm.Count = u'2'
        vm.set_source_items([(u'A101', u'Plan RDC')])
        self.assertEqual([g.NumeroGenere for g in vm.PreviewGroups],
                         [u'A101_1', u'A101_2'])


if __name__ == '__main__':
    unittest.main()
