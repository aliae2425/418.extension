# -*- coding: utf-8 -*-
"""Couleurs et filtres de vue."""
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

# Préfixe des filtres créés : les rend reconnaissables dans l'arbre du projet,
# et permet de les RETROUVER pour les mettre à jour au lieu d'en empiler un
# nouveau à chaque appel.
PREFIXE = '418 · '


@outil('colorer',
       'Colore une catégorie par valeur de paramètre en créant des FILTRES '
       'DE VUE nommés, que l\'architecte retrouve dans les propriétés de la '
       'vue et réutilise. MODIFIE l\'affichage, dans une transaction '
       'annulable. Relancer le même appel met à jour au lieu d\'empiler.',
       proprietes={
           'categorie': {'type': 'string', 'description': 'p. ex. « Portes »'},
           'parametre': {'type': 'string',
                         'description': 'paramètre qui porte les valeurs'}},
       requis=('categorie', 'parametre'), ecrit=True,
       besoins=('doc', 'uidoc'))
def colorer(doc, uidoc, donnees=None):
    donnees = donnees or {}
    vue = uidoc.ActiveView
    if vue is None or vue.IsTemplate:
        raise base.ErreurOutil('aucune vue active où poser un filtre')
    if not vue.AreGraphicsOverridesAllowed():
        raise base.ErreurOutil(
            'cette vue n\'accepte pas de remplacement graphique — se placer '
            'dans une vue de modèle, pas une feuille')
    nom_categorie, nom_parametre = donnees['categorie'], donnees['parametre']
    categorie = base.categorie_par_nom(doc, nom_categorie)
    if categorie is None:
        raise base.ErreurOutil(
            'catégorie introuvable : {0}'.format(nom_categorie))
    elements = list(base.collecteur_categorie(doc, nom_categorie, True)
                    .ToElements())
    if not elements:
        raise base.ErreurOutil(
            'aucun élément de « {0} » dans la vue active'.format(
                nom_categorie))
    identifiant, valeurs = _valeurs(elements, nom_parametre)
    if identifiant is None:
        raise base.ErreurOutil(
            'paramètre introuvable sur cette catégorie : {0}'.format(
                nom_parametre))
    if not valeurs:
        raise base.ErreurOutil(
            'le paramètre « {0} » est vide partout'.format(nom_parametre))

    palette = couleurs(len(valeurs))
    poses = []
    with base.transaction(doc, '418 — couleurs {0}'.format(nom_parametre)):
        motif = _motif_plein(doc)
        for rang, valeur in enumerate(valeurs):
            nom = nom_filtre(nom_categorie, nom_parametre, valeur)
            filtre = _existant(doc, nom) or _creer(
                doc, nom, categorie.Id, identifiant, valeur)
            if not vue.IsFilterApplied(filtre.Id):
                vue.AddFilter(filtre.Id)
            vue.SetFilterOverrides(filtre.Id,
                                   _remplacement(palette[rang], motif))
            poses.append({'filtre': nom, 'valeur': valeur,
                          'couleur': palette[rang]})
    return {'vue': base.nom_element(vue), 'count': len(poses),
            'filtres': poses, 'annulable': True}


@outil('effacer_couleurs',
       'Retire les filtres de couleur posés par 418 dans la vue active. '
       'MODIFIE l\'affichage, dans une transaction annulable.',
       proprietes={'categorie': {
           'type': 'string',
           'description': 'ne retirer que ceux de cette catégorie'}},
       ecrit=True, besoins=('doc', 'uidoc'))
def effacer_couleurs(doc, uidoc, donnees=None):
    donnees = donnees or {}
    vue = uidoc.ActiveView
    if vue is None:
        raise base.ErreurOutil('aucune vue active')
    voulue = (donnees.get('categorie') or '').strip().lower()
    retires = []
    with base.transaction(doc, '418 — effacer les couleurs'):
        for identifiant in list(vue.GetFilters()):
            filtre = doc.GetElement(identifiant)
            nom = base.nom_element(filtre)
            if not nom.startswith(PREFIXE):
                continue           # pas le nôtre, on n'y touche pas
            if voulue and voulue not in nom.lower():
                continue
            vue.RemoveFilter(identifiant)
            retires.append(nom)
    return {'vue': base.nom_element(vue), 'retires': retires,
            'count': len(retires), 'annulable': True}


# --- logique pure, testable hors Revit -----------------------------------

def nom_filtre(categorie, parametre, valeur):
    """Nom lisible et STABLE : c'est ce qui permet de retrouver un filtre."""
    return '{0}{1} · {2} = {3}'.format(
        PREFIXE, categorie, parametre, valeur if valeur != '' else '(vide)')


def couleurs(nombre):
    """``nombre`` teintes distinctes, réparties sur le cercle chromatique.

    Écrite ici plutôt qu'empruntée : le générateur du vendor rendait des
    ``DB.Color``, qu'on avait supposés être des tuples — tout appel au filtre
    de couleur échouait, et les tests ne le voyaient pas parce que hors Revit
    c'est le repli qui tournait.
    """
    return [_tsv(360.0 * i / max(nombre, 1), 0.62, 0.93)
            for i in range(nombre)]


def _tsv(teinte, saturation, valeur):
    secteur = int(teinte // 60) % 6
    reste = (teinte / 60.0) - int(teinte // 60)
    clair = valeur * (1 - saturation)
    descend = valeur * (1 - saturation * reste)
    monte = valeur * (1 - saturation * (1 - reste))
    trio = ((valeur, monte, clair), (descend, valeur, clair),
            (clair, valeur, monte), (clair, descend, valeur),
            (monte, clair, valeur), (valeur, clair, descend))[secteur]
    return tuple(int(round(c * 255)) for c in trio)


# --- mise en œuvre --------------------------------------------------------

def _valeurs(elements, nom_parametre):
    identifiant, vues = None, []
    for element in elements:
        parametre = element.LookupParameter(nom_parametre)
        if parametre is None:
            continue
        if identifiant is None:
            identifiant = parametre.Id
        try:
            if parametre.StorageType == DB.StorageType.String:
                valeur = parametre.AsString() or ''
            else:
                valeur = parametre.AsValueString() or ''
        except Exception:
            valeur = ''
        if valeur and valeur not in vues:
            vues.append(valeur)
    return identifiant, sorted(vues)


def _existant(doc, nom):
    for filtre in (DB.FilteredElementCollector(doc)
                   .OfClass(DB.ParameterFilterElement)):
        if base.nom_element(filtre) == nom:
            return filtre
    return None


def _creer(doc, nom, id_categorie, id_parametre, valeur):
    from System.Collections.Generic import List
    categories = List[DB.ElementId]()
    categories.Add(id_categorie)
    filtre = DB.ParameterFilterElement.Create(doc, nom, categories)
    filtre.SetElementFilter(DB.ElementParameterFilter(
        _regle(id_parametre, valeur)))
    return filtre


def _regle(id_parametre, valeur):
    """``CreateEqualsRule`` a perdu son argument ``caseSensitive`` en 2022.

    Les deux signatures coexistent selon la version ; choisir au hasard donne
    un TypeError remonté en 500 muet.
    """
    fabrique = DB.ParameterFilterRuleFactory
    try:
        return fabrique.CreateEqualsRule(id_parametre, valeur)
    except TypeError:
        return fabrique.CreateEqualsRule(id_parametre, valeur, False)


def _remplacement(rvb, motif):
    couleur = DB.Color(rvb[0], rvb[1], rvb[2])
    remplacement = DB.OverrideGraphicSettings()
    remplacement.SetProjectionLineColor(couleur)
    remplacement.SetCutLineColor(couleur)
    if motif is not None:
        remplacement.SetSurfaceForegroundPatternId(motif)
        remplacement.SetSurfaceForegroundPatternColor(couleur)
        remplacement.SetCutForegroundPatternId(motif)
        remplacement.SetCutForegroundPatternColor(couleur)
    return remplacement


def _motif_plein(doc):
    for motif in (DB.FilteredElementCollector(doc)
                  .OfClass(DB.FillPatternElement)):
        if motif.GetFillPattern().IsSolidFill:
            return motif.Id
    return None
