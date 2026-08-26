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
        """Câble le tableau de la page Remplacer.

        `RailWindow._wire_selection_interactions` ne s'occupe que de la page
        `selection` ; ce tableau-ci affiche la MÊME `SelectionPageVM` avec
        en plus le rond de cible, il lui faut donc son propre câblage.
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

        liste = page.FindName('SourcesList')
        if liste is None:
            return

        from System.Windows import RoutedEventHandler
        from System.Windows.Controls.Primitives import ToggleButton

        def _sur_cible(sender, args):
            carte = getattr(args.OriginalSource, 'DataContext', None)
            if carte is not None:
                vm.Cible = carte

        # Un seul handler pour tous les ronds : un DataTemplate ne peut pas
        # porter de x:Name unique, mais l'événement Checked remonte jusqu'ici.
        liste.AddHandler(ToggleButton.CheckedEvent,
                         RoutedEventHandler(_sur_cible))

        def _sur_ligne(sender, args):
            from System.Windows.Input import Keyboard, ModifierKeys
            if self._dans_bouton(args.OriginalSource):
                return          # clic sur le rond de cible : pas une source
            carte = getattr(args.OriginalSource, 'DataContext', None)
            affichees = list(selection.FilteredItems)
            if carte is None or carte not in affichees:
                return
            mods = Keyboard.Modifiers
            selection.handle_row_click(
                affichees.index(carte),
                bool(int(mods) & int(ModifierKeys.Shift)),
                bool(int(mods) & int(ModifierKeys.Control)))

        liste.PreviewMouseLeftButtonDown += _sur_ligne

    @staticmethod
    def _dans_bouton(element):
        """Vrai si `element` est dans un RadioButton (le rond de cible).

        WPF remonte OriginalSource jusqu'à l'élément visuel le plus profond —
        typiquement un Border du gabarit du rond, pas le rond lui-même.
        """
        try:
            from System.Windows.Media import VisualTreeHelper
            from System.Windows.Controls import RadioButton
        except Exception:
            return False
        courant = element
        while courant is not None:
            if isinstance(courant, RadioButton):
                return True
            try:
                courant = VisualTreeHelper.GetParent(courant)
            except Exception:
                return False
        return False
