# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core import text_filter


class _Row(object):
    def __init__(self, a, b):
        self.A = a
        self.B = b


def _getters():
    return [lambda r: r.A, lambda r: r.B]


class TestTextFilter(unittest.TestCase):

    def setUp(self):
        self.rows = [_Row(u'A-101', u'Plan RDC'),
                     _Row(u'A-102', u'Élévation'),
                     _Row(u'B-201', u'Coupe AA')]

    def test_texte_vide_renvoie_tout(self):
        self.assertEqual(len(text_filter.filtrer(self.rows, u'', _getters())), 3)

    def test_none_renvoie_tout(self):
        self.assertEqual(len(text_filter.filtrer(self.rows, None, _getters())), 3)

    def test_filtre_substring_insensible_casse(self):
        out = text_filter.filtrer(self.rows, u'plan', _getters())
        self.assertEqual([r.A for r in out], [u'A-101'])

    def test_filtre_insensible_accents(self):
        # 'elevation' (sans accent) doit trouver 'Élévation'
        out = text_filter.filtrer(self.rows, u'elevation', _getters())
        self.assertEqual([r.A for r in out], [u'A-102'])

    def test_filtre_sur_second_getter(self):
        out = text_filter.filtrer(self.rows, u'coupe', _getters())
        self.assertEqual([r.A for r in out], [u'B-201'])

    def test_aucun_match(self):
        self.assertEqual(text_filter.filtrer(self.rows, u'zzz', _getters()), [])


if __name__ == '__main__':
    unittest.main()
