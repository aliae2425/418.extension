# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from core import text_filter
except Exception:
    from lib.core import text_filter

try:
    from lib.services.journal import log
except Exception:
    try:
        from services.journal import log
    except Exception:
        def log(gabarit, *args):
            pass


class CategorieVM(BaseViewModel):
    """Une catégorie cochable de la section de portée.

    Cochée à la construction : par défaut le remplacement porte sur tout le
    modèle, et l'utilisateur retire ce qu'il ne veut pas plutôt que de
    devoir tout désigner.
    """

    def __init__(self, categorie_id, nom, on_toggle=None):
        super(CategorieVM, self).__init__()
        self.Id = categorie_id
        self.Nom = nom
        self._est_cochee = True
        self._on_toggle = on_toggle

    @property
    def EstCochee(self):
        return self._est_cochee

    @EstCochee.setter
    def EstCochee(self, value):
        value = bool(value)
        if value != self._est_cochee:
            self._est_cochee = value
            self.notify_property('EstCochee')
            if self._on_toggle is not None:
                self._on_toggle(self)


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
        # Portée du remplacement : les catégories effectivement présentes
        # dans le modèle (calculées par script.py), toutes COCHÉES — donc
        # tout le modèle par défaut.
        self.Categories = list(categories or [])
        for categorie in self.Categories:
            categorie._on_toggle = self._sur_categorie
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
        log(u'cible = {}', value.Nom if value is not None else u'AUCUNE')
        self._oublier_rapport()
        self.notify_property('Cible')
        self.notify_property('Recapitulatif')
        self.notify_property('PeutRemplacer')

    # -- Portée : les catégories à traiter ---------------------------------

    @property
    def _coches(self):
        return [c for c in self.Categories if c.EstCochee]

    @property
    def _categories_ids(self):
        """Ids cochés, ou None quand TOUTES le sont.

        None ne veut pas dire « les mêmes catégories sans filtre » : sans
        filtre, le balayage voit aussi ce qui n'a pas de catégorie de modèle.
        C'est bien ce qu'on veut quand l'utilisateur n'a rien restreint,
        et c'est au passage plus rapide qu'un filtre à 200 entrées.
        """
        coches = self._coches
        if len(coches) == len(self.Categories):
            return None
        return [c.Id for c in coches]

    @property
    def PorteeResume(self):
        """En-tête de la section repliable."""
        coches = self._coches
        if not self.Categories or len(coches) == len(self.Categories):
            return u'Appliquer à toutes les catégories'
        if not coches:
            return u'Aucune catégorie — rien à traiter'
        if len(coches) == 1:
            return u'Appliquer à : %s' % coches[0].Nom
        return u'Appliquer à %d catégories sur %d' % (len(coches),
                                                      len(self.Categories))

    def _sur_categorie(self, categorie):
        self._oublier_rapport()      # le rapport portait sur l'ancienne portée
        for nom in ('PorteeResume', 'Recapitulatif', 'PeutAnalyser',
                    'PeutRemplacer'):
            self.notify_property(nom)

    def cocher_toute_la_portee(self):
        """Recoche tout — revient au défaut, tout le modèle."""
        self._basculer_portee(True)

    def decocher_toute_la_portee(self):
        """Décoche tout — point de départ pour ne désigner que deux ou trois
        catégories sur un gros modèle."""
        self._basculer_portee(False)

    def _basculer_portee(self, valeur):
        for categorie in self.Categories:
            categorie.EstCochee = valeur

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
        log(u'sources = {}', [str(i) for i in self._sources])
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
        coches = self._coches
        if not self.Categories or len(coches) == len(self.Categories):
            return u'%s → %s' % (gauche, droite)
        if not coches:
            return u'%s → %s · aucune catégorie' % (gauche, droite)
        if len(coches) == 1:
            portee = coches[0].Nom
        else:
            portee = u'%d catégories' % len(coches)
        return u'%s → %s · %s' % (gauche, droite, portee)

    @property
    def PeutAnalyser(self):
        # Tout décocher ne veut pas dire « tout le modèle » : ça veut dire
        # qu'il n'y a rien à balayer, donc rien à lancer.
        if self.Categories and not self._coches:
            return False
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

    def _log_etat(self, action):
        """Pourquoi un clic n'a rien lancé — le premier fork à écarter."""
        log(u'{} : {} source(s), cible={}, service={}, {} catégorie(s) '
            u'cochée(s) sur {}, PeutAnalyser={}, PeutRemplacer={}',
            action, len(self._sources),
            self._cible.Nom if self._cible is not None else u'AUCUNE',
            u'oui' if self._service is not None else u'ABSENT',
            len(self._coches), len(self.Categories),
            self.PeutAnalyser, self.PeutRemplacer)

    def analyser(self):
        """Balaye le modèle sans rien modifier."""
        self._log_etat(u'clic Analyser')
        if not self.PeutAnalyser:
            log(u'Analyser ignoré : PeutAnalyser est faux')
            return
        self._rapport = self._service.analyser(self._sources,
                                               self._categories_ids)
        self._Applique = False
        if self._rapport.EstVide:
            self._Etat = u'Aucun élément n\'utilise ces matériaux.'
        else:
            self._Etat = (u'%d élément(s) seraient modifiés.'
                          % self._rapport.Total)
        self._notifier_rapport()

    def remplacer(self):
        """Applique le remplacement en une transaction."""
        self._log_etat(u'clic Remplacer')
        if not self.PeutRemplacer:
            log(u'Remplacer ignoré : PeutRemplacer est faux'
                u' (déjà appliqué ? _Applique={})', self._Applique)
            return
        self._rapport = self._service.remplacer(self._sources, self._cible.Id,
                                                self._categories_ids)
        self._Applique = True
        if self._rapport.EstVide:
            self._Etat = u'Aucun élément modifié.'
        else:
            self._Etat = u'%d élément(s) modifié(s).' % self._rapport.Total
        self._notifier_rapport()
