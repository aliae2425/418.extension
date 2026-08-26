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
    """Fenêtre « Dupliquer les feuilles » : rail 3 onglets
    (Sélection / Paramètres / Nommage), sans modale bloquante."""

    ONGLETS = (
        Onglet(u'selection', 'SelectionPage.xaml', 'SelectionVM',
               icone=u'☑', tooltip=u'Sélection'),
        Onglet(u'params', 'ParamsPage.xaml', 'OptionsVM',
               icone=u'⚙', tooltip=u'Paramètres'),
        Onglet(u'options', 'OptionsPage.xaml', 'OptionsVM',
               icone=u'✎', tooltip=u'Nommage'),
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
