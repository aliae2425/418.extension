# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import math
import os
import re
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.services import hatch, hatch_svg


class TestVignette(unittest.TestCase):
    def test_tuile_vide_donne_du_papier_blanc(self):
        svg = hatch_svg.vignette([])
        self.assertIn(u'viewBox="0 0 64 28"', svg)
        self.assertIn(u'fill="#FFFFFF"', svg)

    def test_le_miroir_vertical_est_pose(self):
        # Revit compte V vers le haut, l'écran y vers le bas : sans ce
        # miroir, toutes les hachures obliques penchent du mauvais côté.
        self.assertIn(u'translate(0,28) scale(1,-1)', hatch_svg.vignette([]))

    def test_couche_absente_ne_dessine_rien(self):
        # `None` = pas de motif, et c'est différent d'un motif « Uni ».
        self.assertEqual(hatch_svg.vignette([None]).count(u'<rect'), 1)

    def test_motif_uni_remplit_la_tuile_de_sa_couleur(self):
        couche = hatch.Couche(est_uni=True, rgb=(176, 65, 62))
        self.assertIn(u'fill="#B0413E"', hatch_svg.vignette([couche]))

    def test_les_couches_sont_empilees_dans_l_ordre_recu(self):
        # Arrière-plan d'abord : un fond uni gris surmonté de briques doit
        # sortir gris ET briques, comme dans la maquette.
        fond = hatch.Couche(est_uni=True, rgb=(10, 10, 10))
        dessus = hatch.Couche(grilles=[hatch.Grille(angle=0.0, offset=0.01)],
                              rgb=(200, 200, 200))
        svg = hatch_svg.vignette([fond, dessus])
        self.assertLess(svg.index(u'#0A0A0A'), svg.index(u'#C8C8C8'))


class TestTraits(unittest.TestCase):
    def _svg_grille(self, **kwargs):
        couche = hatch.Couche(grilles=[hatch.Grille(**kwargs)], rgb=(0, 0, 0))
        return hatch_svg.vignette([couche])

    def test_une_famille_horizontale_donne_un_chemin(self):
        svg = self._svg_grille(angle=0.0, offset=0.01)
        chemins = re.findall(r'<path d="([^"]+)"', svg)
        self.assertEqual(len(chemins), 1)
        self.assertIn(u'M0 ', chemins[0])
        self.assertIn(u'L64 ', chemins[0])

    def test_les_tirets_sortent_en_pointille(self):
        # Les longueurs SVG sont en PIXELS, pas en multiples de l'épaisseur
        # comme le DashStyle de WPF : rien à diviser ici.
        svg = self._svg_grille(angle=0.0, offset=0.01,
                               tirets=[0.02, -0.01])
        self.assertIn(u'stroke-dasharray=', svg)
        self.assertIn(u'stroke-linecap="butt"', svg)

    def test_trait_plein_sans_pointille(self):
        self.assertNotIn(u'stroke-dasharray',
                         self._svg_grille(angle=0.0, offset=0.01))

    def test_famille_illisible_vire_a_l_aplat_dose(self):
        # Sous ECART_ILLISIBLE les droites se recouvrent : Revit vire à
        # l'aplat quand on dézoome, il n'éclaircit pas. L'opacité dose la
        # couverture — des traits de 0,8 espacés de 1,3 impriment gris.
        svg = self._svg_grille(angle=0.0, offset=0.001)
        self.assertNotIn(u'<path', svg)
        self.assertIn(u'opacity=', svg)

    def test_motif_de_modele_suit_l_echelle_de_vue(self):
        # Un motif de MODÈLE est à l'échelle du bâtiment : il se densifie
        # quand la vue s'éloigne. Un motif de dessin, lui, est en taille
        # papier et ne bouge pas — c'est toute la différence que montre
        # l'aperçu comparatif de l'éditeur.
        modele = hatch.Couche(grilles=[hatch.Grille(angle=0.0, offset=0.5)],
                              est_modele=True, rgb=(0, 0, 0))
        pres = hatch_svg.vignette([modele], echelle_vue=20)
        loin = hatch_svg.vignette([modele], echelle_vue=200)
        self.assertGreater(loin.count(u'M0 '), pres.count(u'M0 '))

    def test_motif_de_dessin_ignore_l_echelle_de_vue(self):
        dessin = hatch.Couche(grilles=[hatch.Grille(angle=0.0, offset=0.02)],
                              rgb=(0, 0, 0))
        self.assertEqual(hatch_svg.vignette([dessin], echelle_vue=20),
                         hatch_svg.vignette([dessin], echelle_vue=200))


class TestNombres(unittest.TestCase):
    def test_les_decimales_inutiles_sautent(self):
        # Une vignette de brique compte quelques centaines de segments, et il
        # y en a deux par matériau : « 12 » plutôt que « 12.0 ».
        self.assertEqual(hatch_svg._n(12.0), u'12')
        self.assertEqual(hatch_svg._n(12.25), u'12.2')
        self.assertEqual(hatch_svg._n(0.0), u'0')

    def test_couleur_absente_vaut_noir(self):
        self.assertEqual(hatch_svg.hexa(None), u'#000000')


class TestInjection(unittest.TestCase):
    def test_un_nom_de_motif_ne_passe_pas_dans_le_svg(self):
        # Le SVG est injecté dans la page par `innerHTML` : il ne doit porter
        # que de la géométrie. Un nom de motif venu d'une maquette tierce n'a
        # rien à y faire — il voyage à part, par `textContent`.
        couche = hatch.Couche(nom=u'<script>alert(1)</script>', est_uni=True,
                              rgb=(0, 0, 0))
        self.assertNotIn(u'script', hatch_svg.vignette([couche]))


if __name__ == '__main__':
    unittest.main()
