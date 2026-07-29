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

from lib.services.ViewsDuplicationOptions import ViewsDuplicationOptions


class TestViewsDuplicationOptions(unittest.TestCase):
    def test_defauts(self):
        o = ViewsDuplicationOptions()
        self.assertEqual(o.view_duplicate_option, u'duplicate')
        self.assertEqual(o.count, 1)

    def test_surcharge_mode_et_count(self):
        o = ViewsDuplicationOptions(view_duplicate_option=u'with_detailing', count=3)
        self.assertEqual(o.view_duplicate_option, u'with_detailing')
        self.assertEqual(o.count, 3)

    def test_count_invalide_donne_1(self):
        o = ViewsDuplicationOptions(count='abc')
        self.assertEqual(o.count, 1)

    def test_count_zero_donne_1(self):
        o = ViewsDuplicationOptions(count=0)
        self.assertEqual(o.count, 1)

    def test_count_negatif_donne_1(self):
        o = ViewsDuplicationOptions(count=-5)
        self.assertEqual(o.count, 1)

    def test_champs_nommage_par_defaut(self):
        o = ViewsDuplicationOptions()
        self.assertEqual(o.prefixe, u'')
        self.assertEqual(o.rechercher, u'')
        self.assertEqual(o.remplacer, u'')
        self.assertEqual(o.suffixe, u'')
        self.assertEqual(o.use_regex, False)

    def test_champs_nommage_surcharges(self):
        o = ViewsDuplicationOptions(
            prefixe=u'PFX_', rechercher=u'a', remplacer=u'b',
            suffixe=u'_SFX', use_regex=True,
        )
        self.assertEqual(o.prefixe, u'PFX_')
        self.assertEqual(o.rechercher, u'a')
        self.assertEqual(o.remplacer, u'b')
        self.assertEqual(o.suffixe, u'_SFX')
        self.assertEqual(o.use_regex, True)


if __name__ == '__main__':
    unittest.main()
