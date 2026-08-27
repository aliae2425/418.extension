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
    from System.Windows.Media import (Brushes, Color, DashStyle, DoubleCollection,
                                      DrawingGroup, DrawingImage, GeometryDrawing,
                                      GeometryGroup, LineGeometry, Pen,
                                      RectangleGeometry, ScaleTransform,
                                      SolidColorBrush)
except Exception:
    Point = Rect = Brushes = Color = DrawingGroup = DrawingImage = None
    GeometryDrawing = GeometryGroup = LineGeometry = None
    DashStyle = DoubleCollection = ScaleTransform = None
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


def vignette(couches):
    """Empile les `couches` sur un fond BLANC, comme Revit dessine un matériau.

    `couches` : itérable de `Couche`, arrière-plan d'abord. Le blanc est en
    dur — c'est la couleur du papier, pas celle du thème : une hachure noire
    doit rester lisible en mode sombre.
    """
    if DrawingImage is None:
        return None

    groupe = DrawingGroup()
    # Fond blanc opaque : donne le papier ET fige la taille de la vignette,
    # sinon WPF la recadre sur l'étendue des seules lignes tracées.
    groupe.Children.Add(GeometryDrawing(
        Brushes.White, None, RectangleGeometry(Rect(0, 0, LARGEUR, HAUTEUR))))

    for couche in couches or []:
        for dessin in _dessins(couche):
            groupe.Children.Add(dessin)

    # Revit compte V vers le HAUT, WPF y vers le bas : sans ce miroir, toutes
    # les hachures obliques penchent du mauvais côté. Le fond blanc est
    # symétrique, il ne bouge pas.
    if ScaleTransform is not None:
        groupe.Transform = ScaleTransform(1.0, -1.0, LARGEUR / 2.0, HAUTEUR / 2.0)
    return _geler(DrawingImage(groupe))


def _dessins(couche):
    """Les GeometryDrawing d'une `Couche` : un par famille de droites.

    Une famille par dessin et non un GeometryGroup global : chaque famille
    porte ses propres tirets, qui vivent dans le `Pen`.
    """
    if couche is None:
        return []
    if couche.est_uni:
        return [GeometryDrawing(_brosse(couche.rgb), None,
                                RectangleGeometry(Rect(0, 0, LARGEUR, HAUTEUR)))]
    if not couche.grilles:
        return []
    echelle = hatch.ECHELLE_MODELE if couche.est_modele else hatch.ECHELLE_DESSIN
    dessins = []
    for traits, tirets in hatch.par_grille(couche.grilles, LARGEUR, HAUTEUR,
                                           echelle):
        lignes = GeometryGroup()
        for (x1, y1, x2, y2) in traits:
            lignes.Children.Add(LineGeometry(Point(x1, y1), Point(x2, y2)))
        dessins.append(GeometryDrawing(None, _plume(couche.rgb, tirets), lignes))
    return dessins


def _plume(rgb, tirets):
    """Pen de la couleur donnée, pointillé si `tirets` est non vide."""
    plume = Pen(_brosse(rgb), EPAISSEUR)
    if tirets and DashStyle is not None:
        # DashStyle compte en MULTIPLES de l'épaisseur du trait, pas en pixels.
        longueurs = DoubleCollection()
        for t in tirets:
            longueurs.Add(t / EPAISSEUR)
        plume.DashStyle = DashStyle(longueurs, 0.0)
    return plume


def _geler(image):
    """Freeze : l'image est partagée par le binding, jamais modifiée après."""
    try:
        image.Freeze()
    except Exception:
        pass
    return image
