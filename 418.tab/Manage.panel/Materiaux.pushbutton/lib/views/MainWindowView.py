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

    La coquille vient du socle (lib/ui/GUI/MainWindow.xaml) : cet outil n'a
    pas de MainWindow.xaml à lui.
    """

    ONGLETS = (
        Onglet(u'selection', 'CardsPage.xaml', 'SelectionVM',
               icone=u'▦', tooltip=u'Matériaux'),
        Onglet(u'renommer', 'RenommerPage.xaml', 'RenommerVM',
               icone=u'✎', tooltip=u'Renommer'),
        Onglet(u'remplacer', 'RemplacerPage.xaml', 'RemplacerVM',
               icone=u'⇄', tooltip=u'Remplacer dans la maquette'),
    )
    SUIVANTS = ((u'selection', 'NextButton', u'renommer'),)
    RUN = None
    # Largeur calée sur TROIS cards de matériau par rangée : 3 × 260 (244 de
    # card + 4 d'anneau + 12 de gouttière) + 40 de marge de page + 64 de rail
    # + la barre de défilement = ~901. 940 laisse le jeu qui évite de retomber
    # à deux colonnes. Si la card de CardsPage.xaml change de largeur, ce
    # nombre change avec.
    TAILLE = (940, 640)
    TAILLE_MINI = (700, 480)

    def __init__(self, view_model):
        super(MainWindowView, self).__init__(_BOUTON, view_model)

    def _load(self):
        super(MainWindowView, self)._load()
        if self._window is None:
            return
        self._wire_selection(self._page(u'renommer'), 'ItemsList')
        self._wire_liste_remplacer()
        self._action(u'remplacer', 'CocherPorteeButton',
                     lambda: self._vm.RemplacerVM.cocher_toute_la_portee())
        self._action(u'remplacer', 'DecocherPorteeButton',
                     lambda: self._vm.RemplacerVM.decocher_toute_la_portee())
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
    # Listes cochables des onglets Renommer et Remplacer
    # ------------------------------------------------------------------

    def _wire_selection(self, page, nom_liste):
        """Câble Tout/Aucun + le clic de ligne sur la sélection PARTAGÉE.

        `RailWindow._wire_selection_interactions` ne s'occupe que de la page
        `selection` (les cards). Les tableaux de l'onglet Renommer et de la
        colonne source de Remplacer affichent la même `SelectionPageVM` et
        passent par ici : cocher dans l'un coche dans les deux autres.

        Les cases sont display-only (IsHitTestVisible=False, binding OneWay) :
        un seul handler de clic sur la liste suffit, ce qui évite un double
        déclenchement entre la case et la ligne.
        """
        selection = getattr(self._vm, 'SelectionVM', None)
        if page is None or selection is None:
            return

        bouton = page.FindName('SelectAllButton')
        if bouton is not None:
            bouton.Click += lambda s, a: selection.select_all()
        bouton = page.FindName('DeselectAllButton')
        if bouton is not None:
            bouton.Click += lambda s, a: selection.deselect_all()

        def _bascule(carte):
            affichees = list(selection.FilteredItems)
            if carte not in affichees:
                return
            from System.Windows.Input import Keyboard, ModifierKeys
            mods = Keyboard.Modifiers
            selection.handle_row_click(
                affichees.index(carte),
                bool(int(mods) & int(ModifierKeys.Shift)),
                bool(int(mods) & int(ModifierKeys.Control)))

        self._clic_de_ligne(page, nom_liste, _bascule)

    def _wire_liste_remplacer(self):
        """Les deux colonnes de la page Remplacer : sources cochables à
        gauche (sélection partagée), désignation de la cible à droite."""
        page = self._page(u'remplacer')
        vm = getattr(self._vm, 'RemplacerVM', None)
        if page is None or vm is None:
            return
        self._wire_selection(page, 'SourcesList')

        def _designe_cible(carte):
            vm.Cible = carte

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
