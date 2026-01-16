# -*- coding: utf-8 -*-

__title__ = "Keynotes Editor"

__doc__ = """
    Version 0.5
    Auteur : Aliae
    _____________________________________________
    Editeur de Keynotes pour Revit

     - Permet de visualiser et modifier les keynotes presents dans le projet
     - Permet d'importer et d'exporter les keynotes au format txt
    _____________________________________________
"""
__author__ = 'Aliae'    

from lib.ui.windows.MainWindowController import MainWindowController

if __name__ == "__main__":
    ctrl = MainWindowController()
    ctrl.show()
