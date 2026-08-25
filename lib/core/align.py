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


def deltas_alignement(bornes, operation):
    """Déplacements à appliquer pour aligner sur le bord extrême.

    `bornes` : liste de couples (mini, maxi) projetés sur l'axe.
    `operation` : 'min' (bord le plus bas/gauche), 'max', ou 'centre'
    (centres calés sur le milieu de l'étendue globale de la sélection).
    """
    if operation == 'centre':
        cible = (min(b[0] for b in bornes) + max(b[1] for b in bornes)) / 2
        return [cible - (b[0] + b[1]) / 2 for b in bornes]
    if operation == 'min':
        cible = min(b[0] for b in bornes)
        return [cible - b[0] for b in bornes]
    cible = max(b[1] for b in bornes)
    return [cible - b[1] for b in bornes]


def deltas_distribution(centres):
    """Déplacements pour espacer également les centres entre les 2 extrêmes.

    Les éléments extrêmes ne bougent pas. Moins de 3 éléments : rien à faire.
    """
    if len(centres) < 3:
        return [0.0] * len(centres)
    ordre = sorted(range(len(centres)), key=lambda i: centres[i])
    debut = centres[ordre[0]]
    pas = (centres[ordre[-1]] - debut) / (len(centres) - 1)
    deltas = [0.0] * len(centres)
    for rang, i in enumerate(ordre):
        deltas[i] = debut + rang * pas - centres[i]
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
    elements = [e for e in elements if e is not None and not e.Pinned]

    mesures = []
    for e in elements:
        b = _bornes(e, view, axe)
        if b is not None:
            mesures.append((e, b))

    minimum = 3 if operation == 'repartir' else 2
    if len(mesures) < minimum:
        TaskDialog.Show('418', u'Sélectionner au moins %d éléments non épinglés '
                               u'visibles dans la vue active.' % minimum)
        return 0

    if operation == 'repartir':
        deltas = deltas_distribution([(b[0] + b[1]) / 2 for _, b in mesures])
    else:
        deltas = deltas_alignement([b for _, b in mesures], operation)

    deplaces = 0
    with revit_transaction(doc, u'Aligner la sélection'):
        for (element, _), delta in zip(mesures, deltas):
            if abs(delta) < TOLERANCE:
                continue
            ElementTransformUtils.MoveElement(doc, element.Id, axe.Multiply(delta))
            deplaces += 1
    return deplaces
