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

    def test_centre_cale_les_centres_sur_le_milieu_de_letendue(self):
        bornes = [(0.0, 2.0), (5.0, 6.0), (-3.0, 1.0)]   # étendue globale -3 -> 6
        deltas = deltas_alignement(bornes, 'centre')
        centres = [(b[0] + b[1]) / 2 + d for b, d in zip(bornes, deltas)]
        self.assertEqual(centres, [1.5] * 3)

    def test_centre_ne_bouge_pas_une_selection_deja_centree(self):
        bornes = [(-1.0, 1.0), (-2.0, 2.0)]
        self.assertEqual(deltas_alignement(bornes, 'centre'), [0.0, 0.0])

    def test_les_tailles_sont_preservees(self):
        bornes = [(0.0, 10.0), (5.0, 6.0)]
        for op in ('min', 'max', 'centre'):
            deltas = deltas_alignement(bornes, op)
            for (mini, maxi), d in zip(bornes, deltas):
                self.assertAlmostEqual((maxi + d) - (mini + d), maxi - mini)


class TestAlignementAvecEpingles(unittest.TestCase):

    def test_centre_sur_lunique_epingle(self):
        # (0,2) épinglé -> centre 1.0 ; le libre (10,14) doit venir dessus
        bornes = [(0.0, 2.0), (10.0, 14.0)]
        deltas = deltas_alignement(bornes, 'centre', [True, False])
        self.assertEqual(deltas[0], 0.0)
        self.assertEqual((bornes[1][0] + bornes[1][1]) / 2 + deltas[1], 1.0)

    def test_min_se_cale_sur_lepingle_pas_sur_lextreme(self):
        bornes = [(5.0, 6.0), (-3.0, 1.0), (0.0, 2.0)]
        deltas = deltas_alignement(bornes, 'min', [True, False, False])
        self.assertEqual(deltas[0], 0.0)
        self.assertEqual([b[0] + d for b, d in zip(bornes, deltas)], [5.0] * 3)

    def test_max_se_cale_sur_lepingle(self):
        bornes = [(5.0, 6.0), (-3.0, 1.0), (0.0, 2.0)]
        deltas = deltas_alignement(bornes, 'max', [False, False, True])
        self.assertEqual(deltas[2], 0.0)
        self.assertEqual([b[1] + d for b, d in zip(bornes, deltas)], [2.0] * 3)

    def test_plusieurs_epingles_donnent_letendue_de_reference(self):
        bornes = [(0.0, 2.0), (8.0, 10.0), (100.0, 120.0)]
        deltas = deltas_alignement(bornes, 'centre', [True, True, False])
        self.assertEqual(deltas[:2], [0.0, 0.0])          # les 2 ancres immobiles
        self.assertEqual(110.0 + deltas[2], 5.0)          # milieu de 0 -> 10

    def test_aucun_epingle_comportement_inchange(self):
        bornes = [(0.0, 2.0), (5.0, 6.0), (-3.0, 1.0)]
        for op in ('min', 'max', 'centre'):
            self.assertEqual(deltas_alignement(bornes, op, [False] * 3),
                             deltas_alignement(bornes, op))


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

    def test_epingle_au_milieu_est_un_point_fixe(self):
        # 0 et 12 extrêmes, 4 épinglé : 1 libre entre 0 et 4, 1 libre entre 4 et 12
        centres = [0.0, 1.0, 4.0, 11.0, 12.0]
        deltas = deltas_distribution(centres, [False, False, True, False, False])
        self.assertEqual(deltas[2], 0.0)                              # ancre immobile
        finaux = [c + d for c, d in zip(centres, deltas)]
        self.assertEqual(finaux, [0.0, 2.0, 4.0, 8.0, 12.0])

    def test_epingles_adjacents_ne_bougent_pas(self):
        centres = [0.0, 5.0, 10.0]
        deltas = deltas_distribution(centres, [True, True, True])
        self.assertEqual(deltas, [0.0, 0.0, 0.0])

    def test_aucun_epingle_comportement_inchange(self):
        centres = [0.0, 1.0, 9.0, 10.0]
        self.assertEqual(deltas_distribution(centres, [False] * 4),
                         deltas_distribution(centres))


if __name__ == '__main__':
    unittest.main()
