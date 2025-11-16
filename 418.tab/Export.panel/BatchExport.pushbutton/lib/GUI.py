# -*- coding: utf-8 -*-

# Façade publique de l'UI (fenêtre d'export)
# - Expose ExportMainWindow
# - Fournit GUI.show() comme point d'entrée stable

import os

# Ré-export des éléments clés depuis le package ui
from .ui import ExportMainWindow  # classe réelle de la fenêtre
from .ui.sections_loader import _get_xaml_path  # vérification d'existence XAML


def _show_ui():
    # Affiche la fenêtre principale si le XAML existe
    xaml_path = _get_xaml_path()
    if not os.path.exists(xaml_path):
        try:
            print('[info] XAML introuvable -> {}'.format(xaml_path))
        except Exception:
            print('[info] fenetre_wpf.xaml introuvable')
        return False
    try:
        win = ExportMainWindow()
        # Modal si possible
        try:
            win.ShowDialog()
        except Exception:
            win.show()
        return True
    except Exception as e:
        print('[info] Erreur ouverture UI: {}'.format(e))
        return False


class GUI:
    @staticmethod
    def show():
        # Ouvre la fenêtre d'export et renvoie True si affichée avec succès
        return _show_ui()
