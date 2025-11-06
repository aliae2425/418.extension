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
from pyrevit import script, forms
from pyrevit import DB, revit
from pyrevit.forms import alert

# ------------------------------- Variables globales ------------------------------- #
activ_document = __revit__.ActiveUIDocument.Document
app = __revit__.Application
custom_params = ["Exportation", "Carnet", "DWG"]

# ------------------------------- Fonctions ------------------------------- #

def check_parameters_exist(sheet_set):
    """Vérifie si tous les paramètres requis existent sur un jeu de feuilles"""
    missing_params = []
    for param_name in custom_params:
        if sheet_set.LookupParameter(param_name) is None:
            missing_params.append(param_name)
    return missing_params

def display_sheet_sets_info(sheet_sets):
    """Affiche les informations des jeux de feuilles et leurs paramètres"""
    print("\n=== {} jeu(x) de feuilles trouvé(s) ===".format(len(sheet_sets)))
    
    for sheet_set in sheet_sets:
        print("\nJeu de feuilles: {}".format(sheet_set.Name))
        
        for param_name in custom_params:
            param = sheet_set.LookupParameter(param_name)
            if param and param.HasValue:
                value = param.AsInteger()
                display_value = "Oui" if value == 1 else "Non"
                print("    {}: {}".format(param_name, display_value))
            else:
                print("    {}: Non défini".format(param_name))

# ------------------------------- Script principal ------------------------------- #

if __name__ == "__main__":
    print("=== Hello Batch Export ===")
    
    # Récupérer tous les jeux de feuilles du document
    collector = DB.FilteredElementCollector(activ_document)
    sheet_sets = collector.OfClass(DB.SheetCollection).ToElements()

    if not sheet_sets:
        alert("Aucun jeu de feuilles trouvé dans le document.", title="Batch Export")
        script.exit()
    
    # Vérifier les paramètres sur le premier jeu de feuilles
    if sheet_sets and sheet_sets[0].IsValidObject:
        missing_params = check_parameters_exist(sheet_sets[0])
        
        if missing_params:
            message = "Paramètres manquants détectés:\n\n"
            for param in missing_params:
                message += "- {}\n".format(param)
            message += "\nCes paramètres doivent être créés manuellement dans Revit.\n"
            message += "Allez dans Gérer > Paramètres de projet pour les créer."
            
            alert(message, title="Paramètres manquants")
            print("Paramètres manquants: {}".format(", ".join(missing_params)))
        else:
            print("Tous les paramètres requis sont présents !")
            display_sheet_sets_info(sheet_sets)
    
    print("\n=== Fin du script ===")