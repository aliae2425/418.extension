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


class MaterialCardVM(BaseViewModel):
    """Une card de l'onglet Matériaux.

    Cochable : `SelectionPageVM` pilote `IsSelected` exactement comme un
    `SelectionItemVM`, ce qui donne recherche, Tout/Aucun et clic
    simple/Ctrl/Shift sans une ligne de plus.
    """

    def __init__(self, item_id, nom, classe=u'', apparence=u'', couleur=None,
                 motif_coupe=None, motif_surface=None, is_selected=False,
                 on_toggle=None):
        super(MaterialCardVM, self).__init__()
        self.Id = item_id
        self.Nom = nom
        self.Classe = classe or u'Sans classe'
        self.Apparence = apparence or u'Aucune'
        self.ApparenceCouleur = _hex(couleur)
        self._coupe = motif_coupe or Motif()
        self._surface = motif_surface or Motif()
        self._is_selected = bool(is_selected)
        self._est_cible = False
        self._on_toggle = on_toggle

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

    @property
    def IsSelected(self):
        return self._is_selected

    @IsSelected.setter
    def IsSelected(self, value):
        value = bool(value)
        if value != self._is_selected:
            self._is_selected = value
            self.notify_property('IsSelected')
            if self._on_toggle is not None:
                self._on_toggle(self)
