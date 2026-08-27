# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Lecture d'un `Material` Revit -> objets d'affichage (`Couche`, `Motif`,
# `MaterialCardVM`), plus les catalogues du document (motifs de remplissage,
# assets d'apparence) qui alimentent les menus de l'éditeur.
#
# Ce code vivait dans script.py. Il en est sorti parce que l'éditeur doit
# RELIRE un matériau juste après l'avoir écrit, pour rafraîchir sa card — et
# un module `__main__` ne s'importe pas.

try:
    from lib.viewmodels.MaterialCardVM import Couche, MaterialCardVM, Motif
except Exception:
    from viewmodels.MaterialCardVM import Couche, MaterialCardVM, Motif

try:
    from lib.services import hatch
except Exception:
    from services import hatch

try:
    from Autodesk.Revit.DB import (AppearanceAssetElement, ElementId,
                                   FilteredElementCollector,
                                   FillPatternElement, FillPatternTarget)
except Exception:
    AppearanceAssetElement = None
    ElementId = None
    FilteredElementCollector = None
    FillPatternElement = None
    FillPatternTarget = None

GRIS = (128, 128, 128)

#: Les quatre emplacements de motif d'un matériau, sous la forme
#: (préfixe de face, préfixe de couche). L'attribut Revit se recompose
#: « <face><couche>PatternId » / « …PatternColor » — d'où
#: SurfaceForegroundPatternId, CutBackgroundPatternColor, etc. Un seul endroit
#: où cette convention de nommage est écrite : l'éditeur et la sauvegarde s'en
#: servent tous les deux.
EMPLACEMENTS = (
    (u'Cut', u'Background'),
    (u'Cut', u'Foreground'),
    (u'Surface', u'Background'),
    (u'Surface', u'Foreground'),
)


def attribut(face, couche_, suffixe):
    """« Cut », « Foreground », « Id » -> « CutForegroundPatternId »."""
    return u'%s%sPattern%s' % (face, couche_, suffixe)


def premier(objet, *noms):
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


def rgb(couleur, defaut=GRIS):
    """Couleur Revit -> triplet (r, v, b), `defaut` si non renseignée."""
    try:
        if couleur is None or not couleur.IsValid:
            return defaut
        return (couleur.Red, couleur.Green, couleur.Blue)
    except Exception:
        return defaut


def couche_depuis_element(element, couleur=None):
    """`FillPatternElement` -> `Couche` prête à dessiner.

    `couleur` est celle de l'EMPLACEMENT qui pose le motif, pas une propriété
    du motif : le même remplissage sert en noir en coupe et en gris en
    surface.
    """
    if element is None:
        return None
    try:
        remplissage = element.GetFillPattern()
    except Exception:
        # Motif illisible : on garde le nom pour le menu, mais rien à dessiner.
        return Couche(nom=element.Name)
    if remplissage.IsSolidFill:
        return Couche(nom=element.Name, est_uni=True, rgb=couleur)
    est_modele = False
    if FillPatternTarget is not None:
        try:
            est_modele = remplissage.Target == FillPatternTarget.Model
        except Exception:
            pass
    grilles = [hatch.depuis_fill_grid(g) for g in remplissage.GetFillGrids()]
    return Couche(nom=element.Name, grilles=grilles, est_modele=est_modele,
                  rgb=couleur)


def couche(doc, identifiant, couleur):
    """Id de `FillPatternElement` -> `Couche`, None si pas de motif."""
    if doc is None or identifiant is None:
        return None
    if ElementId is not None and identifiant == ElementId.InvalidElementId:
        return None
    return couche_depuis_element(doc.GetElement(identifiant), couleur)


def motif(doc, materiau, face, couleur):
    """Les deux couches d'une face (`'Cut'` ou `'Surface'`) -> `Motif`.

    Chaque couche a son propre motif ET sa propre couleur. Les graphies sans
    Foreground/Background sont celles d'avant 2019, gardées en repli.
    """
    fond = couche(
        doc, premier(materiau, attribut(face, u'Background', u'Id')),
        rgb(premier(materiau, attribut(face, u'Background', u'Color')),
            defaut=couleur))
    avant = couche(
        doc, premier(materiau, attribut(face, u'Foreground', u'Id'),
                     face + u'PatternId'),
        rgb(premier(materiau, attribut(face, u'Foreground', u'Color'),
                    face + u'PatternColor'), defaut=couleur))
    return Motif(fond=fond, premier=avant)


def apparence(doc, materiau):
    """Nom de l'asset d'apparence, vide s'il n'y en a pas."""
    if doc is None:
        return u''
    try:
        element = doc.GetElement(materiau.AppearanceAssetId)
        return element.Name if element is not None else u''
    except Exception:
        return u''


def _lecture(doc, materiau):
    """Le n-uplet d'affichage d'un matériau, partagé par `carte` et
    `rafraichir` — les deux doivent lire EXACTEMENT la même chose."""
    couleur = rgb(premier(materiau, 'Color'))
    return (materiau.Name,
            premier(materiau, 'MaterialClass') or u'',
            apparence(doc, materiau),
            couleur,
            motif(doc, materiau, u'Cut', couleur),
            motif(doc, materiau, u'Surface', couleur))


def carte(doc, materiau, usages=None):
    """`Material` Revit -> `MaterialCardVM`."""
    nom, classe, asset, couleur, coupe, surface = _lecture(doc, materiau)
    return MaterialCardVM(materiau.Id, nom, classe=classe, apparence=asset,
                          couleur=couleur, motif_coupe=coupe,
                          motif_surface=surface, usages=usages)


def rafraichir(doc, materiau, carte_vm):
    """Relit `materiau` et pousse le résultat sur sa card (notifiant).

    Appelé après une sauvegarde de l'éditeur : la card affiche alors ce que
    Revit a RÉELLEMENT accepté (nom sanitizé, `*` de collision, motif refusé),
    et non ce que l'éditeur a demandé.
    """
    if carte_vm is None or materiau is None:
        return
    nom, classe, asset, couleur, coupe, surface = _lecture(doc, materiau)
    carte_vm.rafraichir(nom, classe, asset, couleur, coupe, surface)


# ---------------------------------------------------------------------------
# Catalogues du document : ce que les menus de l'éditeur proposent
# ---------------------------------------------------------------------------


class MotifRef(object):
    """Une entrée du menu « motif » : un `FillPatternElement` du document.

    Porte une `Couche` prototype (grilles, modèle/dessin) que `pour(couleur)`
    recopie à la couleur demandée. La couleur n'appartient pas au motif mais à
    l'emplacement qui le pose — le même remplissage sert en noir en coupe et
    en gris en surface.

    `Id` vaut `InvalidElementId` pour l'entrée « Aucun » : c'est exactement ce
    qu'attend Revit pour retirer un motif.
    """

    def __init__(self, identifiant, prototype=None):
        self.Id = identifiant
        self._prototype = prototype
        self.Nom = prototype.nom if prototype is not None else u'Aucun'

    @property
    def Libelle(self):
        if self._prototype is None:
            return self.Nom
        return self.Nom + (u'  · modèle' if self._prototype.est_modele else u'')

    @property
    def EstModele(self):
        return self._prototype is not None and self._prototype.est_modele

    def pour(self, couleur):
        """La `Couche` à dessiner pour cette couleur. None pour « Aucun »."""
        proto = self._prototype
        if proto is None:
            return None
        return Couche(nom=proto.nom, grilles=proto.grilles,
                      est_modele=proto.est_modele, est_uni=proto.est_uni,
                      rgb=couleur)


class ApparenceRef(object):
    """Une entrée du menu « asset d'apparence »."""

    def __init__(self, identifiant, nom):
        self.Id = identifiant
        self.Nom = nom or u'Aucune'


def _aucun_id():
    return ElementId.InvalidElementId if ElementId is not None else None


def motifs_du_document(doc):
    """Tous les `FillPatternElement`, « Aucun » en tête, triés par nom.

    ponytail: la géométrie de CHAQUE motif est lue à l'ouverture de l'outil,
    pas à l'ouverture de l'éditeur — sinon le menu se peuple à chaque
    double-clic. Un document en compte quelques dizaines ; si un gabarit en
    trimballe des centaines, c'est ici qu'on passe en lecture paresseuse.
    """
    refs = [MotifRef(_aucun_id())]
    if doc is None or FilteredElementCollector is None or FillPatternElement is None:
        return refs
    elements = FilteredElementCollector(doc).OfClass(FillPatternElement)
    trouves = []
    for element in elements.ToElements():
        prototype = couche_depuis_element(element)
        if prototype is None:
            continue
        trouves.append(MotifRef(element.Id, prototype))
    refs.extend(sorted(trouves, key=lambda r: (r.EstModele, r.Nom.lower())))
    return refs


def apparences_du_document(doc):
    """Tous les `AppearanceAssetElement`, « Aucune » en tête, triés par nom."""
    refs = [ApparenceRef(_aucun_id(), u'Aucune')]
    if doc is None or FilteredElementCollector is None \
            or AppearanceAssetElement is None:
        return refs
    elements = FilteredElementCollector(doc).OfClass(AppearanceAssetElement)
    refs.extend(sorted((ApparenceRef(e.Id, e.Name) for e in elements.ToElements()),
                       key=lambda r: r.Nom.lower()))
    return refs
