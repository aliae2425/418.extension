# -*- coding: utf-8 -*-
"""VM racine du parcours : Dossier -> Pièces -> Aperçu.

Il ne touche jamais Revit. L'analyse du projet et l'écriture dans la maquette
lui sont INJECTÉES par le script — ce qui le rend testable sans rien simuler,
et garde la transaction là où elle doit être : au-dessus, chez l'appelant.
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
    from lib.services import FeuillesService as service
except Exception:
    from services import FeuillesService as service


class MainViewModel(BaseViewModel):

    MODES = (u'dossier', u'pieces', u'apercu')

    def __init__(self, doc=None, uidoc=None, config=None, cartouches=None,
                 analyser=None, numeros_existants=(), jeux_existants=(),
                 creer=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._uidoc = uidoc
        self._mode = u'dossier'
        self._numeros = tuple(numeros_existants or ())
        self._jeux = tuple(jeux_existants or ())
        # `creer(plan, cartouche)` : c'est l'appelant qui tient la
        # transaction, et les tests qui passent un double.
        self._creer = creer
        self.DossierVM = DossierPageVM(config=config, cartouches=cartouches,
                                       on_change=self._sur_changement_type)
        self.PiecesVM = PiecesPageVM(analyser=analyser)
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
        # vérifie ce qui va s'écrire dans son projet.
        if mode == u'pieces':
            self.PiecesVM.charger(self.DossierVM.Type)
        elif mode == u'apercu':
            self.rafraichir_apercu()
        for nom in ('Mode', 'IsDossier', 'IsPieces', 'IsApercu'):
            self.notify_property(nom)

    def planifier(self):
        return service.planifier(self.PiecesVM.attributions(),
                                 self._numeros, self._jeux)

    def rafraichir_apercu(self):
        self.ApercuVM.rafraichir(self.planifier())

    def _sur_changement_type(self):
        """Le type a changé : les pièces ne sont plus les mêmes."""
        self.PiecesVM.charger(self.DossierVM.Type)

    # --- action -----------------------------------------------------------

    def lancer(self, _cible=None):
        """Crée les feuilles et les jeux. Rend la phrase à montrer.

        On replanifie AVANT d'écrire. L'aperçu se rafraîchit déjà en entrant
        dans son onglet, mais faire dépendre ce qui s'écrit d'un passage par
        la bonne page, c'est confier la justesse à l'ordre des clics.
        """
        self.rafraichir_apercu()
        if not self.ApercuVM.PeutCreer:
            return self.ApercuVM.Avertissement
        if self._creer is None:
            return u'Hors Revit : rien n\'a été créé.'
        plan = self.ApercuVM.plan()
        feuilles, jeux, echecs = self._creer(plan,
                                             self.DossierVM.cartouche_id())
        ignores = len([f for j in plan.jeux for f in j.feuilles if f.existe])
        return service.resume(feuilles, ignores, jeux, echecs)
