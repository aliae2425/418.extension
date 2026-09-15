# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from pyrevit import forms

try:
    from core.AppPaths import AppPaths
except Exception:
    from lib.core.AppPaths import AppPaths

try:
    from ui.helpers.UIResourceLoader import UIResourceLoader
    from ui.helpers.DarkMode import is_dark
    from ui.base.BaseWindow import BaseWindow
    from ui.OpenArchiChatVM import OpenArchiChatVM
    from ui.OpenArchiConfigVM import OpenArchiConfigVM
except Exception:
    from lib.ui.helpers.UIResourceLoader import UIResourceLoader
    from lib.ui.helpers.DarkMode import is_dark
    from lib.ui.base.BaseWindow import BaseWindow
    from lib.ui.OpenArchiChatVM import OpenArchiChatVM
    from lib.ui.OpenArchiConfigVM import OpenArchiConfigVM

_FENETRE_CONFIG = os.path.join(AppPaths().ui_gui_dir(), 'OpenArchiConfigWindow.xaml')


def ouvrir_config(config):
    """Modale /config : fournisseur, modèle, projet. Bloquante (ShowDialog)."""
    BaseWindow(_FENETRE_CONFIG, OpenArchiConfigVM(config)).show()


class OpenArchiPanel(forms.WPFPanel):
    """Panneau de chat ancrable dans l'interface Revit.

    Enregistré par ``startup.py`` : l'API Revit n'accepte
    ``RegisterDockablePane`` que pendant OnStartup.
    """

    panel_id = '7f3c1a92-4b6e-4d18-9a55-0c2f8e1d4b07'
    panel_source = os.path.join(AppPaths().pages_dir(), 'OpenArchiPanel.xaml')
    panel_title = 'OpenArchi'

    def __init__(self):
        # Le thème 418 est fusionné AVANT le parse du XAML : les
        # DynamicResource du panneau se résolvent sur Page.Resources.
        UIResourceLoader(self, dark=is_dark()).merge_theme()
        forms.WPFPanel.__init__(self)
        vm = OpenArchiChatVM(ouvrir_config=ouvrir_config)
        self.DataContext = vm
        self._suivre_dernier_message(vm)

    def _suivre_dernier_message(self, vm):
        # Défilement automatique : sans cela le dernier message reste sous la
        # ligne de flottaison dès que la conversation dépasse la hauteur.
        try:
            def _defiler(sender, args):
                self.Conversation.ScrollToEnd()
            vm.Messages.CollectionChanged += _defiler
        except Exception:
            pass
