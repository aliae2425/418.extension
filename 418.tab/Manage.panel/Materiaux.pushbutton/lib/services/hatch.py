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
# Les motifs de DESSIN sont en taille papier : un écart de 1/4" doit sortir à
# 1/4" de papier quelle que soit l'échelle de la vue. Une unité WPF vaut
# 1/96 de pouce, donc 96 unités par pouce de papier — soit 1152 par pied —
# donnent la TAILLE RÉELLE D'IMPRESSION. C'est le réglage fidèle : ce que
# montre l'aperçu est ce qui sortira sur la feuille. Une tuile de 150 unités
# couvre 40 mm de papier.
ECHELLE_DESSIN = 1152.0

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

# En dessous de cet écart en pixels, deux droites voisines se recouvrent : la
# famille ne se lit plus comme des traits mais comme un aplat de sa couleur.
# C'est aussi ce que fait Revit quand on dézoome — la hachure vire à l'aplat,
# elle ne s'éclaircit pas. On la dessine donc pleine plutôt que d'écarter
# artificiellement les droites : écarter mentirait sur la densité, et pour
# une famille seulement, ce qui déforme le motif entier.
ECART_ILLISIBLE = 1.5

# Garde-fou dur : une grille pathologique ne doit pas figer l'interface. Avec
# ECART_ILLISIBLE, une tuile devrait faire 600 unités de diagonale pour
# l'atteindre — c'est un filet, pas le mécanisme principal.
MAX_LIGNES_PAR_GRILLE = 400

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


class Famille(object):
    """Ce qu'il faut dessiner pour UNE famille de droites parallèles.

    `traits` : `(x1, y1, x2, y2, phase)`. `phase` est la distance parcourue le
    long de la droite depuis l'origine de la grille jusqu'au DÉBUT du segment
    découpé. Elle sert à caler les tirets : sans elle chaque droite
    recommencerait son motif au bord de la tuile, et un motif pointillé
    sortirait en escalier au lieu de s'aligner comme dans Revit.

    `aplat` : la famille est trop dense pour se résoudre en traits à cette
    échelle, il faut remplir la tuile de sa couleur (cf. ECART_ILLISIBLE).
    `ecart` : espacement des droites en pixels — il ne sert qu'à doser cet
    aplat, un motif serré à 60 % de couverture imprime en gris, pas en noir.
    """

    def __init__(self, traits=None, tirets=None, aplat=False, ecart=0.0):
        self.traits = traits or []
        self.tirets = tirets or []
        self.aplat = aplat
        self.ecart = ecart


def segments(grilles, largeur, hauteur, echelle):
    """Tous les segments (x1, y1, x2, y2), familles confondues.

    Raccourci de `par_grille()` pour qui n'a besoin ni des tirets ni des
    phases. Une famille rendue en aplat n'a aucun segment à donner.
    """
    sortie = []
    for famille in par_grille(grilles, largeur, hauteur, echelle):
        sortie.extend(trait[:4] for trait in famille.traits)
    return sortie


def par_grille(grilles, largeur, hauteur, echelle):
    """Une `Famille` par famille de droites.

    `grilles` : itérable de `Grille`. `echelle` : pixels par pied.
    Les droites sont découpées sur la tuile de `largeur`×`hauteur` ; celles
    qui la manquent sautent. Les tirets restent attachés à leur famille,
    chacune a les siens.
    """
    familles = []
    for grille in grilles or []:
        famille = _famille(grille, largeur, hauteur, echelle)
        if famille is not None:
            familles.append(famille)
    return familles


def _famille(grille, largeur, hauteur, echelle):
    """La `Famille` d'UNE grille, ou None si elle ne touche pas la tuile."""
    ecart = abs(grille.offset) * echelle
    dx = math.cos(grille.angle)
    dy = math.sin(grille.angle)
    nx, ny = -dy, dx                      # normale à la famille
    ox = grille.origine_u * echelle
    oy = grille.origine_v * echelle
    decalage = grille.shift * echelle     # appareillage (briques)

    if ecart <= 0.0:
        # Offset nul : il n'y a pas de famille, juste la droite d'origine.
        ecart = math.hypot(largeur, hauteur) + 1.0
    if ecart < ECART_ILLISIBLE:
        return Famille(aplat=True, ecart=ecart)

    # Bande de k à couvrir : projeter les 4 coins de la tuile sur la
    # normale, et compter les droites entre les deux extrêmes.
    origine_n = ox * nx + oy * ny
    projections = [x * nx + y * ny
                   for (x, y) in ((0.0, 0.0), (largeur, 0.0),
                                  (0.0, hauteur), (largeur, hauteur))]
    k_min = int(math.floor((min(projections) - origine_n) / ecart))
    k_max = int(math.ceil((max(projections) - origine_n) / ecart))
    if k_max - k_min > MAX_LIGNES_PAR_GRILLE:
        # Tronquer donnerait une tuile à moitié couverte, ce qui ne ressemble
        # à rien. Aplat, comme pour une famille illisible.
        return Famille(aplat=True, ecart=ecart)

    traits = []
    for k in range(k_min, k_max + 1):
        px = ox + nx * (k * ecart) + dx * (k * decalage)
        py = oy + ny * (k * ecart) + dy * (k * decalage)
        decoupe = _clip(px, py, dx, dy, largeur, hauteur)
        if decoupe is None:
            continue
        x1, y1, x2, y2 = decoupe
        traits.append((x1, y1, x2, y2, (x1 - px) * dx + (y1 - py) * dy))
    if not traits:
        return None
    return Famille(traits=traits, tirets=tirets_px(grille.tirets, echelle),
                   ecart=ecart)


def tirets_px(tirets, echelle):
    """Longueurs de tirets en pixels, ou [] si le trait doit rester plein.

    Revit note les blancs en négatif ; on ne garde que les longueurs, l'ordre
    trait/blanc/trait/blanc suffit.

    Une liste IMPAIRE commence et finit par le même genre de segment : au
    bouclage, le dernier se colle bout à bout avec le premier. On les FUSIONNE
    donc, au lieu de jeter le dernier — le jeter changerait la période du
    motif, donc son dessin (0,5/0,25/0,1 n'est pas 0,5/0,25).
    """
    bruts = [t for t in tirets or []]
    if len(bruts) < 2:
        # Un seul segment qui se répète, ou aucun : trait plein.
        return []
    if len(bruts) % 2:
        bruts[0] = bruts[0] + bruts.pop()
    longueurs = [abs(t) * echelle for t in bruts]
    # Sous ce seuil la période est un pointillé sub-pixel : ça se dessine
    # comme un gris sale et coûte un tiret tous les demi-pixels. Trait plein.
    if sum(longueurs) < PERIODE_TIRETS_MINI:
        return []
    return longueurs
