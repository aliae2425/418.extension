# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from ui.base.RailWindow import RailWindow, Onglet

_BOUTON = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))


class MainWindowView(RailWindow):
    """Fenêtre « Dupliquer les vues » : rail 2 onglets (Sélection / Options).

    Après duplication, sélectionne les vues créées dans l'interface Revit.
    """

    ONGLETS = (
        Onglet(u'selection', 'NavSelection', 'SelectionPage.xaml', 'SelectionVM'),
        Onglet(u'options', 'NavOptions', 'OptionsPage.xaml', 'OptionsVM'),
    )
    SUIVANTS = ((u'selection', 'NextButton', u'options'),)
    RUN = (u'options', 'RunButton')
    RADIOS = (u'options',
              ('RadioDuplicate', 'RadioDetailing', 'RadioDependent'),
              'OptionsVM', 'ViewDuplicateOption')

    def __init__(self, view_model, views_par_id, uidoc):
        super(MainWindowView, self).__init__(_BOUTON, view_model, cible=views_par_id)
        self._uidoc = uidoc

    def _apres_run(self, resultat):
        """Sélectionne les vues dupliquées dans l'interface Revit."""
        if not resultat or self._uidoc is None:
            return
        try:
            from System.Collections.Generic import List
            from Autodesk.Revit.DB import ElementId
            self._uidoc.Selection.SetElementIds(List[ElementId](resultat))
        except Exception:
            pass
