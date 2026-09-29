# -*- coding: utf-8 -*-
"""Familles et types chargés, et leur mise en place."""
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


@outil('familles',
       'Familles et types chargés. Filtrables par CATÉGORIE autant que par '
       'nom — c\'est la différence avec le serveur précédent, qui ne savait '
       'filtrer que sur le nom et ne trouvait donc pas « les portes ».',
       proprietes={
           'categorie': {'type': 'string', 'description': 'p. ex. « Portes »'},
           'contient': {'type': 'string',
                        'description': 'fragment de nom de famille ou de type'},
           'limite': {'type': 'integer', 'description': 'défaut 100'}})
def familles(doc, donnees=None):
    donnees = donnees or {}
    voulue = (donnees.get('categorie') or '').strip().lower()
    fragment = (donnees.get('contient') or '').strip().lower()
    limite = int(donnees.get('limite', 100))
    trouves, total = [], 0
    for symbole in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol):
        categorie = base.categorie_nom(symbole)
        if voulue and categorie.lower() != voulue:
            continue
        try:
            famille = symbole.Family.Name
        except Exception:
            famille = ''
        type_nom = base.nom_element(symbole)
        if fragment and fragment not in famille.lower() \
                and fragment not in type_nom.lower():
            continue
        total += 1
        if len(trouves) < limite:
            trouves.append({'famille': famille, 'type': type_nom,
                            'categorie': categorie,
                            'id': base.id_valeur(symbole.Id),
                            'actif': symbole.IsActive})
    trouves.sort(key=lambda f: (f['categorie'], f['famille'], f['type']))
    return {'count': len(trouves), 'total': total,
            'partielle': total > len(trouves), 'familles': trouves}


@outil('placer',
       'Place une instance de famille. MODIFIE la maquette, dans une '
       'transaction annulable. Coordonnées dans l\'UNITÉ DU PROJET : '
       'donne-les telles que l\'architecte les exprime.',
       proprietes={
           'famille': {'type': 'string'},
           'type': {'type': 'string',
                    'description': 'type voulu ; le premier si omis'},
           'position': {'type': 'object',
                        'properties': {'x': {'type': 'number'},
                                       'y': {'type': 'number'},
                                       'z': {'type': 'number'}},
                        'required': ['x', 'y', 'z']},
           'niveau': {'type': 'string'},
           'rotation': {'type': 'number', 'description': 'degrés, 0 par défaut'}},
       requis=('famille', 'position'), ecrit=True)
def placer(doc, donnees=None):
    donnees = donnees or {}
    symbole = _symbole(doc, donnees['famille'], donnees.get('type'))
    position = base.point(doc, donnees['position'])
    niveau = _niveau(doc, donnees.get('niveau'), position)
    with base.transaction(doc, '418 — placer {0}'.format(donnees['famille'])):
        if not symbole.IsActive:
            symbole.Activate()
            doc.Regenerate()
        instance = doc.Create.NewFamilyInstance(
            position, symbole, niveau,
            DB.Structure.StructuralType.NonStructural)
        angle = float(donnees.get('rotation') or 0)
        if angle:
            axe = DB.Line.CreateBound(position,
                                      position + DB.XYZ(0, 0, 1))
            DB.ElementTransformUtils.RotateElement(
                doc, instance.Id, axe, angle * 3.141592653589793 / 180.0)
    return {'place': base.decrire(instance),
            'niveau': base.nom_element(niveau), 'annulable': True}


def _symbole(doc, famille, type_voulu):
    cible = famille.strip().lower()
    voulu = (type_voulu or '').strip().lower()
    candidats = []
    for symbole in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol):
        try:
            nom_famille = symbole.Family.Name
        except Exception:
            continue
        if nom_famille.strip().lower() != cible:
            continue
        if voulu and base.nom_element(symbole).strip().lower() != voulu:
            continue
        candidats.append(symbole)
    if not candidats:
        raise base.ErreurOutil(
            'famille introuvable : {0}{1} — vérifier avec revit_familles'
            .format(famille, ' / ' + type_voulu if type_voulu else ''))
    return candidats[0]


def _niveau(doc, nom, position):
    if nom:
        cible = nom.strip().lower()
        for niveau in DB.FilteredElementCollector(doc).OfClass(DB.Level):
            if base.nom_element(niveau).strip().lower() == cible:
                return niveau
        raise base.ErreurOutil('niveau introuvable : {0}'.format(nom))
    # Sans niveau donné : le plus proche sous le point, comme le ferait un
    # architecte qui pose un objet sur le sol le plus bas au-dessus duquel il
    # se trouve.
    niveaux = sorted(DB.FilteredElementCollector(doc).OfClass(DB.Level),
                     key=lambda n: n.Elevation)
    if not niveaux:
        raise base.ErreurOutil('le projet n\'a aucun niveau')
    sous = [n for n in niveaux if n.Elevation <= position.Z]
    return sous[-1] if sous else niveaux[0]
