# -*- coding: utf-8 -*-
# FACADE: compatibilité rétro avec l'ancien module. Toute la logique a été migrée
# vers lib/data/destination/DestinationStore.py. Ces fonctions redirigent
# vers une instance de DestinationStore.

from __future__ import unicode_literals

def _store():
    try:
        from .data.destination.DestinationStore import DestinationStore
        return DestinationStore()
    except Exception:
        return None

# Clé de configuration (exposée pour compat)
DEST_FOLDER_KEY = 'PathDossier'

# Retourne le dossier de destination enregistré
def get_saved_destination(default=None):
    st = _store()
    return st.get(default) if st is not None else default

# Enregistre le dossier de destination
def set_saved_destination(path):
    st = _store()
    return st.set(path) if st is not None else False

# Crée le dossier si besoin
def ensure_directory(path):
    st = _store()
    return st.ensure(path) if st is not None else (False, 'no-store')

# Nettoyage de nom de fichier
def sanitize_filename(name, replacement='_'):
    st = _store()
    return st.sanitize(name, replacement) if st is not None else name

# Chemin unique
def unique_path(path):
    st = _store()
    return st.unique_path(path) if st is not None else path

# Nom de fichier depuis rows
def build_filename_from_rows(rows, timestamp=False, ext='pdf'):
    st = _store()
    return st.build_filename_from_rows(rows, timestamp=timestamp, ext=ext) if st is not None else None

# Chemin complet d'export
def build_export_path(rows=None, folder=None, timestamp=False, ext='pdf', ensure_dir=True, unique=True):
    st = _store()
    return st.build_export_path(rows=rows, folder=folder, timestamp=timestamp, ext=ext, ensure_dir=ensure_dir, unique=unique) if st is not None else None

# Sélecteur de dossier (pyRevit / console)
def choose_destination_interactive(start_dir=None, save=True):
    st = _store()
    return st.choose_destination_interactive(start_dir=start_dir, save=save) if st is not None else None

# Explorateur Windows
def choose_destination_explorer(start_dir=None, save=True, description=u"Choisir un dossier de destination"):
    st = _store()
    return st.choose_destination_explorer(start_dir=start_dir, save=save, description=description) if st is not None else None

__all__ = [
    'DEST_FOLDER_KEY',
    'get_saved_destination',
    'set_saved_destination',
    'ensure_directory',
    'sanitize_filename',
    'unique_path',
    'build_filename_from_rows',
    'build_export_path',
    'choose_destination_interactive',
    'choose_destination_explorer',
]

