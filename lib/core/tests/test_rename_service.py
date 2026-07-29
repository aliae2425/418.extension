# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.rename_service import RenameService


class TestRenameService(unittest.TestCase):

    def test_litteral_replace(self):
        svc = RenameService(rechercher=u'A', remplacer=u'B')
        self.assertEqual(svc.apply(u'AAA'), u'BBB')

    def test_prefixe_suffixe(self):
        svc = RenameService(prefixe=u'[', suffixe=u']')
        self.assertEqual(svc.apply(u'x'), u'[x]')

    def test_regex_invalide_retourne_nom_intact(self):
        svc = RenameService(rechercher=u'(', use_regex=True)
        self.assertEqual(svc.apply(u'abc'), u'abc')
        self.assertTrue(svc.regex_error)


if __name__ == '__main__':
    unittest.main()
