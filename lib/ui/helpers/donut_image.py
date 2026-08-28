# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import math

# Anneau (torus) de l'onglet Audit : parts -> DrawingImage bindable.
# Même geste que `hatch_image` : la géométrie est du Python pur (testable hors
# Revit), les imports WPF sont gardés pour que le module s'importe quand même.
#
# Un segment n'est PAS un secteur d'anneau construit par quatre arcs : c'est un
# simple arc de cercle TRACÉ avec une plume épaisse. Le trait donne la bande,
# ce qui économise toute la géométrie de couronne.

try:
    from System.Windows import Point, Rect, Size
    from System.Windows.Media import (ArcSegment, Brushes, Color, DrawingGroup,
                                      DrawingImage, EllipseGeometry,
                                      GeometryDrawing, PathFigure, PathGeometry,
                                      Pen, PenLineCap, RectangleGeometry,
                                      SolidColorBrush, SweepDirection)
except Exception:
    Point = Rect = Size = ArcSegment = Brushes = Color = None
    DrawingGroup = DrawingImage = EllipseGeometry = GeometryDrawing = None
    PathFigure = PathGeometry = Pen = PenLineCap = RectangleGeometry = None
    SolidColorBrush = SweepDirection = None

try:
    from ui.helpers.DarkMode import is_dark
except Exception:
    try:
        from lib.ui.helpers.DarkMode import is_dark
    except Exception:
        def is_dark():
            return False

COTE = 140.0            # côté de l'image carrée
RAYON = 52.0            # rayon de la LIGNE MOYENNE de la bande
EPAISSEUR = 20.0

#: Rôle -> (clair, sombre). Reprend les valeurs de Colors/ColorsDark : la
#: DrawingImage est construite en Python, elle ne peut pas aller chercher un
#: DynamicResource, mais les teintes doivent rester celles du thème.
#: 'sains' = SuccessBrush · 'doublons' = WarningBrush ·
#: 'sans_effet' = ErrorBrush · 'non_utilises' = TextDisabledBrush ·
#: 'piste' = fond de l'anneau.
PALETTE = {
    'sains': ((46, 158, 79), (86, 194, 113)),
    'doublons': ((184, 134, 11), (229, 169, 59)),
    'sans_effet': ((209, 52, 56), (209, 52, 56)),
    'non_utilises': ((157, 157, 157), (93, 93, 93)),
    'piste': ((229, 229, 229), (58, 64, 74)),
}


def couleur(role):
    """Triplet RGB du rôle, selon le thème actif."""
    clair, sombre = PALETTE[role]
    try:
        return sombre if is_dark() else clair
    except Exception:
        return clair


def hexa(rgb):
    """RGB -> '#RRGGBB', pour les pastilles de légende (bindées en Background)."""
    return u'#%02X%02X%02X' % tuple(rgb)


def arcs(portions):
    """Parts (0..1) -> [(angle_de_depart, balayage)] en degrés.

    Départ à midi (-90°), sens horaire. Les parts nulles ne produisent pas
    d'arc — un balayage de 0° ne dessine rien mais laisse une capsule de
    plume visible. Les parts sont prises telles quelles : c'est à l'appelant
    de fournir une partition qui somme à 1.
    """
    resultat = []
    angle = -90.0
    for portion in portions or []:
        balayage = 360.0 * max(0.0, float(portion))
        if balayage > 0.0:
            resultat.append((angle, balayage))
        angle += balayage
    return resultat


def torus(segments):
    """`segments` : itérable de (part 0..1, rgb). -> DrawingImage carrée.

    La piste complète est toujours tracée dessous : elle ferme l'anneau quand
    les parts ne somment pas à 1 et donne un visuel correct sur un modèle sans
    aucun matériau.
    """
    if DrawingImage is None:
        return None

    groupe = DrawingGroup()
    # Rectangle transparent : fige la taille de l'image, sinon WPF la recadre
    # sur l'étendue du seul tracé (même raison que le fond blanc des hachures).
    groupe.Children.Add(GeometryDrawing(
        Brushes.Transparent, None, RectangleGeometry(Rect(0, 0, COTE, COTE))))

    centre = Point(COTE / 2.0, COTE / 2.0)
    groupe.Children.Add(GeometryDrawing(
        None, _plume(couleur('piste')),
        EllipseGeometry(centre, RAYON, RAYON)))

    segments = [(portion, rgb) for (portion, rgb) in (segments or [])]
    positions = arcs([portion for (portion, _) in segments])
    non_nuls = [rgb for (portion, rgb) in segments if portion > 0.0]
    for (depart, balayage), rgb in zip(positions, non_nuls):
        groupe.Children.Add(GeometryDrawing(
            None, _plume(rgb), _arc(centre, depart, balayage)))
    return _geler(DrawingImage(groupe))


def _plume(rgb):
    r, v, b = rgb
    plume = Pen(SolidColorBrush(Color.FromRgb(r, v, b)), EPAISSEUR)
    if PenLineCap is not None:
        # Bouts francs : deux segments voisins se touchent sans se chevaucher.
        plume.StartLineCap = PenLineCap.Flat
        plume.EndLineCap = PenLineCap.Flat
    return plume


def _point(centre, angle):
    radians = math.radians(angle)
    return Point(centre.X + RAYON * math.cos(radians),
                 centre.Y + RAYON * math.sin(radians))


def _arc(centre, depart, balayage):
    """Arc de `balayage` degrés à partir de `depart`.

    À 360° (une seule part occupe tout l'anneau) les deux extrémités se
    confondent et l'arc ne dessine RIEN : c'est le cercle entier qu'il faut.
    """
    if balayage >= 359.999:
        return EllipseGeometry(centre, RAYON, RAYON)
    figure = PathFigure()
    figure.StartPoint = _point(centre, depart)
    figure.IsClosed = False
    figure.Segments.Add(ArcSegment(
        _point(centre, depart + balayage), Size(RAYON, RAYON), 0.0,
        balayage > 180.0, SweepDirection.Clockwise, True))
    geometrie = PathGeometry()
    geometrie.Figures.Add(figure)
    return geometrie


def _geler(image):
    """Freeze : l'image est partagée par le binding, jamais modifiée après."""
    try:
        image.Freeze()
    except Exception:
        pass
    return image
