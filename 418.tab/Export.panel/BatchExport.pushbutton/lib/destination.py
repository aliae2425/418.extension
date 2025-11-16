# -*- coding: utf-8 -*-
"""Logique de destination d'export (dossiers et chemins de fichiers).

Objectifs:
- Centraliser la lecture/écriture du dossier de destination (config key: "PathDossier").
- Fournir des helpers pour: valider/créer le dossier, fabriquer un nom de fichier sûr,
  résoudre les collisions (nom déjà existant) et produire un chemin complet.

Ce module ne dépend pas de l'API Revit; il peut être utilisé par l'UI et le script d'export.
"""

from __future__ import unicode_literals

import os
import re
import datetime as _dt

from .config import UserConfigStore
from .naming import build_pattern_from_rows


# Config store (namespace déjà utilisé ailleurs)
CONFIG = UserConfigStore('batch_export')

# Clé de configuration existante pour le dossier cible
DEST_FOLDER_KEY = 'PathDossier'


# -*- coding: utf-8 -*-
"""Facade: re-export destination helpers from core.destination."""

from .core.destination import (
    DEST_FOLDER_KEY,
    get_saved_destination,
    set_saved_destination,
    ensure_directory,
    sanitize_filename,
    unique_path,
    build_filename_from_rows,
    build_export_path,
    choose_destination_interactive,
    choose_destination_explorer,
)

__all__ = [
    "DEST_FOLDER_KEY",
    "get_saved_destination",
    "set_saved_destination",
    "ensure_directory",
    "sanitize_filename",
    "unique_path",
    "build_filename_from_rows",
    "build_export_path",
    "choose_destination_interactive",
    "choose_destination_explorer",
]
    - timestamp: ajoute _YYYYMMDD-HHMMSS au nom
    - ext: extension sans point
    - ensure_dir: crée le dossier s'il n'existe pas
    - unique: s'il existe, incrémente (1), (2), ...
    """
    folder = folder or get_saved_destination()
    if ensure_dir:
        ensure_directory(folder)
    filename = build_filename_from_rows(rows or [], timestamp=timestamp, ext=ext)
    full = os.path.join(folder, filename)
    if unique:
        full = unique_path(full)
    return full


# (Optionnel) UI helper: tentative d'ouverture d'un sélecteur de dossier pyRevit
def choose_destination_interactive(start_dir=None, save=True):
    """Ouvre un sélecteur de dossier (si disponible) et enregistre le choix.

    Retourne le dossier choisi ou None.
    """
    try:
        from pyrevit import forms
    except Exception:
        forms = None  # type: ignore

    start = start_dir or get_saved_destination()
    chosen = None
    if forms is not None:
        # pyRevit fournit "forms.pick_folder" (selon versions). Fallback silencieux sinon.
        try:
            picker = getattr(forms, 'pick_folder', None)
            if callable(picker):
                chosen = picker(title='Choisir un dossier de destination', start_dir=start)
        except Exception:
            chosen = None
    # Fallback simple via input console (rare en production pyRevit)
    if not chosen:
        try:
            hint = u"Entrer un chemin de dossier (laisser vide pour annuler) [{}]: ".format(start)
            entered = input(hint)  # type: ignore
            entered = (entered or '').strip()
            if entered:
                chosen = entered
        except Exception:
            chosen = None
    if chosen:
        ok, _ = ensure_directory(chosen)
        if ok and save:
            set_saved_destination(chosen)
        return chosen
    return None


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

# ----------------------------------------------------------------------------
# Explorateur Windows (FolderBrowserDialog)
# ----------------------------------------------------------------------------

try:
    # Disponible dans l'environnement IronPython/.NET de pyRevit
    from System.Windows.Forms import FolderBrowserDialog, DialogResult
except Exception:
    FolderBrowserDialog = None  # type: ignore
    DialogResult = None  # type: ignore


def choose_destination_explorer(start_dir=None, save=True, description=u"Choisir un dossier de destination"):
    """Ouvre la boîte de dialogue native Windows pour choisir un dossier.

    Fallback automatique vers `choose_destination_interactive` si WinForms indisponible.
    Retourne le dossier choisi ou None.
    """
    # Si WinForms est disponible, l'utiliser et NE PAS faire de fallback si l'utilisateur annule (Échap/CANCEL)
    if FolderBrowserDialog is not None and DialogResult is not None:
        try:
            dlg = FolderBrowserDialog()
            if description:
                try:
                    dlg.Description = description
                except Exception:
                    pass
            dlg.ShowNewFolderButton = True
            # Point de départ
            try:
                start = start_dir or get_saved_destination()
                if start and os.path.isdir(start):
                    dlg.SelectedPath = start
            except Exception:
                pass
            res = dlg.ShowDialog()
            if res == DialogResult.OK:
                try:
                    chosen = dlg.SelectedPath
                except Exception:
                    chosen = None
                if chosen:
                    ok, _ = ensure_directory(chosen)
                    if ok and save:
                        set_saved_destination(chosen)
                return chosen
            else:
                # Annulation / Échap -> ne rien ouvrir d'autre, retourner None
                return None
        except Exception:
            # En cas d'échec d'ouverture du dialogue WinForms, on tente le fallback simple
            pass
    # Fallback uniquement si WinForms indisponible
    return choose_destination_interactive(start_dir=start_dir, save=save)

