# -*- coding: utf-8 -*-
from pyrevit.userconfig import user_config
from pyrevit import DB, forms
import os
import sys

# Assurer la compatibilité UTF-8
if sys.version_info[0] >= 3:
    unicode = str

activ_document = __revit__.ActiveUIDocument.Document
app = __revit__.Application

def create_sheet_parameters():
    try:
        # Démarrer une transaction
        with DB.Transaction(activ_document, "Creer paramètres jeux de feuilles") as t:
            t.Start()
            
            # Paramètres à créer
            parameters_info = [
                {"name": "Exportation", "type": DB.ParameterType.YesNo},
                {"name": "Carnet", "type": DB.ParameterType.YesNo}, 
                {"name": "DWG", "type": DB.ParameterType.YesNo}
            ]
            
            created_count = 0
            
            for param_info in parameters_info:
                # Vérifier si le paramètre existe déjà
                if parameter_exists(param_info["name"]):
                    print("Paramètre '%s' existe déjà" % param_info['name'])
                    created_count += 1
                    continue
                
                # Créer la définition du paramètre
                definition = create_parameter_definition(
                    param_info["name"], 
                    param_info["type"]
                )
                
                if definition:
                    # Créer le binding pour les feuilles
                    binding = create_parameter_binding()
                    
                    # Ajouter au document
                    if activ_document.ParameterBindings.Insert(definition, binding):
                        print("Paramètre '%s' créé avec succès" % param_info['name'])
                        created_count += 1
                    else:
                        print("Échec création paramètre '%s'" % param_info['name'])
            
            t.Commit()
            
            success = created_count == len(parameters_info)
            print("Création terminée: %s/%s paramètres" % created_count, len(parameters_info))
            return success
            
    except Exception as e:
        print("Erreur lors de la création des paramètres: %s" % str(e))
        return False

def parameter_exists(param_name):
    try:
        binding_map = activ_document.ParameterBindings
        iterator = binding_map.ForwardIterator()
        
        while iterator.MoveNext():
            definition = iterator.Key()
            if definition.Name == param_name:
                return True
        return False
    except:
        return False

def create_parameter_definition(name, param_type):

    try:
        # Créer la définition avec le groupe "Données"
        definition = app.Create.NewProjectParameterDefinition(
            name,
            param_type,
            DB.BuiltInParameterGroup.PG_DATA
        )
        return definition
    except Exception as e:
        print("Erreur création définition '%s':" % str(e))
        return None

def create_parameter_binding():
    try:
        # Créer un CategorySet pour les feuilles
        category_set = app.Create.NewCategorySet()
        
        # Ajouter la catégorie des feuilles
        sheet_category = DB.Category.GetCategory(activ_document, DB.BuiltInCategory.OST_Sheets)
        if sheet_category:
            category_set.Insert(sheet_category)
        
        # Créer un binding d'instance
        binding = app.Create.NewInstanceBinding(category_set)
        return binding
        
    except Exception as e:
        print("Erreur création binding: %s" % str(e))
        return None

def get_parameter_value(element, param_name):
    try:
        param = element.LookupParameter(param_name)
        if param and param.HasValue:
            if param.StorageType == DB.StorageType.Integer:
                return param.AsInteger()
            elif param.StorageType == DB.StorageType.String:
                return param.AsString()
            elif param.StorageType == DB.StorageType.Double:
                return param.AsDouble()
        return None
    except:
        return None

def set_parameter_value(element, param_name, value):
    try:
        param = element.LookupParameter(param_name)
        if param and not param.IsReadOnly:
            if param.StorageType == DB.StorageType.Integer:
                param.Set(int(value))
            elif param.StorageType == DB.StorageType.String:
                param.Set(str(value))
            elif param.StorageType == DB.StorageType.Double:
                param.Set(float(value))
            return True
        return False
    except:
        return False

if __name__ == "__main__":
    print("Config module loaded")
    # Test de création des paramètres
    # create_sheet_parameters()