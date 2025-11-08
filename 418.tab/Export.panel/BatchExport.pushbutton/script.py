# -*- coding: utf-8 -*-

# ------------------------------- info pyrevit ------------------------------- #
__title__ = "Exportation"
__doc__ = """
    Version 0.1 - Version nettoyée
    Auteur : Aliae
    _____________________________________________

    Export les feuilles par jeu de feuilles en fonction des parametre du jeu 

    Export : inclus les feuilles du jeux a l'export 
    Export par feuilles : exporte les feuilles une par une, par defaut export en carnet compilé avec le nom du jeu
    Export en DWG : Export en DWG en plus du PDF
    _____________________________________________
"""
__author__ = 'Aliae'                               
__min_revit_ver__ = 2026                                       

# ------------------------------- Imports ------------------------------- #
from pyrevit import forms
import os

class ExportMainWindow(forms.WPFWindow):
    """Charge et affiche l'interface WPF 'fenetre_wpf.xaml'."""
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), 'fenetre_wpf.xaml')
        forms.WPFWindow.__init__(self, xaml_path)
        try:
            self.Title = u"418 • Exportation"
        except Exception:
            pass

def show_ui():
    """Affiche la fenêtre principale si le XAML existe."""
    xaml_path = os.path.join(os.path.dirname(__file__), 'fenetre_wpf.xaml')
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

# ------------------------------- Script principal ------------------------------- #

if __name__ == "__main__":
    show_ui()