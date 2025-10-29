# -*- coding: utf-8 -*-

# ------------------------------- info pyrevit ------------------------------- #
__title__ = "Exportation"
__doc__ = """
    Version 0.0.1
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
# __max_revit_ver__ = 2026

# ------------------------------- info pyrevit ------------------------------- #
from pyrevit.userconfig import user_config
from pyrevit import script, forms
from pyrevit import DB, HOST_APP, UI, revit, script
from pyrevit.forms import alert
from pyrevit.framework import List
from re import sub

activ_document   = __revit__.ActiveUIDocument.Document
new_doc = revit.DOCS.doc
uidoc = __revit__.ActiveUIDocument
app   = __revit__.Application


if __name__ == "__main__":
    print("Hello Batch Export")

    # Récupérer tous les jeux de feuilles du document
    sheet_sets = DB.FilteredElementCollector(activ_document)\
        .OfClass(DB.ViewSheetSet)\
        .ToElements()

    print (sheet_sets.Count)
    print("Jeux de feuilles trouvés:")
    for sheet_set in sheet_sets:
        print(f"Nom: {sheet_set.Name!r}")