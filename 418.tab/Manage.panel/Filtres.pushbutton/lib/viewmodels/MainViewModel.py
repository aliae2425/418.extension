# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.viewmodels.ReperagePageVM import ReperagePageVM
except Exception:
    from viewmodels.ReperagePageVM import ReperagePageVM

try:
    from lib.viewmodels.AuditPageVM import AuditPageVM
except Exception:
    from viewmodels.AuditPageVM import AuditPageVM


class MainViewModel(BaseViewModel):
    """VM racine (contrat RailWindow) : Titre, Mode, set_mode, un attribut par
    onglet.

    Aucun `UserConfig` : l'outil ne persiste plus rien sur le poste de
    l'utilisateur. Les règles de repérage vivent dans le document, le type de
    vue des plans n'est plus mémorisé du tout (les sélections préfabriquées
    l'ont remplacé). Voir docs/adr/0002-intention-de-reperage-dans-le-modele.md.
    """

    def __init__(self, service=None):
        super(MainViewModel, self).__init__()
        self._service = service
        self._mode = u'audit'
        self.AuditVM = None
        self.ReperageVM = None

    @property
    def Titre(self):
        return u'418 · Gérer les filtres'

    @property
    def Mode(self):
        return self._mode

    def set_mode(self, mode):
        if mode != self._mode:
            self._mode = mode
            self.notify_property('Mode')

    @property
    def SelectionVM(self):
        """La liste cochable que `RailWindow` doit câbler (cf. `SELECTION`).

        Elle vit dans l'onglet Repérage ; l'exposer ici évite au socle de savoir
        où l'outil la range.
        """
        return getattr(self.ReperageVM, 'Liste', None)

    def charger(self):
        filtres = self._service.collecter_filtres() if self._service else []
        plans = self._service.collecter_plans() if self._service else []
        coupes = self._service.collecter_coupes() if self._service else []
        self.AuditVM = AuditPageVM(filtres)
        self.ReperageVM = ReperagePageVM(plans, coupes, service=self._service)
        for nom in ('AuditVM', 'ReperageVM', 'SelectionVM'):
            self.notify_property(nom)

    def lancer(self, cible=None):
        """Bouton d'action de RailWindow : applique le repérage.

        `cible` est ignorée — l'onglet travaille sur les vues du document, pas
        sur une sélection passée par le script.
        """
        if self.ReperageVM is None:
            return []
        return self.ReperageVM.appliquer()
