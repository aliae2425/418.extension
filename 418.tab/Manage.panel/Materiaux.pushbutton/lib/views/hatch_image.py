# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Adaptateur WPF de `services.hatch` : segments -> DrawingImage bindable.
# Isolé ici pour que la géométrie reste du Python pur, testable hors Revit.

try:
    from lib.services import hatch
except Exception:
    from services import hatch

try:
    from System.Windows import Point, Rect
    from System.Windows.Media import (Brushes, Color, DrawingGroup, DrawingImage,
                                      GeometryDrawing, GeometryGroup, LineGeometry,
                                      Pen, RectangleGeometry, SolidColorBrush)
except Exception:
    Point = Rect = Brushes = Color = DrawingGroup = DrawingImage = None
    GeometryDrawing = GeometryGroup = LineGeometry = None
    Pen = RectangleGeometry = SolidColorBrush = None

LARGEUR = 64.0
HAUTEUR = 28.0
EPAISSEUR = 0.8


def _brosse(rgb):
    """`rgb` : triplet (r, v, b) 0-255, ou None pour du noir."""
    if SolidColorBrush is None:
        return None
    r, v, b = rgb or (0, 0, 0)
    return SolidColorBrush(Color.FromRgb(r, v, b))


def uni(rgb):
    """Vignette pleine — un motif « Uni » n'a aucune grille à tracer."""
    if DrawingImage is None:
        return None
    dessin = GeometryDrawing(_brosse(rgb), None,
                             RectangleGeometry(Rect(0, 0, LARGEUR, HAUTEUR)))
    return _geler(DrawingImage(dessin))


def depuis_grilles(grilles, est_modele=False, rgb=None):
    """DrawingImage des hachures, ou None hors WPF / sans grille."""
    if DrawingImage is None or not grilles:
        return None
    echelle = hatch.ECHELLE_MODELE if est_modele else hatch.ECHELLE_DESSIN
    segments = hatch.segments(grilles, LARGEUR, HAUTEUR, echelle)
    if not segments:
        return None

    lignes = GeometryGroup()
    for (x1, y1, x2, y2) in segments:
        lignes.Children.Add(LineGeometry(Point(x1, y1), Point(x2, y2)))

    groupe = DrawingGroup()
    # Rectangle transparent : fige la taille de la vignette, sinon WPF la
    # recadre sur l'étendue des seules lignes tracées.
    groupe.Children.Add(GeometryDrawing(
        Brushes.Transparent, None, RectangleGeometry(Rect(0, 0, LARGEUR, HAUTEUR))))
    groupe.Children.Add(GeometryDrawing(
        None, Pen(_brosse(rgb), EPAISSEUR), lignes))
    return _geler(DrawingImage(groupe))


def _geler(image):
    """Freeze : l'image est partagée par le binding, jamais modifiée après."""
    try:
        image.Freeze()
    except Exception:
        pass
    return image
