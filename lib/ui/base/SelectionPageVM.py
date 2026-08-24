# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Base des pages « Sélection » des outils (feuilles / vues) : recherche +
# multi-sélection shift/ctrl. Chaque outil ne fournit que ses items déjà
# construits, l'accès à leur identité et les champs sur lesquels filtrer.
#
# Une seule couche : la version précédente empilait SelectionPageVMBase (qui
# ne faisait que réexporter 8 membres) au-dessus de SelectionListController
# (qui réexportait lui-même trois helpers sans état).

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
    from core.list_selection import ListSelectionService
except Exception:
    from lib.core.list_selection import ListSelectionService

try:
    from core import text_filter
except Exception:
    from lib.core import text_filter

try:
    from core import bulk_edit
except Exception:
    from lib.core import bulk_edit

try:
    from ui.base.SelectionItemVM import SelectionItemVM
except Exception:
    from lib.ui.base.SelectionItemVM import SelectionItemVM


class SelectionPageVM(BaseViewModel):
    """Recherche + multi-sélection sur une liste d'items.

    `items` : ItemVM déjà construits par la sous-classe.
    `id_getter` : item -> identifiant renvoyé par `selected_ids()`.
    `filter_getters` : liste de item -> texte, testés par la recherche.
    `titre` : titre affiché en tête de page (« Feuilles à dupliquer »...).

    Comportement de sélection :
    - clic simple / Ctrl+clic : bascule l'item (accumulation, pas d'exclusif)
    - Shift+clic : plage [ancre, index] sur les items AFFICHÉS (filtrés),
      uniquement si une ancre valide existe ; sinon repli sur une bascule
    - select_all / deselect_all : sur la liste COMPLÈTE (masqués inclus)
    """

    def __init__(self, items, id_getter, filter_getters,
                 on_selection_changed=None, prop=u'IsSelected', titre=u''):
        super(SelectionPageVM, self).__init__()
        self._all = list(items or [])
        self._id_getter = id_getter
        self._filter_getters = list(filter_getters or [])
        self._prop = prop
        self._titre = titre
        self._on_selection_changed = on_selection_changed
        self._selection = ListSelectionService(prop=prop)
        self._filter_text = u''
        self._filtered = list(self._all)
        # Validité de l'ancre : ListSelectionService remet la sienne à -1 sur
        # reset() sans l'exposer. On suit l'information ici pour savoir si un
        # Shift doit produire une plage ou retomber sur une bascule.
        self._has_anchor = False

    @classmethod
    def depuis_descripteurs(cls, descripteurs, ids_selectionnes, titre,
                            est_identifiant=True, on_selection_changed=None):
        """Construit la page depuis des triplets `(id, colonne_gauche, nom)`.

        Couvre les 4 outils : la seule variation est `est_identifiant` (numéro
        de feuille en gras vs type de vue en texte secondaire) et le titre.
        """
        selset = set(ids_selectionnes or [])
        items = []
        vm = cls([], id_getter=lambda it: it.Id,
                 filter_getters=[lambda it: it.ColonneGauche, lambda it: it.Nom],
                 on_selection_changed=on_selection_changed, titre=titre)
        for (iid, colonne_gauche, nom) in descripteurs:
            items.append(SelectionItemVM(
                iid, colonne_gauche, nom, iid in selset, vm._on_item_toggle,
                est_identifiant=est_identifiant))
        vm._all = items
        vm._filtered = list(items)
        return vm

    # --- Titre ---------------------------------------------------------------
    @property
    def TitrePage(self):
        return self._titre

    # --- Recherche -----------------------------------------------------------
    @property
    def FilterText(self):
        return self._filter_text

    @FilterText.setter
    def FilterText(self, value):
        self._filter_text = value or u''
        self._filtered = text_filter.filtrer(
            self._all, self._filter_text, self._filter_getters)
        self._selection.reset()   # index invalidés -> ancre perdue
        self._has_anchor = False
        self.notify_property('FilterText')
        self.notify_property('FilteredItems')

    @property
    def FilteredItems(self):
        return self._filtered

    @property
    def AllItems(self):
        return self._all

    # --- Sélection -----------------------------------------------------------
    def handle_row_click(self, index, shift=False, ctrl=False):
        if shift and self._has_anchor:
            self._selection.handle_click(self._filtered, index, shift=True)
        else:
            # clic simple, Ctrl, OU Shift sans ancre valide -> bascule
            # ponctuelle (la case reste le contrôle, pas d'exclusif)
            self._selection.handle_click(self._filtered, index, ctrl=True)
            self._has_anchor = True
        self._after_selection_change()

    def select_all(self):
        bulk_edit.select_all(self._all, self._prop)
        self._after_selection_change()

    def deselect_all(self):
        bulk_edit.deselect_all(self._all, self._prop)
        self._after_selection_change()

    def selected_ids(self):
        return [self._id_getter(it) for it in self._all
                if getattr(it, self._prop, False)]

    @property
    def HasSelection(self):
        return any(getattr(it, self._prop, False) for it in self._all)

    # --- Interne -------------------------------------------------------------
    def _on_item_toggle(self, item):
        """Passé aux ItemVM : une case cochée directement doit aussi mettre à
        jour HasSelection et prévenir l'outil hôte."""
        self._after_selection_change()

    def _after_selection_change(self):
        self.notify_property('HasSelection')
        if self._on_selection_changed is not None:
            self._on_selection_changed(self.selected_ids())
