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

from lib.services.DuplicationOptions import DuplicationOptions


class TestDuplicationOptions(unittest.TestCase):
    def test_defauts(self):
        o = DuplicationOptions()
        self.assertTrue(o.include_views)
        self.assertFalse(o.include_dimensions)
        self.assertTrue(o.use_existing_legends)
        self.assertEqual(o.view_duplicate_option, u'duplicate')
        self.assertEqual(o.view_prefix, u'')

    def test_surcharge_par_mots_cles(self):
        o = DuplicationOptions(view_prefix=u'DUP_', include_dimensions=True,
                               view_duplicate_option=u'as_dependent')
        self.assertEqual(o.view_prefix, u'DUP_')
        self.assertTrue(o.include_dimensions)
        self.assertEqual(o.view_duplicate_option, u'as_dependent')


if __name__ == '__main__':
    unittest.main()
