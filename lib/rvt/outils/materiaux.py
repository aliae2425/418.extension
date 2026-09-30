# -*- coding: utf-8 -*-
"""Matériaux et métrés : de quoi c'est fait, et combien il y en a."""
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


@outil('materiaux',
       'Matériaux du projet : nom, classe, et combien d\'éléments les '
       'utilisent. Le compte d\'usage est calculé, pas lu — il dit ce qu\'on '
       'peut purger.',
       proprietes={
           'contient': {'type': 'string', 'description': 'fragment de nom'},
           'avec_usage': {'type': 'boolean',
                          'description': 'compter les usages (plus lent)'},
           'limite': {'type': 'integer', 'description': 'défaut 100'}})
def materiaux(doc, donnees=None):
    donnees = donnees or {}
    fragment = (donnees.get('contient') or '').strip().lower()
    usages = _usages(doc) if donnees.get('avec_usage') else None
    trouves = []
    for materiau in DB.FilteredElementCollector(doc).OfClass(DB.Material):
        nom = base.nom_element(materiau)
        if fragment and fragment not in nom.lower():
            continue
        fiche = {'nom': nom, 'id': base.id_valeur(materiau.Id),
                 'classe': materiau.MaterialClass or ''}
        if usages is not None:
            fiche['utilise_par'] = usages.get(base.id_valeur(materiau.Id), 0)
        trouves.append(fiche)
    trouves.sort(key=lambda m: m['nom'])
    limite = int(donnees.get('limite', 100))
    return {'count': min(len(trouves), limite), 'total': len(trouves),
            'partielle': len(trouves) > limite, 'materiaux': trouves[:limite]}


@outil('metres',
       'Métré par matériau sur une catégorie : surface et volume, dans les '
       'unités du projet. Répond à « combien de m² de cloison » sans passer '
       'par une nomenclature.',
       proprietes={
           'categorie': {'type': 'string', 'description': 'p. ex. « Murs »'},
           'vue_active': {'type': 'boolean',
                          'description': 'limiter à la vue active (défaut non)'},
           'limite': {'type': 'integer',
                      'description': 'éléments parcourus, défaut 2000'}},
       requis=('categorie',))
def metres(doc, donnees=None):
    donnees = donnees or {}
    elements = list(base.collecteur_categorie(
        doc, donnees['categorie'], donnees.get('vue_active', False))
        .ToElements())[:int(donnees.get('limite', 2000))]
    if not elements:
        raise base.ErreurOutil(
            'aucun élément dans « {0} »'.format(donnees['categorie']))
    par_materiau, symbole_aire, symbole_volume = {}, '', ''
    for element in elements:
        try:
            identifiants = element.GetMaterialIds(False)
        except Exception:
            continue
        for identifiant in identifiants:
            materiau = doc.GetElement(identifiant)
            if materiau is None:
                continue
            nom = base.nom_element(materiau)
            entree = par_materiau.setdefault(
                nom, {'materiau': nom, 'elements': 0,
                      'surface': 0.0, 'volume': 0.0})
            entree['elements'] += 1
            try:
                surface, symbole_aire = base.aire(
                    doc, element.GetMaterialArea(identifiant, False))
                volume, symbole_volume = base.volume(
                    doc, element.GetMaterialVolume(identifiant))
                entree['surface'] = round(entree['surface'] + surface, 3)
                entree['volume'] = round(entree['volume'] + volume, 3)
            except Exception:
                pass               # certains éléments n'ont pas de géométrie
    lignes = sorted(par_materiau.values(), key=lambda m: -m['volume'])
    return {'categorie': donnees['categorie'],
            'elements_parcourus': len(elements),
            'unite_de_surface': symbole_aire, 'unite_de_volume': symbole_volume,
            'count': len(lignes), 'materiaux': lignes}


@outil('materiaux_de',
       'Matériaux d\'éléments précis, avec leur surface et leur volume.',
       proprietes={
           'ids': {'type': 'array', 'items': {'type': 'integer'}},
           'selection': {'type': 'boolean'},
           'categorie': {'type': 'string'},
           'limite': {'type': 'integer', 'description': 'défaut 10'}},
       besoins=('doc', 'uidoc'))
def materiaux_de(doc, uidoc, donnees=None):
    donnees = donnees or {}
    vises = base.elements_vises(doc, uidoc, donnees, defaut=10)
    limite = int(donnees.get('limite', 10))
    fiches = []
    for element in vises[:limite]:
        fiche = base.decrire(element)
        fiche['materiaux'] = _detail(doc, element)
        fiches.append(fiche)
    return {'count': len(fiches), 'total': len(vises), 'elements': fiches}


def _detail(doc, element):
    lignes = []
    try:
        identifiants = element.GetMaterialIds(False)
    except Exception:
        return lignes
    for identifiant in identifiants:
        materiau = doc.GetElement(identifiant)
        if materiau is None:
            continue
        ligne = {'nom': base.nom_element(materiau)}
        try:
            ligne['surface'] = base.aire(
                doc, element.GetMaterialArea(identifiant, False))[0]
            ligne['volume'] = base.volume(
                doc, element.GetMaterialVolume(identifiant))[0]
        except Exception:
            pass
        lignes.append(ligne)
    return lignes


def _usages(doc):
    comptes = {}
    for element in (DB.FilteredElementCollector(doc)
                    .WhereElementIsNotElementType()):
        try:
            for identifiant in element.GetMaterialIds(False):
                cle = base.id_valeur(identifiant)
                comptes[cle] = comptes.get(cle, 0) + 1
        except Exception:
            continue
    return comptes
