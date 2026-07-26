# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import datetime
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.services.TokenExpander import TokenExpander

_DATE = datetime.date(2026, 7, 26)


class TestTokenExpanderDate(unittest.TestCase):
    def setUp(self):
        self.exp = TokenExpander(today=_DATE)

    def test_date(self):
        self.assertEqual(self.exp.expand(u'{date}'), u'2026-07-26')

    def test_annee(self):
        self.assertEqual(self.exp.expand(u'{annee}'), u'2026')

    def test_mois(self):
        self.assertEqual(self.exp.expand(u'{mois}'), u'07')

    def test_jour(self):
        self.assertEqual(self.exp.expand(u'{jour}'), u'26')

    def test_composition_date(self):
        self.assertEqual(self.exp.expand(u'{annee}/{mois}/{jour}'), u'2026/07/26')


class TestTokenExpanderIndex(unittest.TestCase):
    def setUp(self):
        self.exp = TokenExpander(today=_DATE)

    def test_n_defaut(self):
        self.assertEqual(self.exp.expand(u'copie_{n}'), u'copie_1')

    def test_n_custom(self):
        self.assertEqual(self.exp.expand(u'copie_{n}', index=3), u'copie_3')

    def test_n_dans_phrase(self):
        self.assertEqual(self.exp.expand(u'Vue {n} du {date}', index=2),
                         u'Vue 2 du 2026-07-26')


class TestTokenExpanderContext(unittest.TestCase):
    def setUp(self):
        self.exp = TokenExpander(today=_DATE)

    def test_type_via_context(self):
        self.assertEqual(
            self.exp.expand(u'{type}_{n}', index=1, context={u'type': u'FloorPlan'}),
            u'FloorPlan_1')

    def test_token_inconnu_reste_intact(self):
        self.assertEqual(self.exp.expand(u'{inconnu}'), u'{inconnu}')

    def test_template_vide(self):
        self.assertEqual(self.exp.expand(u''), u'')

    def test_template_sans_token(self):
        self.assertEqual(self.exp.expand(u'Plan RDC'), u'Plan RDC')


class TestTokenExpanderAvailableTokens(unittest.TestCase):
    def test_liste_non_vide(self):
        tokens = TokenExpander.available_tokens()
        self.assertIn(u'{date}', tokens)
        self.assertIn(u'{n}', tokens)
        self.assertIn(u'{type}', tokens)


if __name__ == '__main__':
    unittest.main()
