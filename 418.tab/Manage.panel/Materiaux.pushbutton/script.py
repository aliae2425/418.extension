# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Matériaux"
__doc__ = "Voir, remplacer et renommer les matériaux du modèle."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

try:
    uidoc = __revit__.ActiveUIDocument  # type: ignore
    doc = __revit__.ActiveUIDocument.Document  # type: ignore
except Exception:
    uidoc = None
    doc = None

try:
    from Autodesk.Revit.DB import (CategoryType, ElementId,
                                   FilteredElementCollector, FillPatternTarget)
except Exception:
    CategoryType = None
    ElementId = None
    FilteredElementCollector = None
    FillPatternTarget = None

from lib.viewmodels.MainViewModel import MainViewModel
from lib.viewmodels.MaterialCardVM import Couche, MaterialCardVM, Motif
from lib.viewmodels.RemplacerPageVM import CategorieVM
from lib.views.MainWindowView import MainWindowView
from lib.services.MaterialService import MaterialService
from lib.services import hatch
from lib.services.journal import log, nouvelle_session
from core.selection import all_materials

GRIS = (128, 128, 128)


def _premier(objet, *noms):
    """Première propriété existante parmi `noms`.

    Les motifs de matériau ont été scindés premier plan / arrière-plan en
    2019 : `CutPatternId` est devenu `CutForegroundPatternId`. On accepte
    les deux graphies plutôt que de parier sur la version.
    """
    for nom in noms:
        try:
            valeur = getattr(objet, nom)
        except Exception:
            continue
        if valeur is not None:
            return valeur
    return None


def _rgb(couleur, defaut=GRIS):
    """Couleur Revit -> triplet (r, v, b), `defaut` si non renseignée."""
    try:
        if couleur is None or not couleur.IsValid:
            return defaut
        return (couleur.Red, couleur.Green, couleur.Blue)
    except Exception:
        return defaut


def _couche(identifiant, rgb):
    """`FillPatternElement` -> `Couche` prête à dessiner, None si pas de motif."""
    if doc is None or identifiant is None:
        return None
    if ElementId is not None and identifiant == ElementId.InvalidElementId:
        return None
    element = doc.GetElement(identifiant)
    if element is None:
        return None
    try:
        remplissage = element.GetFillPattern()
    except Exception:
        return Couche(nom=element.Name)
    if remplissage.IsSolidFill:
        return Couche(nom=element.Name, est_uni=True, rgb=rgb)
    est_modele = False
    if FillPatternTarget is not None:
        try:
            est_modele = remplissage.Target == FillPatternTarget.Model
        except Exception:
            pass
    grilles = [hatch.depuis_fill_grid(g) for g in remplissage.GetFillGrids()]
    return Couche(nom=element.Name, grilles=grilles, est_modele=est_modele,
                  rgb=rgb)


def _motif(materiau, face, couleur):
    """Les deux couches d'une face (`'Cut'` ou `'Surface'`) -> `Motif`.

    Chaque couche a son propre motif ET sa propre couleur. Les graphies sans
    Foreground/Background sont celles d'avant 2019, gardées en repli.
    """
    fond = _couche(
        _premier(materiau, face + 'BackgroundPatternId'),
        _rgb(_premier(materiau, face + 'BackgroundPatternColor'), defaut=couleur))
    premier = _couche(
        _premier(materiau, face + 'ForegroundPatternId', face + 'PatternId'),
        _rgb(_premier(materiau, face + 'ForegroundPatternColor',
                      face + 'PatternColor'), defaut=couleur))
    return Motif(fond=fond, premier=premier)


def _apparence(materiau):
    """Nom de l'asset d'apparence, vide s'il n'y en a pas."""
    if doc is None:
        return u''
    try:
        element = doc.GetElement(materiau.AppearanceAssetId)
        return element.Name if element is not None else u''
    except Exception:
        return u''


def _carte(materiau, usages=None):
    couleur = _rgb(_premier(materiau, 'Color'))
    return MaterialCardVM(
        materiau.Id, materiau.Name,
        classe=_premier(materiau, 'MaterialClass') or u'',
        apparence=_apparence(materiau),
        couleur=couleur,
        motif_coupe=_motif(materiau, 'Cut', couleur),
        motif_surface=_motif(materiau, 'Surface', couleur),
        usages=usages)


def _categories_presentes():
    """Catégories de modèle qui contiennent au moins un élément.

    Alimente le menu déroulant de portée de l'onglet Remplacer. On liste ce
    qui est RÉELLEMENT dans la maquette plutôt que les ~200 catégories de
    Revit, sinon le menu est inutilisable.

    ponytail: une requête par catégorie, mais `FirstElementId()` s'arrête au
    premier élément trouvé — c'est bien moins cher qu'un balayage complet
    avec regroupement. Si l'ouverture de l'outil devient lente sur une grosse
    maquette, c'est le premier endroit à regarder.
    """
    if doc is None or CategoryType is None or FilteredElementCollector is None:
        return []
    presentes = []
    for categorie in doc.Settings.Categories:
        try:
            if categorie.CategoryType != CategoryType.Model:
                continue
            collecteur = FilteredElementCollector(doc).OfCategoryId(categorie.Id)
            if collecteur.FirstElementId() == ElementId.InvalidElementId:
                continue
            presentes.append(CategorieVM(categorie.Id, categorie.Name))
        except Exception:
            continue          # catégorie non filtrable (annotation, interne)
    return sorted(presentes, key=lambda c: c.Nom)


def _log_contexte(materiaux, categories):
    """Contexte du document : écarte d'emblée « maquette non modifiable »
    et « API Revit absente », les deux causes de remplacement muet qui ne
    ressemblent pas à un bug de l'outil."""
    if doc is None:
        log(u'AUCUN DOCUMENT ACTIF — aucune action n\'aura d\'effet')
        return
    log(u'document « {} » · modifiable={} · lecture seule={} · famille={}',
        getattr(doc, 'Title', u'?'),
        getattr(doc, 'IsModifiable', u'?'),
        getattr(doc, 'IsReadOnly', u'?'),
        getattr(doc, 'IsFamilyDocument', u'?'))
    log(u'{} matériau(x), {} catégorie(s) présentes',
        len(materiaux), len(categories))


if __name__ == '__main__':
    nouvelle_session(u'Matériaux')
    materiaux = all_materials(doc) if doc is not None else []
    materiaux_par_id = dict((m.Id, m) for m in materiaux)

    # Usages comptés AVANT l'affichage : les onglets Matériaux et Renommer
    # montrent le chiffre d'entrée de jeu, sans clic. C'est un parcours
    # complet de la maquette (cf. MaterialService.compter_utilisations) —
    # l'ouverture de l'outil en paie le prix une fois.
    service = MaterialService(doc)
    usages = service.compter_utilisations(list(materiaux_par_id.keys()))
    cartes = [_carte(m, usages.get(m.Id)) for m in materiaux]

    categories = _categories_presentes()
    _log_contexte(materiaux, categories)

    vm = MainViewModel(service=service)
    vm.charger(cartes, materiaux_par_id, categories)

    view = MainWindowView(vm)
    view.show()
