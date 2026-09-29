# -*- coding: utf-8 -*-
"""Nomenclatures : les lire, et en lire le contenu.

Une nomenclature est déjà le résultat d'un travail de l'architecte — elle
porte les champs qu'il a choisis, filtrés et groupés comme il veut. La lire
vaut mieux que recompter les éléments à côté : on répond avec SES chiffres.
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

# Au-delà, la sortie dépasse ce que la réponse peut porter et se ferait
# tronquer en plein tableau — mieux vaut annoncer la coupe franchement.
LIGNES_MAX = 60


@outil('nomenclatures',
       'Nomenclatures du projet : nom, catégorie, nombre de lignes. À lire '
       'avant revit_lire_nomenclature, qui a besoin du nom exact.',
       proprietes={
           'contient': {'type': 'string', 'description': 'fragment de nom'},
           'limite': {'type': 'integer', 'description': 'défaut 100'}})
def nomenclatures(doc, donnees=None):
    donnees = donnees or {}
    fragment = (donnees.get('contient') or '').strip().lower()
    trouvees = []
    for vue in DB.FilteredElementCollector(doc).OfClass(DB.ViewSchedule):
        if vue.IsTemplate:
            continue
        nom = base.nom_element(vue)
        if fragment and fragment not in nom.lower():
            continue
        trouvees.append({'nom': nom, 'id': base.id_valeur(vue.Id),
                         'categorie': _categorie(doc, vue),
                         'lignes': _lignes(vue),
                         'metre': vue.Definition.IsMaterialTakeoff
                                  if hasattr(vue.Definition,
                                             'IsMaterialTakeoff') else False})
    trouvees.sort(key=lambda n: n['nom'])
    limite = int(donnees.get('limite', 100))
    return {'count': min(len(trouvees), limite), 'total': len(trouvees),
            'partielle': len(trouvees) > limite,
            'nomenclatures': trouvees[:limite]}


@outil('lire_nomenclature',
       'Contenu d\'une nomenclature, en-têtes et lignes. Répond avec les '
       'chiffres tels que l\'architecte les a définis — ses champs, ses '
       'filtres, ses groupements — plutôt qu\'un recomptage approximatif.',
       proprietes={
           'nom': {'type': 'string', 'description': 'nom exact'},
           'id': {'type': 'integer'},
           'limite': {'type': 'integer',
                      'description': 'lignes de corps, défaut 40'}})
def lire_nomenclature(doc, donnees=None):
    donnees = donnees or {}
    vue = _trouver(doc, donnees)
    limite = min(int(donnees.get('limite', 40)), LIGNES_MAX)
    corps = vue.GetTableData().GetSectionData(DB.SectionType.Body)
    colonnes = corps.NumberOfColumns
    total = corps.NumberOfRows
    entetes = _entetes(vue, colonnes)
    lignes = []
    for rang in range(min(total, limite)):
        lignes.append([_cellule(vue, rang, colonne)
                       for colonne in range(colonnes)])
    return {'nomenclature': base.nom_element(vue),
            'colonnes': entetes, 'count': len(lignes), 'total': total,
            'partielle': total > len(lignes), 'lignes': lignes}


def _trouver(doc, donnees):
    if donnees.get('id'):
        vue = doc.GetElement(base.element_id(donnees['id']))
        if isinstance(vue, DB.ViewSchedule):
            return vue
        raise base.ErreurOutil('cet identifiant n\'est pas une nomenclature')
    cible = (donnees.get('nom') or '').strip().lower()
    if not cible:
        raise base.ErreurOutil('préciser « nom » ou « id »')
    for vue in DB.FilteredElementCollector(doc).OfClass(DB.ViewSchedule):
        if not vue.IsTemplate and base.nom_element(vue).strip().lower() == cible:
            return vue
    raise base.ErreurOutil(
        'nomenclature introuvable : {0} — lister avec revit_nomenclatures'
        .format(donnees.get('nom')))


def _entetes(vue, colonnes):
    try:
        entete = vue.GetTableData().GetSectionData(DB.SectionType.Header)
        if entete.NumberOfRows:
            return [vue.GetCellText(DB.SectionType.Header, 0, c)
                    for c in range(colonnes)]
    except Exception:
        pass
    # Repli : les noms de champs de la définition, dans l'ordre affiché.
    try:
        definition = vue.Definition
        return [definition.GetField(i).GetName()
                for i in range(definition.GetFieldCount())]
    except Exception:
        return []


def _cellule(vue, rang, colonne):
    try:
        return vue.GetCellText(DB.SectionType.Body, rang, colonne)
    except Exception:
        return ''


def _lignes(vue):
    try:
        return vue.GetTableData().GetSectionData(
            DB.SectionType.Body).NumberOfRows
    except Exception:
        return 0


def _categorie(doc, vue):
    try:
        identifiant = vue.Definition.CategoryId
        if identifiant == DB.ElementId.InvalidElementId:
            return ''
        categorie = DB.Category.GetCategory(doc, identifiant)
        return categorie.Name if categorie else ''
    except Exception:
        return ''
