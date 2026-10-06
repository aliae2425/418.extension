# -*- coding: utf-8 -*-
"""Outils de lecture : ce qu'il y a dans la maquette, sans rien toucher."""
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


@outil('etat', 'État du lien avec Revit et titre du document ouvert.')
def etat(doc, donnees=None):
    return {'document': doc.Title, 'chemin': doc.PathName or '',
            'travail_partage': doc.IsWorkshared,
            'modifie': doc.IsModified}


@outil('infos_maquette',
       'Vue d\'ensemble : projet, niveaux avec leur altitude, nombre de '
       'pièces, avertissements. Les altitudes sont dans l\'unité du projet.')
def infos_maquette(doc, donnees=None):
    infos = doc.ProjectInformation
    _id, symbole, _par_pied, _en_pieds = base.unite_longueur(doc)
    niveaux = sorted(
        ({'nom': base.nom_element(n), 'id': base.id_valeur(n.Id),
          'altitude': round(base.vers_projet(doc, n.Elevation), 3)}
         for n in DB.FilteredElementCollector(doc).OfClass(DB.Level)),
        key=lambda n: n['altitude'])
    pieces = (DB.FilteredElementCollector(doc)
              .OfCategory(DB.BuiltInCategory.OST_Rooms)
              .WhereElementIsNotElementType().GetElementCount())
    return {
        'projet': {'nom': _texte(infos, 'Name'),
                   'numero': _texte(infos, 'Number'),
                   'client': _texte(infos, 'ClientName')},
        'unite_de_longueur': symbole,
        'niveaux': niveaux,
        'nombre_de_pieces': pieces,
        'avertissements': len(list(doc.GetWarnings())),
    }


@outil('unites',
       'Unité de longueur du projet et son symbole. Les outils convertissent '
       'déjà : cet outil ne sert qu\'à annoncer l\'unité à l\'architecte.')
def unites(doc, donnees=None):
    identifiant, symbole, par_pied, en_pieds = base.unite_longueur(doc)
    return {'unite': identifiant, 'symbole': symbole,
            'par_pied': par_pied, 'en_pieds': en_pieds}


@outil('niveaux',
       'Niveaux du projet avec leur altitude, dans l\'unité du projet.')
def niveaux(doc, donnees=None):
    _id, symbole, _pp, _ep = base.unite_longueur(doc)
    return {'unite_de_longueur': symbole, 'niveaux': sorted(
        ({'nom': base.nom_element(n), 'id': base.id_valeur(n.Id),
          'altitude': round(base.vers_projet(doc, n.Elevation), 3)}
         for n in DB.FilteredElementCollector(doc).OfClass(DB.Level)),
        key=lambda n: n['altitude'])}


@outil('selection',
       'Ce que l\'architecte a sélectionné dans Revit à l\'instant. À '
       'appeler dès qu\'il dit « ça », « ceux-là » ou « ma sélection ».',
       besoins=('doc', 'uidoc'))
def selection(doc, uidoc, donnees=None):
    elements = [doc.GetElement(i) for i in uidoc.Selection.GetElementIds()]
    retenus = [base.decrire(e) for e in elements if e is not None]
    return {'count': len(retenus), 'elements': retenus}


@outil('categories',
       'Catégories présentes dans le projet et leur nombre d\'éléments. À '
       'appeler AVANT de chercher par nom : il donne les noms réellement '
       'utilisés, en français.',
       proprietes={'avec_types': {
           'type': 'boolean',
           'description': 'compter aussi les types, pas que les instances'}})
def categories(doc, donnees=None):
    donnees = donnees or {}
    comptes = {}
    # Un collecteur sans aucun filtre refuse d'être parcouru : pour « tout »,
    # il faut deux passes, instances puis types.
    collecteurs = [
        DB.FilteredElementCollector(doc).WhereElementIsNotElementType()]
    if donnees.get('avec_types'):
        collecteurs.append(
            DB.FilteredElementCollector(doc).WhereElementIsElementType())
    for collecteur in collecteurs:
        for element in collecteur:
            nom = base.categorie_nom(element)
            if nom != 'Inconnue':
                comptes[nom] = comptes.get(nom, 0) + 1
    return {'count': len(comptes), 'categories': comptes}


@outil('elements',
       'Éléments d\'une catégorie, de la vue active par défaut. Chaque '
       'entrée porte id, nom et catégorie — de quoi enchaîner sur '
       'revit_details ou revit_definir_parametre.',
       proprietes={
           'categorie': {'type': 'string', 'description': 'p. ex. « Portes »'},
           'vue_active': {'type': 'boolean',
                          'description': 'limiter à la vue active (défaut oui)'},
           'limite': {'type': 'integer', 'description': 'défaut 200'}},
       requis=('categorie',))
def elements(doc, donnees=None):
    donnees = donnees or {}
    limite = int(donnees.get('limite', 200))
    vue_active = donnees.get('vue_active', True)
    collecteur = base.collecteur_categorie(doc, donnees['categorie'],
                                           vue_active)
    trouves = [base.decrire(e) for e in list(collecteur.ToElements())[:limite]]
    return {'count': len(trouves), 'categorie': donnees['categorie'],
            'vue_active': bool(vue_active), 'elements': trouves}


@outil('details',
       'Tous les paramètres d\'éléments précis, valeurs DÉJÀ converties dans '
       'l\'unité du projet, avec leur symbole. C\'est l\'outil à prendre '
       'quand l\'architecte demande « quelles sont les propriétés de… ».',
       proprietes={
           'ids': {'type': 'array', 'items': {'type': 'integer'}},
           'selection': {'type': 'boolean',
                         'description': 'partir de la sélection Revit'},
           'categorie': {'type': 'string'},
           'limite': {'type': 'integer', 'description': 'défaut 10'}},
       besoins=('doc', 'uidoc'))
def details(doc, uidoc, donnees=None):
    donnees = donnees or {}
    vises = base.elements_vises(doc, uidoc, donnees, defaut=10)
    limite = int(donnees.get('limite', 10))
    return {'count': min(len(vises), limite),
            'elements': [_detail(doc, e) for e in vises[:limite]]}


def _detail(doc, element):
    fiche = base.decrire(element)
    fiche['type'] = base.nom_element(doc.GetElement(element.GetTypeId()))
    parametres = {}
    for parametre in element.Parameters:
        try:
            nom = parametre.Definition.Name
        except Exception:
            continue
        valeur, unite = base.valeur_parametre(doc, parametre)
        if valeur is None or valeur == '':
            continue
        parametres[nom] = ('{0} {1}'.format(valeur, unite).strip()
                           if unite else valeur)
    fiche['parametres'] = parametres
    return fiche


@outil('avertissements',
       'Avertissements du modèle, regroupés par message. Le premier réflexe '
       'd\'un audit de maquette.',
       proprietes={'limite': {'type': 'integer', 'description': 'défaut 20'}})
def avertissements(doc, donnees=None):
    donnees = donnees or {}
    groupes = {}
    for avertissement in doc.GetWarnings():
        message = avertissement.GetDescriptionText()
        entree = groupes.setdefault(message, {'message': message,
                                              'nombre': 0, 'exemples': []})
        entree['nombre'] += 1
        if len(entree['exemples']) < 3:
            entree['exemples'].extend(
                base.id_valeur(i)
                for i in avertissement.GetFailingElements())
    classes = sorted(groupes.values(), key=lambda g: -g['nombre'])
    limite = int(donnees.get('limite', 20))
    return {'total': sum(g['nombre'] for g in classes),
            'distincts': len(classes), 'avertissements': classes[:limite]}


def _texte(infos, attribut):
    try:
        return getattr(infos, attribut) or ''
    except Exception:
        return ''
