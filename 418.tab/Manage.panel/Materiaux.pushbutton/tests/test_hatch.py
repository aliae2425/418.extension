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

    def test_une_famille_illisible_passe_en_aplat_sans_segment(self):
        # Offset ridicule : Revit affiche un aplat quand la hachure ne se
        # résout plus. Écarter les droites mentirait sur la densité.
        grille = hatch.Grille(angle=0.0, offset=1e-6)
        famille = hatch.par_grille([grille], 64.0, 32.0, echelle=1.0)[0]
        self.assertTrue(famille.aplat)
        self.assertEqual(famille.traits, [])
        self.assertEqual(hatch.segments([grille], 64.0, 32.0, echelle=1.0), [])

    def test_laplat_garde_lecart_pour_se_doser(self):
        # L'adaptateur WPF en tire un taux de couverture : un motif à 60 %
        # imprime gris, pas noir.
        grille = hatch.Grille(angle=0.0, offset=0.12)
        famille = hatch.par_grille([grille], 64.0, 32.0, echelle=10.0)[0]
        self.assertTrue(famille.aplat)
        self.assertAlmostEqual(famille.ecart, 1.2)

    def test_deux_familles_de_densites_differentes_gardent_leur_rapport(self):
        # L'ancien plancher d'espacement rapprochait la famille lâche de la
        # serrée : le motif changeait de caractère. Ici le rapport tient.
        serree = hatch.Grille(angle=0.0, offset=0.5)
        lache = hatch.Grille(angle=0.0, offset=2.0)
        familles = hatch.par_grille([serree, lache], 64.0, 96.0, echelle=10.0)
        self.assertEqual(len(familles[0].traits), 4 * len(familles[1].traits))

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


class TestTirets(unittest.TestCase):
    def test_les_longueurs_passent_en_pixels_les_blancs_en_positif(self):
        # Revit note les blancs en négatif : 0.5 pied de trait, 0.25 de blanc
        self.assertEqual(hatch.tirets_px([0.5, -0.25], echelle=100.0),
                         [50.0, 25.0])

    def test_liste_impaire_fusionnee_et_non_tronquee(self):
        # Au bouclage, le dernier trait se colle au premier : 0,5 puis 0,1
        # font un trait de 0,6. Tronquer donnerait 50/25 — une autre période,
        # donc un autre dessin.
        self.assertEqual(hatch.tirets_px([0.5, -0.25, 0.1], echelle=100.0),
                         [60.0, 25.0])

    def test_un_seul_segment_qui_se_repete_est_un_trait_plein(self):
        self.assertEqual(hatch.tirets_px([0.5], echelle=100.0), [])

    def test_periode_sub_pixel_donne_un_trait_plein(self):
        self.assertEqual(hatch.tirets_px([0.001, -0.001], echelle=100.0), [])

    def test_sans_tirets_trait_plein(self):
        self.assertEqual(hatch.tirets_px([], echelle=100.0), [])
        self.assertEqual(hatch.tirets_px(None, echelle=100.0), [])


class TestParGrille(unittest.TestCase):
    def test_une_entree_par_famille_avec_ses_tirets(self):
        pleine = hatch.Grille(angle=0.0, offset=1.0)
        pointillee = hatch.Grille(angle=math.pi / 2.0, offset=1.0,
                                  tirets=[0.5, -0.5])
        familles = hatch.par_grille([pleine, pointillee], 64.0, 32.0,
                                    echelle=10.0)
        self.assertEqual(len(familles), 2)
        self.assertEqual(familles[0].tirets, [])
        self.assertEqual(familles[1].tirets, [5.0, 5.0])

    def test_segments_reste_la_somme_des_familles(self):
        grilles = [hatch.Grille(angle=0.0, offset=1.0),
                   hatch.Grille(angle=math.pi / 2.0, offset=1.0)]
        familles = hatch.par_grille(grilles, 64.0, 32.0, echelle=10.0)
        total = sum(len(famille.traits) for famille in familles)
        self.assertEqual(len(hatch.segments(grilles, 64.0, 32.0, 10.0)), total)


class TestPhaseDesTirets(unittest.TestCase):
    """La phase cale le motif de tirets sur l'origine de la grille, pas sur
    le bord de la tuile — sinon un pointillé sort en escalier."""

    def test_origine_sur_le_bord_donne_une_phase_nulle(self):
        grille = hatch.Grille(angle=0.0, offset=1.0)
        famille = hatch.par_grille([grille], 64.0, 32.0, echelle=10.0)[0]
        for trait in famille.traits:
            self.assertAlmostEqual(trait[4], 0.0)

    def test_origine_decalee_recule_la_phase_dautant(self):
        # Origine à 3 px : la tuile coupe chaque droite 3 px AVANT elle.
        grille = hatch.Grille(angle=0.0, offset=1.0, origine_u=0.3)
        famille = hatch.par_grille([grille], 64.0, 32.0, echelle=10.0)[0]
        for trait in famille.traits:
            self.assertAlmostEqual(trait[4], -3.0)

    def test_lappareillage_decale_une_droite_sur_deux(self):
        # `shift` fait glisser chaque droite le long d'elle-même : c'est ce
        # qui donne l'appareillage des briques. Les phases doivent donc
        # varier d'une droite à l'autre.
        grille = hatch.Grille(angle=0.0, offset=1.0, shift=0.5)
        famille = hatch.par_grille([grille], 64.0, 32.0, echelle=10.0)[0]
        phases = sorted(set(round(trait[4], 6) for trait in famille.traits))
        self.assertGreater(len(phases), 1)
        self.assertAlmostEqual(phases[1] - phases[0], 5.0)


if __name__ == '__main__':
    unittest.main()
