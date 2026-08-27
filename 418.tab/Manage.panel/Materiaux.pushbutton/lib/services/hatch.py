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

# Échelles pixels/pied.
#
# Les motifs de DESSIN sont en taille papier : un écart de 1/4" doit sortir
# à 1/4" de papier quelle que soit l'échelle de la vue. 576 px/pied = 48 px
# par pouce de papier, soit une vignette de 64 px large qui montre ~34 mm de
# papier — l'équivalent d'une petite zone de plan imprimé.
ECHELLE_DESSIN = 576.0

# Les motifs MODÈLE sont à l'échelle du bâtiment : un écart d'un pied sort à
# un pied DIVISÉ par l'échelle de la vue. La vignette n'a pas de vue, on en
# postule une — 1:50, la plus courante en plan d'étage.
ECHELLE_VUE = 50.0

# Échelles de vue proposées par l'aperçu comparatif de l'éditeur. La vignette
# des cards, elle, n'en montre qu'une (ECHELLE_VUE).
ECHELLES_APERCU = (20, 50, 100, 200)


def echelle_modele(echelle_vue=None):
    """Pixels/pied d'un motif MODÈLE vu à l'échelle 1:`echelle_vue`.

    `None` retombe sur `ECHELLE_VUE`. Un motif de DESSIN n'a pas d'équivalent :
    il est en taille papier, donc `ECHELLE_DESSIN` quelle que soit la vue —
    c'est toute la différence que l'aperçu multi-échelle donne à voir.
    """
    return ECHELLE_DESSIN / float(echelle_vue or ECHELLE_VUE)

# En dessous de cet écart, la vignette virerait au gris uni et coûterait des
# centaines de droites pour rien.
ESPACEMENT_MINI = 3.0

# Garde-fou dur : une grille pathologique ne doit pas figer l'interface.
MAX_LIGNES_PAR_GRILLE = 200

# Période trait+blanc en dessous de laquelle on trace plein (voir tirets_px).
PERIODE_TIRETS_MINI = 2.0


class Grille(object):
    """Une famille de droites parallèles — l'équivalent neutre d'une FillGrid.

    Distances en pieds (unité interne de Revit), angle en radians.
    `tirets` : longueurs alternées trait/blanc le long de la droite (comme
    `FillGrid.GetSegments()`), vide pour un trait plein.
    """

    def __init__(self, origine_u=0.0, origine_v=0.0, angle=0.0,
                 offset=0.0, shift=0.0, tirets=None):
        self.origine_u = origine_u
        self.origine_v = origine_v
        self.angle = angle
        self.offset = offset
        self.shift = shift
        self.tirets = list(tirets or [])


def depuis_fill_grid(fill_grid):
    """Convertit une `FillGrid` de l'API Revit en `Grille`."""
    origine = fill_grid.Origin
    try:
        tirets = list(fill_grid.GetSegments())
    except Exception:
        tirets = []
    return Grille(origine_u=origine.U, origine_v=origine.V,
                  angle=fill_grid.Angle, offset=fill_grid.Offset,
                  shift=fill_grid.Shift, tirets=tirets)


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
    """Tous les segments (x1, y1, x2, y2), familles confondues.

    Raccourci de `par_grille()` pour qui n'a pas besoin des tirets.
    """
    sortie = []
    for traits, _ in par_grille(grilles, largeur, hauteur, echelle):
        sortie.extend(traits)
    return sortie


def par_grille(grilles, largeur, hauteur, echelle):
    """Une entrée `(segments, tirets_px)` par famille de droites.

    `grilles` : itérable de `Grille`. `echelle` : pixels par pied.
    Les droites sont découpées sur la tuile de `largeur`×`hauteur` ; celles
    qui la manquent sautent. `tirets_px` est vide pour un trait plein — les
    tirets restent attachés à leur famille, chacune a les siens.
    """
    familles = []
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

        traits = []
        for k in range(k_min, k_max + 1):
            px = ox + nx * (k * ecart) + dx * (k * decalage)
            py = oy + ny * (k * ecart) + dy * (k * decalage)
            decoupe = _clip(px, py, dx, dy, largeur, hauteur)
            if decoupe is not None:
                traits.append(decoupe)
        if traits:
            familles.append((traits, tirets_px(grille.tirets, echelle)))
    return familles


def tirets_px(tirets, echelle):
    """Longueurs de tirets en pixels, ou [] si le trait doit rester plein.

    Revit note les blancs en négatif ; on ne garde que les longueurs, l'ordre
    trait/blanc/trait/blanc suffit. Une liste impaire est tronquée : un motif
    doit alterner par paires pour se répéter.
    """
    longueurs = [abs(t) * echelle for t in tirets or []]
    if len(longueurs) % 2:
        longueurs = longueurs[:-1]
    if not longueurs:
        return []
    # Sous ce seuil la période est un pointillé sub-pixel : ça se dessine
    # comme un gris sale et coûte un tiret tous les demi-pixels. Trait plein.
    if sum(longueurs) < PERIODE_TIRETS_MINI:
        return []
    return longueurs
