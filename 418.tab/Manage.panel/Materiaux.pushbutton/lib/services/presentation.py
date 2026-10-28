# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

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
Material = None
StorageType = None
for _nom_type in ('AppearanceAssetElement', 'CategoryType', 'ElementId',
                  'FilteredElementCollector', 'FillPatternElement',
                  'FillPatternTarget', 'Material', 'StorageType'):
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

# Vignette d'une entrée de catalogue. Plus large que celle des tableaux : un
# appareillage de brique ne se reconnaît pas sur deux rangs.
APERCU_MOTIF = (120.0, 26.0)

#: La tuile d'un matériau, et son grossissement. 256×112 à zoom 4, c'est
#: EXACTEMENT 64×28 à zoom 1 — même nombre de segments, donc même poids dans
#: le message. Une seule tuile sert les deux usages : la carte l'agrandit,
#: les tableaux la réduisent d'autant, et comme elle est en `slice` aucun des
#: deux ne la déforme.
TUILE_MATERIAU = (256.0, 112.0)
ZOOM_MATERIAU = 4.0

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
    'MaterialCategory': u'Catégorie',
    'Color': u'Couleur graphique',
    'Transparency': u'Transparence',
    'Shininess': u'Brillance',
    'Smoothness': u'Lissage',
    'UseRenderAppearanceForShading': u'Utiliser l\'apparence en rendu',
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

    Rien de ce qui se DESSINE n'est rendu à la construction : les vignettes
    de motif attendent le premier accès à `motifs` (l'éditeur, qui s'ouvre
    rarement) et les tuiles de matériau sont mémorisées à mesure. C'est
    l'ouverture de l'outil qui est en jeu — elle se faisait précéder d'une
    centaine de rendus dont personne ne se servait.
    """

    def __init__(self, doc):
        self._doc = doc
        self._ids = {}
        self._prototypes = {}
        self._vignettes = {}
        self._motifs_rendus = False
        self._motifs = self._lire_motifs(doc)
        self.apparences = self._lire_apparences(doc)
        #: Posées par `poser_categories`, au retour du parcours d'inventaire.
        self.categories = []

    # -- ce que la page lit ------------------------------------------------

    @property
    def motifs(self):
        """Les motifs du document, vignette comprise — rendues au PREMIER
        accès, et une seule fois.

        Seul l'éditeur les affiche, et la fenêtre principale ne les reçoit
        même pas. Les dessiner à l'ouverture faisait payer à tout le monde
        (un gabarit en porte une centaine, certaines très denses) ce dont
        presque personne ne se sert dans la session.
        """
        if not self._motifs_rendus:
            self._motifs_rendus = True
            for entree in self._motifs:
                prototype = self._prototypes.get(entree['id'])
                if prototype is not None:
                    entree['svg'] = hatch_svg.vignette(
                        [prototype.pour(NOIR)], *APERCU_MOTIF)
        return self._motifs

    def tuile(self, cle, dessiner):
        """La tuile mémorisée pour cette combinaison, dessinée au besoin.

        Les matériaux d'un modèle se partagent une poignée de combinaisons
        (motif, couleur) par face — « Aucun » à lui seul en couvre la moitié.
        Sans ce cache, la même tuile est redessinée une fois par matériau.

        La valeur rendue est PARTAGÉE : elle part telle quelle dans plusieurs
        cartes, et personne ne la modifie.
        """
        if cle not in self._vignettes:
            self._vignettes[cle] = dessiner()
        return self._vignettes[cle]

    def poser_categories(self, ids):
        """Les catégories de MODÈLE vues par le parcours d'inventaire.

        On liste ce qui est RÉELLEMENT dans la maquette plutôt que les ~200
        catégories de Revit, sinon la liste est inutilisable. C'est le
        parcours qui le dit maintenant : le faire ici demandait une requête
        par catégorie, et prouver qu'une catégorie est vide coûte un
        parcours complet.
        """
        vues = set(ident(i) for i in ids or [])
        presentes = []
        if self._doc is not None:
            for categorie in self._doc.Settings.Categories:
                try:
                    if not _est_categorie_de_modele(categorie):
                        continue
                    identifiant = ident(categorie.Id)
                    if identifiant not in vues:
                        continue
                    self._ids[identifiant] = categorie.Id
                    presentes.append({'id': identifiant,
                                      'nom': categorie.Name})
                except Exception:
                    continue      # catégorie illisible (annotation, interne)
        self.categories = sorted(presentes, key=lambda c: c['nom'])
        return self.categories

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

        La géométrie est lue ici — elle sert aux tuiles de matériau — mais
        PAS la vignette du menu, qui attend le premier accès à `motifs`.
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
                'svg': u'',           # rendue par la propriété `motifs`
            })
        # Les motifs de dessin d'abord : ce sont les seuls que trois des
        # quatre emplacements acceptent.
        entrees.extend(sorted(trouves,
                              key=lambda e: (e['modele'], e['nom'].lower())))
        modeles = sum(1 for e in trouves if e['modele'])
        log(u'motifs du document : {} de dessin, {} de modèle',
            len(trouves) - modeles, modeles)
        return entrees

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


def titre_emplacement(face, couche):
    """« Coupe · premier plan » — le titre de la fenêtre de choix."""
    return u'%s · %s' % (dict(LIBELLES_FACE).get(face, face),
                         LIBELLES_COUCHE.get(couche, couche).lower())


def proposables(catalogue, face, couche, courant=None):
    """Les motifs que CET emplacement a le droit d'offrir.

    Filtrer en amont plutôt que laisser choisir puis récolter un « refusé par
    Revit » à l'enregistrement, où plus rien ne dit pourquoi.

    Le motif DÉJÀ en place reste proposé même s'il enfreint la règle
    (matériau hérité d'un vieux gabarit, fichier lié) : sinon la fenêtre
    s'ouvre sur du vide et le premier changement de couleur effacerait
    silencieusement le motif.
    """
    motifs = list(catalogue.motifs if catalogue is not None else [])
    if accepte_modele(face, couche):
        return motifs
    offerts = [motif for motif in motifs if not motif['modele']]
    courant = entier(courant)
    if all(motif['id'] != courant for motif in offerts):
        enfreint = next((motif for motif in motifs
                         if motif['id'] == courant), None)
        if enfreint is not None:
            offerts.insert(0, enfreint)
    return offerts


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


def _cles_de_face(materiau, face, couleur):
    """Tout ce dont le dessin d'une face dépend : motif et couleur de chaque
    couche, arrière-plan d'abord.

    Sorti de `_couches_de_face` pour servir de CLÉ de cache : deux matériaux
    qui s'accordent sur ces quatre valeurs donnent la même tuile au pixel.
    Les graphies sans Foreground/Background sont celles d'avant 2019,
    gardées en repli.
    """
    return (
        ident(premier(materiau, attribut(face, u'Background', u'Id'))),
        hex_de_rgb(rgb(premier(materiau, attribut(face, u'Background',
                                                  u'Color')),
                       defaut=couleur)),
        ident(premier(materiau, attribut(face, u'Foreground', u'Id'),
                      face + u'PatternId')),
        hex_de_rgb(rgb(premier(materiau, attribut(face, u'Foreground',
                                                  u'Color'),
                               face + u'PatternColor'), defaut=couleur)),
    )


def _couches_de_face(cles, catalogue):
    """Les deux couches d'une face, arrière-plan d'abord. Chaque couche a son
    propre motif ET sa propre couleur."""
    id_fond, couleur_fond, id_avant, couleur_avant = cles
    return [catalogue.couche(id_fond, couleur_fond),
            catalogue.couche(id_avant, couleur_avant)]


def _nom_de_motif(couches):
    """« Briques sur Uni » — premier plan d'abord, comme on le lit."""
    noms = [c.nom for c in (couches[1], couches[0])
            if c is not None and c.nom]
    return u' sur '.join(noms) if noms else u'Aucun'


def _face(materiau, face, couleur, catalogue):
    cles = _cles_de_face(materiau, face, couleur)

    def dessiner():
        couches = _couches_de_face(cles, catalogue)
        largeur, hauteur = TUILE_MATERIAU
        return {'nom': _nom_de_motif(couches),
                'svg': hatch_svg.vignette(couches, largeur, hauteur,
                                          zoom=ZOOM_MATERIAU)}

    return catalogue.tuile(cles, dessiner)


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
    """`Material` Revit -> le dictionnaire d'une carte.

    `transparence`, `brillance` et `lissage` ne servent pas à l'éditeur ici :
    ce sont les trois paramètres dont la carte tire sa sphère d'aperçu. Ils
    ne coûtent que trois entiers, là où une image en coûterait mille.
    """
    couleur = rgb(premier(materiau, 'Color'))
    return {
        'id': ident(materiau.Id),
        'nom': materiau.Name,
        'classe': premier(materiau, 'MaterialClass') or u'Sans classe',
        'apparence': _apparence(doc, materiau) or u'Aucune',
        'couleur': hex_de_rgb(couleur),
        'transparence': entier(premier(materiau, 'Transparency') or 0),
        'brillance': entier(premier(materiau, 'Shininess') or 0),
        'lissage': entier(premier(materiau, 'Smoothness') or 0),
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
        'MaterialCategory': premier(materiau, 'MaterialCategory') or u'',
        'Color': hex_de_rgb(couleur),
        'Transparency': entier(premier(materiau, 'Transparency') or 0),
        'Shininess': entier(premier(materiau, 'Shininess') or 0),
        'Smoothness': entier(premier(materiau, 'Smoothness') or 0),
        # Revit coche « Utiliser l'apparence de rendu » et la couleur
        # d'ombrage cesse d'être lue : la page doit pouvoir le dire, sinon on
        # modifie une couleur qui n'a plus d'effet sans comprendre pourquoi.
        'UseRenderAppearanceForShading': bool(
            premier(materiau, 'UseRenderAppearanceForShading')),
        'AppearanceAssetId': ident(premier(materiau, 'AppearanceAssetId')),
    }
    for face, couche in EMPLACEMENTS:
        valeurs[attribut(face, couche, u'Id')] = ident(
            premier(materiau, attribut(face, couche, u'Id')))
        valeurs[attribut(face, couche, u'Color')] = hex_de_rgb(
            rgb(premier(materiau, attribut(face, couche, u'Color')),
                defaut=couleur))
    return valeurs


def _texte_parametre(parametre):
    """Ce qu'un paramètre a à montrer : sa chaîne, ou sa valeur formatée.

    `AsValueString` rend le coût avec sa devise et son séparateur, soit ce
    que Revit affiche — on ne reformate rien ici.
    """
    try:
        if StorageType is not None \
                and parametre.StorageType == StorageType.String:
            return parametre.AsString() or u''
        return parametre.AsValueString() or u''
    except Exception:
        return u''


def identite(materiau):
    """Les paramètres de l'onglet « Identité » de Revit, dans son ordre à lui.

    La liste vient de `Material.GetIdentityParameterIds()` : c'est Revit qui
    dit lesquels sont des paramètres d'identité, pas nous. L'écrire à la main
    aurait vieilli à la première version — et elle aurait été fausse dans une
    langue sur deux.

    Seuls les paramètres de type TEXTE sont annoncés modifiables : un coût
    porte une devise et une unité, et se poser sans elles ferait écrire un
    nombre dans la monnaie du voisin.

    ponytail: le reste (nombres, cases, listes) est rendu en lecture. Les
    brancher demande une conversion par type de stockage et la gestion des
    unités de projet — c'est le vrai morceau, et il ne se devine pas depuis
    une maquette vide.
    """
    sortie = []
    if Material is None:
        return sortie
    try:
        attendus = [ident(i) for i in Material.GetIdentityParameterIds()]
    except Exception as erreur:
        log(u'paramètres d\'identité illisibles : {}', erreur)
        return sortie
    rang = dict((identifiant, index)
                for index, identifiant in enumerate(attendus))
    for parametre in materiau.Parameters:
        try:
            identifiant = ident(parametre.Definition.Id)
            if identifiant not in rang:
                continue
            texte = (StorageType is not None
                     and parametre.StorageType == StorageType.String)
            sortie.append({
                'id': identifiant,
                'nom': parametre.Definition.Name,
                'valeur': _texte_parametre(parametre),
                'modifiable': bool(texte and not parametre.IsReadOnly),
            })
        except Exception:
            continue          # paramètre illisible : il ne bloque pas les autres
    return sorted(sortie, key=lambda p: rang.get(p['id'], 999))


# ---------------------------------------------------------------------------
# L'apparence en rendu : ce que l'asset donne à voir
# ---------------------------------------------------------------------------
#
# Revit n'expose AUCUNE image de prévisualisation de matériau : ni sur
# `Material`, ni sur `AppearanceAssetElement`. La sphère du navigateur de
# matériaux est rendue par un moteur qui ne sort pas de l'application.
#
# On lit donc l'asset et on en rejoue les trois traits qui se voient à
# l'œil : la couleur diffuse, le brillant, et la texture s'il y en a une. Le
# reste — relief, réflexion, anisotropie — demanderait le moteur.

#: Les noms de propriétés changent avec le schéma de l'asset (`generic`,
#: `ceramic`, `metal`, `concrete`…) : on les reconnaît par fragment plutôt
#: que d'écrire les vingt tables de Revit.
FRAGMENTS_COULEUR = ('diffuse', 'color', 'tint')
FRAGMENTS_BRILLANT = ('glossiness', 'gloss', 'shininess', 'reflectivity')
FRAGMENTS_VOILE = ('transparency', 'transparent', 'opacity')
#: La propriété d'un asset `UnifiedBitmap` qui porte le chemin du fichier.
NOM_BITMAP = 'unifiedbitmap_bitmap'

#: Côté de la vignette de texture envoyée à la page. La sphère fait 160 px :
#: au-delà, on transporte des pixels que personne ne verra.
COTE_TEXTURE = 256

#: Racines de la bibliothèque de textures d'Autodesk. Un asset range souvent
#: un chemin RELATIF (« Wood/Finishes/… ») qui n'a de sens que là.
RACINES_TEXTURES = (
    r'C:\Program Files (x86)\Common Files\Autodesk Shared\Materials\Textures',
    r'C:\Program Files\Common Files\Autodesk Shared\Materials\Textures',
)


def _proprietes_directes(asset):
    """Les propriétés d'UN asset, sans descendre dans ce qui lui est accroché."""
    if asset is None:
        return
    try:
        taille = asset.Size
    except Exception:
        return
    for index in range(taille):
        propriete = None
        for acces in (lambda: asset[index], lambda: asset.Get(index)):
            # L'indexeur .NET et `Get` font la même chose ; lequel des deux
            # IronPython expose dépend de la version, et ça ne se découvre
            # qu'à l'exécution.
            try:
                propriete = acces()
                break
            except Exception:
                continue
        if propriete is not None:
            yield propriete


def _connecte(propriete):
    """L'asset accroché à une propriété, None s'il n'y en a pas."""
    try:
        return propriete.GetSingleConnectedAsset()
    except Exception:
        return None


def _proprietes(asset, profondeur=2):
    """Les propriétés d'un asset, et celles de ses assets connectés.

    Deux niveaux suffisent : le chemin d'une texture vit dans l'asset
    `UnifiedBitmap` accroché à la propriété de couleur, soit juste en
    dessous.
    """
    if profondeur <= 0:
        return
    for propriete in _proprietes_directes(asset):
        yield propriete
        for autre in _proprietes(_connecte(propriete), profondeur - 1):
            yield autre


def _correspond(nom, fragments):
    return any(fragment in nom for fragment in fragments)


def _nombre(propriete):
    """La valeur d'une propriété numérique, 0.0 si ce n'en est pas une."""
    for nom in ('Value',):
        try:
            return float(getattr(propriete, nom))
        except Exception:
            continue
    return 0.0


def _chemin_texture(brut):
    """Le chemin d'un bitmap, rendu absolu quand c'est possible.

    Revit en range parfois plusieurs, séparés par une barre verticale, et
    souvent en relatif de la bibliothèque Autodesk.
    """
    chemin = (brut or u'').split(u'|')[0].strip()
    if not chemin:
        return u''
    if os.path.isabs(chemin) and os.path.exists(chemin):
        return chemin
    for racine in RACINES_TEXTURES:
        candidat = os.path.join(racine, chemin.replace(u'/', os.sep))
        if os.path.exists(candidat):
            return candidat
    return u''


def _texture_encodee(chemin):
    """Une vignette JPEG de la texture, en data-URI. Vide si ça ne va pas.

    Décodée directement à `COTE_TEXTURE` par `DecodePixelWidth` : le fichier
    d'origine fait souvent plusieurs mégaoctets, et il n'est jamais chargé en
    entier. Passe par l'imagerie de WPF, déjà présente — pas de
    `System.Drawing`, qui n'est plus garanti sous .NET 8.
    """
    if not chemin:
        return u''
    try:
        from System import Convert, Uri, UriKind
        from System.IO import MemoryStream
        from System.Windows.Media.Imaging import (BitmapCacheOption,
                                                  BitmapFrame, BitmapImage,
                                                  JpegBitmapEncoder)
        image = BitmapImage()
        image.BeginInit()
        image.UriSource = Uri(chemin, UriKind.Absolute)
        image.DecodePixelWidth = COTE_TEXTURE
        image.CacheOption = BitmapCacheOption.OnLoad
        image.EndInit()
        encodeur = JpegBitmapEncoder()
        encodeur.QualityLevel = 80
        encodeur.Frames.Add(BitmapFrame.Create(image))
        flux = MemoryStream()
        encodeur.Save(flux)
        return u'data:image/jpeg;base64,%s' % Convert.ToBase64String(
            flux.ToArray())
    except Exception as erreur:
        log(u'texture « {} » illisible : {}', chemin, erreur)
        return u''


def lire_asset(asset):
    """Asset de rendu -> {couleur, brillant, voile, texture}, en Python pur.

    Séparé de la lecture du document pour se tester avec de faux assets :
    c'est ici que vivent les heuristiques de nom, et ce sont elles qui
    cassent quand Autodesk ajoute un schéma.
    """
    trouve = {'couleur': None, 'brillant': 0.0, 'voile': 0.0, 'texture': u''}
    for propriete in _proprietes(asset):
        try:
            nom = (propriete.Name or u'').lower()
        except Exception:
            continue
        if nom == NOM_BITMAP and not trouve['texture']:
            trouve['texture'] = getattr(propriete, 'Value', u'') or u''
        elif trouve['couleur'] is None and _correspond(nom, FRAGMENTS_COULEUR):
            couleur = _couleur_asset(propriete)
            if couleur is not None:
                trouve['couleur'] = couleur
        elif not trouve['brillant'] and _correspond(nom, FRAGMENTS_BRILLANT):
            trouve['brillant'] = _nombre(propriete)
        elif not trouve['voile'] and _correspond(nom, FRAGMENTS_VOILE):
            trouve['voile'] = _nombre(propriete)
    return trouve


def _couleur_asset(propriete):
    """Triplet RGB d'une propriété de couleur, None si ce n'en est pas une."""
    try:
        return rgb(propriete.GetValueAsColor(), defaut=None)
    except Exception:
        return None


def rendu(doc, materiau):
    """Ce que l'apparence en rendu donne à voir, pour la sphère de l'éditeur.

    ponytail: lu à la demande, pour UN matériau. Le faire pour les cartes
    demanderait d'ouvrir les 700 assets d'un modèle à l'ouverture de l'outil,
    et les textures avec — leurs sphères gardent donc la couleur d'ombrage,
    qui est ce que Revit affiche hors vue réaliste.
    """
    if doc is None:
        return rendu_asset(None)
    try:
        return rendu_asset(doc.GetElement(materiau.AppearanceAssetId))
    except Exception as erreur:
        log(u'asset d\'apparence illisible : {}', erreur)
        return rendu_asset(None)


def rendu_asset(element):
    """Idem depuis l'`AppearanceAssetElement` lui-même : c'est ce que demande
    la page quand on change d'asset dans la liste, sans rien enregistrer."""
    infos = {'nom': u'', 'bibliotheque': u'', 'couleur': u'',
             'brillant': 0, 'voile': 0, 'texture': u''}
    if element is None:
        return infos
    try:
        infos['nom'] = element.Name
        asset = element.GetRenderingAsset()
    except Exception as erreur:
        log(u'asset de rendu illisible : {}', erreur)
        return infos
    try:
        infos['bibliotheque'] = asset.LibraryName or u''
    except Exception:
        pass
    lu = lire_asset(asset)
    if lu['couleur'] is not None:
        infos['couleur'] = hex_de_rgb(lu['couleur'])
    # Le brillant et le voile sortent en 0..1 de l'asset ; la page les
    # manipule comme les curseurs de Revit, en pourcentage.
    infos['brillant'] = entier(max(0.0, min(1.0, lu['brillant'])) * 100)
    infos['voile'] = entier(max(0.0, min(1.0, lu['voile'])) * 100)
    infos['texture'] = _texture_encodee(_chemin_texture(lu['texture']))
    return infos


# ---------------------------------------------------------------------------
# L'audit : ce qu'Enscape saura rendre, et ce qu'il laissera tomber
# ---------------------------------------------------------------------------
#
# Enscape n'embarque pas le moteur de textures d'Autodesk. Il lit l'asset
# d'apparence de Revit et ne sait en rendre que les textures BITMAP : tout ce
# qui est PROCÉDURAL (damier, bruit, bois, marbre, carrelage…) est calculé par
# Revit à la volée, et Enscape le remplace par la couleur diffuse. Un bitmap
# dont le fichier est introuvable tombe exactement pareil, pour une autre
# raison — d'où les deux motifs de refus ci-dessous, et un seul compteur.

#: Fragment du nom de schéma -> nom français, pour les textures procédurales
#: de Revit. Reconnues par FRAGMENT : les schémas s'appellent « WoodSchema »,
#: « 3D Checker », selon la version et la bibliothèque.
PROCEDURALES = (
    (u'checker', u'Damier'),
    (u'gradient', u'Dégradé'),
    (u'marble', u'Marbre'),
    (u'noise', u'Bruit'),
    (u'speckle', u'Moucheté'),
    (u'tile', u'Carrelage'),
    (u'wave', u'Vagues'),
    (u'wood', u'Bois'),
)


def _nom_asset(asset):
    for nom in ('Name', 'Title'):
        try:
            valeur = getattr(asset, nom)
        except Exception:
            continue
        if valeur:
            return valeur
    return u''


def _classer_texture(asset):
    """Un asset connecté -> ce qu'il est. None quand ce n'est pas une texture.

    Un bitmap se reconnaît à SA PROPRIÉTÉ de chemin, pas à son nom de schéma :
    la propriété `unifiedbitmap_bitmap` est la même partout, le nom non.
    """
    nom = _nom_asset(asset)
    for propriete in _proprietes_directes(asset):
        try:
            if (propriete.Name or u'').lower() == NOM_BITMAP:
                return {'schema': nom or u'Bitmap', 'bitmap': True,
                        'libelle': u'Fichier image',
                        'chemin': getattr(propriete, 'Value', u'') or u''}
        except Exception:
            continue
    minuscule = nom.lower()
    for fragment, libelle in PROCEDURALES:
        if fragment in minuscule:
            return {'schema': nom, 'bitmap': False, 'libelle': libelle,
                    'chemin': u''}
    # Ni l'un ni l'autre : un asset de structure (teinte, masque, relief). Il
    # ne compte pas, mais l'appelant continue de descendre dedans — c'est
    # souvent là que le bitmap est rangé.
    return None


def textures_asset(asset, profondeur=3):
    """Les textures d'un asset de rendu, une entrée par emplacement rempli."""
    if asset is None or profondeur <= 0:
        return
    for propriete in _proprietes_directes(asset):
        connecte = _connecte(propriete)
        if connecte is None:
            continue
        texture = _classer_texture(connecte)
        if texture is not None:
            yield texture
        for autre in textures_asset(connecte, profondeur - 1):
            yield autre


def _refus_enscape(texture):
    """Pourquoi Enscape ne rendra pas cette texture. Vide = il la rendra."""
    if not texture['bitmap']:
        return (u'Texture procédurale : Enscape ne rend que des fichiers '
                u'image.')
    if not _chemin_texture(texture['chemin']):
        return u'Fichier introuvable : %s' % (texture['chemin']
                                              or u'aucun chemin')
    return u''


def audit_enscape(entrees):
    """Le bilan « textures lisibles par Enscape » sur une liste de matériaux.

    `entrees` : des couples (nom de matériau, asset de rendu) — du Python nu,
    pour que la règle s'éprouve avec de faux assets. Le pourcentage est
    TRONQUÉ : 100 % doit vouloir dire « toutes », pas « 999 sur 1000 ».
    """
    total = 0
    compatibles = 0
    soucis = []
    for nom, asset in entrees:
        for texture in textures_asset(asset):
            total += 1
            raison = _refus_enscape(texture)
            if not raison:
                compatibles += 1
                continue
            soucis.append({'materiau': nom,
                           'texture': texture['libelle'] or texture['schema'],
                           'raison': raison})
    return {
        'total': total,
        'compatibles': compatibles,
        'pourcentage': 100 if not total else int(100.0 * compatibles / total),
        'soucis': soucis,
    }


def asset_rendu(doc, materiau):
    """L'asset de rendu d'un matériau, None s'il n'en a pas."""
    if doc is None:
        return None
    try:
        element = doc.GetElement(materiau.AppearanceAssetId)
        return element.GetRenderingAsset() if element is not None else None
    except Exception as erreur:
        log(u'asset de « {} » illisible : {}', materiau.Name, erreur)
        return None


#: Les trois jeux de propriétés qu'un matériau porte en plus de son aspect.
#: `aspect` est le nom de l'attribut Revit, `libelle` celui de l'onglet.
ASSETS = (
    ('StructuralAssetId', u'Physique'),
    ('ThermalAssetId', u'Thermique'),
    ('EmbodiedCarbonAssetId', u'Carbone incorporé'),
)


def assets(doc, materiau):
    """Les jeux de propriétés rattachés, et leur nom s'ils existent.

    Lecture seule pour l'instant : en poser un demande un navigateur d'assets
    (la bibliothèque physique de Revit), qui est un outil à lui seul.
    """
    sortie = []
    for attribut_revit, libelle in ASSETS:
        identifiant = ident(premier(materiau, attribut_revit))
        nom = u''
        if doc is not None and identifiant != AUCUN:
            try:
                element = doc.GetElement(premier(materiau, attribut_revit))
                nom = element.Name if element is not None else u''
            except Exception:
                nom = u''
        sortie.append({'attribut': attribut_revit, 'libelle': libelle,
                       'id': identifiant, 'nom': nom})
    return sortie


def editeur(doc, materiau, catalogue):
    """L'état complet que la page d'édition affiche à l'ouverture."""
    valeurs = valeurs_lues(materiau)
    emplacements = {}
    for face, couche in EMPLACEMENTS:
        emplacements[cle(face, couche)] = {
            'face': face,
            'couche': couche,
            'libelle': LIBELLES_COUCHE[couche],
            'titre': titre_emplacement(face, couche),
            'motif': valeurs[attribut(face, couche, u'Id')],
            'couleur': valeurs[attribut(face, couche, u'Color')],
            'accepte_modele': accepte_modele(face, couche),
            'contrainte': contrainte(face, couche),
        }
    # Le rendu n'est PAS ici : lire un asset et décoder sa texture peut
    # prendre plusieurs secondes sur un fichier de bibliothèque posé sur un
    # serveur, et la fenêtre resterait vide tout ce temps. La page demande sa
    # sphère après s'être affichée — c'est le seul morceau qui peut attendre.
    return {'id': ident(materiau.Id), 'valeurs': valeurs,
            'emplacements': emplacements,
            'identite': identite(materiau),
            'assets': assets(doc, materiau)}


def identite_modifiee(identite_page, materiau):
    """Les paramètres d'identité que la page a changés. Clés en ENTIERS.

    Même geste que `modifiees` pour les attributs : on relit le matériau
    plutôt que de se fier à l'état d'ouverture.
    """
    actuels = dict((p['id'], p['valeur']) for p in identite(materiau)
                   if p['modifiable'])
    changes = {}
    for identifiant, valeur in (identite_page or {}).items():
        identifiant = entier(identifiant)
        if identifiant not in actuels:
            continue          # inconnu ou non modifiable : jamais écrit
        if (valeur or u'') != actuels[identifiant]:
            changes[identifiant] = valeur or u''
    return changes


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
