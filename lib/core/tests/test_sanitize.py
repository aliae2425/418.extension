# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.sanitize import sanitize, sanitize_revit_name


class TestSanitizeNomFichier(unittest.TestCase):
    def test_remplace_les_caracteres_interdits(self):
        self.assertEqual(sanitize(u'a/b:c*?"<>|'), u'a_b_c______')

    def test_tronque_a_max_len(self):
        self.assertEqual(len(sanitize(u'x' * 300)), 180)

    def test_retire_points_et_espaces_finaux(self):
        # Windows rejette un nom de fichier finissant par '.' ou ' '.
        self.assertEqual(sanitize(u'Plan RDC. '), u'Plan RDC')
        self.assertEqual(sanitize(u'Coupe...'), u'Coupe')

    def test_retire_les_points_finaux_apres_troncature(self):
        # La troncature peut faire tomber la fin sur un point.
        self.assertEqual(sanitize(u'x' * 179 + u'..', max_len=180), u'x' * 179)

    def test_repli_si_vide_ou_sans_reste(self):
        self.assertEqual(sanitize(u''), u'export')
        self.assertEqual(sanitize(None), u'export')
        self.assertEqual(sanitize(u'   '), u'export')
        self.assertEqual(sanitize(u'', fallback=u'untitled'), u'untitled')


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
