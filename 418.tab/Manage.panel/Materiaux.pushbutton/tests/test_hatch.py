# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import math
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.services import hatch


class TestClip(unittest.TestCase):
    def test_droite_horizontale_traverse_la_tuile(self):
        seg = hatch._clip(0.0, 10.0, 1.0, 0.0, 64.0, 32.0)
        self.assertEqual(seg, (0.0, 10.0, 64.0, 10.0))

    def test_droite_hors_tuile_est_rejetee(self):
        self.assertIsNone(hatch._clip(0.0, 99.0, 1.0, 0.0, 64.0, 32.0))

    def test_diagonale_reste_dans_la_tuile(self):
        x1, y1, x2, y2 = hatch._clip(0.0, 0.0, 1.0, 1.0, 64.0, 32.0)
        for v, borne in ((x1, 64.0), (x2, 64.0), (y1, 32.0), (y2, 32.0)):
            self.assertGreaterEqual(v, -1e-6)
            self.assertLessEqual(v, borne + 1e-6)


class TestSegments(unittest.TestCase):
    def test_grille_horizontale_espacee_regulierement(self):
        # offset 10 px après échelle : 32 px de haut -> 4 droites (0,10,20,30)
        grille = hatch.Grille(angle=0.0, offset=1.0)
        segs = hatch.segments([grille], 64.0, 32.0, echelle=10.0)
        ordonnees = sorted(round(s[1], 6) for s in segs)
        self.assertEqual(ordonnees, [0.0, 10.0, 20.0, 30.0])
        for (x1, _, x2, _) in segs:
            self.assertAlmostEqual(x1, 0.0)
            self.assertAlmostEqual(x2, 64.0)

    def test_espacement_minimal_borne_le_nombre_de_droites(self):
        # offset ridicule -> retombe sur ESPACEMENT_MINI, pas sur 10000 droites
        grille = hatch.Grille(angle=0.0, offset=1e-6)
        segs = hatch.segments([grille], 64.0, 32.0, echelle=1.0)
        self.assertLessEqual(len(segs), int(32.0 / hatch.ESPACEMENT_MINI) + 2)

    def test_deux_grilles_croisees_donnent_les_deux_familles(self):
        croix = [hatch.Grille(angle=0.0, offset=1.0),
                 hatch.Grille(angle=math.pi / 2.0, offset=1.0)]
        segs = hatch.segments(croix, 64.0, 32.0, echelle=10.0)
        horizontales = [s for s in segs if abs(s[1] - s[3]) < 1e-6]
        verticales = [s for s in segs if abs(s[0] - s[2]) < 1e-6]
        self.assertTrue(horizontales)
        self.assertTrue(verticales)
        self.assertEqual(len(segs), len(horizontales) + len(verticales))

    def test_sans_grille_aucun_segment(self):
        self.assertEqual(hatch.segments([], 64.0, 32.0, echelle=10.0), [])
        self.assertEqual(hatch.segments(None, 64.0, 32.0, echelle=10.0), [])

    def test_grille_a_45_degres_reste_dans_la_tuile(self):
        grille = hatch.Grille(angle=math.pi / 4.0, offset=0.5)
        segs = hatch.segments([grille], 64.0, 32.0, echelle=20.0)
        self.assertTrue(segs)
        for (x1, y1, x2, y2) in segs:
            for v, borne in ((x1, 64.0), (x2, 64.0), (y1, 32.0), (y2, 32.0)):
                self.assertGreaterEqual(v, -1e-6)
                self.assertLessEqual(v, borne + 1e-6)


if __name__ == '__main__':
    unittest.main()
