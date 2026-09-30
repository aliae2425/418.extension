# -*- coding: utf-8 -*-
"""Organisation : gabarits de vue, sous-projets, groupes, liens."""
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


@outil('gabarits',
       'Gabarits de vue du projet, et combien de vues les appliquent.')
def gabarits(doc, donnees=None):
    usages = {}
    for vue in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if not vue.IsTemplate and \
                vue.ViewTemplateId != DB.ElementId.InvalidElementId:
            cle = base.id_valeur(vue.ViewTemplateId)
            usages[cle] = usages.get(cle, 0) + 1
    trouves = [{'nom': base.nom_element(v), 'id': base.id_valeur(v.Id),
                'type': '{0}'.format(v.ViewType),
                'applique_a': usages.get(base.id_valeur(v.Id), 0)}
               for v in DB.FilteredElementCollector(doc).OfClass(DB.View)
               if v.IsTemplate]
    trouves.sort(key=lambda g: g['nom'])
    return {'count': len(trouves), 'gabarits': trouves}


@outil('appliquer_gabarit',
       'Applique un gabarit de vue. MODIFIE l\'affichage, dans une '
       'transaction annulable. Sans « vues », s\'applique à la vue active.',
       proprietes={
           'gabarit': {'type': 'string', 'description': 'nom du gabarit'},
           'vues': {'type': 'array', 'items': {'type': 'string'},
                    'description': 'noms de vues ; la vue active si omis'}},
       requis=('gabarit',), ecrit=True, besoins=('doc', 'uidoc'))
def appliquer_gabarit(doc, uidoc, donnees=None):
    donnees = donnees or {}
    cible = donnees['gabarit'].strip().lower()
    gabarit = None
    for vue in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if vue.IsTemplate and base.nom_element(vue).strip().lower() == cible:
            gabarit = vue
            break
    if gabarit is None:
        raise base.ErreurOutil(
            'gabarit introuvable : {0} — lister avec revit_gabarits'.format(
                donnees['gabarit']))
    vues = _vues_visees(doc, uidoc, donnees.get('vues'))
    appliquees, refusees = [], []
    with base.transaction(doc, '418 — gabarit {0}'.format(
            base.nom_element(gabarit))):
        for vue in vues:
            try:
                vue.ViewTemplateId = gabarit.Id
                appliquees.append(base.nom_element(vue))
            except Exception as e:
                refusees.append({'vue': base.nom_element(vue),
                                 'raison': '{0}'.format(e)})
    if not appliquees:
        raise base.ErreurOutil(
            'aucune vue modifiée — {0}'.format(
                refusees[0]['raison'] if refusees else 'raison inconnue'))
    return {'gabarit': base.nom_element(gabarit), 'vues': appliquees,
            'refusees': refusees, 'annulable': True}


@outil('sous_projets',
       'Sous-projets du modèle et leur état. Vide si le projet n\'est pas '
       'en travail partagé.')
def sous_projets(doc, donnees=None):
    if not doc.IsWorkshared:
        return {'travail_partage': False, 'count': 0, 'sous_projets': []}
    trouves = []
    for workset in DB.FilteredWorksetCollector(doc).OfKind(
            DB.WorksetKind.UserWorkset):
        trouves.append({'nom': workset.Name, 'id': workset.Id.IntegerValue,
                        'ouvert': workset.IsOpen,
                        'proprietaire': workset.Owner or ''})
    trouves.sort(key=lambda s: s['nom'])
    return {'travail_partage': True, 'count': len(trouves),
            'sous_projets': trouves}


@outil('groupes',
       'Groupes du modèle : nom du type, nombre d\'instances, contenu.')
def groupes(doc, donnees=None):
    par_type = {}
    for groupe in (DB.FilteredElementCollector(doc)
                   .OfClass(DB.Group)):
        nom = base.nom_element(doc.GetElement(groupe.GetTypeId())) \
              or base.nom_element(groupe)
        entree = par_type.setdefault(nom, {'nom': nom, 'instances': 0,
                                           'elements': 0})
        entree['instances'] += 1
        try:
            entree['elements'] = len(list(groupe.GetMemberIds()))
        except Exception:
            pass
    lignes = sorted(par_type.values(), key=lambda g: g['nom'])
    return {'count': len(lignes), 'groupes': lignes}


@outil('liens',
       'Modèles liés : nom, chemin, état de chargement. Ce qui explique '
       'souvent qu\'un élément visible ne se retrouve pas dans le projet.')
def liens(doc, donnees=None):
    trouves = []
    for type_lien in (DB.FilteredElementCollector(doc)
                      .OfClass(DB.RevitLinkType)):
        trouves.append({
            'nom': base.nom_element(type_lien),
            'id': base.id_valeur(type_lien.Id),
            'charge': _charge(type_lien),
            'chemin': _chemin(doc, type_lien)})
    trouves.sort(key=lambda l: l['nom'])
    return {'count': len(trouves), 'liens': trouves}


def _vues_visees(doc, uidoc, noms):
    if not noms:
        vue = uidoc.ActiveView
        if vue is None:
            raise base.ErreurOutil('aucune vue active')
        return [vue]
    cibles = set(n.strip().lower() for n in noms)
    trouvees = [v for v in DB.FilteredElementCollector(doc).OfClass(DB.View)
                if not v.IsTemplate
                and base.nom_element(v).strip().lower() in cibles]
    if not trouvees:
        raise base.ErreurOutil('aucune vue ne correspond')
    return trouvees


def _charge(type_lien):
    try:
        return type_lien.GetLinkedFileStatus() == DB.LinkedFileStatus.Loaded
    except Exception:
        return None


def _chemin(doc, type_lien):
    try:
        reference = type_lien.GetExternalFileReference()
        return DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(
            reference.GetAbsolutePath())
    except Exception:
        return ''
