# -*- coding: utf-8 -*-

"""GUI module centralisant l'ouverture de la fenêtre WPF pour l'export.

API publique:
  - GUI.show(): ouvre la fenêtre principale (modal si possible).

Notes:
  - Ce module dépend de pyRevit (pyrevit.forms.WPFWindow). L'analyse statique
    hors Revit peut indiquer un import manquant; dans Revit/pyRevit, l'import
    est disponible.
"""

from pyrevit import forms
import os

# ------------------------------- Helpers ------------------------------- #

GUI_FILE = 'GUI.xaml'
EXPORT_WINDOW_TITLE = u"418 • Exportation"


def _get_xaml_path():
    """Chemin absolu vers GUI.xaml situé un dossier au-dessus de ce fichier."""
    # GUI.py est dans .../BatchExport.pushbutton/lib
    # Le XAML est dans .../BatchExport.pushbutton/GUI.xaml
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), GUI_FILE)


class ExportMainWindow(forms.WPFWindow):
    """Fenêtre WPF basée sur le XAML GUI.xaml."""
    def __init__(self):
        forms.WPFWindow.__init__(self, _get_xaml_path())
        try:
            self.Title = EXPORT_WINDOW_TITLE
        except Exception:
            # En environnement ironpython/pyRevit, certaines propriétés peuvent lever.
            pass


def _show_ui():
    """Affiche la fenêtre principale si le XAML existe."""
    xaml_path = _get_xaml_path()
    if not os.path.exists(xaml_path):
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
        """Ouvre la fenêtre d'export et renvoie True si affichée avec succès."""
        return _show_ui()