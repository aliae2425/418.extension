# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.align import deltas_alignement, deltas_distribution


class TestAlignement(unittest.TestCase):

    def test_min_cale_tout_le_monde_sur_la_borne_basse(self):
        bornes = [(0.0, 2.0), (5.0, 6.0), (-3.0, 1.0)]
        deltas = deltas_alignement(bornes, 'min')
        self.assertEqual(deltas, [-3.0, -8.0, 0.0])
        self.assertEqual([b[0] + d for b, d in zip(bornes, deltas)], [-3.0] * 3)

    def test_max_cale_tout_le_monde_sur_la_borne_haute(self):
        bornes = [(0.0, 2.0), (5.0, 6.0), (-3.0, 1.0)]
        deltas = deltas_alignement(bornes, 'max')
        self.assertEqual([b[1] + d for b, d in zip(bornes, deltas)], [6.0] * 3)

    def test_les_tailles_sont_preservees(self):
        bornes = [(0.0, 10.0), (5.0, 6.0)]
        for op in ('min', 'max'):
            deltas = deltas_alignement(bornes, op)
            for (mini, maxi), d in zip(bornes, deltas):
                self.assertAlmostEqual((maxi + d) - (mini + d), maxi - mini)


class TestDistribution(unittest.TestCase):

    def test_espacement_regulier_extremes_fixes(self):
        centres = [0.0, 1.0, 9.0, 10.0]
        deltas = deltas_distribution(centres)
        finaux = sorted(c + d for c, d in zip(centres, deltas))
        self.assertEqual(finaux, [0.0, 10.0 / 3, 20.0 / 3, 10.0])
        self.assertEqual(deltas[0], 0.0)   # extrême bas immobile
        self.assertEqual(deltas[3], 0.0)   # extrême haut immobile

    def test_ordre_desordonne_respecte(self):
        centres = [10.0, 0.0, 1.0]
        deltas = deltas_distribution(centres)
        self.assertEqual([c + d for c, d in zip(centres, deltas)], [10.0, 0.0, 5.0])

    def test_moins_de_trois_elements_ne_bouge_rien(self):
        self.assertEqual(deltas_distribution([3.0, 8.0]), [0.0, 0.0])
        self.assertEqual(deltas_distribution([]), [])


if __name__ == '__main__':
    unittest.main()
