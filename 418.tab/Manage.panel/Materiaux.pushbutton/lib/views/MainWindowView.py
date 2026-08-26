# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.RailWindow import RailWindow, Onglet
except Exception:
    from lib.ui.base.RailWindow import RailWindow, Onglet

_BOUTON = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))


class MainWindowView(RailWindow):
    """Fenêtre « Matériaux » : rail à trois onglets.

    `RUN` du socle n'est pas utilisé : il ne câble qu'UN bouton et ferme la
    fenêtre derrière. Ici il en faut trois, et aucun ne doit fermer — on
    veut lire le rapport de remplacement ou l'aperçu de renommage juste
    après l'action. Les trois sont donc câblés dans `_load`.

    ponytail: GUI/Views/MainWindow.xaml est la 5e copie de la coquille rail
    (les 4 outils de Tools.panel ont la meme). Sortir la coquille dans
    lib/ui/GUI/ avec le repli bouton->socle deja fait par _chemin_page, et
    deriver les items de nav d'ONGLETS. ~440 lignes en moins au total.
    """

    ONGLETS = (
        Onglet(u'selection', 'NavSelection', 'CardsPage.xaml', 'SelectionVM'),
        Onglet(u'renommer', 'NavRenommer', 'RenommerPage.xaml', 'RenommerVM'),
        Onglet(u'remplacer', 'NavRemplacer', 'RemplacerPage.xaml', 'RemplacerVM'),
    )
    SUIVANTS = ((u'selection', 'NextButton', u'renommer'),)
    RUN = None

    def __init__(self, view_model):
        super(MainWindowView, self).__init__(_BOUTON, view_model)

    def _load(self):
        super(MainWindowView, self)._load()
        if self._window is None:
            return
        self._wire_liste_remplacer()
        self._action(u'remplacer', 'AnalyserButton',
                     lambda: self._vm.RemplacerVM.analyser())
        self._action(u'remplacer', 'RemplacerButton',
                     lambda: self._vm.RemplacerVM.remplacer())
        self._action(u'renommer', 'RenommerButton',
                     lambda: self._vm.RenommerVM.renommer())

    def _action(self, mode, nom_bouton, callback):
        """Câble un bouton de page sur une action du VM, sans fermer."""
        page = self._page(mode)
        if page is None:
            return
        bouton = page.FindName(nom_bouton)
        if bouton is None:
            return
        bouton.Click += lambda sender, args: callback()

    # ------------------------------------------------------------------
    # Tableau de l'onglet Remplacer : sources ET cible dans la même liste
    # ------------------------------------------------------------------

    def _wire_liste_remplacer(self):
        """Câble les deux colonnes de la page Remplacer.

        `RailWindow._wire_selection_interactions` ne s'occupe que de la page
        `selection` ; ces deux listes-ci ont leur propre câblage. Chacune n'a
        qu'un rôle — cocher une source à gauche, désigner la cible à droite —
        donc un seul handler de clic de ligne suffit de part et d'autre, la
        case et le rond restant display-only.
        """
        page = self._page(u'remplacer')
        vm = getattr(self._vm, 'RemplacerVM', None)
        selection = getattr(vm, 'SelectionVM', None) if vm is not None else None
        if page is None or selection is None:
            return

        bouton = page.FindName('SelectAllButton')
        if bouton is not None:
            bouton.Click += lambda s, a: selection.select_all()
        bouton = page.FindName('DeselectAllButton')
        if bouton is not None:
            bouton.Click += lambda s, a: selection.deselect_all()

        def _bascule_source(carte):
            affichees = list(selection.FilteredItems)
            if carte not in affichees:
                return
            from System.Windows.Input import Keyboard, ModifierKeys
            mods = Keyboard.Modifiers
            selection.handle_row_click(
                affichees.index(carte),
                bool(int(mods) & int(ModifierKeys.Shift)),
                bool(int(mods) & int(ModifierKeys.Control)))

        def _designe_cible(carte):
            vm.Cible = carte

        self._clic_de_ligne(page, 'SourcesList', _bascule_source)
        self._clic_de_ligne(page, 'CiblesList', _designe_cible)

    @staticmethod
    def _clic_de_ligne(page, nom_liste, callback):
        """Un handler unique sur la liste, appelé avec la ligne cliquée."""
        liste = page.FindName(nom_liste)
        if liste is None:
            return

        def _au_clic(sender, args):
            carte = getattr(args.OriginalSource, 'DataContext', None)
            if carte is not None:
                callback(carte)

        liste.PreviewMouseLeftButtonDown += _au_clic
