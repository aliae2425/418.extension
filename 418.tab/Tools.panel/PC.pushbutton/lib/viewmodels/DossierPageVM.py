# -*- coding: utf-8 -*-
"""Page « Dossier » : le type d'autorisation, et le cartouche des feuilles."""
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.models import pieces as catalogue
except Exception:
    from models import pieces as catalogue


AUCUN_CARTOUCHE = u'— aucun —'


class DossierPageVM(BaseViewModel):
    """Le type décide de tout le reste : il est en tête du parcours.

    Les cinq types du catalogue sont TOUS exposés, actifs ou non. Un type
    sans pièce rend son ``…Actif`` faux, le XAML grise son chip — on annonce
    ce qui arrive au lieu de le cacher, et le jour où le catalogue se remplit
    le chip s'allume sans qu'on touche à cette classe.
    """

    def __init__(self, config=None, cartouches=None, on_change=None):
        super(DossierPageVM, self).__init__()
        self._config = config
        self._on_change = on_change
        # (identifiant, libellé) — l'identifiant est un ElementId en vrai,
        # mais le VM ne le regarde jamais : il le transporte, c'est tout, et
        # il reste testable hors Revit.
        self._cartouches = list(cartouches or [])
        self._type = self._lire('type', catalogue.premier_actif()) or u''
        if not catalogue.actif(self._type):
            self._type = catalogue.premier_actif() or u''
        self._cartouche = self._choix_initial()

    # --- persistance ------------------------------------------------------

    def _lire(self, cle, defaut):
        if self._config is None:
            return defaut
        try:
            return self._config.get(cle, defaut)
        except Exception:
            return defaut

    def _ecrire(self, cle, valeur):
        if self._config is None:
            return
        try:
            # UserConfig est un magasin de chaînes : '' pour « pas de choix »,
            # jamais None — il le sérialiserait en « None ».
            self._config.set(cle, valeur or u'')
        except Exception:
            pass

    # --- le type ----------------------------------------------------------

    @property
    def Type(self):
        return self._type

    @Type.setter
    def Type(self, valeur):
        valeur = valeur or u''
        # Le XAML grise déjà les chips inactifs ; la tabulation passe outre.
        if valeur == self._type or not catalogue.actif(valeur):
            return
        self._type = valeur
        self._ecrire('type', valeur)
        self.notify_property('Type')
        self.notify_property('TypeLibelle')
        if self._on_change is not None:
            self._on_change()

    @property
    def TypeLibelle(self):
        entree = catalogue.dossier(self._type)
        return entree.libelle if entree else u''

    # Un booléen par type : le XAML lie l'IsEnabled de son chip dessus. Cinq
    # propriétés triviales plutôt qu'une liste et un convertisseur — c'est du
    # binding, pas de la logique.
    @property
    def DPActif(self):
        return catalogue.actif(u'DP')

    @property
    def PCMIActif(self):
        return catalogue.actif(u'PCMI')

    @property
    def PCActif(self):
        return catalogue.actif(u'PC')

    @property
    def PAActif(self):
        return catalogue.actif(u'PA')

    @property
    def PDActif(self):
        return catalogue.actif(u'PD')

    # --- le cartouche -----------------------------------------------------

    def _choix_initial(self):
        """Le cartouche retenu la dernière fois, sinon le premier chargé.

        Un projet qui n'a aucun cartouche chargé n'est pas une erreur : on
        crée alors des feuilles nues, et la liste le dit.
        """
        garde = self._lire('cartouche', u'')
        noms = [nom for _id, nom in self._cartouches]
        if garde in noms:
            return garde
        return noms[0] if noms else AUCUN_CARTOUCHE

    @property
    def Cartouches(self):
        return [AUCUN_CARTOUCHE] + [nom for _id, nom in self._cartouches]

    @property
    def Cartouche(self):
        return self._cartouche

    @Cartouche.setter
    def Cartouche(self, valeur):
        self._cartouche = valeur or AUCUN_CARTOUCHE
        self._ecrire('cartouche',
                     u'' if self._cartouche == AUCUN_CARTOUCHE
                     else self._cartouche)
        self.notify_property('Cartouche')

    def cartouche_id(self):
        """L'identifiant du cartouche retenu, ``None`` pour « aucun »."""
        for identifiant, nom in self._cartouches:
            if nom == self._cartouche:
                return identifiant
        return None

    @property
    def CartoucheMention(self):
        if self._cartouche == AUCUN_CARTOUCHE:
            return u'Feuilles créées nues — le cartouche sera à poser à la main.'
        return u'Posé sur chaque feuille créée.'
