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
    """Fenêtre « Gérer les filtres » : un onglet par famille de filtres.

    Comme « Matériaux », l'Audit ouvre le rail ET sert de mode initial : un
    état des lieux en lecture seule, sans câblage.

    `SUIVANTS` et `RUN` restent vides : le scaffold n'a ni enchaînement ni
    bouton d'action. Les onglets à venir câbleront leurs boutons ici.
    """

    ONGLETS = (
        Onglet(u'audit', 'AuditPage.xaml', 'AuditVM',
               icone=u'IconAudit', tooltip=u'Audit des filtres'),
        Onglet(u'coupes', 'CoupesPage.xaml', 'CoupesVM',
               icone=u'IconSelection', tooltip=u'Filtres des coupes'),
        Onglet(u'reperage', 'ReperagePage.xaml', 'ReperageVM',
               icone=u'IconRemplacer', tooltip=u'Filtres des plans de repérage'),
    )
    SUIVANTS = ()
    RUN = None
    TAILLE = (900, 620)
    TAILLE_MINI = (720, 480)

    def __init__(self, view_model):
        super(MainWindowView, self).__init__(_BOUTON, view_model)
