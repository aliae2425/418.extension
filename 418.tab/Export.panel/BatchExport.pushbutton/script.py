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

# Importer les fonctions de configuration
from config import select_export_folder, get_export_path, ensure_export_path, EXPORT_PATH

activ_document   = __revit__.ActiveUIDocument.Document
new_doc = revit.DOCS.doc
uidoc = __revit__.ActiveUIDocument
app   = __revit__.Application

custom_params = ["Exportation", "Carnet", "DWG"]


if __name__ == "__main__":
    print("Hello Batch Export")
    
    # === SÉLECTION DU DOSSIER D'EXPORT ===
    # Ouvrir la fenêtre de sélection de dossier
    export_folder = select_export_folder()
    
    if not export_folder:
        print("Aucun dossier sélectionné. Arrêt du script.")
        exit()
    
    print(f"Dossier d'export sélectionné: {export_folder}")
    
    # Récupérer tous les jeux de feuilles du document
    collector = DB.FilteredElementCollector(activ_document)
    sheet_sets = collector.OfClass(DB.SheetCollection).ToElements()



    # print(sheet_sets.Count)
    for sheet_set in sheet_sets:
        print("nom : %s" % sheet_set.Name)
        for param_name in custom_params:
            param = sheet_set.LookupParameter(param_name)
            if param:
                value = param.AsInteger()  # ou AsString(), AsDouble()
                print("    %s : %s" % (param_name, value))
        