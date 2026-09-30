# -*- coding: utf-8 -*-
"""Annotation : étiquettes et notes de texte dans la vue active."""
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


@outil('etiqueter',
       'Pose une étiquette sur des éléments de la vue active. MODIFIE la '
       'maquette, dans une transaction annulable. Ceux qui sont déjà '
       'étiquetés sont ignorés — relancer ne crée pas de doublon.',
       proprietes={
           'categorie': {'type': 'string', 'description': 'p. ex. « Portes »'},
           'ids': {'type': 'array', 'items': {'type': 'integer'}},
           'selection': {'type': 'boolean'},
           'avec_ligne': {'type': 'boolean',
                          'description': 'ligne de rappel (défaut non)'},
           'limite': {'type': 'integer', 'description': 'défaut 200'}},
       ecrit=True, besoins=('doc', 'uidoc'))
def etiqueter(doc, uidoc, donnees=None):
    donnees = donnees or {}
    vue = uidoc.ActiveView
    if vue is None:
        raise base.ErreurOutil('aucune vue active')
    vises = base.elements_vises(doc, uidoc, donnees, defaut=200)
    if not vises:
        raise base.ErreurOutil('aucun élément visé')
    deja = _deja_etiquetes(doc, vue)
    avec_ligne = bool(donnees.get('avec_ligne'))
    poses, ignores, refuses = [], 0, []
    with base.transaction(doc, '418 — étiqueter'):
        for element in vises[:int(donnees.get('limite', 200))]:
            if base.id_valeur(element.Id) in deja:
                ignores += 1
                continue
            point = _point(element)
            if point is None:
                refuses.append({'id': base.id_valeur(element.Id),
                                'raison': 'pas de position'})
                continue
            try:
                etiquette = DB.IndependentTag.Create(
                    doc, vue.Id, DB.Reference(element), avec_ligne,
                    DB.TagMode.TM_ADDBY_CATEGORY,
                    DB.TagOrientation.Horizontal, point)
                poses.append(base.id_valeur(etiquette.Id))
            except Exception as e:
                refuses.append({'id': base.id_valeur(element.Id),
                                'raison': '{0}'.format(e)[:120]})
    if not poses and not ignores:
        raise base.ErreurOutil(
            'aucune étiquette posée — {0}'.format(
                refuses[0]['raison'] if refuses
                else 'aucun type d\'étiquette chargé pour cette catégorie ?'))
    return {'vue': base.nom_element(vue), 'posees': len(poses),
            'deja_etiquetes': ignores, 'refuses': refuses[:10],
            'nombre_refuses': len(refuses), 'annulable': True}


@outil('noter',
       'Pose une note de texte dans la vue active. MODIFIE la maquette, dans '
       'une transaction annulable. Position dans l\'unité du projet.',
       proprietes={
           'texte': {'type': 'string'},
           'position': {'type': 'object',
                        'properties': {'x': {'type': 'number'},
                                       'y': {'type': 'number'},
                                       'z': {'type': 'number'}},
                        'required': ['x', 'y', 'z']}},
       requis=('texte', 'position'), ecrit=True, besoins=('doc', 'uidoc'))
def noter(doc, uidoc, donnees=None):
    donnees = donnees or {}
    vue = uidoc.ActiveView
    if vue is None:
        raise base.ErreurOutil('aucune vue active')
    types = list(DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType))
    if not types:
        raise base.ErreurOutil('aucun type de texte dans ce projet')
    point = base.point(doc, donnees['position'])
    with base.transaction(doc, '418 — note'):
        note = DB.TextNote.Create(doc, vue.Id, point, donnees['texte'],
                                  types[0].Id)
    return {'cree': base.decrire(note), 'vue': base.nom_element(vue),
            'annulable': True}


@outil('etiquettes',
       'Étiquettes de la vue active : ce qu\'elles désignent et ce qu\'elles '
       'affichent. Utile pour repérer celles qui sont vides ou orphelines.',
       proprietes={'limite': {'type': 'integer', 'description': 'défaut 200'}},
       besoins=('doc', 'uidoc'))
def etiquettes(doc, uidoc, donnees=None):
    donnees = donnees or {}
    vue = uidoc.ActiveView
    if vue is None:
        raise base.ErreurOutil('aucune vue active')
    trouvees = []
    for etiquette in (DB.FilteredElementCollector(doc, vue.Id)
                      .OfClass(DB.IndependentTag)):
        cibles = _cibles(etiquette)
        trouvees.append({'id': base.id_valeur(etiquette.Id),
                         'texte': _texte(etiquette),
                         'designe': cibles,
                         'orpheline': not cibles})
    limite = int(donnees.get('limite', 200))
    return {'vue': base.nom_element(vue),
            'count': min(len(trouvees), limite), 'total': len(trouvees),
            'partielle': len(trouvees) > limite,
            'orphelines': sum(1 for e in trouvees if e['orpheline']),
            'etiquettes': trouvees[:limite]}


# --- plomberie ------------------------------------------------------------

def _deja_etiquetes(doc, vue):
    deja = set()
    for etiquette in (DB.FilteredElementCollector(doc, vue.Id)
                      .OfClass(DB.IndependentTag)):
        for identifiant in _cibles_ids(etiquette):
            deja.add(identifiant)
    return deja


def _cibles_ids(etiquette):
    try:
        return [base.id_valeur(i)
                for i in etiquette.GetTaggedLocalElementIds()]
    except Exception:
        # Revit < 2022 n'expose que TaggedLocalElementId.
        try:
            return [base.id_valeur(etiquette.TaggedLocalElementId)]
        except Exception:
            return []


def _cibles(etiquette):
    return [i for i in _cibles_ids(etiquette) if i]


def _texte(etiquette):
    try:
        return etiquette.TagText or ''
    except Exception:
        return ''


def _point(element):
    emplacement = getattr(element, 'Location', None)
    position = getattr(emplacement, 'Point', None)
    if position is not None:
        return position
    courbe = getattr(emplacement, 'Curve', None)
    if courbe is not None:
        return courbe.Evaluate(0.5, True)
    try:
        boite = element.get_BoundingBox(None)
        return (boite.Min + boite.Max) / 2.0 if boite else None
    except Exception:
        return None
