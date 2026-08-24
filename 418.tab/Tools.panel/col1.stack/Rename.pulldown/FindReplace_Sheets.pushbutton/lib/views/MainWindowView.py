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
    """Fenêtre « Renommer les feuilles » : rail 2 onglets (Sélection / Nommage)."""

    ONGLETS = (
        Onglet(u'selection', 'NavSelection', 'SelectionPage.xaml', 'SelectionVM'),
        Onglet(u'nommage', 'NavNommage', 'NamingPage.xaml', 'NamingVM'),
    )
    SUIVANTS = ((u'selection', 'NextButton', u'nommage'),)
    RUN = (u'nommage', 'RunButton')

    def __init__(self, view_model, sheets_par_id):
        super(MainWindowView, self).__init__(_BOUTON, view_model, cible=sheets_par_id)
