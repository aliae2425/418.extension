# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.token_expander import TokenExpander


class TestTokenExpander(unittest.TestCase):

    def test_token_inconnu_reste_intact(self):
        self.assertEqual(TokenExpander().expand(u'{inconnu}'), u'{inconnu}')

    def test_index_alimente_n(self):
        self.assertEqual(TokenExpander().expand(u'p{n}', index=2), u'p2')

    def test_rang_alimente_i(self):
        self.assertEqual(TokenExpander().expand(u'{n}-{i}', index=2, rang=7), u'2-7')

    def test_i_sans_rang_retombe_sur_index(self):
        self.assertEqual(TokenExpander().expand(u'{i}', index=3), u'3')

    def test_context_resout_token_custom(self):
        out = TokenExpander().expand(u'{type}', context={u'type': u'Plan'})
        self.assertEqual(out, u'Plan')


if __name__ == '__main__':
    unittest.main()
