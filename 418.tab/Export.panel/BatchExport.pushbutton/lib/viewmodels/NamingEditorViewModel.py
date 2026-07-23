# -*- coding: utf-8 -*-
# ViewModel de l'éditeur de nommage (modale), mode TOKENS : édition d'un
# motif texte unique avec jetons `{...}` insérables, presets nommés et
# aperçu, via NamingService. Remplace l'ancien système à lignes
# paramètre/préfixe/suffixe (NamingRowVM et consorts, supprimés).
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

# Double forme d'import (régime pyRevit vs régime tests standalone),
# cf. convention du projet (voir MainViewModel.py).
try:
    from services.NamingService import NamingService
except Exception:
    try:
        from lib.services.NamingService import NamingService
    except Exception:
        NamingService = None  # type: ignore


_TITRES = {
    u'sheet': u'Nommage des feuilles',
    u'set': u'Nommage des carnets',
}


class TokenItemVM(object):
    """Item bindable pour un badge de jeton insérable.

    Wrap un dict `{'token': ..., 'desc': ...}` (contrat de
    `NamingService.available_tokens()`) en objet à propriétés réelles
    (`.token`/`.desc`) -- WPF/IronPython ne résout pas de façon fiable un
    binding `{Binding token}` directement sur une clé de dict Python (aucun
    précédent de ce genre dans ce projet : SheetItemVM/CollectionItemVM sont
    déjà de vraies instances). Nécessaire pour `Content="{Binding token}"`
    et `ToolTip="{Binding desc}"` côté XAML.
    """

    def __init__(self, token, desc):
        self.token = token or u''
        self.desc = desc or u''


class PresetItemVM(object):
    """Item bindable pour un preset nommé.

    Wrap un dict `{'name': ..., 'pattern': ...}` (contrat de
    `NamingService.list_presets()`) en objet à propriétés réelles
    (`.name`/`.pattern`), pour `DisplayMemberPath="name"` côté ComboBox.
    """

    def __init__(self, name, pattern):
        self.name = name or u''
        self.pattern = pattern or u''


class NamingEditorViewModel(BaseViewModel):
    """VM de la modale « Éditeur de nommage », mode jetons.

    `kind` : 'sheet' ou 'set'. Détermine le titre affiché et la clé de
    persistance utilisée par `NamingService.load`/`save`.

    Le motif (`Pattern`) est une chaîne éditable directement par
    l'utilisateur, enrichie de jetons `{...}` insérables via des badges
    (voir `AvailableTokens`). Le VM n'a pas accès au curseur du TextBox --
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

        self._preset_selectionne = None

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
        Les mutations programmatiques (preset, insertion de jeton) utilisent
        `_set_pattern` ci-dessous, qui notifie `Pattern` explicitement.
        """
        value = value or u''
        if value == self._pattern:
            return
        self._pattern = value
        self.notify_property(u'Apercu')

    def _set_pattern(self, value):
        """Mutation programmatique du motif (preset, insertion de jeton) :
        notifie `Pattern` (rafraîchit le TextBox lié) ET `Apercu`."""
        value = value or u''
        if value == self._pattern:
            return
        self._pattern = value
        self.notify_property(u'Pattern')
        self.notify_property(u'Apercu')

    @property
    def AvailableTokens(self):
        """Liste de `TokenItemVM` (adaptés depuis
        `naming_service.available_tokens()` -> `[{'token','desc'}, ...]`)
        pour les badges insérables, bindables en XAML (`.token`/`.desc`).
        Best-effort : `[]` si le service est absent."""
        if self._naming_service is None:
            return []
        try:
            bruts = self._naming_service.available_tokens() or []
        except Exception:
            return []
        return [TokenItemVM(d.get('token', u''), d.get('desc', u'')) for d in bruts]

    @property
    def Presets(self):
        """Liste de `PresetItemVM` (adaptés depuis
        `naming_service.list_presets()` -> `[{'name','pattern'}, ...]`),
        bindables en XAML (`.name`/`.pattern`). Best-effort : `[]` si le
        service est absent ou si la lecture échoue."""
        if self._naming_service is None:
            return []
        try:
            bruts = self._naming_service.list_presets() or []
        except Exception:
            return []
        return [PresetItemVM(d.get('name', u''), d.get('pattern', u'')) for d in bruts]

    @property
    def PresetSelectionne(self):
        return self._preset_selectionne

    @PresetSelectionne.setter
    def PresetSelectionne(self, value):
        if value == self._preset_selectionne:
            return
        self._preset_selectionne = value
        self.notify_property(u'PresetSelectionne')

    @property
    def Apercu(self):
        """Aperçu « template » : le motif courant tel quel (pas de
        résolution contre un élément Revit réel -- amélioration future,
        hors périmètre ici pour ne pas coupler ce VM à un doc)."""
        return self._pattern

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    def charger_preset(self, name):
        """Charge le preset nommé `name` : remplace `Pattern` par son motif
        et notifie. Best-effort : ne fait rien si le preset est introuvable
        ou si le service est absent."""
        if not name or self._naming_service is None:
            return False
        try:
            presets = self._naming_service.list_presets() or []
        except Exception:
            presets = []
        for p in presets:
            if p.get('name') == name:
                self._set_pattern(p.get('pattern', u'') or u'')
                self._preset_selectionne = name
                self.notify_property(u'PresetSelectionne')
                return True
        return False

    def enregistrer_preset(self, name):
        """Enregistre `Pattern` courant comme preset nommé `name`. Rafraîchit
        `Presets` en cas de succès. Best-effort."""
        name = (name or u'').strip()
        if not name or self._naming_service is None:
            return False
        try:
            ok = bool(self._naming_service.save_preset(name, self._pattern))
        except Exception:
            ok = False
        if ok:
            self._preset_selectionne = name
            self.notify_property(u'Presets')
            self.notify_property(u'PresetSelectionne')
        return ok

    def supprimer_preset(self, name):
        """Supprime le preset nommé `name`. Rafraîchit `Presets` en cas de
        succès. Best-effort."""
        name = (name or u'').strip()
        if not name or self._naming_service is None:
            return False
        try:
            ok = bool(self._naming_service.delete_preset(name))
        except Exception:
            ok = False
        if ok:
            if self._preset_selectionne == name:
                self._preset_selectionne = None
                self.notify_property(u'PresetSelectionne')
            self.notify_property(u'Presets')
        return ok

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
