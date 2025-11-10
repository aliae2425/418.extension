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


def get_saved_destination(default=None):
    """Retourne le dossier de destination enregistré, ou `default`.

    Si rien n'est configuré, tente "Documents\\Exports" dans le profil utilisateur.
    """
    try:
        path = CONFIG.get(DEST_FOLDER_KEY, '') or ''
    except Exception:
        path = ''
    if path:
        return path
    if default:
        return default
    # Fallback: Documents/Exports
    try:
        home = os.path.expanduser('~')
        docs = os.path.join(home, 'Documents')
        return os.path.join(docs, 'Exports')
    except Exception:
        return os.getcwd()


def set_saved_destination(path):
    """Enregistre le dossier de destination (tel quel). Retourne True/False."""
    try:
        return bool(CONFIG.set(DEST_FOLDER_KEY, path or ''))
    except Exception:
        return False


def ensure_directory(path):
    """Crée le dossier s'il n'existe pas. Retourne (exists_ok: bool, error: str|None)."""
    try:
        if not path:
            return False, 'chemin vide'
        if not os.path.exists(path):
            os.makedirs(path)
        return True, None
    except Exception as e:
        return False, str(e)


_INVALID_CHARS_RE = re.compile(r"[\\\\/:*?\"<>|]+")
_TRIM_DOTS_SPACES_RE = re.compile(r"[\s\.]+$")


def sanitize_filename(name, replacement="_"):
    """Nettoie un nom de fichier pour Windows.

    - remplace les caractères interdits <>:"/\|?* par `replacement`
    - rogne les espaces/points finaux (Windows n'aime pas)
    - limite la longueur à ~180 caractères pour garder de la marge pour l'extension
    """
    if not name:
        return "untitled"
    # Retirer séparateurs de chemin au cas où
    base = name.replace(os.sep, replacement).replace('/', replacement)
    base = _INVALID_CHARS_RE.sub(replacement, base)
    base = base.strip()
    base = _TRIM_DOTS_SPACES_RE.sub('', base)
    if len(base) > 180:
        base = base[:180]
    return base or 'untitled'


def unique_path(path):
    """Si `path` existe déjà, ajoute un suffixe (1), (2), ... et retourne le premier libre."""
    if not os.path.exists(path):
        return path
    root, ext = os.path.splitext(path)
    i = 1
    while True:
        cand = u"{} ({}){}".format(root, i, ext)
        if not os.path.exists(cand):
            return cand
        i += 1


def build_filename_from_rows(rows, timestamp=False, ext='pdf'):
    """Construit un nom de fichier depuis les `rows` du Piker.

    Utilise build_pattern_from_rows pour générer un pattern puis nettoie pour un usage en nom de fichier.
    Options:
      - timestamp: bool -> ajoute _YYYYMMDD-HHMMSS
      - ext: extension sans point (pdf, dwg, ...)
    """
    pattern = build_pattern_from_rows(rows)
    fname = sanitize_filename(pattern)
    if timestamp:
        ts = _dt.datetime.now().strftime('%Y%m%d-%H%M%S')
        fname = u"{}_{}".format(fname, ts)
    ext = (ext or '').lstrip('.')
    if ext:
        return u"{}.{}".format(fname, ext)
    return fname


def build_export_path(rows=None, folder=None, timestamp=False, ext='pdf', ensure_dir=True, unique=True):
    """Retourne un chemin de fichier complet pour l'export.

    - rows: liste de dicts {Name, Prefix, Suffix} (optionnelle, peut être vide)
    - folder: dossier cible; si None, prend la valeur sauvegardée (ou fallback)
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
    chosen = None
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
        except Exception:
            chosen = None
    # Fallback si nécessaire
    if not chosen:
        return choose_destination_interactive(start_dir=start_dir, save=save)
    ok, _ = ensure_directory(chosen)
    if ok and save:
        set_saved_destination(chosen)
    return chosen

