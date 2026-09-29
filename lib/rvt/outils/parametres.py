# -*- coding: utf-8 -*-
"""Paramètres : les lire avec leur unité, les écrire en transaction.

Ce que le vendor ne savait pas faire. ``list_category_parameters`` donnait
les NOMS disponibles sur une catégorie, jamais les valeurs, et rien sur leur
unité — d'où « quels paramètres sur les murs » répondu en pieds.
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


@outil('parametres_de_categorie',
       'Paramètres disponibles sur une catégorie : nom, type de donnée, '
       'unité, et s\'ils sont modifiables. À lire avant d\'écrire.',
       proprietes={
           'categorie': {'type': 'string', 'description': 'p. ex. « Portes »'},
           'modifiables': {'type': 'boolean',
                           'description': 'ne garder que ceux qu\'on peut écrire'}},
       requis=('categorie',))
def parametres_de_categorie(doc, donnees=None):
    donnees = donnees or {}
    collecteur = base.collecteur_categorie(doc, donnees['categorie'], False)
    element = None
    for candidat in collecteur:
        element = candidat
        break
    if element is None:
        raise base.ErreurOutil(
            'aucun élément dans « {0} »'.format(donnees['categorie']))
    seulement_modifiables = donnees.get('modifiables')
    fiches = []
    for parametre in element.Parameters:
        try:
            definition = parametre.Definition
            nom = definition.Name
        except Exception:
            continue
        if seulement_modifiables and parametre.IsReadOnly:
            continue
        fiches.append({'nom': nom, 'modifiable': not parametre.IsReadOnly,
                       'unite': _unite(doc, parametre),
                       'stockage': '{0}'.format(parametre.StorageType)})
    fiches.sort(key=lambda p: p['nom'])
    return {'categorie': donnees['categorie'], 'count': len(fiches),
            'parametres': fiches}


@outil('lire_parametre',
       'Valeur d\'un paramètre sur des éléments, DÉJÀ convertie dans '
       'l\'unité du projet. Répond une ligne par élément.',
       proprietes={
           'nom': {'type': 'string', 'description': 'nom du paramètre'},
           'ids': {'type': 'array', 'items': {'type': 'integer'}},
           'selection': {'type': 'boolean'},
           'categorie': {'type': 'string'},
           'limite': {'type': 'integer', 'description': 'défaut 100'}},
       requis=('nom',), besoins=('doc', 'uidoc'))
def lire_parametre(doc, uidoc, donnees=None):
    donnees = donnees or {}
    nom = donnees['nom']
    vises = base.elements_vises(doc, uidoc, donnees, defaut=100)
    limite = int(donnees.get('limite', 100))
    lignes, unite = [], ''
    for element in vises[:limite]:
        parametre = element.LookupParameter(nom)
        valeur, symbole = base.valeur_parametre(doc, parametre)
        unite = unite or symbole
        lignes.append({'id': base.id_valeur(element.Id),
                       'element': base.nom_element(element),
                       'valeur': valeur})
    return {'parametre': nom, 'unite': unite, 'count': len(lignes),
            'total': len(vises), 'valeurs': lignes}


@outil('definir_parametre',
       'Écrit un paramètre sur des éléments. MODIFIE la maquette, dans une '
       'transaction annulable au Ctrl+Z. Les longueurs se donnent dans '
       'l\'unité du projet, la conversion est faite pour toi.',
       proprietes={
           'nom': {'type': 'string', 'description': 'nom du paramètre'},
           'valeur': {'description': 'texte, nombre ou booléen selon le type'},
           'ids': {'type': 'array', 'items': {'type': 'integer'}},
           'selection': {'type': 'boolean'},
           'categorie': {'type': 'string'},
           'limite': {'type': 'integer', 'description': 'défaut 500'}},
       requis=('nom', 'valeur'), ecrit=True, besoins=('doc', 'uidoc'))
def definir_parametre(doc, uidoc, donnees=None):
    donnees = donnees or {}
    nom, valeur = donnees['nom'], donnees['valeur']
    vises = base.elements_vises(doc, uidoc, donnees, defaut=500)
    if not vises:
        raise base.ErreurOutil('aucun élément visé')
    poses, refuses = 0, []
    with base.transaction(doc, '418 — {0} = {1}'.format(nom, valeur)):
        for element in vises[:int(donnees.get('limite', 500))]:
            parametre = element.LookupParameter(nom)
            if parametre is None:
                refuses.append({'id': base.id_valeur(element.Id),
                                'raison': 'paramètre absent'})
                continue
            try:
                base.poser_parametre(doc, parametre, valeur)
                poses += 1
            except base.ErreurOutil as e:
                refuses.append({'id': base.id_valeur(element.Id),
                                'raison': '{0}'.format(e)})
    # Tout refuser n'est pas une réussite : le dire, sinon le modèle annonce
    # une modification qui n'a pas eu lieu.
    if not poses:
        raise base.ErreurOutil(
            'aucun élément modifié — {0}'.format(
                refuses[0]['raison'] if refuses else 'raison inconnue'))
    return {'parametre': nom, 'valeur': valeur, 'modifies': poses,
            'refuses': refuses[:10], 'nombre_refuses': len(refuses),
            'annulable': True}


def _unite(doc, parametre):
    try:
        type_donnee = parametre.Definition.GetDataType()
        if not DB.UnitUtils.IsMeasurableSpec(type_donnee):
            return ''
        return base.symbole_unite(doc.GetUnits().GetFormatOptions(type_donnee))
    except Exception:
        return ''
