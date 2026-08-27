# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# ViewModel de la fenêtre d'édition d'UN matériau (prototype).
#
# Aucun objet de l'API Revit n'est manipulé ici en dehors des `ElementId` que
# portent les entrées de catalogue (`MotifRef`, `ApparenceRef`) : les couleurs
# sont des chaînes « #RRGGBB » côté binding et des triplets (r, v, b) côté
# valeurs, et c'est `MaterialService.enregistrer` qui les convertit. Le module
# s'importe donc hors Revit, et `valeurs_modifiees()` se teste tel quel.

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    from lib.ui.helpers.RelayCommand import RelayCommand

try:
    from lib.services import hatch
except Exception:
    from services import hatch

try:
    from lib.viewmodels import lecture_materiau
except Exception:
    from viewmodels import lecture_materiau

try:
    from lib.views import hatch_image
except Exception:
    try:
        from views import hatch_image
    except Exception:
        hatch_image = None

# Taille d'une tuile d'aperçu, en pixels. Assez large pour qu'un motif de
# brique montre son appareillage — la vignette de card (64×28) n'en donne
# qu'un fragment.
LARGEUR_TUILE = 150.0
HAUTEUR_TUILE = 96.0

#: Libellés d'affichage des quatre emplacements de `lecture_materiau`.
LIBELLES = {
    (u'Cut', u'Background'): u'Arrière-plan',
    (u'Cut', u'Foreground'): u'Premier plan',
    (u'Surface', u'Background'): u'Arrière-plan',
    (u'Surface', u'Foreground'): u'Premier plan',
}
LIBELLES_FACE = ((u'Cut', u'Coupe'), (u'Surface', u'Surface'))


def _libelles_attributs():
    """Nom d'attribut Revit -> libellé lisible, pour le message de refus.

    « 1 propriété refusée : CutForegroundPatternId » ne dit rien à personne ;
    « Coupe · premier plan (motif) » situe le champ à corriger.
    """
    table = {
        'Name': u'Nom',
        'MaterialClass': u'Classe',
        'Color': u'Couleur graphique',
        'Transparency': u'Transparence',
        'Shininess': u'Brillance',
        'Smoothness': u'Lissage',
        'AppearanceAssetId': u'Apparence en rendu',
    }
    for face, nom_face in LIBELLES_FACE:
        for couche in (u'Background', u'Foreground'):
            situe = u'%s · %s' % (nom_face,
                                  LIBELLES[(face, couche)].lower())
            table[lecture_materiau.attribut(face, couche, u'Id')] = \
                u'%s (motif)' % situe
            table[lecture_materiau.attribut(face, couche, u'Color')] = \
                u'%s (couleur)' % situe
    return table


LIBELLES_ATTRIBUTS = _libelles_attributs()


def hex_de_rgb(couleur):
    return u'#%02X%02X%02X' % tuple(couleur or (0, 0, 0))


def rgb_de_hex(texte, defaut=(0, 0, 0)):
    """« #B0413E » -> (176, 65, 62). `defaut` sur saisie incomplète.

    L'utilisateur tape dans un TextBox lié en PropertyChanged : la valeur est
    invalide à chaque frappe intermédiaire. On ne veut ni exception ni aperçu
    qui clignote en noir — d'où le repli silencieux.
    """
    brut = (texte or u'').strip().lstrip(u'#')
    if len(brut) != 6:
        return defaut
    try:
        return tuple(int(brut[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return defaut


def _champ(nom, coerce=None):
    """Fabrique une propriété notifiante qui prévient la face parente.

    Même geste que `_case` dans MaterialCardVM : WPF exige une vraie propriété
    par champ, et il y en a une dizaine ici dont le corps est identique.
    `coerce` normalise ce que WPF envoie — un Slider écrit des `double`.
    """
    interne = '_' + nom

    def _lire(self):
        return getattr(self, interne)

    def _ecrire(self, valeur):
        if coerce is not None:
            valeur = coerce(valeur)
        if valeur == getattr(self, interne):
            return
        setattr(self, interne, valeur)
        self.notify_property(nom)
        self._au_changement()

    return property(_lire, _ecrire)


def _entier(valeur):
    try:
        return int(round(float(valeur)))
    except (TypeError, ValueError):
        return 0


def _appeler(rappel, porteur):
    """Déclenche un dialogue s'il a été branché. Sans vue, ne fait rien."""
    if rappel is not None:
        rappel(porteur)


class Tuile(object):
    """Un aperçu de hachure à UNE échelle de vue."""

    def __init__(self, libelle, image):
        self.Libelle = libelle
        self.Image = image


class EmplacementVM(BaseViewModel):
    """Un des deux calques d'une face : un motif de remplissage + sa couleur.

    `Motifs` (le catalogue) est porté par l'emplacement et non par le VM
    racine : les quatre emplacements n'offrent pas tous la même chose,
    cf. `_proposables`. La liste part telle quelle dans `MotifPickerVM` quand
    on clique sur le motif ; le choix se fait dans une modale, pas dans une
    liste déroulante — une maquette a des dizaines de motifs qui se
    ressemblent par le nom, il faut les voir côte à côte.
    """

    Motif = _champ('Motif')
    Couleur = _champ('Couleur')

    def __init__(self, face, couche, motif, couleur, motifs, au_changement):
        super(EmplacementVM, self).__init__()
        self.Face = face
        self.Couche = couche
        self.Libelle = LIBELLES.get((face, couche), couche)
        self.Motifs = self._proposables(motifs, motif)
        self._Motif = motif
        self._Couleur = hex_de_rgb(couleur)
        self._au_changement = au_changement
        self._sur_motif = None
        self._sur_couleur = None
        # Les commandes existent dès la construction — le binding les lit au
        # chargement du XAML — mais ne font rien tant que la vue ne les a pas
        # branchées : un ViewModel n'ouvre pas de fenêtre.
        self.ChoisirMotif = RelayCommand(
            lambda parametre: _appeler(self._sur_motif, self))
        self.ChoisirCouleur = RelayCommand(
            lambda parametre: _appeler(self._sur_couleur, self))

    def brancher_dialogues(self, sur_motif, sur_couleur):
        self._sur_motif = sur_motif
        self._sur_couleur = sur_couleur

    @property
    def Titre(self):
        """Titre de la modale de choix : « Coupe · premier plan »."""
        return u'%s · %s' % (dict(LIBELLES_FACE).get(self.Face, self.Face),
                             self.Libelle.lower())

    @property
    def AccepteModele(self):
        """Cet emplacement admet-il un motif de MODÈLE ?

        Un seul des quatre : le premier plan de SURFACE. Les motifs de coupe
        sont en taille papier — Revit refuse `CutForegroundPatternId` et
        `CutBackgroundPatternId` dès qu'on y pose un motif de modèle — et un
        arrière-plan est toujours en taille papier lui aussi.
        """
        return self.Face == u'Surface' and self.Couche == u'Foreground'

    @property
    def Contrainte(self):
        """Phrase affichée dans la modale quand le modèle est exclu."""
        if self.AccepteModele:
            return u''
        if self.Face == u'Cut':
            return (u'Motifs de dessin uniquement — un motif de coupe est en '
                    u'taille papier, Revit y refuse les motifs de modèle.')
        return (u'Motifs de dessin uniquement — Revit réserve les motifs de '
                u'modèle au premier plan de surface.')

    def _proposables(self, motifs, courant):
        """Les motifs que CET emplacement a le droit d'offrir.

        Filtrer en amont plutôt que laisser choisir puis récolter un
        « propriété refusée » à l'enregistrement, où plus rien ne dit pourquoi.

        Le motif déjà en place reste dans la liste même s'il enfreint la règle
        (matériau hérité d'un vieux gabarit, fichier lié) : sinon la modale
        s'ouvre sur du vide et le premier changement de couleur effacerait
        silencieusement le motif.
        """
        motifs = list(motifs or [])
        if self.AccepteModele:
            return motifs
        offerts = [motif for motif in motifs if not motif.EstModele]
        if courant is not None and courant not in offerts:
            offerts.insert(0, courant)
        return offerts

    def couche_dessin(self):
        """La `Couche` à empiler dans l'aperçu, None si « Aucun »."""
        if self._Motif is None:
            return None
        return self._Motif.pour(rgb_de_hex(self._Couleur))

    def valeurs(self):
        """Les deux attributs Revit de cet emplacement."""
        sorties = {lecture_materiau.attribut(self.Face, self.Couche, u'Color'):
                   rgb_de_hex(self._Couleur)}
        if self._Motif is not None:
            sorties[lecture_materiau.attribut(self.Face, self.Couche, u'Id')] = \
                self._Motif.Id
        return sorties


class FaceVM(BaseViewModel):
    """Une face du matériau (coupe ou surface) : ses deux calques et son
    aperçu comparatif à `hatch.ECHELLES_APERCU`.

    L'aperçu empile arrière-plan PUIS premier plan sur du blanc, comme la
    vignette de card et comme Revit — un fond uni gris surmonté de briques
    doit sortir gris ET briques.
    """

    def __init__(self, face, motifs, choisis, au_changement):
        super(FaceVM, self).__init__()
        self.Face = face
        self.Libelle = dict(LIBELLES_FACE).get(face, face)
        self._au_changement = au_changement
        self.Fond = self._emplacement(face, u'Background', motifs, choisis)
        self.Premier = self._emplacement(face, u'Foreground', motifs, choisis)
        self._apercu = []
        self.rafraichir()

    def _emplacement(self, face, couche, motifs, choisis):
        motif, couleur = choisis.get((face, couche), (None, None))
        return EmplacementVM(face, couche, motif, couleur, motifs,
                             self._sur_changement)

    def _sur_changement(self):
        self.rafraichir()
        self._au_changement()

    @property
    def Apercu(self):
        return self._apercu

    @property
    def Emplacements(self):
        return [self.Premier, self.Fond]

    def rafraichir(self):
        couches = [self.Fond.couche_dessin(), self.Premier.couche_dessin()]
        self._apercu = [
            Tuile(u'1:%d' % echelle,
                  hatch_image.vignette(couches, LARGEUR_TUILE, HAUTEUR_TUILE,
                                       echelle_vue=echelle)
                  if hatch_image is not None else None)
            for echelle in hatch.ECHELLES_APERCU]
        self.notify_property('Apercu')

    def valeurs(self):
        sorties = {}
        sorties.update(self.Fond.valeurs())
        sorties.update(self.Premier.valeurs())
        return sorties


class EditeurVM(BaseViewModel):
    """Édition complète d'un matériau : identité, apparence, hachures.

    Ne connaît que des valeurs simples et des entrées de catalogue. Construire
    depuis un `Material` Revit passe par `depuis_materiau()`.

    L'état initial est mémorisé au chargement : `enregistrer()` n'envoie que
    ce qui a bougé. Réécrire les treize attributs à chaque sauvegarde ferait
    remonter en « refusé » tout ce que Revit n'accepte pas d'écrire sur ce
    matériau, y compris les champs auxquels l'utilisateur n'a pas touché.
    """

    Nom = _champ('Nom')
    Classe = _champ('Classe')
    Couleur = _champ('Couleur')
    Apparence = _champ('Apparence')
    Transparence = _champ('Transparence', coerce=_entier)
    Brillance = _champ('Brillance', coerce=_entier)
    Lissage = _champ('Lissage', coerce=_entier)

    def __init__(self, nom=u'', classe=u'', couleur=None, transparence=0,
                 brillance=0, lissage=0, apparence=None, choisis=None,
                 motifs=None, apparences=None, service=None, materiau=None,
                 carte=None, doc=None):
        super(EditeurVM, self).__init__()
        self._Nom = nom or u''
        self._Classe = classe or u''
        self._Couleur = hex_de_rgb(couleur)
        self._Transparence = _entier(transparence)
        self._Brillance = _entier(brillance)
        self._Lissage = _entier(lissage)
        self._Apparence = apparence
        self.Apparences = list(apparences or [])
        self._statut = u''
        self._service = service
        self._materiau = materiau
        self._carte = carte
        self._doc = doc
        self.Faces = [FaceVM(face, motifs, choisis or {}, self._au_changement)
                      for face, _ in LIBELLES_FACE]
        self._initial = self._valeurs()
        self._sur_couleur = None
        self.ChoisirCouleur = RelayCommand(
            lambda parametre: _appeler(self._sur_couleur, self))

    def brancher_dialogues(self, sur_motif, sur_couleur):
        """Branche les deux modales que seule la VUE peut ouvrir.

        `sur_motif(emplacement)` et `sur_couleur(porteur)` — « porteur » étant
        indifféremment ce VM (couleur graphique du matériau) ou un
        emplacement : les deux exposent une propriété `Couleur` en hex, le
        même dialogue les sert.
        """
        self._sur_couleur = sur_couleur
        for face in self.Faces:
            for emplacement in face.Emplacements:
                emplacement.brancher_dialogues(sur_motif, sur_couleur)

    # -- Affichage ---------------------------------------------------------

    @property
    def Titre(self):
        return u'Éditer le matériau'

    @property
    def Statut(self):
        return self._statut

    @Statut.setter
    def Statut(self, valeur):
        valeur = valeur or u''
        if valeur != self._statut:
            self._statut = valeur
            self.notify_property('Statut')

    def _au_changement(self):
        """Un champ a bougé : le message de refus qui traînait n'a plus cours."""
        self.Statut = u''

    # -- Valeurs -----------------------------------------------------------

    def _valeurs(self):
        """Tous les attributs Revit pilotés par l'éditeur, à plat."""
        valeurs = {
            'Name': self._Nom,
            'MaterialClass': self._Classe,
            'Color': rgb_de_hex(self._Couleur),
            'Transparency': self._Transparence,
            'Shininess': self._Brillance,
            'Smoothness': self._Lissage,
        }
        if self._Apparence is not None:
            valeurs['AppearanceAssetId'] = self._Apparence.Id
        for face in self.Faces:
            valeurs.update(face.valeurs())
        return valeurs

    def valeurs_modifiees(self):
        """Ce qui diffère de l'état lu à l'ouverture."""
        courant = self._valeurs()
        return dict((cle, valeur) for cle, valeur in courant.items()
                    if self._initial.get(cle) != valeur)

    # -- Enregistrement ----------------------------------------------------

    def enregistrer(self):
        """Écrit les valeurs modifiées. True si tout est passé.

        La card est ensuite RELUE depuis Revit, pas mise à jour depuis les
        champs : elle affiche donc le nom réellement accepté (sanitize, `*` de
        collision) et les motifs réellement posés.
        """
        modifiees = self.valeurs_modifiees()
        if not modifiees:
            self.Statut = u'Rien à enregistrer.'
            return True
        if self._service is None or self._materiau is None:
            self.Statut = u'Aucun document actif.'
            return False

        echecs = self._service.enregistrer(self._materiau, modifiees)
        lecture_materiau.rafraichir(self._doc, self._materiau, self._carte)
        if self._carte is not None:
            self.Nom = self._carte.Nom
        # Ré-ancrer l'état initial sur ce qui est PASSÉ : un second clic ne
        # doit pas réessayer les écritures réussies, mais doit garder les
        # refusées en attente si l'utilisateur corrige.
        courant = self._valeurs()
        for cle in modifiees:
            if cle not in echecs:
                self._initial[cle] = courant[cle]

        if echecs:
            self.Statut = u'Refusé par Revit : %s.' % u', '.join(
                sorted(LIBELLES_ATTRIBUTS.get(cle, cle) for cle in echecs))
            return False
        self.Statut = u''
        return True


def depuis_materiau(doc, materiau, carte, service, motifs, apparences):
    """Construit l'éditeur depuis un `Material` Revit et les catalogues."""
    motifs = list(motifs or [])
    apparences = list(apparences or [])
    aucun_motif = motifs[0] if motifs else None
    index_motifs = dict((ref.Id, ref) for ref in motifs)
    index_apparences = dict((ref.Id, ref) for ref in apparences)

    couleur = lecture_materiau.rgb(lecture_materiau.premier(materiau, 'Color'))
    choisis = {}
    for face, couche in lecture_materiau.EMPLACEMENTS:
        identifiant = lecture_materiau.premier(
            materiau, lecture_materiau.attribut(face, couche, u'Id'))
        teinte = lecture_materiau.rgb(
            lecture_materiau.premier(
                materiau, lecture_materiau.attribut(face, couche, u'Color')),
            defaut=couleur)
        choisis[(face, couche)] = (index_motifs.get(identifiant, aucun_motif),
                                   teinte)

    asset = index_apparences.get(
        lecture_materiau.premier(materiau, 'AppearanceAssetId'),
        apparences[0] if apparences else None)

    return EditeurVM(
        nom=materiau.Name,
        classe=lecture_materiau.premier(materiau, 'MaterialClass') or u'',
        couleur=couleur,
        transparence=lecture_materiau.premier(materiau, 'Transparency') or 0,
        brillance=lecture_materiau.premier(materiau, 'Shininess') or 0,
        lissage=lecture_materiau.premier(materiau, 'Smoothness') or 0,
        apparence=asset, choisis=choisis, motifs=motifs, apparences=apparences,
        service=service, materiau=materiau, carte=carte, doc=doc)
