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
