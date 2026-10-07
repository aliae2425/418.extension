# -*- coding: utf-8 -*-
"""Page « Dossier » : le type, le motif de nommage, la destination."""
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    try:
        from lib.ui.helpers.RelayCommand import RelayCommand
    except Exception:
        RelayCommand = None

try:
    from lib.models import pieces as catalogue
except Exception:
    from models import pieces as catalogue

try:
    from lib.services.NomRacineService import MOTIF_DEFAUT, resoudre
except Exception:
    from services.NomRacineService import MOTIF_DEFAUT, resoudre


def _choisir_dossier_revit():
    """Sélecteur de dossier de pyRevit. ``None`` hors Revit, ou si annulé."""
    try:
        from pyrevit import forms
    except Exception:
        return None
    try:
        return forms.pick_folder(title='Où déposer le dossier d\'urbanisme ?')
    except Exception:
        return None


class DossierPageVM(BaseViewModel):
    """Le type décide de tout le reste : il est en tête du parcours.

    Les cinq types du catalogue sont TOUS exposés, actifs ou non. Un type
    sans pièce rend son ``…Actif`` faux, le XAML grise son chip — on annonce
    ce qui arrive au lieu de le cacher, et le jour où le catalogue se remplit
    le chip s'allume sans qu'on touche à cette classe.
    """

    def __init__(self, config=None, infos=None, on_change=None,
                 choisir_dossier=None):
        super(DossierPageVM, self).__init__()
        self._config = config
        self._infos = infos or {}
        self._on_change = on_change
        self._choisir = choisir_dossier or _choisir_dossier_revit
        self._type = self._lire('type', catalogue.premier_actif()) or u''
        if not catalogue.actif(self._type):
            self._type = catalogue.premier_actif() or u''
        self._motif = self._lire('motif', MOTIF_DEFAUT) or MOTIF_DEFAUT
        self._destination = self._lire('destination', u'') or u''
        self.ParcourirCommand = (RelayCommand(self._parcourir)
                                 if RelayCommand else None)

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
        self.notify_property('NomRacine')
        self.notify_property('Racine')
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

    # --- nommage ----------------------------------------------------------

    @property
    def Motif(self):
        return self._motif

    @Motif.setter
    def Motif(self, valeur):
        self._motif = valeur or u''
        self._ecrire('motif', self._motif)
        self.notify_property('Motif')
        self.notify_property('NomRacine')
        self.notify_property('Racine')

    @property
    def NomRacine(self):
        """Le nom résolu, affiché sous le champ : on voit avant d'écrire."""
        return resoudre(self._motif, self._type, self._infos)

    # --- destination ------------------------------------------------------

    @property
    def Destination(self):
        return self._destination

    @Destination.setter
    def Destination(self, valeur):
        self._destination = valeur or u''
        self._ecrire('destination', self._destination)
        self.notify_property('Destination')
        self.notify_property('Racine')
        self.notify_property('DestinationValide')

    @property
    def DestinationValide(self):
        return bool(self._destination) and os.path.isdir(self._destination)

    @property
    def Racine(self):
        """Le dossier qui sera créé, chemin complet. '' sans destination."""
        if not self._destination:
            return u''
        return os.path.join(self._destination, self.NomRacine)

    def _parcourir(self, _=None):
        choisi = self._choisir()
        if choisi:
            self.Destination = choisi
