# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from pyrevit import forms

try:
    from core.AppPaths import AppPaths
    from core.journal import journal
    from core.presse_papiers import historique, demander
except Exception:
    from lib.core.AppPaths import AppPaths
    from lib.core.journal import journal
    from lib.core.presse_papiers import historique, demander

_log = journal('presse_papiers')

try:
    from ui.helpers.UIResourceLoader import UIResourceLoader
    from ui.helpers.DarkMode import is_dark
    from ui.PressePapiersVM import PressePapiersVM
except Exception:
    from lib.ui.helpers.UIResourceLoader import UIResourceLoader
    from lib.ui.helpers.DarkMode import is_dark
    from lib.ui.PressePapiersVM import PressePapiersVM


def _etat_flottant():
    """Flottant à la première ouverture. Revit mémorise ensuite la position
    choisie par l'utilisateur : ceci ne joue qu'une fois par poste."""
    try:
        from Autodesk.Revit.DB import Rectangle
        from Autodesk.Revit.UI import DockablePaneState, DockPosition
        etat = DockablePaneState()
        etat.DockPosition = DockPosition.Floating
        etat.FloatingRectangle = Rectangle(200, 200, 560, 720)
        return etat
    except Exception:
        return None


def _executer_differe(fn):
    # Le volet n'est pas en contexte API : on passe par l'ExternalEvent.
    demander(lambda uiapp: fn(uiapp.ActiveUIDocument))


class PressePapiersPanel(forms.WPFPanel):
    """Historique du presse-papiers, ancrable. Enregistré par ``startup.py``
    (``default_visible=False``) : masqué tant qu'on ne l'ouvre pas."""

    panel_id = '3d9b6e41-8c27-4f5a-b1e0-6a4c2d7f9e83'
    panel_source = os.path.join(AppPaths().pages_dir(), 'PressePapiersPanel.xaml')
    panel_title = 'Presse-papiers'
    initial_state = _etat_flottant()

    def __init__(self):
        try:
            # Thème 418 fusionné AVANT le parse, comme OpenArchiPanel.
            UIResourceLoader(self, dark=is_dark()).merge_theme()
            forms.WPFPanel.__init__(self)
            self.DataContext = PressePapiersVM(historique(), _executer_differe,
                                               dispatcher=self.Dispatcher)
        except Exception:
            # Revit avale les exceptions de construction d'un volet ancré.
            _log.exception('construction du panneau impossible')
            raise
