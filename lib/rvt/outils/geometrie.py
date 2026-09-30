# -*- coding: utf-8 -*-
"""Géométrie : où sont les choses, et est-ce qu'elles se rentrent dedans."""
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


@outil('emprise',
       'Position et encombrement d\'éléments : point d\'insertion et boîte '
       'englobante, dans l\'unité du projet.',
       proprietes={
           'ids': {'type': 'array', 'items': {'type': 'integer'}},
           'selection': {'type': 'boolean'},
           'categorie': {'type': 'string'},
           'limite': {'type': 'integer', 'description': 'défaut 20'}},
       besoins=('doc', 'uidoc'))
def emprise(doc, uidoc, donnees=None):
    donnees = donnees or {}
    vises = base.elements_vises(doc, uidoc, donnees, defaut=20)
    limite = int(donnees.get('limite', 20))
    _id, symbole, _pp, _ep = base.unite_longueur(doc)
    fiches = []
    for element in vises[:limite]:
        fiche = base.decrire(element)
        fiche.update(_emprise(doc, element))
        fiches.append(fiche)
    return {'unite_de_longueur': symbole, 'count': len(fiches),
            'total': len(vises), 'elements': fiches}


@outil('distance',
       'Distance entre deux éléments, de centre à centre, dans l\'unité du '
       'projet.',
       proprietes={'a': {'type': 'integer', 'description': 'id du premier'},
                   'b': {'type': 'integer', 'description': 'id du second'}},
       requis=('a', 'b'))
def distance(doc, donnees=None):
    donnees = donnees or {}
    premier = doc.GetElement(base.element_id(donnees['a']))
    second = doc.GetElement(base.element_id(donnees['b']))
    if premier is None or second is None:
        raise base.ErreurOutil('élément introuvable')
    a, b = _centre(premier), _centre(second)
    if a is None or b is None:
        raise base.ErreurOutil('ces éléments n\'ont pas de géométrie située')
    _id, symbole, _pp, _ep = base.unite_longueur(doc)
    return {'de': base.decrire(premier), 'a': base.decrire(second),
            'unite_de_longueur': symbole,
            'distance': round(base.vers_projet(doc, a.DistanceTo(b)), 3),
            'horizontale': round(base.vers_projet(
                doc, DB.XYZ(a.X - b.X, a.Y - b.Y, 0).GetLength()), 3),
            'verticale': round(base.vers_projet(doc, abs(a.Z - b.Z)), 3)}


@outil('collisions',
       'Cherche les collisions entre deux catégories, dans la vue active. '
       'Compare les boîtes englobantes : c\'est une PRÉ-détection, pas un '
       'contrôle de clash — elle signale des candidats à vérifier, jamais '
       'des collisions certaines.',
       proprietes={
           'categorie': {'type': 'string'},
           'contre': {'type': 'string',
                      'description': 'seconde catégorie ; la même si omis'},
           'limite': {'type': 'integer', 'description': 'défaut 50'}},
       requis=('categorie',))
def collisions(doc, donnees=None):
    donnees = donnees or {}
    premiers = list(base.collecteur_categorie(
        doc, donnees['categorie'], True).ToElements())
    autre = donnees.get('contre') or donnees['categorie']
    seconds = (premiers if autre == donnees['categorie']
               else list(base.collecteur_categorie(doc, autre, True)
                         .ToElements()))
    if not premiers or not seconds:
        raise base.ErreurOutil('aucun élément dans la vue active à comparer')
    # Au-delà, le produit croisé devient trop long pour une réponse de chat.
    if len(premiers) * len(seconds) > 400000:
        raise base.ErreurOutil(
            'trop d\'éléments à croiser ({0} x {1}) — restreindre la vue ou '
            'les catégories'.format(len(premiers), len(seconds)))
    boites_a = [(e, _boite(doc, e)) for e in premiers]
    boites_b = boites_a if seconds is premiers else \
        [(e, _boite(doc, e)) for e in seconds]
    limite = int(donnees.get('limite', 50))
    trouvees, total = [], 0
    for rang, (element, boite) in enumerate(boites_a):
        if boite is None:
            continue
        debut = rang + 1 if boites_b is boites_a else 0
        for autre_element, autre_boite in boites_b[debut:]:
            if autre_boite is None or autre_element.Id == element.Id:
                continue
            if not _se_croisent(boite, autre_boite):
                continue
            total += 1
            if len(trouvees) < limite:
                trouvees.append({'a': base.decrire(element),
                                 'b': base.decrire(autre_element)})
    return {'categorie': donnees['categorie'], 'contre': autre,
            'count': len(trouvees), 'total': total,
            'partielle': total > len(trouvees), 'candidats': trouvees,
            'note': 'Boîtes englobantes : à vérifier dans la maquette.'}


# --- plomberie ------------------------------------------------------------

def _boite(doc, element):
    try:
        return element.get_BoundingBox(None)
    except Exception:
        return None


def _se_croisent(a, b):
    return (a.Min.X <= b.Max.X and a.Max.X >= b.Min.X and
            a.Min.Y <= b.Max.Y and a.Max.Y >= b.Min.Y and
            a.Min.Z <= b.Max.Z and a.Max.Z >= b.Min.Z)


def _centre(element):
    emplacement = getattr(element, 'Location', None)
    position = getattr(emplacement, 'Point', None)
    if position is not None:
        return position
    courbe = getattr(emplacement, 'Curve', None)
    if courbe is not None:
        return courbe.Evaluate(0.5, True)
    boite = _boite(None, element)
    if boite is not None:
        return (boite.Min + boite.Max) / 2.0
    return None


def _emprise(doc, element):
    fiche = {}
    centre = _centre(element)
    if centre is not None:
        fiche['position'] = {
            'x': round(base.vers_projet(doc, centre.X), 3),
            'y': round(base.vers_projet(doc, centre.Y), 3),
            'z': round(base.vers_projet(doc, centre.Z), 3)}
    boite = _boite(doc, element)
    if boite is not None:
        fiche['dimensions'] = {
            'longueur': round(base.vers_projet(
                doc, boite.Max.X - boite.Min.X), 3),
            'largeur': round(base.vers_projet(
                doc, boite.Max.Y - boite.Min.Y), 3),
            'hauteur': round(base.vers_projet(
                doc, boite.Max.Z - boite.Min.Z), 3)}
    return fiche
