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

try:
    from core import text_filter
except Exception:
    from lib.core import text_filter


class CategorieVM(object):
    """Une entrée du menu déroulant de portée.

    `Id` à None = « Toutes les catégories », c'est-à-dire tout le modèle.
    """

    def __init__(self, categorie_id, nom):
        self.Id = categorie_id
        self.Nom = nom


TOUTES_CATEGORIES = CategorieVM(None, u'Toutes les catégories')


class RemplacerPageVM(BaseViewModel):
    """Onglet Remplacer : deux colonnes, sources à gauche, cible à droite.

    Plusieurs sources pour une cible, ce qui sert autant à substituer qu'à
    fusionner des doublons. Le service ignore la cible si elle figure aussi
    parmi les sources.

    Les deux colonnes montrent les MÊMES matériaux mais se filtrent
    séparément : la colonne source est la `SelectionPageVM` partagée avec
    l'onglet Matériaux (elle porte la sélection multiple), la colonne cible
    n'a besoin que d'un filtre et d'un élément courant — d'où sa propre
    recherche ici plutôt qu'une seconde page de sélection.
    """

    def __init__(self, service=None, selection_vm=None, categories=None):
        super(RemplacerPageVM, self).__init__()
        self._service = service
        # Portée du remplacement. « Toutes » d'abord, puis les catégories
        # effectivement présentes dans le modèle (calculées par script.py).
        self.Categories = [TOUTES_CATEGORIES] + list(categories or [])
        self._categorie = TOUTES_CATEGORIES
        # MÊME SelectionPageVM que l'onglet Matériaux : cocher une source
        # ici coche la card là-bas, et réciproquement.
        self.SelectionVM = selection_vm
        self._cible_filtre = u''
        self._cibles = list(selection_vm.AllItems) if selection_vm else []
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
        if value is self._cible:
            return
        if self._cible is not None:
            self._cible.EstCible = False
        self._cible = value
        if value is not None:
            value.EstCible = True
        self._oublier_rapport()
        self.notify_property('Cible')
        self.notify_property('Recapitulatif')
        self.notify_property('PeutRemplacer')

    # -- Portée : la catégorie à traiter -----------------------------------

    @property
    def Categorie(self):
        return self._categorie

    @Categorie.setter
    def Categorie(self, value):
        value = value or TOUTES_CATEGORIES
        if value is not self._categorie:
            self._categorie = value
            self._oublier_rapport()      # le rapport portait sur l'ancienne
            self.notify_property('Categorie')
            self.notify_property('Recapitulatif')

    @property
    def _categorie_id(self):
        return self._categorie.Id if self._categorie is not None else None

    # -- Colonne cible : sa propre recherche -------------------------------

    @property
    def CibleFilterText(self):
        return self._cible_filtre

    @CibleFilterText.setter
    def CibleFilterText(self, value):
        value = value or u''
        if value != self._cible_filtre:
            self._cible_filtre = value
            self.notify_property('CibleFilterText')
            self.notify_property('CiblesFiltrees')

    @property
    def CiblesFiltrees(self):
        return text_filter.filtrer(self._cibles, self._cible_filtre,
                                   [lambda carte: carte.Nom])

    # -- Sources (pilotées par les cases de l'onglet Matériaux) ------------

    def set_sources(self, ids):
        self._sources = list(ids or [])
        self._oublier_rapport()
        self.notify_property('Recapitulatif')
        self.notify_property('PeutAnalyser')
        self.notify_property('PeutRemplacer')

    @property
    def Recapitulatif(self):
        """Récapitulatif de pied de page : « 3 sources fusionnées → BA25 »."""
        nombre = len(self._sources)
        if not nombre:
            return u'Aucune source cochée.'
        if nombre == 1:
            gauche = u'1 source'
        else:
            gauche = u'%d sources fusionnées' % nombre
        if self._cible is None:
            droite = u'aucune cible'
        else:
            droite = self._cible.Nom
        if self._categorie_id is None:
            return u'%s → %s' % (gauche, droite)
        return u'%s → %s · %s' % (gauche, droite, self._categorie.Nom)

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
        self._rapport = self._service.analyser(self._sources,
                                               self._categorie_id)
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
        self._rapport = self._service.remplacer(self._sources, self._cible.Id,
                                                self._categorie_id)
        self._Applique = True
        if self._rapport.EstVide:
            self._Etat = u'Aucun élément modifié.'
        else:
            self._Etat = u'%d élément(s) modifié(s).' % self._rapport.Total
        self._notifier_rapport()
