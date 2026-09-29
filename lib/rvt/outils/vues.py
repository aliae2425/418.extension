# -*- coding: utf-8 -*-
"""Vues : ce qu'on regarde, et ce qu'on y voit."""
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


@outil('vue_active',
       'La vue ouverte : nom, type, échelle, discipline, niveau associé.',
       besoins=('doc', 'uidoc'))
def vue_active(doc, uidoc, donnees=None):
    vue = uidoc.ActiveView
    if vue is None:
        raise base.ErreurOutil('aucune vue active')
    return _fiche(doc, vue, complet=True)


@outil('vues',
       'Vues du projet, filtrables. Les FEUILLES ont leur propre outil '
       '(revit_feuilles) et ne sont pas rendues ici.',
       proprietes={
           'type': {'type': 'string',
                    'description': 'FloorPlan, Section, Elevation, ThreeD, '
                                   'Schedule, DraftingView…'},
           'contient': {'type': 'string',
                        'description': 'fragment de nom, insensible à la casse'},
           'limite': {'type': 'integer', 'description': 'défaut 100'}})
def vues(doc, donnees=None):
    donnees = donnees or {}
    voulu = (donnees.get('type') or '').strip().lower()
    fragment = (donnees.get('contient') or '').strip().lower()
    limite = int(donnees.get('limite', 100))
    trouvees, total = [], 0
    for vue in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if vue.IsTemplate or not _exposable(vue):
            continue
        genre = '{0}'.format(vue.ViewType)
        nom = base.nom_element(vue)
        if voulu and voulu not in genre.lower():
            continue
        if fragment and fragment not in nom.lower():
            continue
        total += 1
        if len(trouvees) < limite:
            trouvees.append(_fiche(doc, vue))
    trouvees.sort(key=lambda v: (v['type'], v['nom']))
    return {'count': len(trouvees), 'total': total,
            'partielle': total > len(trouvees), 'vues': trouvees}


@outil('elements_de_la_vue',
       'Éléments visibles dans la vue active, groupés par catégorie. Sans '
       'filtre de catégorie il ne rend que les comptes : demander le détail '
       'sur une vue chargée dépasserait la place disponible.',
       proprietes={
           'categorie': {'type': 'string',
                         'description': 'détailler cette catégorie seulement'},
           'limite': {'type': 'integer', 'description': 'défaut 200'}},
       besoins=('doc', 'uidoc'))
def elements_de_la_vue(doc, uidoc, donnees=None):
    donnees = donnees or {}
    vue = uidoc.ActiveView
    if vue is None:
        raise base.ErreurOutil('aucune vue active')
    if donnees.get('categorie'):
        limite = int(donnees.get('limite', 200))
        collecteur = base.collecteur_categorie(doc, donnees['categorie'], True)
        trouves = list(collecteur.ToElements())
        return {'vue': base.nom_element(vue),
                'categorie': donnees['categorie'],
                'count': min(len(trouves), limite),
                'total': len(trouves),
                'elements': [base.decrire(e) for e in trouves[:limite]]}
    comptes = {}
    for element in (DB.FilteredElementCollector(doc, vue.Id)
                    .WhereElementIsNotElementType()):
        nom = base.categorie_nom(element)
        if nom != 'Inconnue':
            comptes[nom] = comptes.get(nom, 0) + 1
    return {'vue': base.nom_element(vue), 'total': sum(comptes.values()),
            'par_categorie': comptes,
            'note': 'Rappeler avec « categorie » pour le détail.'}


@outil('activer_vue',
       'Ouvre une vue dans Revit. MODIFIE ce que voit l\'architecte à '
       'l\'écran, rien dans la maquette — et ce n\'est PAS annulable au '
       'Ctrl+Z, c\'est une action d\'interface.',
       proprietes={'nom': {'type': 'string'},
                   'id': {'type': 'integer'}},
       ecrit=True, besoins=('doc', 'uidoc'))
def activer_vue(doc, uidoc, donnees=None):
    donnees = donnees or {}
    vue = None
    if donnees.get('id'):
        vue = doc.GetElement(base.element_id(donnees['id']))
    elif donnees.get('nom'):
        cible = donnees['nom'].strip().lower()
        for candidate in DB.FilteredElementCollector(doc).OfClass(DB.View):
            if not candidate.IsTemplate and \
                    base.nom_element(candidate).lower() == cible:
                vue = candidate
                break
    if vue is None:
        raise base.ErreurOutil('vue introuvable — préciser « nom » ou « id »')
    uidoc.ActiveView = vue
    return {'ouverte': base.nom_element(vue), 'id': base.id_valeur(vue.Id)}


def _exposable(vue):
    genre = vue.ViewType
    return genre not in (DB.ViewType.Internal, DB.ViewType.ProjectBrowser,
                         DB.ViewType.DrawingSheet, DB.ViewType.SystemBrowser)


def _fiche(doc, vue, complet=False):
    fiche = {'nom': base.nom_element(vue), 'id': base.id_valeur(vue.Id),
             'type': '{0}'.format(vue.ViewType)}
    if not complet:
        return fiche
    fiche.update({
        'echelle': getattr(vue, 'Scale', None),
        'discipline': '{0}'.format(getattr(vue, 'Discipline', '')),
        'niveau_de_detail': '{0}'.format(getattr(vue, 'DetailLevel', '')),
        'cadrage_actif': bool(getattr(vue, 'CropBoxActive', False)),
        'gabarit': base.nom_element(doc.GetElement(vue.ViewTemplateId))
                   if vue.ViewTemplateId != DB.ElementId.InvalidElementId
                   else '',
    })
    try:
        fiche['niveau'] = base.nom_element(vue.GenLevel) if vue.GenLevel \
            else ''
    except Exception:
        fiche['niveau'] = ''
    return fiche
