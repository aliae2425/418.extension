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
    """Fenêtre « Matériaux » : rail à un seul onglet (Sélection).

    Le bouton « Suivant » de la page Sélection partagée sert de bouton
    d'action tant qu'il n'y a pas de second onglet.
    """

    # ponytail: GUI/Views/MainWindow.xaml est la 5e copie de la coquille rail
    # (les 4 outils de Tools.panel ont la meme). Sortir la coquille dans
    # lib/ui/GUI/ avec le repli bouton->socle deja fait par _chemin_page, et
    # deriver les items de nav d'ONGLETS. ~440 lignes en moins au total.

    ONGLETS = (
        Onglet(u'selection', 'NavSelection', 'SelectionPage.xaml', 'SelectionVM'),
    )
    RUN = (u'selection', 'NextButton')

    def __init__(self, view_model, materiaux_par_id):
        super(MainWindowView, self).__init__(
            _BOUTON, view_model, cible=materiaux_par_id)
