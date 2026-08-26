# -*- coding: utf-8 -*-
"""Lecture d'un fichier SVG : extraction des tracés et de leurs matrices.

Logique pure — aucune dépendance Revit ni WPF, donc testable hors Revit.
Chaque forme SVG est convertie en chaîne de chemin (« path mini-language »),
accompagnée de la matrice cumulée des `transform` des groupes parents.
L'aplatissement des courbes (WPF) et la création des lignes de détail se font
dans `script.py`.

Non géré (volontairement) : `<use>`, `<text>`, `skewX/skewY`, les coins
arrondis des `<rect>`, les remplissages (seuls les contours sont importés).
"""
from __future__ import unicode_literals, division
import math
import xml.etree.ElementTree as ET
import re

IDENTITE = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

# Éléments dont le contenu n'est pas rendu directement : les importer
# dessinerait des tracés fantômes (définitions, masques, dégradés...).
_NON_RENDUS = frozenset((
    'defs', 'clipPath', 'symbol', 'marker', 'mask', 'pattern',
    'linearGradient', 'radialGradient', 'filter', 'title', 'desc', 'style',
))

_NOMBRES = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')
_FONCTIONS = re.compile(r'([a-zA-Z]+)\s*\(([^)]*)\)')


def nombres(texte):
    """Tous les nombres d'une chaîne, dans l'ordre."""
    return [float(n) for n in _NOMBRES.findall(texte or '')]


def multiplier(parent, enfant):
    """Composition SVG : un point est transformé par `enfant`, puis `parent`."""
    a1, b1, c1, d1, e1, f1 = parent
    a2, b2, c2, d2, e2, f2 = enfant
    return (a1 * a2 + c1 * b2,
            b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2,
            b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1,
            b1 * e2 + d1 * f2 + f1)


def appliquer(matrice, x, y):
    """Applique une matrice à un point 2D."""
    a, b, c, d, e, f = matrice
    return (a * x + c * y + e, b * x + d * y + f)


def parser_transform(texte):
    """Convertit un attribut `transform` SVG en matrice (a, b, c, d, e, f)."""
    matrice = IDENTITE
    for nom, args in _FONCTIONS.findall(texte or ''):
        v = nombres(args)
        nom = nom.lower()
        if not v:
            continue
        if nom == 'translate':
            m = (1.0, 0.0, 0.0, 1.0, v[0], v[1] if len(v) > 1 else 0.0)
        elif nom == 'scale':
            m = (v[0], 0.0, 0.0, v[1] if len(v) > 1 else v[0], 0.0, 0.0)
        elif nom == 'matrix' and len(v) >= 6:
            m = tuple(v[:6])
        elif nom == 'rotate':
            angle = math.radians(v[0])
            cos, sin = math.cos(angle), math.sin(angle)
            m = (cos, sin, -sin, cos, 0.0, 0.0)
            if len(v) >= 3:
                # rotate(a, cx, cy) == translate(c) rotate(a) translate(-c)
                m = multiplier((1.0, 0.0, 0.0, 1.0, v[1], v[2]), m)
                m = multiplier(m, (1.0, 0.0, 0.0, 1.0, -v[1], -v[2]))
        elif nom == 'translatex':
            m = (1.0, 0.0, 0.0, 1.0, v[0], 0.0)
        elif nom == 'translatey':
            m = (1.0, 0.0, 0.0, 1.0, 0.0, v[0])
        else:
            continue
        matrice = multiplier(matrice, m)
    return matrice


def _nombre(attrs, nom, defaut=0.0):
    v = nombres(attrs.get(nom))
    return v[0] if v else defaut


def chemin_depuis_forme(balise, attrs):
    """Chaîne de chemin équivalente à une forme SVG, ou None si non gérée."""
    if balise == 'path':
        return attrs.get('d') or None

    if balise == 'line':
        return 'M {0} {1} L {2} {3}'.format(
            _nombre(attrs, 'x1'), _nombre(attrs, 'y1'),
            _nombre(attrs, 'x2'), _nombre(attrs, 'y2'))

    if balise in ('polyline', 'polygon'):
        pts = nombres(attrs.get('points'))
        if len(pts) < 4:
            return None
        paires = ' '.join('{0} {1}'.format(pts[i], pts[i + 1])
                          for i in range(2, len(pts) - 1, 2))
        chemin = 'M {0} {1} L {2}'.format(pts[0], pts[1], paires)
        return chemin + ' Z' if balise == 'polygon' else chemin

    if balise == 'rect':
        # ponytail: rx/ry ignorés, les coins sortent carrés.
        x, y = _nombre(attrs, 'x'), _nombre(attrs, 'y')
        largeur, hauteur = _nombre(attrs, 'width'), _nombre(attrs, 'height')
        if largeur <= 0 or hauteur <= 0:
            return None
        return 'M {0} {1} L {2} {1} L {2} {3} L {0} {3} Z'.format(
            x, y, x + largeur, y + hauteur)

    if balise in ('circle', 'ellipse'):
        cx, cy = _nombre(attrs, 'cx'), _nombre(attrs, 'cy')
        if balise == 'circle':
            rx = ry = _nombre(attrs, 'r')
        else:
            rx, ry = _nombre(attrs, 'rx'), _nombre(attrs, 'ry')
        if rx <= 0 or ry <= 0:
            return None
        # Deux demi-arcs : syntaxe d'arc identique en SVG et en WPF.
        return ('M {0} {1} A {2} {3} 0 1 0 {4} {1} '
                'A {2} {3} 0 1 0 {0} {1} Z').format(
                    cx - rx, cy, rx, ry, cx + rx)

    return None


def _invisible(attrs):
    if attrs.get('display') == 'none':
        return True
    style = (attrs.get('style') or '').replace(' ', '')
    return 'display:none' in style


def _descendre(noeud, matrice, traces):
    for enfant in noeud:
        balise = enfant.tag
        if callable(balise):  # commentaire ou instruction de traitement
            continue
        balise = balise.split('}')[-1]
        if balise in _NON_RENDUS or _invisible(enfant.attrib):
            continue
        m = multiplier(matrice, parser_transform(enfant.get('transform')))
        chemin = chemin_depuis_forme(balise, enfant.attrib)
        if chemin:
            traces.append((chemin, m))
        _descendre(enfant, m, traces)


def cadrer(bornes, largeur_mm):
    """Retourne (échelle mm/unité, fonction (x, y) -> (mm, mm)).

    Le coin haut-gauche du tracé arrive en (0, 0) et l'axe Y est retourné : il
    pointe vers le bas en SVG, vers le haut en DXF comme dans Revit. Les
    ordonnées produites sont donc négatives ou nulles.
    """
    min_x, min_y, max_x, _ = bornes
    echelle = largeur_mm / (max_x - min_x)

    def vers_mm(x, y):
        return ((x - min_x) * echelle, -(y - min_y) * echelle)

    return echelle, vers_mm


def lire_svg(chemin_fichier):
    """Retourne [(chaine_de_chemin, matrice), ...] pour tout le fichier."""
    traces = []
    _descendre(ET.parse(chemin_fichier).getroot(), IDENTITE, traces)
    return traces
