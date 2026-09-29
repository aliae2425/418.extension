# -*- coding: utf-8 -*-
"""Feuilles : ce que le vendor noyait dans un seau « other ».

``list_views`` rangeait les feuilles avec le reste, sans leur numéro et sans
dire ce qu'elles portaient — et sur un gros projet ce seau, dernier du JSON,
tombait dans la troncature. D'où « il ne voit pas les vues dans les feuilles ».
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


@outil('feuilles',
       'Feuilles du projet : numéro, titre, et les vues posées dessus. '
       'Triées par numéro.',
       proprietes={
           'contient': {'type': 'string',
                        'description': 'fragment de numéro ou de titre'},
           'avec_vues': {'type': 'boolean',
                         'description': 'lister les vues placées (défaut oui)'},
           'limite': {'type': 'integer', 'description': 'défaut 100'}})
def feuilles(doc, donnees=None):
    donnees = donnees or {}
    fragment = (donnees.get('contient') or '').strip().lower()
    avec_vues = donnees.get('avec_vues', True)
    limite = int(donnees.get('limite', 100))
    trouvees, total = [], 0
    for feuille in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet):
        numero = feuille.SheetNumber or ''
        titre = base.nom_element(feuille)
        if fragment and fragment not in numero.lower() \
                and fragment not in titre.lower():
            continue
        total += 1
        if len(trouvees) >= limite:
            continue
        fiche = {'numero': numero, 'titre': titre,
                 'id': base.id_valeur(feuille.Id)}
        if avec_vues:
            fiche['vues'] = _vues_placees(doc, feuille)
        trouvees.append(fiche)
    trouvees.sort(key=lambda f: f['numero'])
    return {'count': len(trouvees), 'total': total,
            'partielle': total > len(trouvees), 'feuilles': trouvees}


@outil('vues_hors_feuille',
       'Vues qui ne sont posées sur aucune feuille. La question que se pose '
       'tout architecte avant de rendre un dossier.',
       proprietes={'limite': {'type': 'integer', 'description': 'défaut 100'}})
def vues_hors_feuille(doc, donnees=None):
    donnees = donnees or {}
    placees = set()
    for feuille in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet):
        for identifiant in feuille.GetAllPlacedViews():
            placees.add(base.id_valeur(identifiant))
    orphelines = []
    for vue in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if vue.IsTemplate or vue.ViewType in (
                DB.ViewType.Internal, DB.ViewType.ProjectBrowser,
                DB.ViewType.DrawingSheet, DB.ViewType.SystemBrowser):
            continue
        if base.id_valeur(vue.Id) in placees:
            continue
        orphelines.append({'nom': base.nom_element(vue),
                           'id': base.id_valeur(vue.Id),
                           'type': '{0}'.format(vue.ViewType)})
    limite = int(donnees.get('limite', 100))
    orphelines.sort(key=lambda v: (v['type'], v['nom']))
    return {'count': min(len(orphelines), limite), 'total': len(orphelines),
            'partielle': len(orphelines) > limite,
            'vues': orphelines[:limite]}


def _vues_placees(doc, feuille):
    noms = []
    for identifiant in feuille.GetAllPlacedViews():
        vue = doc.GetElement(identifiant)
        if vue is not None:
            noms.append(base.nom_element(vue))
    return sorted(noms)
