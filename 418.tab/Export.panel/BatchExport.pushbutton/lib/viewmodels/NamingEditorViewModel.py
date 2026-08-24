# -*- coding: utf-8 -*-
# ViewModel de l'éditeur de nommage (modale), mode TOKENS : édition d'un
# motif texte unique avec jetons `{...}` insérables (filtrables par source)
# et aperçu, via NamingService. Remplace l'ancien système à lignes
# paramètre/préfixe/suffixe (NamingRowVM et consorts, supprimés). Les
# presets nommés ont été retirés (voir historique git) : la modale ne gère
# plus que motif + jetons + aperçu.
from __future__ import unicode_literals
from ui.base.BaseViewModel import BaseViewModel
from services.NamingService import NamingService


_TITRES = {
    u'sheet': u'Nommage des feuilles',
    u'set': u'Nommage des carnets',
}

# Mapping source -> nom de brush (clés définies dans Colors.xaml/ColorsDark.xaml).
# 'systeme' -> gris neutre (MediumGrayBrush) ; 'feuille' -> accent ;
# 'jeu'/'projet' réutilisent les brushes sémantiques déjà présentes dans le
# projet (badges EXPORT/DWG de MainWindow.xaml). Pas de nouvelle brush ajoutée.
_COULEUR_PAR_SOURCE = {
    u'systeme': u'MediumGrayBrush',
    u'feuille': u'AccentBrush',
    u'jeu': u'SuccessBrush',
    u'projet': u'WarningBrush',
}
_COULEUR_DEFAUT = u'AccentBrush'

# Libellés lisibles pour les boutons de filtre + valeur 'FiltreSource'.
_SOURCES_DISPONIBLES = (
    {'valeur': u'tout', 'libelle': u'Tout'},
    {'valeur': u'systeme', 'libelle': u'Système'},
    {'valeur': u'feuille', 'libelle': u'Feuille'},
    {'valeur': u'jeu', 'libelle': u'Jeu'},
    {'valeur': u'projet', 'libelle': u'Projet'},
)


class TokenItemVM(object):
    """Item bindable pour un badge de jeton insérable.

    Wrap un dict `{'token': ..., 'desc': ..., 'source': ..., 'label': ...}`
    (contrat de `NamingService.available_tokens()`) en objet à propriétés
    réelles (`.token`/`.desc`/`.source`/`.label`/`.CouleurBrush`) --
    WPF/IronPython ne résout pas de façon fiable un binding `{Binding token}`
    directement sur une clé de dict Python (aucun précédent de ce genre dans
    ce projet : SheetItemVM/CollectionItemVM sont déjà de vraies instances).
    Nécessaire pour `ToolTip="{Binding desc}"` et le texte du badge
    (`{Binding label}`) côté XAML.

    `.label` : nom COURT affiché sur le badge (sans qualifier de source --
    la couleur du badge indique déjà l'origine). `.token` reste le jeton
    complet, celui réellement inséré dans le motif au clic -- jamais affiché
    tel quel sur le badge. Repli sur `.token` si `label` est absent (ex.
    ancien contrat de service sans cette clé), pour qu'un badge n'affiche
    jamais un texte vide.

    `.CouleurBrush` porte le NOM de la ressource brush à appliquer (ex.
    "AccentBrush") -- pas un `Brush` .NET. Un `{Binding CouleurBrush}` direct
    sur `Background` ne colorerait rien (BrushConverter ne résout pas un nom
    de DynamicResource) : le XAML doit utiliser des `DataTrigger` sur
    `.source` avec `Value="{DynamicResource ...}"` pour le rendu réel. Cette
    propriété reste utile pour les tests et pour un éventuel converter futur.
    """

    def __init__(self, token, desc, source=None, label=None):
        self.token = token or u''
        self.desc = desc or u''
        self.source = source or u''
        self.label = label or self.token
        self.CouleurBrush = _COULEUR_PAR_SOURCE.get(self.source, _COULEUR_DEFAUT)


class SourceItemVM(object):
    """Item bindable pour un bouton/onglet de filtre de source.

    `.valeur` : identifiant technique ('tout'/'systeme'/'feuille'/'jeu'/'projet'),
    utilisé pour piloter `FiltreSource`. `.libelle` : texte affiché.
    """

    def __init__(self, valeur, libelle):
        self.valeur = valeur or u''
        self.libelle = libelle or u''


class NamingEditorViewModel(BaseViewModel):
    """VM de la modale « Éditeur de nommage », mode jetons.

    `kind` : 'sheet' ou 'set'. Détermine le titre affiché et la clé de
    persistance utilisée par `NamingService.load`/`save`.

    Le motif (`Pattern`) est une chaîne éditable directement par
    l'utilisateur, enrichie de jetons `{...}` insérables via des badges
    (voir `TokensFiltres`, filtrés depuis `AvailableTokens` selon
    `FiltreSource`). Le VM n'a pas accès au curseur du TextBox --
    l'insertion à la position du curseur est câblée côté VUE
    (NamingEditorView) ; `inserer_token` ci-dessous n'est qu'un repli qui
    ajoute le jeton en fin de motif (utilisable hors contexte WPF, ex. tests).
    """

    def __init__(self, kind, naming_service=None):
        super(NamingEditorViewModel, self).__init__()
        self._kind = kind if kind in (u'sheet', u'set') else u'sheet'

        if naming_service is not None:
            self._naming_service = naming_service
        else:
            try:
                self._naming_service = NamingService() if NamingService is not None else None
            except Exception:
                self._naming_service = None

        # Chargement initial du motif (chaîne canonique) via le service.
        pattern = u''
        if self._naming_service is not None:
            try:
                pattern, _rows = self._naming_service.load(self._kind)
            except Exception:
                pattern = u''
        self._pattern = pattern or u''

        self._filtre_source = u'tout'

    # ------------------------------------------------------------------
    # Propriétés bindables
    # ------------------------------------------------------------------

    @property
    def Titre(self):
        return _TITRES.get(self._kind, u'Nommage')

    @property
    def Pattern(self):
        return self._pattern

    @Pattern.setter
    def Pattern(self, value):
        """Setter TWO-WAY (TextBox du motif, UpdateSourceTrigger=PropertyChanged).

        NE notifie PAS `Pattern` : à chaque frappe, ce setter est rappelé
        par le binding WPF lui-même -- renotifier `Pattern` ici repositionnerait
        le caret du TextBox en fin de texte à chaque caractère saisi. Seule
        `Apercu` (calculée à la demande) est notifiée, pour tenir l'aperçu à jour.
        Les mutations programmatiques (insertion de jeton) utilisent
        `_set_pattern` ci-dessous, qui notifie `Pattern` explicitement.
        """
        value = value or u''
        if value == self._pattern:
            return
        self._pattern = value
        self.notify_property(u'Apercu')

    def _set_pattern(self, value):
        """Mutation programmatique du motif (insertion de jeton) : notifie
        `Pattern` (rafraîchit le TextBox lié) ET `Apercu`."""
        value = value or u''
        if value == self._pattern:
            return
        self._pattern = value
        self.notify_property(u'Pattern')
        self.notify_property(u'Apercu')

    @property
    def AvailableTokens(self):
        """Liste de `TokenItemVM` : jetons génériques statiques
        (`available_tokens()` -> système / feuille / jeu) FUSIONNÉS avec les
        paramètres projet dynamiques (`project_param_tokens()` -> énumérés
        depuis ProjectInformation, catégorie 'projet'). Ensemble complet, non
        filtré. Best-effort : `[]` si le service est absent, chaque source
        gardée indépendamment si l'autre échoue."""
        if self._naming_service is None:
            return []
        bruts = []
        try:
            bruts = list(self._naming_service.available_tokens() or [])
        except Exception:
            bruts = []
        try:
            projet = self._naming_service.project_param_tokens() or []
            bruts = bruts + list(projet)
        except Exception:
            pass
        return [
            TokenItemVM(
                d.get('token', u''), d.get('desc', u''), d.get('source', u''),
                d.get('label', u''),
            )
            for d in bruts
        ]

    @property
    def FiltreSource(self):
        return self._filtre_source

    @FiltreSource.setter
    def FiltreSource(self, value):
        value = (value or u'tout').strip().lower()
        if not value:
            value = u'tout'
        if value == self._filtre_source:
            return
        self._filtre_source = value
        self.notify_property(u'FiltreSource')
        self.notify_property(u'TokensFiltres')

    @property
    def SourcesDisponibles(self):
        """Liste de `SourceItemVM` pour les boutons/onglets de filtre
        (Tout / Projet / Feuille / Carnet)."""
        return [SourceItemVM(d['valeur'], d['libelle']) for d in _SOURCES_DISPONIBLES]

    @property
    def TokensFiltres(self):
        """Sous-ensemble de `AvailableTokens` filtré par `FiltreSource`.
        'tout' (valeur par défaut) retourne l'ensemble complet, sans filtre."""
        tokens = self.AvailableTokens
        if self._filtre_source == u'tout':
            return tokens
        return [t for t in tokens if t.source == self._filtre_source]

    @property
    def Apercu(self):
        """Aperçu « projet seulement » : les jetons de paramètre PROJET
        (`{param_projet:NOM}` + legacy `{projet_*}`) sont résolus en leur
        VALEUR réelle ; tout autre jeton (`{numero}`, `{nom}`, `{titre}`,
        `{date}`) reste littéral. Repli sur le motif brut si le service est
        absent ou ne fournit pas `resolve_project_values` (ex. tests)."""
        if self._naming_service is not None:
            try:
                return self._naming_service.resolve_project_values(self._pattern)
            except Exception:
                pass
        return self._pattern

    # ------------------------------------------------------------------
    # Insertion de jeton (repli sans curseur -- append en fin de motif)
    # ------------------------------------------------------------------

    def inserer_token(self, token):
        """Ajoute `token` en fin de motif. Repli utilisable hors contexte
        WPF (tests, absence de curseur) -- l'insertion à la position du
        curseur est gérée côté vue (NamingEditorView)."""
        if not token:
            return
        self._set_pattern(self._pattern + token)

    # ------------------------------------------------------------------
    # Persistance
    # ------------------------------------------------------------------

    def enregistrer(self):
        """Persiste `Pattern` via `naming_service.save(kind, Pattern)`.

        Best-effort : ne lève jamais si le service est absent ou si `save`
        échoue."""
        if self._naming_service is None:
            return False
        try:
            return bool(self._naming_service.save(self._kind, self._pattern))
        except Exception:
            return False
