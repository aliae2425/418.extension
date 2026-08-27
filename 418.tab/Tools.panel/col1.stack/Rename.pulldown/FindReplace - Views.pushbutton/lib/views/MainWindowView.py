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
    """Fenêtre « Renommer les vues » : rail 2 onglets (Sélection / Nommage)."""

    ONGLETS = (
        Onglet(u'selection', 'SelectionPage.xaml', 'SelectionVM',
               icone=u'IconSelection', tooltip=u'Sélection'),
        Onglet(u'nommage', 'NamingPage.xaml', 'NamingVM',
               icone=u'IconRenommer', tooltip=u'Nommage'),
    )
    SUIVANTS = ((u'selection', 'NextButton', u'nommage'),)
    RUN = (u'nommage', 'RunButton')
    TAILLE = (640, 500)
    TAILLE_MINI = (480, 380)

    def __init__(self, view_model, views_par_id):
        super(MainWindowView, self).__init__(_BOUTON, view_model, cible=views_par_id)
