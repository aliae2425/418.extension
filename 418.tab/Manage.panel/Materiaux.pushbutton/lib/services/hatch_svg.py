# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Adaptateur SVG de `services.hatch` : une `Couche` -> une chaîne `<svg>`,
# affichable telle quelle dans la page. Remplace `views/hatch_image.py` (la
# DrawingImage WPF) geste pour geste : mêmes tailles, même empilement sur du
# papier blanc, même miroir vertical, même dosage de l'aplat.
#
# Pourquoi le SVG se fabrique en Python et pas en JS : porter `hatch` en
# JavaScript ferait DEUX implémentations de la même géométrie, à tenir
# d'accord à chaque correction. L'aller-retour par le pont se mesure en
# fractions de milliseconde — l'éditeur peut redemander ses tuiles à chaque
# changement de motif sans qu'on le voie.

try:
    from lib.services import hatch
except Exception:
    from services import hatch

LARGEUR = 64.0
HAUTEUR = 28.0
EPAISSEUR = 0.8

# Les tirets vivent dans l'attribut de trait, donc une phase = un `<path>`.
# Regroupées à ce pas (en pixels) pour qu'un motif pointillé n'en coûte pas un
# par droite ; à un quart de pixel près l'œil ne fait pas la différence.
PAS_DE_PHASE = 0.25

BLANC = u'#FFFFFF'


def hexa(rgb):
    """Triplet (r, v, b) -> « #RRGGBB ». None vaut noir."""
    r, v, b = rgb or (0, 0, 0)
    return u'#%02X%02X%02X' % (int(r), int(v), int(b))


def vignette(couches, largeur=LARGEUR, hauteur=HAUTEUR, echelle_vue=None,
             zoom=1.0):
    """Empile les `couches` sur du papier BLANC, comme Revit dessine un
    matériau. Retourne une chaîne SVG complète.

    `couches` : itérable de `hatch.Couche`, arrière-plan d'abord. Le blanc est
    en dur — c'est la couleur du papier, pas celle du thème : une hachure
    noire doit rester lisible en mode sombre.

    `echelle_vue` : dénominateur de l'échelle postulée (50 pour 1:50). C'est
    le SEUL paramètre qui change quelque chose pour un motif de MODÈLE ; un
    motif de dessin est en taille papier et sort identique à toutes les
    échelles — comportement de Revit, pas défaut d'aperçu.

    `zoom` : grossit le motif ET le trait d'autant. Une tuile de 256×112 à
    `zoom=4` compte exactement autant de segments qu'une de 64×28 à 1 — même
    poids dans le message, quatre fois plus grande à l'écran. C'est ce qui
    permet à la carte de montrer un aperçu lisible sans que la charge utile
    n'explose : les segments vont comme l'aire divisée par le carré du zoom.
    """
    epaisseur = EPAISSEUR * zoom
    corps = []
    for couche in couches or []:
        corps.extend(_formes(couche, largeur, hauteur, echelle_vue,
                             zoom, epaisseur))
    # Revit compte V vers le HAUT, l'écran y vers le bas : sans ce miroir,
    # toutes les hachures obliques penchent du mauvais côté.
    # ponytail: le miroir retourne aussi le sens de parcours des droites, donc
    # un motif de tirets ASYMÉTRIQUE (long/court/long) sort inversé. Même
    # limite que la vignette WPF d'avant ; se corrigerait en construisant la
    # géométrie directement en repère écran.
    # `slice` et non `none` : la même tuile sert à deux tailles d'affichage
    # (le tableau la réduit, la carte l'agrandit), et un étirement tordrait
    # les angles d'une hachure à 45°. Elle couvre et déborde, elle ne se
    # déforme jamais.
    return (
        u'<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s" '
        u'viewBox="0 0 %s %s" preserveAspectRatio="xMidYMid slice">'
        u'<rect width="%s" height="%s" fill="%s"/>'
        u'<g transform="translate(0,%s) scale(1,-1)">%s</g></svg>'
        % (_n(largeur), _n(hauteur), _n(largeur), _n(hauteur),
           _n(largeur), _n(hauteur), BLANC, _n(hauteur), u''.join(corps))
    )


def _formes(couche, largeur, hauteur, echelle_vue=None, zoom=1.0,
            epaisseur=EPAISSEUR):
    """Les formes SVG d'UNE couche. Liste vide pour « aucun motif »."""
    if couche is None:
        return []
    if couche.est_uni:
        return [_aplat(couche.rgb, largeur, hauteur)]
    if not couche.grilles:
        return []
    echelle = (hatch.echelle_modele(echelle_vue) if couche.est_modele
               else hatch.ECHELLE_DESSIN) * zoom
    formes = []
    for famille in hatch.par_grille(couche.grilles, largeur, hauteur, echelle):
        if famille.aplat:
            # Dosé par le taux de couverture : des traits de 0,8 espacés de
            # 1,3 couvrent 60 % du papier, ça imprime gris et pas noir. Le
            # zoom tire les deux termes, le rapport ne bouge pas.
            formes.append(_aplat(
                couche.rgb, largeur, hauteur,
                opacite=min(1.0, epaisseur / famille.ecart)
                if famille.ecart else 1.0))
        else:
            formes.extend(_traits(famille, couche.rgb, epaisseur))
    return formes


def _aplat(rgb, largeur, hauteur, opacite=1.0):
    """Toute la tuile dans la couleur : remplissage plein, ou hachure trop
    dense pour se résoudre en traits à cette échelle."""
    opacite_attr = u'' if opacite >= 1.0 else u' opacity="%s"' % _n(opacite, 3)
    return u'<rect width="%s" height="%s" fill="%s"%s/>' % (
        _n(largeur), _n(hauteur), hexa(rgb), opacite_attr)


def _traits(famille, rgb, epaisseur=EPAISSEUR):
    """Les `<path>` d'une famille de droites, groupés par phase de tirets.

    Trait plein : un seul chemin pour toute la famille. Pointillé : la phase
    dépend de l'endroit où la tuile coupe chaque droite et vit dans l'attribut
    de trait — les droites sont donc regroupées par phase, ce qui en laisse
    peu (des parallèles se font souvent couper au même endroit).
    """
    if not famille.tirets:
        return [_chemin(famille.traits, rgb, epaisseur=epaisseur)]
    periode = sum(famille.tirets)
    groupes = {}
    for trait in famille.traits:
        cle = int(round((trait[4] % periode) / PAS_DE_PHASE))
        groupes.setdefault(cle, []).append(trait)
    return [_chemin(groupes[cle], rgb, famille.tirets, cle * PAS_DE_PHASE,
                    epaisseur)
            for cle in sorted(groupes)]


def _chemin(traits, rgb, tirets=None, phase=0.0, epaisseur=EPAISSEUR):
    """Un `<path>` pour tous les segments d'un même pointillé.

    `stroke-linecap="butt"` : par défaut un tiret serait coiffé d'un carré qui
    l'allonge d'une demi-épaisseur de chaque côté, et un pointillé fin se
    remplirait tout seul. Revit trace des tirets à bouts francs.

    Contrairement à WPF, les longueurs SVG sont en pixels et non en multiples
    de l'épaisseur : pas de division ici, et surtout pas de copier-coller de
    `hatch_image._plume`.
    """
    d = u''.join(u'M%s %sL%s %s' % (_n(t[0]), _n(t[1]), _n(t[2]), _n(t[3]))
                 for t in traits)
    pointille = u''
    if tirets:
        pointille = u' stroke-dasharray="%s" stroke-dashoffset="%s"' % (
            u' '.join(_n(t) for t in tirets), _n(phase))
    return u'<path d="%s" fill="none" stroke="%s" stroke-width="%s" ' \
           u'stroke-linecap="butt"%s/>' % (
               d, hexa(rgb), _n(epaisseur, 2), pointille)


def _n(valeur, decimales=1):
    """Nombre court : « 12 » plutôt que « 12.0 ».

    Une vignette de brique compte quelques centaines de segments et il y en a
    deux par matériau — les décimales inutiles pèsent plus que la précision
    qu'elles n'apportent pas à 64 pixels de large.
    """
    texte = (u'%.*f' % (decimales, valeur)).rstrip(u'0').rstrip(u'.')
    return texte or u'0'
