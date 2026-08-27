# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.views import hatch_image
except Exception:
    try:
        from views import hatch_image
    except Exception:
        hatch_image = None


class Couche(object):
    """UN motif de remplissage Revit, tel que lu par script.py.

    `grilles` : liste de `services.hatch.Grille`. Vide pour un motif « Uni »
    (Revit ne stocke aucune grille pour un remplissage plein) et pour
    l'absence de motif — `est_uni` tranche entre les deux.
    """

    def __init__(self, nom=u'', grilles=None, est_modele=False, est_uni=False,
                 rgb=None):
        self.nom = nom or u''
        self.grilles = grilles or []
        self.est_modele = est_modele
        self.est_uni = est_uni
        self.rgb = rgb


class Motif(object):
    """Le rendu d'une face : arrière-plan + premier plan, comme dans Revit.

    Depuis 2019 un matériau porte DEUX motifs par face. La vignette les
    empile dans cet ordre sur du blanc, sinon un fond uni gris surmonté de
    briques s'affiche briques seules — pas ce que montre la maquette.
    """

    def __init__(self, fond=None, premier=None):
        self.fond = fond
        self.premier = premier
        self._image = None
        self._construite = False

    @property
    def Nom(self):
        noms = [c.nom for c in (self.premier, self.fond) if c is not None and c.nom]
        return u' sur '.join(noms) if noms else u'Aucun'

    def image(self):
        # Construite une fois : le binding la relit à chaque recyclage de
        # ligne, et une DrawingImage figée se partage sans risque.
        if not self._construite:
            self._construite = True
            if hatch_image is not None:
                self._image = hatch_image.vignette([self.fond, self.premier])
        return self._image


def _hex(rgb):
    return u'#%02X%02X%02X' % tuple(rgb or (128, 128, 128))


def _case(nom):
    """Fabrique UNE case cochable notifiante, nommée `nom`.

    Un onglet = une case = une sélection indépendante. WPF a besoin d'une
    vraie propriété par case (pas d'indexeur), et `SelectionPageVM` reçoit
    son nom via `prop` — d'où trois propriétés jumelles plutôt qu'un
    dictionnaire. La fabrique évite d'en écrire trois fois le corps.
    """
    interne = '_' + nom

    def _lire(self):
        return getattr(self, interne)

    def _ecrire(self, value):
        value = bool(value)
        if value == getattr(self, interne):
            return
        setattr(self, interne, value)
        self.notify_property(nom)
        rappel = self._on_toggle.get(nom)
        if rappel is not None:
            rappel(self)

    return property(_lire, _ecrire)


class MaterialCardVM(BaseViewModel):
    """LA vue d'un matériau : card de l'onglet 1, ligne des onglets 2 et 3.

    Un seul objet par matériau, mais TROIS cases indépendantes — une par
    onglet. Chaque onglet a sa `SelectionPageVM` construite sur ces mêmes
    cards avec son propre `prop`, ce qui donne trois sélections et trois
    recherches sans dupliquer la donnée du matériau (vignettes, usages).
    Cocher dans un onglet ne touche donc pas aux deux autres.

    La card porte aussi l'aperçu de renommage (`NouveauNom`, écrit par
    `RenommerPageVM`) : le tableau de l'onglet Renommer EST l'aperçu, il n'y
    a pas de seconde liste à tenir synchrone avec la sélection.

    `usages` : `services.MaterialService.LigneRapport` comptée à l'ouverture,
    ou None hors Revit — la colonne reste alors vide.
    """

    IsSelected = _case('IsSelected')                    # onglet Matériaux
    IsSelectedRenommer = _case('IsSelectedRenommer')    # onglet Renommer
    IsSelectedRemplacer = _case('IsSelectedRemplacer')  # onglet Remplacer

    def __init__(self, item_id, nom, classe=u'', apparence=u'', couleur=None,
                 motif_coupe=None, motif_surface=None, is_selected=False,
                 usages=None):
        super(MaterialCardVM, self).__init__()
        self.Id = item_id
        self._nom = nom or u''
        self._nouveau_nom = u''
        self._classe = classe or u'Sans classe'
        self._apparence = apparence or u'Aucune'
        self._apparence_couleur = _hex(couleur)
        self._coupe = motif_coupe or Motif()
        self._surface = motif_surface or Motif()
        self._IsSelected = bool(is_selected)
        self._IsSelectedRenommer = False
        self._IsSelectedRemplacer = False
        self._est_cible = False
        # Nom de case -> rappel de SA page. Posé par `brancher`.
        self._on_toggle = {}
        self._usages = usages

    def brancher(self, nom_case, rappel):
        """Relie une case au `_on_item_toggle` de la page qui la pilote."""
        self._on_toggle[nom_case] = rappel

    # -- Nom et aperçu de renommage ---------------------------------------

    @property
    def Nom(self):
        return self._nom

    @Nom.setter
    def Nom(self, value):
        """Notifiant : après un renommage, les cards affichent le nom que
        Revit a réellement accepté (sanitize + `*` en cas de collision)."""
        value = value or u''
        if value != self._nom:
            self._nom = value
            self.notify_property('Nom')
            self.notify_property('NomChange')

    @property
    def NouveauNom(self):
        """Nom obtenu par la règle de l'onglet Renommer. Vide quand la card
        n'est pas cochée : elle ne sera pas renommée."""
        return self._nouveau_nom

    @NouveauNom.setter
    def NouveauNom(self, value):
        value = value or u''
        if value != self._nouveau_nom:
            self._nouveau_nom = value
            self.notify_property('NouveauNom')
            self.notify_property('NomChange')

    @property
    def NomChange(self):
        return bool(self._nouveau_nom) and self._nouveau_nom != self._nom

    # -- Ce que l'éditeur peut changer -------------------------------------

    @property
    def Classe(self):
        return self._classe

    @property
    def Apparence(self):
        return self._apparence

    @property
    def ApparenceCouleur(self):
        return self._apparence_couleur

    def rafraichir(self, nom, classe, apparence, couleur, motif_coupe,
                   motif_surface):
        """Recharge tout l'affichage depuis une relecture du matériau Revit.

        Appelée après une sauvegarde de l'éditeur. Les `Motif` sont REMPLACÉS,
        pas modifiés : `Motif.image()` met sa DrawingImage en cache une fois
        pour toutes (elle est gelée et partagée par le binding), donc la seule
        façon de changer une vignette est d'en fabriquer une autre.
        """
        self.Nom = nom
        self._classe = classe or u'Sans classe'
        self._apparence = apparence or u'Aucune'
        self._apparence_couleur = _hex(couleur)
        self._coupe = motif_coupe or Motif()
        self._surface = motif_surface or Motif()
        for propriete in ('Classe', 'Apparence', 'ApparenceCouleur',
                          'MotifCoupeNom', 'MotifSurfaceNom',
                          'MotifCoupeImage', 'MotifSurfaceImage'):
            self.notify_property(propriete)

    # -- Usages dans la maquette ------------------------------------------

    @property
    def Utilisations(self):
        return self._usages.Total if self._usages is not None else 0

    @property
    def EstUtilise(self):
        return self.Utilisations > 0

    @property
    def SansInstance(self):
        """Aucune instance ne porte ce matériau.

        Inclut les non utilisés : c'est la lecture littérale de « sans
        instance ». Un matériau déclaré dans les couches d'un WallType mais
        jamais posé est le cas intéressant, il tombe aussi ici.
        """
        return self._usages is None or self._usages.Instances == 0

    @property
    def UtilisationsTexte(self):
        """« 3 types · 50 instances », « Non utilisé », ou vide si non compté."""
        if self._usages is None:
            return u''
        return self._usages.Detail or u'Non utilisé'

    @property
    def MotifCoupeNom(self):
        return self._coupe.Nom

    @property
    def MotifSurfaceNom(self):
        return self._surface.Nom

    @property
    def MotifCoupeImage(self):
        return self._coupe.image()

    @property
    def MotifSurfaceImage(self):
        return self._surface.image()

    @property
    def EstCible(self):
        """Matériau désigné comme cible du remplacement. Exclusif — c'est
        `RemplacerPageVM.Cible` qui éteint le précédent."""
        return self._est_cible

    @EstCible.setter
    def EstCible(self, value):
        value = bool(value)
        if value != self._est_cible:
            self._est_cible = value
            self.notify_property('EstCible')
