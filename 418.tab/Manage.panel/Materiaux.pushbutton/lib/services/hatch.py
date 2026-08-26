# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import math

# Géométrie d'un motif de remplissage Revit, en Python pur : aucune référence
# à l'API Revit ni à WPF, donc testable hors Revit.
#
# Une FillGrid Revit décrit une FAMILLE de droites parallèles :
#   origine (u, v), angle (radians), offset (écart perpendiculaire entre deux
#   droites), shift (décalage de chaque droite le long de sa direction —
#   c'est lui qui donne l'appareillage des motifs de brique).
# `segments()` matérialise cette famille sur une tuile de w×h pixels.

# Échelles pixels/pied. Les motifs de DESSIN sont exprimés en taille papier
# (un écart courant vaut 1/4" ≈ 0.0208 pied) alors que les motifs MODÈLE sont
# à l'échelle du bâtiment (un écart courant vaut un pied). D'où deux facteurs
# très différents pour obtenir une vignette lisible dans les deux cas.
# ponytail: calées à l'œil sur les motifs livrés avec Revit FR. Si une vignette
# sort trop dense ou trop vide sur une vraie maquette, c'est ici que ça se règle.
ECHELLE_DESSIN = 576.0
ECHELLE_MODELE = 16.0

# En dessous de cet écart, la vignette virerait au gris uni et coûterait des
# centaines de droites pour rien.
ESPACEMENT_MINI = 3.0

# Garde-fou dur : une grille pathologique ne doit pas figer l'interface.
MAX_LIGNES_PAR_GRILLE = 200


class Grille(object):
    """Une famille de droites parallèles — l'équivalent neutre d'une FillGrid.

    Distances en pieds (unité interne de Revit), angle en radians.
    """

    def __init__(self, origine_u=0.0, origine_v=0.0, angle=0.0,
                 offset=0.0, shift=0.0):
        self.origine_u = origine_u
        self.origine_v = origine_v
        self.angle = angle
        self.offset = offset
        self.shift = shift


def depuis_fill_grid(fill_grid):
    """Convertit une `FillGrid` de l'API Revit en `Grille`."""
    origine = fill_grid.Origin
    return Grille(origine_u=origine.U, origine_v=origine.V,
                  angle=fill_grid.Angle, offset=fill_grid.Offset,
                  shift=fill_grid.Shift)


def _clip(px, py, dx, dy, largeur, hauteur):
    """Liang-Barsky : découpe la droite (px,py)+t·(dx,dy) sur la tuile.

    Retourne (x1, y1, x2, y2) ou None si la droite manque la tuile.
    """
    t0, t1 = -1e9, 1e9
    for p, q in ((-dx, px), (dx, largeur - px), (-dy, py), (dy, hauteur - py)):
        if p == 0.0:
            if q < 0.0:
                return None          # parallèle et hors bande
            continue
        r = q / p
        if p < 0.0:
            if r > t1:
                return None
            if r > t0:
                t0 = r
        else:
            if r < t0:
                return None
            if r < t1:
                t1 = r
    return (px + t0 * dx, py + t0 * dy, px + t1 * dx, py + t1 * dy)


def segments(grilles, largeur, hauteur, echelle):
    """Segments (x1, y1, x2, y2) à tracer dans une tuile de `largeur`×`hauteur`.

    `grilles` : itérable de `Grille`. `echelle` : pixels par pied.
    Les droites sont découpées sur la tuile ; celles qui la manquent sautent.
    """
    sortie = []
    for grille in grilles or []:
        ecart = abs(grille.offset) * echelle
        if ecart < ESPACEMENT_MINI:
            ecart = ESPACEMENT_MINI
        dx = math.cos(grille.angle)
        dy = math.sin(grille.angle)
        nx, ny = -dy, dx                      # normale à la famille
        ox = grille.origine_u * echelle
        oy = grille.origine_v * echelle
        decalage = grille.shift * echelle     # appareillage (briques)

        # Bande de k à couvrir : projeter les 4 coins de la tuile sur la
        # normale, et compter les droites entre les deux extrêmes.
        origine_n = ox * nx + oy * ny
        projections = [x * nx + y * ny
                       for (x, y) in ((0.0, 0.0), (largeur, 0.0),
                                      (0.0, hauteur), (largeur, hauteur))]
        k_min = int(math.floor((min(projections) - origine_n) / ecart))
        k_max = int(math.ceil((max(projections) - origine_n) / ecart))
        if k_max - k_min > MAX_LIGNES_PAR_GRILLE:
            k_max = k_min + MAX_LIGNES_PAR_GRILLE

        for k in range(k_min, k_max + 1):
            px = ox + nx * (k * ecart) + dx * (k * decalage)
            py = oy + ny * (k * ecart) + dy * (k * decalage)
            decoupe = _clip(px, py, dx, dy, largeur, hauteur)
            if decoupe is not None:
                sortie.append(decoupe)
    return sortie

# ponytail: les tirets (FillGrid.GetSegments()) sont ignorés — un motif
# pointillé se dessine plein dans la vignette. Invisible à 64 px de large ;
# à reprendre le jour où les vignettes grandissent.
