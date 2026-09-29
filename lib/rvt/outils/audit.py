# -*- coding: utf-8 -*-
"""Audit : ce qui cloche avant de rendre un dossier.

Le pendant « lint » de rvt-mcp. Chaque outil répond à une question qu'un
architecte se pose vraiment la veille d'un rendu, et rend des identifiants
pour qu'on puisse enchaîner sur une correction.
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


@outil('non_etiquetes',
       'Éléments d\'une catégorie non étiquetés dans la vue active. La '
       'vérification qu\'on fait feuille par feuille avant un rendu.',
       proprietes={
           'categorie': {'type': 'string', 'description': 'p. ex. « Portes »'},
           'limite': {'type': 'integer', 'description': 'défaut 100'}},
       requis=('categorie',), besoins=('doc', 'uidoc'))
def non_etiquetes(doc, uidoc, donnees=None):
    donnees = donnees or {}
    vue = uidoc.ActiveView
    if vue is None:
        raise base.ErreurOutil('aucune vue active')
    elements = list(base.collecteur_categorie(doc, donnees['categorie'], True)
                    .ToElements())
    if not elements:
        raise base.ErreurOutil(
            'aucun élément de « {0} » dans la vue active'.format(
                donnees['categorie']))
    etiquetes = set()
    for etiquette in (DB.FilteredElementCollector(doc, vue.Id)
                      .OfClass(DB.IndependentTag)):
        try:
            for identifiant in etiquette.GetTaggedLocalElementIds():
                etiquetes.add(base.id_valeur(identifiant))
        except Exception:
            # Revit < 2022 n'expose que TaggedLocalElementId.
            try:
                etiquetes.add(base.id_valeur(
                    etiquette.TaggedLocalElementId))
            except Exception:
                pass
    manquants = [base.decrire(e) for e in elements
                 if base.id_valeur(e.Id) not in etiquetes]
    limite = int(donnees.get('limite', 100))
    return {'vue': base.nom_element(vue), 'categorie': donnees['categorie'],
            'total_elements': len(elements), 'total': len(manquants),
            'count': min(len(manquants), limite),
            'partielle': len(manquants) > limite,
            'elements': manquants[:limite]}


@outil('vues_inutilisees',
       'Vues et nomenclatures qui ne sont sur aucune feuille, et gabarits '
       'que personne n\'applique. Ce qu\'on peut purger sans rien casser.',
       proprietes={'limite': {'type': 'integer', 'description': 'défaut 100'}})
def vues_inutilisees(doc, donnees=None):
    donnees = donnees or {}
    placees, gabarits_utilises = set(), set()
    for feuille in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet):
        for identifiant in feuille.GetAllPlacedViews():
            placees.add(base.id_valeur(identifiant))
    orphelines, gabarits = [], []
    for vue in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if vue.ViewType in (DB.ViewType.Internal, DB.ViewType.ProjectBrowser,
                            DB.ViewType.DrawingSheet,
                            DB.ViewType.SystemBrowser):
            continue
        if vue.IsTemplate:
            gabarits.append(vue)
            continue
        if vue.ViewTemplateId != DB.ElementId.InvalidElementId:
            gabarits_utilises.add(base.id_valeur(vue.ViewTemplateId))
        if base.id_valeur(vue.Id) not in placees:
            orphelines.append({'nom': base.nom_element(vue),
                               'id': base.id_valeur(vue.Id),
                               'type': '{0}'.format(vue.ViewType)})
    inutiles = [{'nom': base.nom_element(g), 'id': base.id_valeur(g.Id)}
                for g in gabarits
                if base.id_valeur(g.Id) not in gabarits_utilises]
    limite = int(donnees.get('limite', 100))
    orphelines.sort(key=lambda v: (v['type'], v['nom']))
    return {'vues_hors_feuille': orphelines[:limite],
            'total_vues_hors_feuille': len(orphelines),
            'partielle': len(orphelines) > limite,
            'gabarits_inutilises': sorted(inutiles, key=lambda g: g['nom']),
            'total_gabarits_inutilises': len(inutiles)}


@outil('familles_inutilisees',
       'Types de famille chargés mais posés nulle part. Le premier poste '
       'd\'allègement d\'une maquette.',
       proprietes={
           'categorie': {'type': 'string', 'description': 'restreindre'},
           'limite': {'type': 'integer', 'description': 'défaut 100'}})
def familles_inutilisees(doc, donnees=None):
    donnees = donnees or {}
    voulue = (donnees.get('categorie') or '').strip().lower()
    poses = set()
    for instance in (DB.FilteredElementCollector(doc)
                     .OfClass(DB.FamilyInstance)):
        poses.add(base.id_valeur(instance.GetTypeId()))
    inutiles = []
    for symbole in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol):
        if base.id_valeur(symbole.Id) in poses:
            continue
        categorie = base.categorie_nom(symbole)
        if voulue and categorie.lower() != voulue:
            continue
        try:
            famille = symbole.Family.Name
        except Exception:
            famille = ''
        inutiles.append({'famille': famille, 'type': base.nom_element(symbole),
                         'categorie': categorie,
                         'id': base.id_valeur(symbole.Id)})
    inutiles.sort(key=lambda f: (f['categorie'], f['famille'], f['type']))
    limite = int(donnees.get('limite', 100))
    return {'count': min(len(inutiles), limite), 'total': len(inutiles),
            'partielle': len(inutiles) > limite, 'types': inutiles[:limite]}


@outil('statistiques',
       'Poids de la maquette : éléments par catégorie, vues, feuilles, '
       'familles, avertissements. Le tableau de bord d\'un audit.')
def statistiques(doc, donnees=None):
    par_categorie = {}
    for element in (DB.FilteredElementCollector(doc)
                    .WhereElementIsNotElementType()):
        nom = base.categorie_nom(element)
        if nom != 'Inconnue':
            par_categorie[nom] = par_categorie.get(nom, 0) + 1
    lourdes = sorted(par_categorie.items(), key=lambda c: -c[1])[:15]
    vues = [v for v in DB.FilteredElementCollector(doc).OfClass(DB.View)
            if not v.IsTemplate]
    return {
        'elements': sum(par_categorie.values()),
        'categories': len(par_categorie),
        'plus_nombreuses': dict(lourdes),
        'vues': len(vues),
        'feuilles': DB.FilteredElementCollector(doc).OfClass(
            DB.ViewSheet).GetElementCount(),
        'nomenclatures': DB.FilteredElementCollector(doc).OfClass(
            DB.ViewSchedule).GetElementCount(),
        'types_de_famille': DB.FilteredElementCollector(doc).OfClass(
            DB.FamilySymbol).GetElementCount(),
        'avertissements': len(list(doc.GetWarnings())),
        'travail_partage': doc.IsWorkshared,
    }
