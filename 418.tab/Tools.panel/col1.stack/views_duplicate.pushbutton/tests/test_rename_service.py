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

from lib.services.RenameService import RenameService


class TestRenameServiceLitteral(unittest.TestCase):
    def test_sans_transformation(self):
        svc = RenameService()
        self.assertEqual(svc.apply(u'Niveau 0'), u'Niveau 0')

    def test_prefixe_suffixe(self):
        svc = RenameService(prefixe=u'[A] ', suffixe=u' _COPY')
        self.assertEqual(svc.apply(u'Plan'), u'[A] Plan _COPY')

    def test_remplacement_litteral(self):
        svc = RenameService(rechercher=u'Plan', remplacer=u'Vue')
        self.assertEqual(svc.apply(u'Plan RDC'), u'Vue RDC')

    def test_remplacement_litteral_multiple(self):
        svc = RenameService(rechercher=u'A', remplacer=u'X')
        self.assertEqual(svc.apply(u'AAA'), u'XXX')

    def test_rechercher_vide_ne_modifie_pas(self):
        svc = RenameService(rechercher=u'', remplacer=u'X')
        self.assertEqual(svc.apply(u'Plan'), u'Plan')

    def test_combinaison_complete(self):
        svc = RenameService(prefixe=u'PRE-', rechercher=u'Old', remplacer=u'New', suffixe=u'-SUF')
        self.assertEqual(svc.apply(u'Old Vue'), u'PRE-New Vue-SUF')

    def test_is_valid_en_mode_litteral(self):
        self.assertTrue(RenameService(use_regex=False).is_valid)


class TestRenameServiceRegex(unittest.TestCase):
    def test_regex_simple(self):
        svc = RenameService(rechercher=u'[0-9]+', remplacer=u'N', use_regex=True)
        self.assertEqual(svc.apply(u'Plan 42'), u'Plan N')

    def test_regex_groupe_capture(self):
        svc = RenameService(rechercher=u'(Plan) (.*)', remplacer=u'\\2 - \\1', use_regex=True)
        self.assertEqual(svc.apply(u'Plan RDC'), u'RDC - Plan')

    def test_regex_invalide_ne_crash_pas(self):
        svc = RenameService(rechercher=u'[invalide', use_regex=True)
        self.assertFalse(svc.is_valid)
        self.assertNotEqual(svc.regex_error, u'')
        self.assertEqual(svc.apply(u'Niveau 0'), u'Niveau 0')

    def test_regex_vide_ne_modifie_pas(self):
        svc = RenameService(rechercher=u'', remplacer=u'X', use_regex=True)
        self.assertTrue(svc.is_valid)
        self.assertEqual(svc.apply(u'Plan'), u'Plan')

    def test_regex_avec_prefixe_suffixe(self):
        svc = RenameService(prefixe=u'A_', rechercher=u'\\.', remplacer=u'-', suffixe=u'_Z', use_regex=True)
        self.assertEqual(svc.apply(u'v.1.0'), u'A_v-1-0_Z')

    def test_is_valid_regex_valide(self):
        svc = RenameService(rechercher=u'\\d+', use_regex=True)
        self.assertTrue(svc.is_valid)
        self.assertEqual(svc.regex_error, u'')


if __name__ == '__main__':
    unittest.main()
