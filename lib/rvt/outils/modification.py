# -*- coding: utf-8 -*-
"""Transformer des éléments : déplacer, tourner, copier, supprimer.

**Un seul outil paramétré** plutôt que quatre. Les quatre gestes partagent
exactement la même moitié de code — désigner les éléments, ouvrir une
transaction, rendre ce qui a bougé — et ne diffèrent que d'un appel. Quatre
outils, c'était quatre fois la même description à tenir d'accord.
"""
from __future__ import unicode_literals

try:
    from rvt.registre import outil
    from rvt import base
except Exception:
    from lib.rvt.registre import outil
    from lib.rvt import base

try:
    from Autodesk.Revit import DB
except Exception:
    DB = None

ACTIONS = ('deplacer', 'copier', 'tourner', 'supprimer')


@outil('transformer',
       'Déplace, copie, tourne ou supprime des éléments. MODIFIE la maquette, '
       'dans une transaction annulable. Désigne les éléments par « ids », par '
       '« selection » ou par « categorie ». Vecteurs dans l\'unité du projet, '
       'angles en degrés.',
       proprietes={
           'action': {'type': 'string', 'enum': list(ACTIONS)},
           'ids': {'type': 'array', 'items': {'type': 'integer'}},
           'selection': {'type': 'boolean'},
           'categorie': {'type': 'string'},
           'vecteur': {'type': 'object',
                       'description': 'pour deplacer et copier',
                       'properties': {'x': {'type': 'number'},
                                      'y': {'type': 'number'},
                                      'z': {'type': 'number'}}},
           'angle': {'type': 'number',
                     'description': 'degrés, pour tourner'},
           'centre': {'type': 'object',
                      'description': 'axe de rotation ; barycentre si omis',
                      'properties': {'x': {'type': 'number'},
                                     'y': {'type': 'number'},
                                     'z': {'type': 'number'}}},
           'limite': {'type': 'integer', 'description': 'défaut 200'}},
       requis=('action',), ecrit=True, besoins=('doc', 'uidoc'))
def transformer(doc, uidoc, donnees=None):
    donnees = donnees or {}
    action = (donnees.get('action') or '').strip().lower()
    if action not in ACTIONS:
        raise base.ErreurOutil(
            'action inconnue : {0} — attendu {1}'.format(
                action, ', '.join(ACTIONS)))
    vises = base.elements_vises(doc, uidoc, donnees, defaut=200)
    if not vises:
        raise base.ErreurOutil('aucun élément visé')
    vises = vises[:int(donnees.get('limite', 200))]
    identifiants = _liste_ids(vises)

    with base.transaction(doc, '418 — {0} {1} élément(s)'.format(
            action, len(vises))):
        if action == 'supprimer':
            doc.Delete(identifiants)
            return {'action': action, 'nombre': len(vises),
                    'supprimes': [base.id_valeur(e.Id) for e in vises],
                    'annulable': True}
        if action == 'tourner':
            angle = float(donnees.get('angle') or 0)
            if not angle:
                raise base.ErreurOutil('préciser « angle » en degrés')
            axe = _axe(doc, donnees.get('centre'), vises)
            DB.ElementTransformUtils.RotateElements(
                doc, identifiants, axe, angle * 3.141592653589793 / 180.0)
            return {'action': action, 'nombre': len(vises), 'angle': angle,
                    'annulable': True}
        vecteur = _vecteur(doc, donnees.get('vecteur'))
        if action == 'deplacer':
            DB.ElementTransformUtils.MoveElements(doc, identifiants, vecteur)
            return {'action': action, 'nombre': len(vises),
                    'annulable': True}
        copies = DB.ElementTransformUtils.CopyElements(
            doc, identifiants, vecteur)
        return {'action': action, 'nombre': len(vises),
                'copies': [base.id_valeur(i) for i in copies],
                'annulable': True}


def _liste_ids(elements):
    from System.Collections.Generic import List
    identifiants = List[DB.ElementId]()
    for element in elements:
        identifiants.Add(element.Id)
    return identifiants


def _vecteur(doc, brut):
    if not isinstance(brut, dict):
        raise base.ErreurOutil('préciser « vecteur » sous la forme {x, y, z}')
    return DB.XYZ(*[base.vers_revit(doc, brut.get(cle, 0))
                    for cle in ('x', 'y', 'z')])


def _axe(doc, centre, elements):
    """Axe vertical de rotation. Barycentre des éléments si rien n'est donné.

    Faire tourner autour de l'origine du projet quand l'architecte dit
    « tourne-les de 90° » enverrait les éléments à l'autre bout de la
    maquette — le geste attendu est une rotation sur place.
    """
    if isinstance(centre, dict):
        point = base.point(doc, centre)
    else:
        points = []
        for element in elements:
            emplacement = getattr(element, 'Location', None)
            position = getattr(emplacement, 'Point', None)
            if position is not None:
                points.append(position)
        if not points:
            raise base.ErreurOutil(
                'impossible de deviner le centre — préciser « centre »')
        point = DB.XYZ(sum(p.X for p in points) / len(points),
                       sum(p.Y for p in points) / len(points),
                       sum(p.Z for p in points) / len(points))
    return DB.Line.CreateBound(point, point + DB.XYZ(0, 0, 1))
