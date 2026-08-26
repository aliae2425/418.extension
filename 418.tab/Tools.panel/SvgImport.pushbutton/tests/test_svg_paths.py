# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.svg_paths import (IDENTITE, appliquer, cadrer, chemin_depuis_forme,
                           lire_svg, multiplier, parser_transform)


def _ecrire_svg(contenu):
    fd, chemin = tempfile.mkstemp(suffix='.svg')
    with os.fdopen(fd, 'wb') as f:
        f.write(contenu.encode('utf-8'))
    return chemin


class TestMatrices(unittest.TestCase):
    def test_translate_puis_scale_ordre_svg(self):
        # "translate(10,0) scale(2)" : le point est mis à l'échelle EN PREMIER.
        m = parser_transform('translate(10,0) scale(2)')
        self.assertEqual(appliquer(m, 5, 3), (20.0, 6.0))

    def test_scale_puis_translate(self):
        m = parser_transform('scale(2) translate(10,0)')
        self.assertEqual(appliquer(m, 5, 3), (30.0, 6.0))

    def test_rotate_autour_dun_centre(self):
        x, y = appliquer(parser_transform('rotate(90, 1, 1)'), 2, 1)
        self.assertAlmostEqual(x, 1.0)
        self.assertAlmostEqual(y, 2.0)

    def test_matrix_et_transform_vide(self):
        self.assertEqual(appliquer(parser_transform('matrix(1,0,0,1,4,5)'), 0, 0),
                         (4.0, 5.0))
        self.assertEqual(parser_transform(None), IDENTITE)
        self.assertEqual(parser_transform('rotate()'), IDENTITE)

    def test_composition_imbriquee(self):
        parent = parser_transform('translate(100,100)')
        enfant = parser_transform('scale(0.5)')
        self.assertEqual(appliquer(multiplier(parent, enfant), 10, 10),
                         (105.0, 105.0))


class TestFormes(unittest.TestCase):
    def test_rect_ferme_sur_quatre_coins(self):
        d = chemin_depuis_forme('rect', {'x': '1', 'y': '2',
                                         'width': '10', 'height': '4'})
        self.assertEqual(d, 'M 1.0 2.0 L 11.0 2.0 L 11.0 6.0 L 1.0 6.0 Z')

    def test_rect_sans_dimension_ignore(self):
        self.assertIsNone(chemin_depuis_forme('rect', {'width': '0'}))

    def test_polygon_ferme_polyline_non(self):
        pts = {'points': '0,0 10,0 10,10'}
        self.assertTrue(chemin_depuis_forme('polygon', pts).endswith(' Z'))
        self.assertFalse(chemin_depuis_forme('polyline', pts).endswith(' Z'))

    def test_polyline_conserve_tous_les_points(self):
        d = chemin_depuis_forme('polyline', {'points': '0,0 1,2 3,4'})
        self.assertEqual(d, 'M 0.0 0.0 L 1.0 2.0 3.0 4.0')

    def test_line_et_circle(self):
        self.assertEqual(
            chemin_depuis_forme('line', {'x1': '0', 'y1': '0', 'x2': '5',
                                         'y2': '-5'}),
            'M 0.0 0.0 L 5.0 -5.0')
        d = chemin_depuis_forme('circle', {'cx': '10', 'cy': '10', 'r': '4'})
        self.assertTrue(d.startswith('M 6.0 10.0 A 4.0 4.0'))

    def test_forme_non_geree(self):
        self.assertIsNone(chemin_depuis_forme('text', {'x': '0'}))


class TestCadrer(unittest.TestCase):
    # bornes = (min_x, min_y, max_x, max_y) : tracé de 200 x 100 unités.
    BORNES = (100.0, 50.0, 300.0, 150.0)

    def test_largeur_respectee(self):
        echelle, vers_mm = cadrer(self.BORNES, 80.0)
        self.assertAlmostEqual(echelle, 0.4)
        self.assertAlmostEqual(vers_mm(300.0, 50.0)[0], 80.0)

    def test_coin_haut_gauche_a_l_origine(self):
        _, vers_mm = cadrer(self.BORNES, 80.0)
        self.assertEqual(vers_mm(100.0, 50.0), (0.0, 0.0))

    def test_axe_y_retourne(self):
        # Le bas du SVG (max_y) doit devenir l'ordonnée la PLUS BASSE.
        _, vers_mm = cadrer(self.BORNES, 80.0)
        self.assertAlmostEqual(vers_mm(100.0, 150.0)[1], -40.0)
        self.assertLess(vers_mm(100.0, 150.0)[1], vers_mm(100.0, 50.0)[1])

    def test_ratio_conserve(self):
        _, vers_mm = cadrer(self.BORNES, 80.0)
        largeur = vers_mm(300.0, 50.0)[0] - vers_mm(100.0, 50.0)[0]
        hauteur = vers_mm(100.0, 50.0)[1] - vers_mm(100.0, 150.0)[1]
        self.assertAlmostEqual(largeur / hauteur, 200.0 / 100.0)


class TestLecture(unittest.TestCase):
    def test_traces_groupes_defs_et_invisibles(self):
        chemin = _ecrire_svg("""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs><path d="M 0 0 L 1 1"/></defs>
  <!-- commentaire -->
  <g transform="translate(10,20)">
    <path d="M 0 0 L 5 0"/>
    <g style="display: none"><path d="M 0 0 L 9 9"/></g>
  </g>
  <rect x="0" y="0" width="2" height="2" display="none"/>
  <line x1="0" y1="0" x2="1" y2="0"/>
</svg>""")
        try:
            traces = lire_svg(chemin)
        finally:
            os.remove(chemin)

        self.assertEqual(len(traces), 2, traces)
        d_path, m_path = traces[0]
        self.assertEqual(d_path, 'M 0 0 L 5 0')
        self.assertEqual(appliquer(m_path, 0, 0), (10.0, 20.0))
        self.assertEqual(appliquer(traces[1][1], 0, 0), (0.0, 0.0))

    def test_svg_sans_namespace(self):
        chemin = _ecrire_svg('<svg><path d="M 0 0 L 1 1"/></svg>')
        try:
            self.assertEqual(len(lire_svg(chemin)), 1)
        finally:
            os.remove(chemin)


if __name__ == '__main__':
    unittest.main()
