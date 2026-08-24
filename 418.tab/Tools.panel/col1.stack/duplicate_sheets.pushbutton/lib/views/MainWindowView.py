# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from ui.base.RailWindow import RailWindow, Onglet

_BOUTON = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))


class MainWindowView(RailWindow):
    """Fenêtre « Dupliquer les feuilles » : rail 3 onglets
    (Sélection / Paramètres / Nommage), sans modale bloquante."""

    ONGLETS = (
        Onglet(u'selection', 'NavSelection', 'SelectionPage.xaml', 'SelectionVM'),
        Onglet(u'params', 'NavParams', 'ParamsPage.xaml', 'OptionsVM'),
        Onglet(u'options', 'NavOptions', 'OptionsPage.xaml', 'OptionsVM'),
    )
    SUIVANTS = (
        (u'selection', 'NextButton', u'params'),
        (u'params', 'NextToNommageButton', u'options'),
    )
    RUN = (u'options', 'RunButton')
    # Les radios d'option de duplication de vue vivent dans ParamsPage.
    RADIOS = (u'params',
              ('RadioDuplicate', 'RadioDetailing', 'RadioDependent'),
              'OptionsVM', 'ViewDuplicateOption')

    def __init__(self, view_model, sheets_par_id):
        super(MainWindowView, self).__init__(_BOUTON, view_model, cible=sheets_par_id)
