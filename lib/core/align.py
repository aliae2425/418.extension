# -*- coding: utf-8 -*-
"""Alignement et répartition des éléments sélectionnés dans la vue active.

Les deux fonctions de calcul (`deltas_alignement`, `deltas_distribution`)
sont pures : elles travaillent sur des scalaires projetés sur un axe de la
vue, donc testables hors Revit. `executer()` fait la glu Revit.
"""
from __future__ import unicode_literals, division

try:
    from Autodesk.Revit.DB import XYZ, ElementTransformUtils
    from Autodesk.Revit.UI import TaskDialog
except Exception:
    XYZ = None
    ElementTransformUtils = None
    TaskDialog = None

try:
    from core.transaction import revit_transaction
except ImportError:
    try:
        from lib.core.transaction import revit_transaction
    except ImportError:
        revit_transaction = None

# mode -> (axe de la vue, opération)
MODES = {
    'gauche':    ('right', 'min'),
    'droite':    ('right', 'max'),
    'bas':       ('up',    'min'),
    'haut':      ('up',    'max'),
    'centre_h':  ('right', 'centre'),
    'centre_v':  ('up',    'centre'),
    'repartir_h': ('right', 'repartir'),
    'repartir_v': ('up',    'repartir'),
}

TOLERANCE = 1e-9


def deltas_alignement(bornes, operation, ancres=None):
    """Déplacements à appliquer pour aligner sur le bord extrême.

    `bornes` : liste de couples (mini, maxi) projetés sur l'axe.
    `operation` : 'min' (bord le plus bas/gauche), 'max', ou 'centre'
    (centres calés sur le milieu de l'étendue globale de la sélection).
    `ancres` : liste de booléens de même longueur. Les ancres (éléments
    épinglés) ne bougent jamais et sont prioritaires : dès qu'il y en a une,
    la cible est calculée sur elles seules.
    """
    reference = [b for b, a in zip(bornes, ancres or []) if a] or bornes
    if operation == 'centre':
        cible = (min(b[0] for b in reference) + max(b[1] for b in reference)) / 2
        deltas = [cible - (b[0] + b[1]) / 2 for b in bornes]
    elif operation == 'min':
        cible = min(b[0] for b in reference)
        deltas = [cible - b[0] for b in bornes]
    else:
        cible = max(b[1] for b in reference)
        deltas = [cible - b[1] for b in bornes]
    if ancres:
        return [0.0 if a else d for d, a in zip(deltas, ancres)]
    return deltas


def deltas_distribution(centres, ancres=None):
    """Déplacements pour espacer également les centres entre les 2 extrêmes.

    Les éléments extrêmes ne bougent pas. Moins de 3 éléments : rien à faire.
    `ancres` : liste de booléens (éléments épinglés). Chaque ancre est un point
    fixe supplémentaire ; les éléments libres sont répartis régulièrement dans
    chaque intervalle délimité par deux points fixes consécutifs.
    """
    if len(centres) < 3:
        return [0.0] * len(centres)
    ordre = sorted(range(len(centres)), key=lambda i: centres[i])
    fixes = [0, len(ordre) - 1]
    if ancres:
        fixes += [rang for rang, i in enumerate(ordre) if ancres[i]]
    fixes = sorted(set(fixes))

    deltas = [0.0] * len(centres)
    for debut_rang, fin_rang in zip(fixes, fixes[1:]):
        if fin_rang - debut_rang < 2:
            continue   # ancres adjacentes : aucun élément libre entre elles
        debut = centres[ordre[debut_rang]]
        pas = (centres[ordre[fin_rang]] - debut) / (fin_rang - debut_rang)
        for rang in range(debut_rang + 1, fin_rang):
            deltas[ordre[rang]] = debut + (rang - debut_rang) * pas - centres[ordre[rang]]
    return deltas


def _bornes(element, view, axe):
    """(mini, maxi) de la boîte englobante de l'élément projetée sur `axe`."""
    bb = element.get_BoundingBox(view)
    if bb is None:
        return None
    valeurs = []
    for x in (bb.Min.X, bb.Max.X):
        for y in (bb.Min.Y, bb.Max.Y):
            for z in (bb.Min.Z, bb.Max.Z):
                p = bb.Transform.OfPoint(XYZ(x, y, z))
                valeurs.append(p.DotProduct(axe))
    return (min(valeurs), max(valeurs))


def executer(uidoc, mode):
    """Aligne ou répartit la sélection courante. Retourne le nb d'éléments déplacés."""
    axe_nom, operation = MODES[mode]
    doc = uidoc.Document
    view = uidoc.ActiveView
    axe = view.RightDirection if axe_nom == 'right' else view.UpDirection

    elements = [doc.GetElement(eid) for eid in uidoc.Selection.GetElementIds()]
    elements = [e for e in elements if e is not None]

    mesures = []
    for e in elements:
        b = _bornes(e, view, axe)
        if b is not None:
            mesures.append((e, b))

    minimum = 3 if operation == 'repartir' else 2
    if len(mesures) < minimum:
        TaskDialog.Show('418', u'Sélectionner au moins %d éléments '
                               u'visibles dans la vue active.' % minimum)
        return 0

    # Les épinglés servent de référence : ils ne bougent pas, les autres s'y calent.
    ancres = [bool(element.Pinned) for element, _ in mesures]
    if all(ancres):
        TaskDialog.Show('418', u'Tous les éléments sélectionnés sont épinglés : '
                               u'aucun élément à déplacer.')
        return 0

    if operation == 'repartir':
        deltas = deltas_distribution([(b[0] + b[1]) / 2 for _, b in mesures], ancres)
    else:
        deltas = deltas_alignement([b for _, b in mesures], operation, ancres)

    deplaces = 0
    with revit_transaction(doc, u'Aligner la sélection'):
        for (element, _), delta in zip(mesures, deltas):
            if abs(delta) < TOLERANCE:
                continue
            ElementTransformUtils.MoveElement(doc, element.Id, axe.Multiply(delta))
            deplaces += 1
    return deplaces
