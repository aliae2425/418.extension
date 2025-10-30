from pyrevit.userconfig import user_config
from pyrevit import DB, forms
import os

activ_document   = __revit__.ActiveUIDocument.Document

# Variable globale pour stocker le chemin d'accès
EXPORT_PATH = None

def select_export_folder():
    """
    Ouvre une fenêtre de dialogue pour sélectionner un dossier d'export
    et stocke le chemin dans la variable globale EXPORT_PATH
    """
    global EXPORT_PATH
    
    # Méthode 1: Utiliser forms.pick_folder (recommandée pour pyRevit)
    selected_folder = forms.pick_folder(
        title="Sélectionnez le dossier d'export",
        default=os.path.expanduser("~/Desktop")  # Dossier par défaut: Bureau
    )
    
    if selected_folder:
        EXPORT_PATH = selected_folder
        print(f"Dossier sélectionné: {EXPORT_PATH}")
        return EXPORT_PATH
    else:
        print("Aucun dossier sélectionné")
        return None

def select_export_file():
    """
    Alternative: Ouvre une fenêtre pour sélectionner un fichier existant
    et récupère son dossier parent
    """
    global EXPORT_PATH
    
    selected_file = forms.pick_file(
        title="Sélectionnez un fichier (le dossier parent sera utilisé)",
        files_filter="Tous les fichiers (*.*)|*.*"
    )
    
    if selected_file:
        EXPORT_PATH = os.path.dirname(selected_file)
        print(f"Dossier parent sélectionné: {EXPORT_PATH}")
        return EXPORT_PATH
    else:
        print("Aucun fichier sélectionné")
        return None

def get_export_path():
    """
    Retourne le chemin d'export stocké dans la variable globale
    """
    global EXPORT_PATH
    return EXPORT_PATH

def set_export_path(path):
    """
    Définit manuellement le chemin d'export
    """
    global EXPORT_PATH
    if os.path.exists(path):
        EXPORT_PATH = path
        print(f"Chemin d'export défini: {EXPORT_PATH}")
        return True
    else:
        print(f"Le chemin n'existe pas: {path}")
        return False

def ensure_export_path():
    """
    Vérifie si un chemin est défini, sinon ouvre la fenêtre de sélection
    """
    global EXPORT_PATH
    if not EXPORT_PATH or not os.path.exists(EXPORT_PATH):
        print("Aucun chemin d'export valide. Sélection d'un dossier...")
        return select_export_folder()
    return EXPORT_PATH

