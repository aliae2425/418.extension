# -*- coding: utf-8 -*-

# ------------------------------- info pyrevit ------------------------------- #
__title__ = "Exportation"
__doc__ = """
    Version 0.4
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
from lib.ui.windows.MainWindowController import MainWindowController



if __name__ == "__main__":
    ctrl = MainWindowController()
    if not ctrl.show():
        print('[erreur] UI non affichée')
