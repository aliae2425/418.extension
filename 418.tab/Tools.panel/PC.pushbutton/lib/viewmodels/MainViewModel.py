# -*- coding: utf-8 -*-
"""VM racine du parcours : Dossier -> Pièces -> Aperçu.

Il ne fait rien lui-même. Il tient les trois VM de page, propage ce qui
dépend d'une autre étape (changer de type recharge les pièces, entrer dans
l'aperçu le recalcule), et lance le service au bout. Les services sont
instanciés ici et INJECTÉS — les couches basses n'en créent jamais.
"""
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.viewmodels.DossierPageVM import DossierPageVM
    from lib.viewmodels.PiecesPageVM import PiecesPageVM
    from lib.viewmodels.ApercuPageVM import ApercuPageVM
except Exception:
    from viewmodels.DossierPageVM import DossierPageVM
    from viewmodels.PiecesPageVM import PiecesPageVM
    from viewmodels.ApercuPageVM import ApercuPageVM

try:
    from lib.services import ArborescenceService as arbo
except Exception:
    from services import ArborescenceService as arbo


class MainViewModel(BaseViewModel):

    MODES = (u'dossier', u'pieces', u'apercu')

    def __init__(self, doc=None, uidoc=None, config=None, infos=None,
                 jeux=None, choisir_dossier=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._uidoc = uidoc
        self._mode = u'dossier'
        self.DossierVM = DossierPageVM(config=config, infos=infos,
                                       on_change=self._sur_changement_type,
                                       choisir_dossier=choisir_dossier)
        self.PiecesVM = PiecesPageVM(jeux=jeux)
        self.ApercuVM = ApercuPageVM()
        self.PiecesVM.charger(self.DossierVM.Type)

    @property
    def Titre(self):
        return u'418 · Dossier d\'urbanisme'

    # --- rail -------------------------------------------------------------

    @property
    def Mode(self):
        return self._mode

    @property
    def IsDossier(self):
        return self._mode == u'dossier'

    @property
    def IsPieces(self):
        return self._mode == u'pieces'

    @property
    def IsApercu(self):
        return self._mode == u'apercu'

    def set_mode(self, mode):
        if mode == self._mode:
            return
        self._mode = mode
        # Entrer dans une étape, c'est la remettre à jour : l'aperçu ne doit
        # jamais montrer l'état d'avant, c'est le seul endroit où l'architecte
        # vérifie ce qui va s'écrire.
        if mode == u'pieces':
            self.PiecesVM.charger(self.DossierVM.Type)
        elif mode == u'apercu':
            self.rafraichir_apercu()
        for nom in ('Mode', 'IsDossier', 'IsPieces', 'IsApercu'):
            self.notify_property(nom)

    def rafraichir_apercu(self):
        self.ApercuVM.rafraichir(self.DossierVM.Racine,
                                 self.PiecesVM.retenues())

    def _sur_changement_type(self):
        """Le type a changé : les pièces ne sont plus les mêmes."""
        self.PiecesVM.charger(self.DossierVM.Type)

    # --- action -----------------------------------------------------------

    def lancer(self, _cible=None):
        """Écrit l'arborescence. Rend la phrase à montrer, jamais une exception.

        La fenêtre se referme juste après (RailWindow) : ce qui est rendu ici
        est la seule chose que l'architecte lira.

        On recalcule AVANT d'écrire. L'aperçu se rafraîchit déjà en entrant
        dans son onglet, mais faire dépendre ce qui s'écrit d'un passage par
        la bonne page, c'est confier la justesse à l'ordre des clics.
        """
        self.rafraichir_apercu()
        if not self.ApercuVM.PeutGenerer:
            return self.ApercuVM.Avertissement
        racine = self.DossierVM.Racine
        retenues = [vm.piece() for vm in self.PiecesVM.retenues()]
        crees, existants, echecs = arbo.creer(racine, retenues)
        return u'{0}\n{1}'.format(racine,
                                  arbo.resume(crees, existants, echecs))
