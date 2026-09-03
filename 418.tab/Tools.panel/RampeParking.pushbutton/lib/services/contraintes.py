# -*- coding: utf-8 -*-
"""Lecture des contraintes de rampe de parking depuis la maquette.

Deux entrées, et deux seulement :

* **DEUX niveaux sélectionnés** — la dénivelée est exacte (`|Δ Elevation|`) ;
  c'est le cas courant en parking et le seul où l'on ne déduit rien.
* **UNE rampe ou UN sol** — les niveaux bas/haut sont lus sur l'élément,
  longueur et largeur viennent de son encombrement.

Tout ce qui touche à l'API Revit est isolé derrière le `try/except` d'en-tête.
Le calcul (pente, verdict, URL) est pur et testé hors Revit par
`tests/test_contraintes.py`.
"""
from __future__ import unicode_literals, division

try:
    from Autodesk.Revit.DB import Level, StorageType
except Exception:
    Level = None
    StorageType = None


# Pied vers mètre : exact par définition. Pas d'appel `UnitUtils` — une
# constante se teste hors Revit, une conversion d'API non.
FEET_TO_M = 0.3048

BASE_TOOLBOX = 'https://toolbox.carmi-family.com/rampe-parking'

AIDE_SELECTION = (
    u'Sélectionnez soit DEUX niveaux (la dénivelée est alors exacte), '
    u'soit UNE rampe ou UN sol.')


# ----------------------------------------------------------------------
# Calcul pur — aucune dépendance Revit, testé par tests/test_contraintes.py
# ----------------------------------------------------------------------

def nombre(texte):
    """Lit un nombre saisi dans la fenêtre. `None` si ce n'en est pas un.

    Accepte la virgule décimale : c'est un outil francophone et Revit
    lui-même affiche « 3,20 m ».
    """
    if texte is None:
        return None
    if isinstance(texte, (int, float)):
        return float(texte) if texte > 0 else None
    try:
        valeur = float(texte.strip().replace(',', '.'))
    except (AttributeError, TypeError, ValueError):
        return None
    return valeur if valeur > 0 else None


def pente_pct(hauteur_m, longueur_m):
    """Pente en %. `None` si l'un des deux termes manque."""
    if not hauteur_m or not longueur_m or longueur_m <= 0:
        return None
    return (hauteur_m / longueur_m) * 100.0


def verdict(pente):
    """Seuils NF P91-100 : `(niveau, libellé)`.

    Recopie délibérée de `slopeStatut()` dans
    `ArchitectToolbox/src/pages/RampeParking.jsx` — le but est un retour
    immédiat dans Revit sans attendre le chargement de la page. Les deux
    doivent bouger ensemble ; si un troisième copiste apparaît, c'est le
    signal qu'il faut une source unique côté web (endpoint ou JSON partagé).
    """
    if pente is None:
        return ('', u'')
    # Arrondi AVANT comparaison : la dénivelée passe par les pieds Revit, donc
    # 3,00 m sur 20,00 m tombe à 15,00000005 % et basculait en « toléré » alors
    # que la fenêtre affiche « 15,0 % ». Deux décimales, comme le champ web.
    pente = round(pente, 2)
    if pente <= 15:
        return ('ok', u'≤ 15 % — NF P91-100')
    if pente <= 17:
        return ('warning', u'≤ 17 % — toléré')
    if pente <= 20:
        return ('warning', u'≤ 20 % — cas particulier')
    return ('error', u'Non conforme (> 20 %)')


def url_toolbox(hauteur_m=None, largeur_m=None, pente=None, base=BASE_TOOLBOX):
    """Lien profond vers le calculateur web.

    Contrat, côté `RampeParking.jsx` : `h` hauteur totale à franchir (m),
    `w` largeur (m), `p` pente du tronçon de rampe (%). Seules les valeurs
    strictement positives sont transmises — pour le reste la page garde ses
    propres défauts, et sans aucun paramètre elle se comporte comme avant.

    On n'envoie PAS de longueur : la page raisonne en hauteur + pente en mode
    réglementaire, la longueur y est une valeur dérivée. La division est donc
    faite ici.
    """
    params = []
    for cle, valeur in (('h', hauteur_m), ('w', largeur_m), ('p', pente)):
        try:
            v = float(valeur)
        except (TypeError, ValueError):
            continue
        if v <= 0:
            continue
        params.append('{}={:.2f}'.format(cle, v))
    if not params:
        return base
    return '{}?{}'.format(base, '&'.join(params))


class Contraintes(object):
    """Ce que la maquette a livré, plus de quoi l'afficher tel quel.

    `Avertissement` n'est pas décoratif : il dit à l'utilisateur ce qui a été
    déduit plutôt que lu (décalages ignorés, encombrement pris pour hauteur).
    Les trois valeurs restent éditables dans la fenêtre — c'est le rattrapage.
    """

    def __init__(self, denivelee=None, longueur=None, largeur=None,
                 source=u'', parametres=None, avertissement=u''):
        self.Denivelee = denivelee
        self.Longueur = longueur
        self.Largeur = largeur
        self.Source = source
        self.Parametres = list(parametres or [])
        self.Avertissement = avertissement


# ----------------------------------------------------------------------
# Lecture Revit
# ----------------------------------------------------------------------

def _valeur_affichee(parametre):
    """La valeur telle que Revit l'affiche, unités du projet comprises.

    `AsValueString()` d'abord, `AsString()` pour les paramètres texte. On ne
    reformate rien : cette liste est là pour être LUE, pas pour alimenter un
    calcul.
    """
    for lecture in (parametre.AsValueString, parametre.AsString):
        try:
            valeur = lecture()
        except Exception:
            continue
        if valeur:
            return valeur
    return u''


def parametres_lisibles(element):
    """`[(nom, valeur), ...]` des paramètres d'instance, triés par nom."""
    lignes = []
    for parametre in (getattr(element, 'Parameters', None) or []):
        try:
            nom = parametre.Definition.Name
        except Exception:
            continue                      # paramètre sans définition lisible
        lignes.append((nom, _valeur_affichee(parametre)))
    return sorted(lignes, key=lambda ligne: ligne[0].lower())


def _niveaux_references(element, doc):
    """Niveaux vers lesquels pointent les paramètres de l'élément, triés par
    élévation et dédoublonnés.

    Générique VOLONTAIREMENT : les `BuiltInParameter` de niveau ne sont pas
    les mêmes pour une rampe, un sol et une famille in-situ. Chercher tout
    paramètre qui POINTE vers un `Level` couvre les trois sans les énumérer,
    et survit aux catégories auxquelles on n'a pas pensé.
    """
    if Level is None or StorageType is None or doc is None:
        return []
    trouves = {}
    for parametre in (getattr(element, 'Parameters', None) or []):
        try:
            if parametre.StorageType != StorageType.ElementId:
                continue
            cible = doc.GetElement(parametre.AsElementId())
        except Exception:
            continue
        if isinstance(cible, Level):
            trouves[cible.Id] = cible     # ElementId est hashable côté .NET
    return sorted(trouves.values(), key=lambda niveau: niveau.Elevation)


def _encombrement(element):
    """`(longueur, largeur, hauteur)` en mètres depuis la bounding box.

    ponytail: la bbox est alignée sur les axes du projet — une rampe en biais
    est donc surestimée, et la « longueur » est celle de l'emprise, pas du
    tracé. Le champ Longueur est éditable dans la fenêtre, c'est le rattrapage
    prévu. Passer par la géométrie (courbe de tracé du `Ramp`, ou les faces du
    `Solid`) si ça devient gênant.
    """
    try:
        bbox = element.get_BoundingBox(None)
    except Exception:
        bbox = None
    if bbox is None:
        return (None, None, None)
    dx = abs(bbox.Max.X - bbox.Min.X) * FEET_TO_M
    dy = abs(bbox.Max.Y - bbox.Min.Y) * FEET_TO_M
    dz = abs(bbox.Max.Z - bbox.Min.Z) * FEET_TO_M
    return (max(dx, dy), min(dx, dy), dz)


def _designation(element):
    """« Catégorie — Nom » pour la ligne d'en-tête de la fenêtre."""
    categorie = u''
    try:
        categorie = element.Category.Name
    except Exception:
        pass
    nom = u''
    try:
        nom = element.Name
    except Exception:
        pass
    if categorie and nom:
        return u'{} — {}'.format(categorie, nom)
    return categorie or nom or u'Élément sélectionné'


def _depuis_niveaux(niveaux):
    niveaux = sorted(niveaux, key=lambda niveau: niveau.Elevation)
    bas, haut = niveaux[0], niveaux[-1]
    avertissement = u''
    if len(niveaux) > 2:
        avertissement = (
            u'{} niveaux sélectionnés : la dénivelée retenue va du plus bas '
            u'au plus haut.'.format(len(niveaux)))
    return Contraintes(
        denivelee=abs(haut.Elevation - bas.Elevation) * FEET_TO_M,
        source=u'Niveaux « {} » → « {} »'.format(bas.Name, haut.Name),
        parametres=parametres_lisibles(haut),
        avertissement=avertissement)


def _depuis_element(element, doc):
    longueur, largeur, hauteur_bbox = _encombrement(element)
    niveaux = _niveaux_references(element, doc)
    if len(niveaux) >= 2:
        denivelee = abs(niveaux[-1].Elevation - niveaux[0].Elevation) * FEET_TO_M
        avertissement = (
            u'Dénivelée prise entre les niveaux « {} » et « {} » : les '
            u'décalages ne sont PAS comptés. Corrigez la hauteur si besoin.'
            .format(niveaux[0].Name, niveaux[-1].Name))
    else:
        denivelee = hauteur_bbox
        avertissement = (
            u'Aucun couple de niveaux sur cet élément : la hauteur vient de '
            u'son encombrement vertical, épaisseur comprise.')
    return Contraintes(denivelee, longueur, largeur,
                       source=_designation(element),
                       parametres=parametres_lisibles(element),
                       avertissement=avertissement)


def lire(elements, doc):
    """Contraintes déduites de la sélection Revit. Ne lève jamais."""
    elements = [e for e in (elements or []) if e is not None]
    niveaux = [e for e in elements
               if Level is not None and isinstance(e, Level)]
    if len(niveaux) >= 2:
        return _depuis_niveaux(niveaux)
    if len(elements) == 1:
        return _depuis_element(elements[0], doc)
    return Contraintes(avertissement=AIDE_SELECTION)
