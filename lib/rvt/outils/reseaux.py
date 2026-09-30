# -*- coding: utf-8 -*-
"""MEP et structure : deux outils paramétrés plutôt que dix.

rvt-mcp a un handler par type d'élément linéaire — gaine, canalisation,
chemin de câbles, poteau, poutre. Tous prennent deux points, un niveau et un
type, et ne diffèrent que de la classe appelée. Deux outils suffisent.
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
    from Autodesk.Revit.DB import Mechanical, Plumbing, Electrical, Structure
except Exception:
    DB = Mechanical = Plumbing = Electrical = Structure = None

RESEAUX = ('gaine', 'canalisation', 'chemin_de_cables')
PORTEURS = ('poteau', 'poutre')


@outil('creer_reseau',
       'Crée un tronçon de gaine, de canalisation ou de chemin de câbles '
       'entre deux points. MODIFIE la maquette, dans une transaction '
       'annulable. Coordonnées et diamètre dans l\'unité du projet.',
       proprietes={
           'type': {'type': 'string', 'enum': list(RESEAUX)},
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
           'systeme': {'type': 'string',
                       'description': 'nom du type de système ; le premier '
                                      'si omis'},
           'diametre': {'type': 'number',
                        'description': 'dans l\'unité du projet'}},
       requis=('type', 'depart', 'arrivee'), ecrit=True)
def creer_reseau(doc, donnees=None):
    donnees = donnees or {}
    genre = (donnees.get('type') or '').strip().lower()
    if genre not in RESEAUX:
        raise base.ErreurOutil('type inconnu : {0} — attendu {1}'.format(
            genre, ', '.join(RESEAUX)))
    if Mechanical is None:
        raise base.ErreurOutil('les API MEP ne sont pas disponibles ici')
    depart = base.point(doc, donnees['depart'])
    arrivee = base.point(doc, donnees['arrivee'])
    if depart.IsAlmostEqualTo(arrivee):
        raise base.ErreurOutil('départ et arrivée confondus')
    niveau = _niveau(doc, donnees.get('niveau'), depart.Z)

    with base.transaction(doc, '418 — {0}'.format(genre)):
        element = _creer(doc, genre, depart, arrivee, niveau,
                         donnees.get('systeme'))
        if donnees.get('diametre'):
            _poser_diametre(doc, element, donnees['diametre'])
    return {'cree': base.decrire(element), 'type': genre,
            'niveau': base.nom_element(niveau), 'annulable': True}


@outil('creer_porteur',
       'Crée un poteau ou une poutre structurels. MODIFIE la maquette, dans '
       'une transaction annulable. Un poteau prend « position » et une '
       'hauteur de niveau à niveau ; une poutre prend « depart » et '
       '« arrivee ». Coordonnées dans l\'unité du projet.',
       proprietes={
           'type': {'type': 'string', 'enum': list(PORTEURS)},
           'famille': {'type': 'string',
                       'description': 'type de famille porteuse ; le premier '
                                      'si omis'},
           'position': {'type': 'object',
                        'description': 'pour un poteau',
                        'properties': {'x': {'type': 'number'},
                                       'y': {'type': 'number'},
                                       'z': {'type': 'number'}}},
           'depart': {'type': 'object',
                      'description': 'pour une poutre',
                      'properties': {'x': {'type': 'number'},
                                     'y': {'type': 'number'},
                                     'z': {'type': 'number'}}},
           'arrivee': {'type': 'object',
                       'description': 'pour une poutre',
                       'properties': {'x': {'type': 'number'},
                                      'y': {'type': 'number'},
                                      'z': {'type': 'number'}}},
           'niveau': {'type': 'string'}},
       requis=('type',), ecrit=True)
def creer_porteur(doc, donnees=None):
    donnees = donnees or {}
    genre = (donnees.get('type') or '').strip().lower()
    if genre not in PORTEURS:
        raise base.ErreurOutil('type inconnu : {0} — attendu {1}'.format(
            genre, ', '.join(PORTEURS)))
    categorie = (DB.BuiltInCategory.OST_StructuralColumns if genre == 'poteau'
                 else DB.BuiltInCategory.OST_StructuralFraming)
    symbole = _symbole(doc, categorie, donnees.get('famille'))
    structurel = (Structure.StructuralType.Column if genre == 'poteau'
                  else Structure.StructuralType.Beam)

    with base.transaction(doc, '418 — {0}'.format(genre)):
        if not symbole.IsActive:
            symbole.Activate()
            doc.Regenerate()
        if genre == 'poteau':
            if not donnees.get('position'):
                raise base.ErreurOutil('un poteau demande « position »')
            point = base.point(doc, donnees['position'])
            niveau = _niveau(doc, donnees.get('niveau'), point.Z)
            element = doc.Create.NewFamilyInstance(
                point, symbole, niveau, structurel)
        else:
            if not donnees.get('depart') or not donnees.get('arrivee'):
                raise base.ErreurOutil(
                    'une poutre demande « depart » et « arrivee »')
            a = base.point(doc, donnees['depart'])
            b = base.point(doc, donnees['arrivee'])
            if a.IsAlmostEqualTo(b):
                raise base.ErreurOutil('départ et arrivée confondus')
            niveau = _niveau(doc, donnees.get('niveau'), a.Z)
            element = doc.Create.NewFamilyInstance(
                DB.Line.CreateBound(a, b), symbole, niveau, structurel)
    return {'cree': base.decrire(element), 'type': genre,
            'niveau': base.nom_element(niveau),
            'famille': base.nom_element(symbole), 'annulable': True}


# --- plomberie ------------------------------------------------------------

def _creer(doc, genre, depart, arrivee, niveau, systeme):
    if genre == 'gaine':
        return Mechanical.Duct.Create(
            doc, _systeme(doc, Mechanical.MechanicalSystemType, systeme),
            _type_reseau(doc, Mechanical.DuctType), niveau.Id, depart, arrivee)
    if genre == 'canalisation':
        return Plumbing.Pipe.Create(
            doc, _systeme(doc, Plumbing.PipingSystemType, systeme),
            _type_reseau(doc, Plumbing.PipeType), niveau.Id, depart, arrivee)
    return Electrical.CableTray.Create(
        doc, _type_reseau(doc, Electrical.CableTrayType).Id,
        depart, arrivee, niveau.Id)


def _systeme(doc, classe, nom):
    types = list(DB.FilteredElementCollector(doc).OfClass(classe))
    if not types:
        raise base.ErreurOutil('aucun type de système dans ce projet')
    if nom:
        cible = nom.strip().lower()
        for candidat in types:
            if base.nom_element(candidat).strip().lower() == cible:
                return candidat.Id
        disponibles = ', '.join(sorted(
            base.nom_element(t) for t in types)[:8])
        raise base.ErreurOutil(
            'système introuvable : {0} — disponibles : {1}'.format(
                nom, disponibles))
    return types[0].Id


def _type_reseau(doc, classe):
    types = list(DB.FilteredElementCollector(doc).OfClass(classe))
    if not types:
        raise base.ErreurOutil(
            'aucun type de ce réseau dans le projet — charger une famille '
            'système d\'abord')
    return types[0]


def _poser_diametre(doc, element, valeur):
    for nom in ('Diameter', 'Diamètre', 'Width', 'Largeur'):
        parametre = element.LookupParameter(nom)
        if parametre is not None and not parametre.IsReadOnly:
            try:
                base.poser_parametre(doc, parametre, valeur)
                return
            except Exception:
                continue


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


def _symbole(doc, categorie, nom):
    symboles = list(DB.FilteredElementCollector(doc)
                    .OfCategory(categorie).OfClass(DB.FamilySymbol))
    if not symboles:
        raise base.ErreurOutil(
            'aucune famille de cette catégorie chargée dans le projet')
    if not nom:
        return symboles[0]
    cible = nom.strip().lower()
    for symbole in symboles:
        if base.nom_element(symbole).strip().lower() == cible:
            return symbole
    disponibles = ', '.join(sorted(
        base.nom_element(s) for s in symboles)[:8])
    raise base.ErreurOutil(
        'famille introuvable : {0} — disponibles : {1}'.format(
            nom, disponibles))
