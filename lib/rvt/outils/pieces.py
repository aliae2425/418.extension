# -*- coding: utf-8 -*-
"""Pièces : surfaces, occupation, et ce qui cloche dans le zonage.

Absent du serveur précédent, alors que c'est le premier sujet d'un architecte
en phase de conception : combien de mètres carrés, où, et lesquelles ne sont
pas placées.
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


@outil('pieces',
       'Pièces du projet : nom, numéro, niveau, surface. Surfaces dans '
       'l\'unité du projet. Les pièces NON PLACÉES sont rendues à part — '
       'elles ont une surface nulle et fausseraient tout total.',
       proprietes={
           'niveau': {'type': 'string',
                      'description': 'ne garder que ce niveau'},
           'contient': {'type': 'string',
                        'description': 'fragment de nom ou de numéro'},
           'limite': {'type': 'integer', 'description': 'défaut 200'}})
def pieces(doc, donnees=None):
    donnees = donnees or {}
    voulu = (donnees.get('niveau') or '').strip().lower()
    fragment = (donnees.get('contient') or '').strip().lower()
    limite = int(donnees.get('limite', 200))
    placees, non_placees, symbole = [], [], ''
    for piece in (DB.FilteredElementCollector(doc)
                  .OfCategory(DB.BuiltInCategory.OST_Rooms)
                  .WhereElementIsNotElementType()):
        nom = base.nom_element(piece)
        numero = _texte(piece, 'Number')
        if fragment and fragment not in nom.lower() \
                and fragment not in numero.lower():
            continue
        niveau = base.nom_element(piece.Level) if piece.Level else ''
        if voulu and niveau.lower() != voulu:
            continue
        surface, symbole = base.aire(doc, piece.Area)
        fiche = {'nom': nom, 'numero': numero, 'niveau': niveau,
                 'id': base.id_valeur(piece.Id), 'surface': surface}
        # Une pièce non placée a une surface nulle : la compter dans un
        # total donnerait une somme juste et un décompte faux.
        (non_placees if piece.Area == 0 else placees).append(fiche)
    placees.sort(key=lambda p: (p['niveau'], p['numero'], p['nom']))
    return {'unite_de_surface': symbole,
            'count': min(len(placees), limite), 'total': len(placees),
            'partielle': len(placees) > limite,
            'surface_totale': round(sum(p['surface'] for p in placees), 2),
            'pieces': placees[:limite],
            'non_placees': len(non_placees),
            'detail_non_placees': non_placees[:20]}


@outil('surfaces_par_niveau',
       'Somme des surfaces de pièces par niveau. La question qu\'on pose '
       'avant un dépôt de permis.')
def surfaces_par_niveau(doc, donnees=None):
    par_niveau, symbole = {}, ''
    for piece in (DB.FilteredElementCollector(doc)
                  .OfCategory(DB.BuiltInCategory.OST_Rooms)
                  .WhereElementIsNotElementType()):
        if piece.Area == 0:
            continue               # non placée : hors total
        niveau = base.nom_element(piece.Level) if piece.Level else '(sans)'
        surface, symbole = base.aire(doc, piece.Area)
        entree = par_niveau.setdefault(niveau, {'niveau': niveau,
                                                'pieces': 0, 'surface': 0.0})
        entree['pieces'] += 1
        entree['surface'] = round(entree['surface'] + surface, 2)
    lignes = sorted(par_niveau.values(), key=lambda n: n['niveau'])
    return {'unite_de_surface': symbole, 'niveaux': lignes,
            'surface_totale': round(sum(n['surface'] for n in lignes), 2),
            'pieces_totales': sum(n['pieces'] for n in lignes)}


@outil('pieces_sans_nom',
       'Pièces dont le nom est resté par défaut ou vide. Le premier ménage '
       'avant de sortir un dossier.',
       proprietes={'limite': {'type': 'integer', 'description': 'défaut 100'}})
def pieces_sans_nom(doc, donnees=None):
    donnees = donnees or {}
    suspectes = []
    for piece in (DB.FilteredElementCollector(doc)
                  .OfCategory(DB.BuiltInCategory.OST_Rooms)
                  .WhereElementIsNotElementType()):
        nom = base.nom_element(piece).strip()
        if nom and nom.lower() not in ('pièce', 'piece', 'room', 'local'):
            continue
        suspectes.append({'nom': nom or '(vide)',
                          'numero': _texte(piece, 'Number'),
                          'niveau': base.nom_element(piece.Level)
                                    if piece.Level else '',
                          'id': base.id_valeur(piece.Id)})
    limite = int(donnees.get('limite', 100))
    return {'count': min(len(suspectes), limite), 'total': len(suspectes),
            'partielle': len(suspectes) > limite, 'pieces': suspectes[:limite]}


def _texte(element, attribut):
    try:
        return getattr(element, attribut) or ''
    except Exception:
        return ''
