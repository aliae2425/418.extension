# -*- coding: utf-8 -*-
"""Créer : niveaux, quadrillages, murs, sols.

Le premier lot où le modèle construit au lieu de regarder. Toutes les
coordonnées sont dans l'unité du projet — la conversion se fait à la
frontière, dans ``base.point()``.
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


@outil('creer_niveau',
       'Crée un niveau à une altitude donnée. MODIFIE la maquette, dans une '
       'transaction annulable. Altitude dans l\'unité du projet.',
       proprietes={
           'nom': {'type': 'string'},
           'altitude': {'type': 'number',
                        'description': 'dans l\'unité du projet'}},
       requis=('nom', 'altitude'), ecrit=True)
def creer_niveau(doc, donnees=None):
    donnees = donnees or {}
    nom = donnees['nom'].strip()
    if _niveau_existe(doc, nom):
        raise base.ErreurOutil('un niveau porte déjà ce nom : {0}'.format(nom))
    altitude = base.vers_revit(doc, donnees['altitude'])
    with base.transaction(doc, '418 — niveau {0}'.format(nom)):
        niveau = DB.Level.Create(doc, altitude)
        niveau.Name = nom
    return {'cree': base.decrire(niveau), 'altitude': donnees['altitude'],
            'annulable': True}


@outil('creer_quadrillage',
       'Crée une file de quadrillage entre deux points. MODIFIE la maquette, '
       'dans une transaction annulable. Coordonnées dans l\'unité du projet.',
       proprietes={
           'nom': {'type': 'string', 'description': 'p. ex. « A » ou « 1 »'},
           'depart': {'type': 'object',
                      'properties': {'x': {'type': 'number'},
                                     'y': {'type': 'number'},
                                     'z': {'type': 'number'}},
                      'required': ['x', 'y', 'z']},
           'arrivee': {'type': 'object',
                       'properties': {'x': {'type': 'number'},
                                      'y': {'type': 'number'},
                                      'z': {'type': 'number'}},
                       'required': ['x', 'y', 'z']}},
       requis=('depart', 'arrivee'), ecrit=True)
def creer_quadrillage(doc, donnees=None):
    donnees = donnees or {}
    ligne = _ligne(doc, donnees['depart'], donnees['arrivee'])
    with base.transaction(doc, '418 — quadrillage'):
        file_ = DB.Grid.Create(doc, ligne)
        if donnees.get('nom'):
            try:
                file_.Name = donnees['nom'].strip()
            except Exception:
                pass               # un nom déjà pris n'annule pas la création
    return {'cree': base.decrire(file_), 'annulable': True}


@outil('creer_mur',
       'Crée un mur entre deux points. MODIFIE la maquette, dans une '
       'transaction annulable. Coordonnées et hauteur dans l\'unité du '
       'projet ; sans « type », le type de mur par défaut du projet.',
       proprietes={
           'depart': {'type': 'object',
                      'properties': {'x': {'type': 'number'},
                                     'y': {'type': 'number'},
                                     'z': {'type': 'number'}},
                      'required': ['x', 'y', 'z']},
           'arrivee': {'type': 'object',
                       'properties': {'x': {'type': 'number'},
                                      'y': {'type': 'number'},
                                      'z': {'type': 'number'}},
                       'required': ['x', 'y', 'z']},
           'niveau': {'type': 'string'},
           'hauteur': {'type': 'number',
                       'description': 'dans l\'unité du projet'},
           'type': {'type': 'string', 'description': 'nom du type de mur'},
           'structurel': {'type': 'boolean'}},
       requis=('depart', 'arrivee'), ecrit=True)
def creer_mur(doc, donnees=None):
    donnees = donnees or {}
    ligne = _ligne(doc, donnees['depart'], donnees['arrivee'])
    niveau = _niveau(doc, donnees.get('niveau'), ligne.GetEndPoint(0).Z)
    hauteur = (base.vers_revit(doc, donnees['hauteur'])
               if donnees.get('hauteur') else _hauteur_par_defaut(doc, niveau))
    type_mur = _type(doc, DB.WallType, donnees.get('type'))
    with base.transaction(doc, '418 — mur'):
        mur = DB.Wall.Create(doc, ligne, type_mur.Id, niveau.Id, hauteur,
                             0.0, False, bool(donnees.get('structurel')))
    return {'cree': base.decrire(mur), 'niveau': base.nom_element(niveau),
            'type': base.nom_element(type_mur), 'annulable': True}


@outil('creer_sol',
       'Crée un sol sur un contour fermé de points. MODIFIE la maquette, '
       'dans une transaction annulable. Le contour se referme tout seul : '
       'inutile de répéter le premier point.',
       proprietes={
           'contour': {'type': 'array',
                       'description': 'au moins 3 points {x, y, z}',
                       'items': {'type': 'object',
                                 'properties': {'x': {'type': 'number'},
                                                'y': {'type': 'number'},
                                                'z': {'type': 'number'}}}},
           'niveau': {'type': 'string'},
           'type': {'type': 'string', 'description': 'nom du type de sol'}},
       requis=('contour',), ecrit=True)
def creer_sol(doc, donnees=None):
    donnees = donnees or {}
    points = [base.point(doc, p) for p in donnees['contour']]
    if len(points) < 3:
        raise base.ErreurOutil('un contour demande au moins trois points')
    boucle = DB.CurveLoop()
    for rang in range(len(points)):
        depart, arrivee = points[rang], points[(rang + 1) % len(points)]
        if depart.IsAlmostEqualTo(arrivee):
            continue               # point répété : le contour se referme seul
        boucle.Append(DB.Line.CreateBound(depart, arrivee))
    niveau = _niveau(doc, donnees.get('niveau'), points[0].Z)
    type_sol = _type(doc, DB.FloorType, donnees.get('type'))
    with base.transaction(doc, '418 — sol'):
        from System.Collections.Generic import List
        boucles = List[DB.CurveLoop]()
        boucles.Add(boucle)
        sol = DB.Floor.Create(doc, boucles, type_sol.Id, niveau.Id)
    return {'cree': base.decrire(sol), 'niveau': base.nom_element(niveau),
            'type': base.nom_element(type_sol), 'annulable': True}


# --- plomberie ------------------------------------------------------------

def _ligne(doc, depart, arrivee):
    a, b = base.point(doc, depart), base.point(doc, arrivee)
    if a.IsAlmostEqualTo(b):
        raise base.ErreurOutil('départ et arrivée confondus')
    return DB.Line.CreateBound(a, b)


def _niveau(doc, nom, altitude):
    niveaux = sorted(DB.FilteredElementCollector(doc).OfClass(DB.Level),
                     key=lambda n: n.Elevation)
    if not niveaux:
        raise base.ErreurOutil('le projet n\'a aucun niveau')
    if nom:
        cible = nom.strip().lower()
        for niveau in niveaux:
            if base.nom_element(niveau).strip().lower() == cible:
                return niveau
        raise base.ErreurOutil('niveau introuvable : {0}'.format(nom))
    sous = [n for n in niveaux if n.Elevation <= altitude + 1e-6]
    return sous[-1] if sous else niveaux[0]


def _niveau_existe(doc, nom):
    cible = nom.strip().lower()
    return any(base.nom_element(n).strip().lower() == cible
               for n in DB.FilteredElementCollector(doc).OfClass(DB.Level))


def _type(doc, classe, nom):
    types = list(DB.FilteredElementCollector(doc).OfClass(classe))
    if not types:
        raise base.ErreurOutil('aucun type disponible dans ce projet')
    if not nom:
        return types[0]
    cible = nom.strip().lower()
    for candidat in types:
        if base.nom_element(candidat).strip().lower() == cible:
            return candidat
    disponibles = ', '.join(sorted(base.nom_element(t) for t in types)[:8])
    raise base.ErreurOutil(
        'type introuvable : {0} — disponibles : {1}'.format(nom, disponibles))


def _hauteur_par_defaut(doc, niveau):
    """Jusqu'au niveau au-dessus, ou 3 m si c'est le dernier."""
    niveaux = sorted(DB.FilteredElementCollector(doc).OfClass(DB.Level),
                     key=lambda n: n.Elevation)
    dessus = [n for n in niveaux if n.Elevation > niveau.Elevation + 1e-6]
    if dessus:
        return dessus[0].Elevation - niveau.Elevation
    return DB.UnitUtils.ConvertToInternalUnits(3.0, DB.UnitTypeId.Meters)
