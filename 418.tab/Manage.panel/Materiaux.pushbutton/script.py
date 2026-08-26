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
    from Autodesk.Revit.DB import ElementId, FillPatternTarget
except Exception:
    ElementId = None
    FillPatternTarget = None

from lib.viewmodels.MainViewModel import MainViewModel
from lib.viewmodels.MaterialCardVM import MaterialCardVM, Motif
from lib.views.MainWindowView import MainWindowView
from lib.services.MaterialService import MaterialService
from lib.services import hatch
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


def _motif(identifiant, rgb):
    """`FillPatternElement` -> `Motif` prêt à dessiner."""
    if doc is None or identifiant is None:
        return Motif()
    if ElementId is not None and identifiant == ElementId.InvalidElementId:
        return Motif()
    element = doc.GetElement(identifiant)
    if element is None:
        return Motif()
    try:
        remplissage = element.GetFillPattern()
    except Exception:
        return Motif(nom=element.Name)
    if remplissage.IsSolidFill:
        return Motif(nom=element.Name, est_uni=True, rgb=rgb)
    est_modele = False
    if FillPatternTarget is not None:
        try:
            est_modele = remplissage.Target == FillPatternTarget.Model
        except Exception:
            pass
    grilles = [hatch.depuis_fill_grid(g) for g in remplissage.GetFillGrids()]
    return Motif(nom=element.Name, grilles=grilles, est_modele=est_modele,
                 rgb=rgb)


def _apparence(materiau):
    """Nom de l'asset d'apparence, vide s'il n'y en a pas."""
    if doc is None:
        return u''
    try:
        element = doc.GetElement(materiau.AppearanceAssetId)
        return element.Name if element is not None else u''
    except Exception:
        return u''


def _carte(materiau):
    couleur = _rgb(_premier(materiau, 'Color'))
    coupe = _premier(materiau, 'CutForegroundPatternId', 'CutPatternId')
    surface = _premier(materiau, 'SurfaceForegroundPatternId', 'SurfacePatternId')
    coupe_rgb = _rgb(_premier(materiau, 'CutForegroundPatternColor',
                              'CutPatternColor'), defaut=couleur)
    surface_rgb = _rgb(_premier(materiau, 'SurfaceForegroundPatternColor',
                                'SurfacePatternColor'), defaut=couleur)
    return MaterialCardVM(
        materiau.Id, materiau.Name,
        classe=_premier(materiau, 'MaterialClass') or u'',
        apparence=_apparence(materiau),
        couleur=couleur,
        motif_coupe=_motif(coupe, coupe_rgb),
        motif_surface=_motif(surface, surface_rgb))


if __name__ == '__main__':
    materiaux = all_materials(doc) if doc is not None else []
    materiaux_par_id = dict((m.Id, m) for m in materiaux)
    cartes = [_carte(m) for m in materiaux]

    vm = MainViewModel(service=MaterialService(doc))
    vm.charger(cartes, materiaux_par_id)

    view = MainWindowView(vm)
    view.show()
