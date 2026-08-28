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

    `RUN` est sur l'onglet Coupes : c'est le seul qui écrit. RailWindow ferme
    la fenêtre après l'action, d'où le compte rendu imprimé dans
    `_apres_run` — la sortie pyRevit reste, elle.
    """

    ONGLETS = (
        Onglet(u'audit', 'AuditPage.xaml', 'AuditVM',
               icone=u'IconAudit', tooltip=u'Audit des filtres'),
        Onglet(u'coupes', 'CoupesPage.xaml', 'CoupesVM',
               icone=u'IconSelection', tooltip=u'Repérage des coupes'),
        Onglet(u'reperage', 'ReperagePage.xaml', 'ReperageVM',
               icone=u'IconRemplacer', tooltip=u'Filtres des plans de repérage'),
    )
    SUIVANTS = ()
    RUN = (u'coupes', 'AppliquerButton')
    TAILLE = (900, 620)
    TAILLE_MINI = (720, 480)

    def __init__(self, view_model):
        super(MainWindowView, self).__init__(_BOUTON, view_model)

    def _apres_run(self, resultat):
        for message in (resultat or []):
            print(message)
