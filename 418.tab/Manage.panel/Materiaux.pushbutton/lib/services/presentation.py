# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Lecture d'un `Material` Revit -> dictionnaires JSON, prêts pour la page.
#
# Remplace `viewmodels/lecture_materiau.py` et toute la couche ViewModel : la
# page tient son propre état, l'hôte ne lui envoie que de la donnée. Ne sort
# donc d'ici que des types que `json.dumps` accepte — pas un seul objet de
# l'API Revit, les `ElementId` sont réduits à des entiers (cf. `ident`).
#
# Le chemin inverse (entier -> `ElementId`) passe par `Catalogue` : on garde
# les identifiants LUS plutôt que d'en reconstruire, ce qui évite de parier
# sur le constructeur `ElementId(Int64)` depuis IronPython.

try:
    from lib.services import hatch, hatch_svg
except Exception:
    from services import hatch, hatch_svg

try:
    from lib.services.journal import log
except Exception:
    try:
        from services.journal import log
    except Exception:
        def log(gabarit, *args):
            pass

# Un import par nom, et non un bloc unique : un seul nom manquant mettait
# TOUS les autres à None, et le symptôme n'avait rien à voir avec la cause —
# sans FillPatternTarget, par exemple, plus aucun motif n'est reconnu comme
# motif de MODÈLE, donc plus aucun badge et plus aucune règle d'arrière-plan.
AppearanceAssetElement = None
CategoryType = None
ElementId = None
FilteredElementCollector = None
FillPatternElement = None
FillPatternTarget = None
for _nom_type in ('AppearanceAssetElement', 'CategoryType', 'ElementId',
                  'FilteredElementCollector', 'FillPatternElement',
                  'FillPatternTarget'):
    try:
        globals()[_nom_type] = getattr(
            __import__('Autodesk.Revit.DB', fromlist=[str(_nom_type)]),
            _nom_type)
    except Exception:
        log(u'Autodesk.Revit.DB.{} introuvable', _nom_type)

GRIS = (128, 128, 128)
NOIR = (0, 0, 0)

#: « Aucun motif » / « Aucune apparence ». Revit l'écrit
#: `ElementId.InvalidElementId`, dont la valeur est -1 : le même entier sert
#: donc de part et d'autre du pont, sans entrée spéciale.
AUCUN = -1

# Vignette d'une carte, et vignette d'une entrée de catalogue. La seconde est
# plus large : un appareillage de brique ne se reconnaît pas sur deux rangs.
APERCU_MOTIF = (120.0, 26.0)

# Tuile de l'aperçu comparatif de l'éditeur. Assez grande pour montrer un
# appareillage entier.
TUILE_EDITEUR = (150.0, 96.0)

#: Les quatre emplacements de motif d'un matériau, sous la forme
#: (préfixe de face, préfixe de couche). L'attribut Revit se recompose
#: « <face><couche>PatternId » / « …PatternColor ».
EMPLACEMENTS = (
    (u'Cut', u'Background'),
    (u'Cut', u'Foreground'),
    (u'Surface', u'Background'),
    (u'Surface', u'Foreground'),
)

LIBELLES_FACE = ((u'Cut', u'Coupe'), (u'Surface', u'Surface'))
LIBELLES_COUCHE = {u'Background': u'Arrière-plan', u'Foreground': u'Premier plan'}

#: Nom d'attribut Revit -> libellé lisible, pour le message de refus.
#: « 1 propriété refusée : CutForegroundPatternId » ne dit rien à personne ;
#: « Coupe · premier plan (motif) » situe le champ à corriger.
LIBELLES_ATTRIBUTS = {
    'Name': u'Nom',
    'MaterialClass': u'Classe',
    'Color': u'Couleur graphique',
    'Transparency': u'Transparence',
    'Shininess': u'Brillance',
    'Smoothness': u'Lissage',
    'AppearanceAssetId': u'Apparence en rendu',
}


def attribut(face, couche, suffixe):
    """« Cut », « Foreground », « Id » -> « CutForegroundPatternId »."""
    return u'%s%sPattern%s' % (face, couche, suffixe)


def cle(face, couche):
    """La clé d'emplacement vue de la page : « Cut.Foreground »."""
    return u'%s.%s' % (face, couche)


for _face, _nom_face in LIBELLES_FACE:
    for _couche in (u'Background', u'Foreground'):
        _situe = u'%s · %s' % (_nom_face, LIBELLES_COUCHE[_couche].lower())
        LIBELLES_ATTRIBUTS[attribut(_face, _couche, u'Id')] = \
            u'%s (motif)' % _situe
        LIBELLES_ATTRIBUTS[attribut(_face, _couche, u'Color')] = \
            u'%s (couleur)' % _situe


def ident(element_id):
    """`ElementId` -> entier. -1 pour l'invalide, comme Revit.

    `Value` depuis Revit 2024 (Int64), `IntegerValue` avant : on essaie les
    deux plutôt que de parier sur la version.
    """
    if element_id is None:
        return AUCUN
    for nom in ('Value', 'IntegerValue'):
        try:
            return int(getattr(element_id, nom))
        except Exception:
            continue
    try:
        return int(element_id)
    except Exception:
        return AUCUN


def premier(objet, *noms):
    """Première propriété existante parmi `noms`.

    Les motifs de matériau ont été scindés premier plan / arrière-plan en
    2019 : `CutPatternId` est devenu `CutForegroundPatternId`. On accepte les
    deux graphies plutôt que de parier sur la version.
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


def hex_de_rgb(couleur):
    return hatch_svg.hexa(couleur)


def rgb_de_hex(texte, defaut=(0, 0, 0)):
    """« #B0413E » -> (176, 65, 62). `defaut` sur saisie incomplète.

    La page envoie ce que l'utilisateur tape, et une saisie est invalide à
    chaque frappe intermédiaire. On ne veut ni exception ni aperçu qui
    clignote en noir — d'où le repli silencieux.
    """
    brut = (texte or u'').strip().lstrip(u'#')
    if len(brut) != 6:
        return defaut
    try:
        return tuple(int(brut[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return defaut


def entier(valeur):
    try:
        return int(round(float(valeur)))
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Catalogues du document : ce que les menus de l'éditeur proposent
# ---------------------------------------------------------------------------


class Catalogue(object):
    """Les motifs et les apparences du document, lus une fois à l'ouverture.

    Porte les deux sens de la traduction :
      - vers la page, `motifs` / `apparences`, du JSON pur ;
      - vers Revit, `element_id(entier)`, qui rend l'`ElementId` LU.

    Garde aussi les `hatch.Couche` prototypes : l'aperçu de l'éditeur
    redessine un motif à une autre couleur sans retoucher au document.
    """

    def __init__(self, doc):
        self._ids = {}
        self._prototypes = {}
        self.motifs = self._lire_motifs(doc)
        self.apparences = self._lire_apparences(doc)
        self.categories = self._lire_categories(doc)

    # -- vers Revit --------------------------------------------------------

    def element_id(self, identifiant):
        """L'`ElementId` lu pour cet entier, ou None s'il est inconnu.

        None vaut « ne pas écrire » : un identifiant que le document ne
        connaît pas ne doit surtout pas finir dans une transaction.
        """
        return self._ids.get(entier(identifiant))

    def couche(self, identifiant, couleur_hex):
        """La `hatch.Couche` à dessiner pour ce motif à cette couleur.

        None pour « Aucun » — il n'y a alors rien à empiler.
        """
        proto = self._prototypes.get(entier(identifiant))
        if proto is None:
            return None
        return proto.pour(rgb_de_hex(couleur_hex))

    def accepte(self, identifiant, face, couche):
        """Cet emplacement a-t-il le droit de porter ce motif ?

        Un seul des quatre admet un motif de MODÈLE : le premier plan de
        SURFACE. Les motifs de coupe sont en taille papier — Revit refuse
        `CutForegroundPatternId` dès qu'on y pose un motif de modèle — et un
        arrière-plan l'est toujours aussi.
        """
        if accepte_modele(face, couche):
            return True
        proto = self._prototypes.get(entier(identifiant))
        return proto is None or not proto.est_modele

    # -- lecture -----------------------------------------------------------

    def _lire_motifs(self, doc):
        """Tous les `FillPatternElement`, « Aucun » en tête, triés par nom.

        ponytail: la géométrie de CHAQUE motif est lue à l'ouverture de
        l'outil, et sa vignette rendue dans la foulée. Un document en compte
        quelques dizaines ; si un gabarit en trimballe des centaines, c'est
        ici qu'on passe en rendu paresseux (ordre `apercu_motif`).
        """
        self._prototypes[AUCUN] = None
        entrees = [{'id': AUCUN, 'nom': u'Aucun', 'type': u'',
                    'modele': False, 'svg': u''}]
        if doc is None or FilteredElementCollector is None \
                or FillPatternElement is None:
            return entrees
        trouves = []
        for element in FilteredElementCollector(doc) \
                .OfClass(FillPatternElement).ToElements():
            prototype = _couche_depuis_element(element)
            if prototype is None:
                continue
            identifiant = ident(element.Id)
            self._ids[identifiant] = element.Id
            self._prototypes[identifiant] = prototype
            trouves.append({
                'id': identifiant,
                'nom': prototype.nom,
                'modele': prototype.est_modele,
                'type': u'modèle' if prototype.est_modele else u'dessin',
                'svg': hatch_svg.vignette([prototype.pour(NOIR)],
                                          *APERCU_MOTIF),
            })
        # Les motifs de dessin d'abord : ce sont les seuls que trois des
        # quatre emplacements acceptent.
        entrees.extend(sorted(trouves,
                              key=lambda e: (e['modele'], e['nom'].lower())))
        modeles = sum(1 for e in trouves if e['modele'])
        log(u'motifs du document : {} de dessin, {} de modèle',
            len(trouves) - modeles, modeles)
        return entrees

    def _lire_categories(self, doc):
        """Catégories de MODÈLE qui contiennent au moins un élément.

        Alimente la portée de l'onglet Remplacer. On liste ce qui est
        RÉELLEMENT dans la maquette plutôt que les ~200 catégories de Revit,
        sinon la liste est inutilisable.

        ponytail: une requête par catégorie, mais `FirstElementId()` s'arrête
        au premier élément trouvé — bien moins cher qu'un balayage complet
        avec regroupement. Si l'ouverture de l'outil devient lente sur une
        grosse maquette, c'est le premier endroit à regarder.
        """
        if doc is None or FilteredElementCollector is None \
                or ElementId is None:
            return []
        presentes = []
        for categorie in doc.Settings.Categories:
            try:
                if not _est_categorie_de_modele(categorie):
                    continue
                collecteur = FilteredElementCollector(doc) \
                    .OfCategoryId(categorie.Id)
                if collecteur.FirstElementId() == ElementId.InvalidElementId:
                    continue
                identifiant = ident(categorie.Id)
                self._ids[identifiant] = categorie.Id
                presentes.append({'id': identifiant, 'nom': categorie.Name})
            except Exception:
                continue      # catégorie non filtrable (annotation, interne)
        return sorted(presentes, key=lambda c: c['nom'])

    def _lire_apparences(self, doc):
        """Tous les `AppearanceAssetElement`, « Aucune » en tête."""
        entrees = [{'id': AUCUN, 'nom': u'Aucune'}]
        if doc is None or FilteredElementCollector is None \
                or AppearanceAssetElement is None:
            return entrees
        trouves = []
        for element in FilteredElementCollector(doc) \
                .OfClass(AppearanceAssetElement).ToElements():
            identifiant = ident(element.Id)
            self._ids[identifiant] = element.Id
            trouves.append({'id': identifiant, 'nom': element.Name})
        entrees.extend(sorted(trouves, key=lambda e: e['nom'].lower()))
        return entrees


def accepte_modele(face, couche):
    """Le premier plan de surface, et lui seul, admet un motif de modèle."""
    return face == u'Surface' and couche == u'Foreground'


def contrainte(face, couche):
    """Phrase affichée dans le sélecteur quand le modèle est exclu."""
    if accepte_modele(face, couche):
        return u''
    if face == u'Cut':
        return (u'Motifs de dessin uniquement — un motif de coupe est en '
                u'taille papier, Revit y refuse les motifs de modèle.')
    return (u'Motifs de dessin uniquement — Revit réserve les motifs de '
            u'modèle au premier plan de surface.')


def _est_categorie_de_modele(categorie):
    """Sans `CategoryType`, on ne trie pas : mieux vaut une liste trop longue
    qu'une liste vide qui ferait croire à une maquette sans catégories."""
    if CategoryType is None:
        return True
    return categorie.CategoryType == CategoryType.Model


def _couche_depuis_element(element):
    """`FillPatternElement` -> `hatch.Couche` prête à dessiner, sans couleur."""
    if element is None:
        return None
    try:
        remplissage = element.GetFillPattern()
    except Exception:
        # Motif illisible : on garde le nom pour le menu, rien à dessiner.
        return hatch.Couche(nom=element.Name)
    if remplissage.IsSolidFill:
        return hatch.Couche(nom=element.Name, est_uni=True)
    est_modele = False
    if FillPatternTarget is None:
        log(u'FillPatternTarget absent : « {} » sera classé motif de dessin',
            element.Name)
    else:
        try:
            est_modele = remplissage.Target == FillPatternTarget.Model
        except Exception as erreur:
            log(u'Target illisible sur « {} » : {}', element.Name, erreur)
    grilles = [hatch.depuis_fill_grid(g) for g in remplissage.GetFillGrids()]
    return hatch.Couche(nom=element.Name, grilles=grilles,
                        est_modele=est_modele)


# ---------------------------------------------------------------------------
# Un matériau : la carte affichée dans les trois onglets
# ---------------------------------------------------------------------------


def _couches_de_face(materiau, face, couleur, catalogue):
    """Les deux couches d'une face, arrière-plan d'abord.

    Chaque couche a son propre motif ET sa propre couleur. Les graphies sans
    Foreground/Background sont celles d'avant 2019, gardées en repli.
    """
    fond = catalogue.couche(
        ident(premier(materiau, attribut(face, u'Background', u'Id'))),
        hex_de_rgb(rgb(premier(materiau, attribut(face, u'Background',
                                                  u'Color')),
                       defaut=couleur)))
    avant = catalogue.couche(
        ident(premier(materiau, attribut(face, u'Foreground', u'Id'),
                      face + u'PatternId')),
        hex_de_rgb(rgb(premier(materiau, attribut(face, u'Foreground',
                                                  u'Color'),
                               face + u'PatternColor'), defaut=couleur)))
    return [fond, avant]


def _nom_de_motif(couches):
    """« Briques sur Uni » — premier plan d'abord, comme on le lit."""
    noms = [c.nom for c in (couches[1], couches[0])
            if c is not None and c.nom]
    return u' sur '.join(noms) if noms else u'Aucun'


def _face(materiau, face, couleur, catalogue):
    couches = _couches_de_face(materiau, face, couleur, catalogue)
    return {'nom': _nom_de_motif(couches),
            'svg': hatch_svg.vignette(couches)}


def _apparence(doc, materiau):
    """Nom de l'asset d'apparence, vide s'il n'y en a pas."""
    if doc is None:
        return u''
    try:
        element = doc.GetElement(materiau.AppearanceAssetId)
        return element.Name if element is not None else u''
    except Exception:
        return u''


def usages_json(ligne):
    """`MaterialService.LigneRapport` -> ce que la page affiche.

    `texte` vide quand rien n'a été compté (hors Revit) : la colonne reste
    alors vide, au lieu d'annoncer « Non utilisé » à tort.
    """
    if ligne is None:
        return {'types': 0, 'instances': 0, 'total': 0, 'texte': u''}
    return {'types': ligne.Types, 'instances': ligne.Instances,
            'total': ligne.Total, 'texte': ligne.Detail or u'Non utilisé'}


def carte(doc, materiau, catalogue, usages=None):
    """`Material` Revit -> le dictionnaire d'une carte."""
    couleur = rgb(premier(materiau, 'Color'))
    return {
        'id': ident(materiau.Id),
        'nom': materiau.Name,
        'classe': premier(materiau, 'MaterialClass') or u'Sans classe',
        'apparence': _apparence(doc, materiau) or u'Aucune',
        'couleur': hex_de_rgb(couleur),
        'usages': usages_json(usages),
        'coupe': _face(materiau, u'Cut', couleur, catalogue),
        'surface': _face(materiau, u'Surface', couleur, catalogue),
    }


# ---------------------------------------------------------------------------
# L'éditeur : lire, comparer, écrire
# ---------------------------------------------------------------------------


def valeurs_lues(materiau):
    """Tous les attributs pilotés par l'éditeur, dans la forme de la PAGE.

    Couleurs en « #RRGGBB », identifiants en entiers : c'est la forme dans
    laquelle la page les renvoie, donc la seule dans laquelle on peut les
    comparer sans convertir deux fois.
    """
    couleur = rgb(premier(materiau, 'Color'))
    valeurs = {
        'Name': materiau.Name,
        'MaterialClass': premier(materiau, 'MaterialClass') or u'',
        'Color': hex_de_rgb(couleur),
        'Transparency': entier(premier(materiau, 'Transparency') or 0),
        'Shininess': entier(premier(materiau, 'Shininess') or 0),
        'Smoothness': entier(premier(materiau, 'Smoothness') or 0),
        'AppearanceAssetId': ident(premier(materiau, 'AppearanceAssetId')),
    }
    for face, couche in EMPLACEMENTS:
        valeurs[attribut(face, couche, u'Id')] = ident(
            premier(materiau, attribut(face, couche, u'Id')))
        valeurs[attribut(face, couche, u'Color')] = hex_de_rgb(
            rgb(premier(materiau, attribut(face, couche, u'Color')),
                defaut=couleur))
    return valeurs


def editeur(doc, materiau, catalogue):
    """L'état complet que la page d'édition affiche à l'ouverture."""
    valeurs = valeurs_lues(materiau)
    emplacements = {}
    for face, couche in EMPLACEMENTS:
        emplacements[cle(face, couche)] = {
            'face': face,
            'couche': couche,
            'libelle': LIBELLES_COUCHE[couche],
            'titre': u'%s · %s' % (dict(LIBELLES_FACE)[face],
                                   LIBELLES_COUCHE[couche].lower()),
            'motif': valeurs[attribut(face, couche, u'Id')],
            'couleur': valeurs[attribut(face, couche, u'Color')],
            'accepte_modele': accepte_modele(face, couche),
            'contrainte': contrainte(face, couche),
        }
    return {'id': ident(materiau.Id), 'valeurs': valeurs,
            'emplacements': emplacements}


def modifiees(valeurs_page, materiau):
    """Ce que la page a changé par rapport à ce que Revit porte MAINTENANT.

    Relire plutôt que mémoriser l'état d'ouverture : après un enregistrement
    partiellement refusé, ce qui est passé n'a plus à être réécrit, et ce qui
    a été refusé reste en attente. Le ViewModel d'avant tenait ce ré-ancrage à
    la main.
    """
    actuelles = valeurs_lues(materiau)
    changees = {}
    for nom, valeur in (valeurs_page or {}).items():
        if nom not in actuelles:
            continue                       # clé inconnue : jamais écrite
        if _normaliser(valeur, actuelles[nom]) != actuelles[nom]:
            changees[nom] = valeur
    return changees


def _normaliser(valeur, reference):
    """Met `valeur` dans le type de `reference` pour une comparaison juste.

    La page renvoie les curseurs en nombres JSON (donc en `float` après
    `json.loads`) et les identifiants en entiers : sans ça, 0.0 != 0 ferait
    réécrire une transparence que personne n'a touchée.
    """
    if isinstance(reference, bool):
        return bool(valeur)
    if isinstance(reference, int):
        return entier(valeur)
    if valeur is None:
        return u''
    # Une couleur ne diffère pas par sa casse : `<input type="color">` rend du
    # minuscule, la lecture Revit du majuscule, et sans ça chaque ouverture
    # d'éditeur réécrirait les cinq couleurs sans que rien n'ait bougé.
    if isinstance(reference, type(u'')) and reference.startswith(u'#'):
        return valeur.upper()
    return valeur


def valeurs_revit(valeurs, catalogue):
    """Forme page -> forme Revit, pour `MaterialService.enregistrer`.

    Les couleurs redeviennent des triplets (le service les convertit en
    `Color`), les identifiants redeviennent des `ElementId` LUS. Un
    identifiant inconnu du catalogue est ÉCARTÉ : mieux vaut ne pas écrire
    que d'écrire n'importe quoi dans une transaction.
    """
    sortie = {}
    for nom, valeur in (valeurs or {}).items():
        if nom.endswith('Color') or nom == 'Color':
            sortie[nom] = rgb_de_hex(valeur)
        elif nom.endswith('Id'):
            element_id = catalogue.element_id(valeur)
            if element_id is None and entier(valeur) != AUCUN:
                log(u'identifiant {} inconnu du catalogue : {} non écrit',
                    valeur, nom)
                continue
            # « Aucun » : `InvalidElementId` est exactement ce qu'attend Revit
            # pour retirer un motif ou une apparence.
            sortie[nom] = element_id if element_id is not None \
                else (ElementId.InvalidElementId if ElementId is not None
                      else None)
        elif nom in ('Transparency', 'Shininess', 'Smoothness'):
            sortie[nom] = entier(valeur)
        else:
            sortie[nom] = valeur
    return sortie


def libelles(attributs):
    """Noms d'attributs refusés -> libellés lisibles, triés."""
    return sorted(LIBELLES_ATTRIBUTS.get(nom, nom) for nom in attributs or [])


def tuiles(catalogue, fond, premier_plan, echelles=None):
    """L'aperçu comparatif d'une face : une tuile par échelle de vue.

    `fond` / `premier_plan` : `{'motif': entier, 'couleur': '#RRGGBB'}`, tels
    que la page les tient. Un motif de DESSIN sort identique aux quatre
    échelles — c'est le comportement de Revit, pas un défaut d'aperçu.
    """
    couches = [catalogue.couche((fond or {}).get('motif'),
                                (fond or {}).get('couleur')),
               catalogue.couche((premier_plan or {}).get('motif'),
                                (premier_plan or {}).get('couleur'))]
    largeur, hauteur = TUILE_EDITEUR
    return [{'libelle': u'1:%d' % echelle,
             'svg': hatch_svg.vignette(couches, largeur, hauteur, echelle)}
            for echelle in (echelles or hatch.ECHELLES_APERCU)]
