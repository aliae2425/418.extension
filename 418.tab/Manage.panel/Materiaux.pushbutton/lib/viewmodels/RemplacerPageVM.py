# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        class BaseViewModel(object):
            def __init__(self):
                pass

            def notify_property(self, name):
                pass


class RemplacerPageVM(BaseViewModel):
    """Onglet Remplacer : les matériaux cochés (sources) cèdent leurs
    affectations à un matériau cible.

    Plusieurs sources pour une cible, ce qui sert autant à substituer qu'à
    fusionner des doublons. Le service ignore la cible si elle figure aussi
    parmi les sources.
    """

    def __init__(self, service=None, cartes=None):
        super(RemplacerPageVM, self).__init__()
        self._service = service
        self.Cibles = list(cartes or [])
        self._cible = None
        self._sources = []
        self._rapport = None
        self._Etat = u''
        self._Applique = False

    # -- Cible -------------------------------------------------------------

    @property
    def Cible(self):
        return self._cible

    @Cible.setter
    def Cible(self, value):
        if value is not self._cible:
            self._cible = value
            self._oublier_rapport()
            self.notify_property('Cible')
            self.notify_property('PeutRemplacer')

    # -- Sources (pilotées par les cases de l'onglet Matériaux) ------------

    def set_sources(self, ids):
        self._sources = list(ids or [])
        self._oublier_rapport()
        self.notify_property('SourcesResume')
        self.notify_property('PeutAnalyser')
        self.notify_property('PeutRemplacer')

    @property
    def SourcesResume(self):
        nombre = len(self._sources)
        if not nombre:
            return u'Aucun matériau coché dans l\'onglet Matériaux.'
        if nombre == 1:
            return u'1 matériau source.'
        return u'%d matériaux sources — ils seront fusionnés vers la cible.' % nombre

    @property
    def PeutAnalyser(self):
        return bool(self._sources) and self._service is not None

    @property
    def PeutRemplacer(self):
        return self.PeutAnalyser and self._cible is not None and not self._Applique

    # -- Rapport -----------------------------------------------------------

    @property
    def Rapport(self):
        return self._rapport

    @property
    def Lignes(self):
        return self._rapport.Lignes if self._rapport else []

    @property
    def HasRapport(self):
        return self._rapport is not None

    @property
    def Etat(self):
        return self._Etat

    @property
    def Peints(self):
        return self._rapport.Peints if self._rapport else 0

    @property
    def HasPeints(self):
        return self.Peints > 0

    @property
    def AvertissementPeints(self):
        nombre = self.Peints
        if not nombre:
            return u''
        return (u'%d élément%s avec une face peinte : la peinture n\'est pas '
                u'modifiée, à reprendre à la main.'
                % (nombre, u's' if nombre > 1 else u''))

    def _oublier_rapport(self):
        if self._rapport is None and not self._Etat:
            return
        self._rapport = None
        self._Etat = u''
        self._Applique = False
        self._notifier_rapport()

    def _notifier_rapport(self):
        for nom in ('Rapport', 'Lignes', 'HasRapport', 'Etat', 'Peints',
                    'HasPeints', 'AvertissementPeints', 'PeutRemplacer'):
            self.notify_property(nom)

    # -- Actions -----------------------------------------------------------

    def analyser(self):
        """Balaye le modèle sans rien modifier."""
        if not self.PeutAnalyser:
            return
        self._rapport = self._service.analyser(self._sources)
        self._Applique = False
        if self._rapport.EstVide:
            self._Etat = u'Aucun élément n\'utilise ces matériaux.'
        else:
            self._Etat = (u'%d élément(s) seraient modifiés.'
                          % self._rapport.Total)
        self._notifier_rapport()

    def remplacer(self):
        """Applique le remplacement en une transaction."""
        if not self.PeutRemplacer:
            return
        self._rapport = self._service.remplacer(self._sources, self._cible.Id)
        self._Applique = True
        if self._rapport.EstVide:
            self._Etat = u'Aucun élément modifié.'
        else:
            self._Etat = u'%d élément(s) modifié(s).' % self._rapport.Total
        self._notifier_rapport()
