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
from lib.ui.windows.TutorialWindow import show_tutorial
from lib.data.sheets.SheetParameterRepository import SheetParameterRepository


if __name__ == "__main__":
    try:
        doc = __revit__.ActiveUIDocument.Document  # type: ignore
    except Exception:
        doc = None

    if doc:
        repo = SheetParameterRepository()
        # On verifie s'il existe des parametres booleens pour les collections
        params = repo.collect_for_collections(doc, only_boolean=True)
        
        if not params:
            show_tutorial()
        else:
            ctrl = MainWindowController()
            if not ctrl.show():
                print('[erreur] UI non affichée')
