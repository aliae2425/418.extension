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


def create_custom_parameter(param_name, sheet_set):
    with DB.Transaction(activ_document, "Créer paramètre") as t:
        t.Start()
        try:
            external_definition = DB.ExternalDefinitionCreationOptions(param_name, DB.SpecTypeId.Boolean.YesNo)
            print(type(sheet_set), dir(sheet_set))
            sheet_set.Document.FamilyManager.AddParameter(external_definition, DB.BuiltInParameterGroup.PG_TEXT, False)
            """
            AddParameter(
                ExternalDefinition familyDefinition,
                ForgeTypeId groupTypeId,
                bool isInstance
            )"""
        except Exception as e:
            print("Erreur lors de la création du paramètre '%s': %s" % (param_name, str(e)))
            return False
        t.Commit()
    return True

def check_missing_parameters(sheet_set):
    missing_params = []
    for param in custom_params:
        if sheet_set.LookupParameter(param) is None:
            missing_params.append(param)
    return missing_params

def check_base_parameters(sheet_sets):
    if sheet_sets[0].IsValidObject:
        missing_params = check_missing_parameters(sheet_sets[0])
        if len(missing_params)>0:
            # Proposer de créer les paramètres manquants
            result = alert(
                "%s parametres manquants détectés.\n\n" %  len(missing_params) + \
                "Les paramètres personnalisés requis ne sont pas présents dans les jeux de feuilles.\n\n"
                "Voulez-vous les créer automatiquement ?",
                title="Paramètres manquants",
                yes=True, no=True
            )

            if result:
                print("Création des paramètres de projet...")
                print(type(missing_params[0]))
                for param in missing_params:
                    if create_custom_parameter(param, sheet_sets[0]):
                        alert("Paramètres créés avec succès ! Relancez le script.", title="Succès")
                    else:
                        alert("Erreur lors de la création des paramètres.", title="Erreur")
#                    script.exit()
            else:
                script.exit()
    return True


if __name__ == "__main__":
    print("Hello Batch Export")
     
    # Récupérer tous les jeux de feuilles du document
    collector = DB.FilteredElementCollector(activ_document)
    sheet_sets = collector.OfClass(DB.SheetCollection).ToElements()

    if not sheet_sets:
        alert("Aucun jeu de feuilles trouvé dans le document.", title="Batch Export")
        script.exit()
    
    # Vérifier la présence des paramètres personnalisés
    if check_base_parameters(sheet_sets):
        print("Liste des jeux de feuilles et valeurs des paramètres personnalisés:")
        # print(sheet_sets.Count)
        for sheet_set in sheet_sets:
            print("nom : %s" % sheet_set.Name)
            for param_name in custom_params:
                param = sheet_set.LookupParameter(param_name)
                if param:
                    value = param.AsInteger()  # ou AsString(), AsDouble()
                    print("    %s : %s" % (param_name, value))
            