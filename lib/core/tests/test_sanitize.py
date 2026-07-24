# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.sanitize import sanitize_revit_name


class TestSanitizeRevitName(unittest.TestCase):
    def test_retire_caracteres_interdits(self):
        self.assertEqual(sanitize_revit_name(u'A{B}[C];D'), u'ABCD')

    def test_retire_backtick_et_tilde(self):
        self.assertEqual(sanitize_revit_name(u'X`Y~Z'), u'XYZ')

    def test_retire_slash_colon_pipe(self):
        self.assertEqual(sanitize_revit_name(u'a\\b:c|d'), u'abcd')

    def test_conserve_texte_valide(self):
        self.assertEqual(sanitize_revit_name(u'Plan RDC 1-100'), u'Plan RDC 1-100')

    def test_conserve_le_slash(self):
        # Revit autorise « / » dans les noms (ex. échelle 1/100) : ne pas le retirer.
        self.assertEqual(sanitize_revit_name(u'Coupe 1/100'), u'Coupe 1/100')
        self.assertEqual(sanitize_revit_name(u'a\\b/c:d|e'), u'ab/cde')

    def test_vide_donne_sansnom(self):
        self.assertEqual(sanitize_revit_name(u'{}'), u'SansNom')
        self.assertEqual(sanitize_revit_name(u''), u'SansNom')


if __name__ == '__main__':
    unittest.main()
