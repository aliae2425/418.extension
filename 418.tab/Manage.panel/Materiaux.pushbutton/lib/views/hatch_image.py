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
                                      PenLineCap, RectangleGeometry,
                                      ScaleTransform, SolidColorBrush)
except Exception:
    Point = Rect = Brushes = Color = DrawingGroup = DrawingImage = None
    GeometryDrawing = GeometryGroup = LineGeometry = None
    DashStyle = DoubleCollection = ScaleTransform = PenLineCap = None
    Pen = RectangleGeometry = SolidColorBrush = None

LARGEUR = 64.0
HAUTEUR = 28.0
EPAISSEUR = 0.8

# Les phases de tirets sont regroupées à ce pas (en pixels) : la phase vit
# dans le Pen, donc une phase = un GeometryDrawing. Sans regroupement un motif
# pointillé en coûterait un par droite ; à un quart de pixel près l'œil ne
# fait pas la différence et il en reste une poignée.
PAS_DE_PHASE = 0.25


def _brosse(rgb):
    """`rgb` : triplet (r, v, b) 0-255, ou None pour du noir."""
    if SolidColorBrush is None:
        return None
    r, v, b = rgb or (0, 0, 0)
    return SolidColorBrush(Color.FromRgb(r, v, b))


def vignette(couches, largeur=LARGEUR, hauteur=HAUTEUR, echelle_vue=None):
    """Empile les `couches` sur un fond BLANC, comme Revit dessine un matériau.

    `couches` : itérable de `Couche`, arrière-plan d'abord. Le blanc est en
    dur — c'est la couleur du papier, pas celle du thème : une hachure noire
    doit rester lisible en mode sombre.

    `largeur`/`hauteur` : taille de la tuile en pixels. Les défauts sont ceux
    de la vignette de card ; l'éditeur demande plus grand.

    `echelle_vue` : dénominateur de l'échelle de vue postulée (50 pour 1:50).
    None reprend `hatch.ECHELLE_VUE`. C'est le SEUL paramètre qui change quoi
    que ce soit pour un motif de MODÈLE — un motif de dessin est en taille
    papier, il sort identique à toutes les échelles, et c'est le comportement
    de Revit qu'on veut montrer.
    """
    if DrawingImage is None:
        return None

    groupe = DrawingGroup()
    # Fond blanc opaque : donne le papier ET fige la taille de la vignette,
    # sinon WPF la recadre sur l'étendue des seules lignes tracées.
    groupe.Children.Add(GeometryDrawing(
        Brushes.White, None, RectangleGeometry(Rect(0, 0, largeur, hauteur))))

    for couche in couches or []:
        for dessin in _dessins(couche, largeur, hauteur, echelle_vue):
            groupe.Children.Add(dessin)

    # Revit compte V vers le HAUT, WPF y vers le bas : sans ce miroir, toutes
    # les hachures obliques penchent du mauvais côté. Le fond blanc est
    # symétrique, il ne bouge pas.
    # ponytail: le miroir retourne aussi le sens de parcours des droites
    # obliques, donc un motif de tirets ASYMÉTRIQUE (trait long/court/long)
    # sort inversé. Pour le corriger il faudrait construire la géométrie
    # directement en repère écran plutôt que miroiter le groupe.
    if ScaleTransform is not None:
        groupe.Transform = ScaleTransform(1.0, -1.0, largeur / 2.0, hauteur / 2.0)
    return _geler(DrawingImage(groupe))


def _dessins(couche, largeur, hauteur, echelle_vue=None):
    """Les GeometryDrawing d'une `Couche`.

    Une famille de droites ne peut pas partager son dessin avec une autre :
    ses tirets vivent dans le `Pen`, et une famille trop dense se rend en
    aplat plutôt qu'en traits.
    """
    if couche is None:
        return []
    if couche.est_uni:
        return [_aplat(couche.rgb, largeur, hauteur)]
    if not couche.grilles:
        return []
    echelle = hatch.echelle_modele(echelle_vue) if couche.est_modele \
        else hatch.ECHELLE_DESSIN
    dessins = []
    for famille in hatch.par_grille(couche.grilles, largeur, hauteur, echelle):
        if famille.aplat:
            # Dosé par le taux de couverture : des traits de 0,8 espacés de
            # 1,3 couvrent 60 % du papier, ça imprime gris et pas noir.
            # Au-delà de 100 % les traits se chevauchent, l'aplat est plein.
            dessins.append(_aplat(couche.rgb, largeur, hauteur,
                                  opacite=min(1.0, EPAISSEUR / famille.ecart)
                                  if famille.ecart else 1.0))
        else:
            dessins.extend(_traits(famille, couche.rgb))
    return dessins


def _aplat(rgb, largeur, hauteur, opacite=1.0):
    """Toute la tuile dans la couleur : remplissage plein, ou hachure trop
    dense pour se résoudre en traits à cette échelle."""
    brosse = _brosse(rgb)
    if brosse is not None and opacite < 1.0:
        brosse.Opacity = opacite
    return GeometryDrawing(brosse, None,
                           RectangleGeometry(Rect(0, 0, largeur, hauteur)))


def _traits(famille, rgb):
    """Les dessins d'une famille de droites, groupés par phase de tirets.

    Trait plein : une seule géométrie pour toute la famille. Pointillé : la
    phase du motif dépend de l'endroit où la tuile coupe chaque droite, et
    elle vit dans le `Pen` — les droites sont donc regroupées par phase, ce
    qui en laisse peu (des parallèles se font souvent couper au même endroit).
    """
    if not famille.tirets:
        return [GeometryDrawing(None, _plume(rgb, [], 0.0),
                                _geometries(famille.traits))]
    periode = sum(famille.tirets)
    groupes = {}
    for trait in famille.traits:
        cle = int(round((trait[4] % periode) / PAS_DE_PHASE))
        groupes.setdefault(cle, []).append(trait)
    return [GeometryDrawing(None,
                            _plume(rgb, famille.tirets, cle * PAS_DE_PHASE),
                            _geometries(groupes[cle]))
            for cle in sorted(groupes)]


def _geometries(traits):
    lignes = GeometryGroup()
    for trait in traits:
        lignes.Children.Add(LineGeometry(Point(trait[0], trait[1]),
                                         Point(trait[2], trait[3])))
    return lignes


def _plume(rgb, tirets, phase=0.0):
    """Pen de la couleur donnée, pointillé calé sur `phase` si `tirets`."""
    plume = Pen(_brosse(rgb), EPAISSEUR)
    if tirets and DashStyle is not None:
        # DashStyle compte en MULTIPLES de l'épaisseur du trait, pas en pixels
        # — décalage compris.
        longueurs = DoubleCollection()
        for t in tirets:
            longueurs.Add(t / EPAISSEUR)
        plume.DashStyle = DashStyle(longueurs, phase / EPAISSEUR)
        if PenLineCap is not None:
            # Par défaut WPF coiffe chaque tiret d'un carré, ce qui l'allonge
            # d'une demi-épaisseur de chaque côté : un pointillé fin se
            # remplit tout seul. Revit trace des tirets à bouts francs.
            plume.DashCap = PenLineCap.Flat
    return plume


def _geler(image):
    """Freeze : l'image est partagée par le binding, jamais modifiée après."""
    try:
        image.Freeze()
    except Exception:
        pass
    return image
