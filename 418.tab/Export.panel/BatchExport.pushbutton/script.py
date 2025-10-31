# -*- coding: utf-8 -*-

import sys
# Assurer la compatibilité UTF-8
if sys.version_info[0] >= 3:
    unicode = str

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

import config

# Importer les fonctions de configuration

activ_document   = __revit__.ActiveUIDocument.Document
new_doc = revit.DOCS.doc
uidoc = __revit__.ActiveUIDocument
app   = __revit__.Application

custom_params = ["Exportation", "Carnet", "DWG"]


if __name__ == "__main__":
    print("Hello Batch Export")
     
    # Récupérer tous les jeux de feuilles du document
    collector = DB.FilteredElementCollector(activ_document)
    sheet_sets = collector.OfClass(DB.SheetCollection).ToElements()

    if not sheet_sets:
        alert("Aucun jeu de feuilles trouvé dans le document.", title="Batch Export")
        script.exit()
    
    if sheet_sets[0].IsValidObject:
        flag = True
        for param in custom_params:
            if sheet_sets[0].LookupParameter(param) == None :
                flag = False
        if not flag:
            # Proposer de créer les paramètres manquants
            result = alert(
                "Les paramètres personnalisés requis ne sont pas présents dans les jeux de feuilles.\n\n"
                "Voulez-vous les créer automatiquement ?",
                title="Paramètres manquants",
                yes=True, no=True
            )
            
            if result:
                print("Création des paramètres de projet...")
                if config.create_sheet_parameters():
                    alert("Paramètres créés avec succès ! Relancez le script.", title="Succès")
                else:
                    alert("Erreur lors de la création des paramètres.", title="Erreur")
                script.exit()
            else:
                script.exit()
            
            

    # print(sheet_sets.Count)
    for sheet_set in sheet_sets:
        print("nom : %s" % sheet_set.Name)
        for param_name in custom_params:
            param = sheet_set.LookupParameter(param_name)
            if param:
                value = param.AsInteger()  # ou AsString(), AsDouble()
                print("    %s : %s" % (param_name, value))
        