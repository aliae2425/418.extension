# -*- coding: utf-8 -*-
"""Core destination helpers: folder handling and filename building."""

from __future__ import unicode_literals

import os
import re
import datetime as _dt

from .config import UserConfigStore
from .naming import build_pattern_from_rows

CONFIG = UserConfigStore('batch_export')
DEST_FOLDER_KEY = 'PathDossier'


def get_saved_destination(default=None):
    try:
        path = CONFIG.get(DEST_FOLDER_KEY, '') or ''
    except Exception:
        path = ''
    if path:
        return path
    if default:
        return default
    try:
        home = os.path.expanduser('~')
        docs = os.path.join(home, 'Documents')
        return os.path.join(docs, 'Exports')
    except Exception:
        return os.getcwd()


def set_saved_destination(path):
    try:
        return bool(CONFIG.set(DEST_FOLDER_KEY, path or ''))
    except Exception:
        return False


def ensure_directory(path):
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
    if not name:
        return "untitled"
    base = name.replace(os.sep, replacement).replace('/', replacement)
    base = _INVALID_CHARS_RE.sub(replacement, base)
    base = base.strip()
    base = _TRIM_DOTS_SPACES_RE.sub('', base)
    if len(base) > 180:
        base = base[:180]
    return base or 'untitled'


def unique_path(path):
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
    folder = folder or get_saved_destination()
    if ensure_dir:
        ensure_directory(folder)
    filename = build_filename_from_rows(rows or [], timestamp=timestamp, ext=ext)
    full = os.path.join(folder, filename)
    if unique:
        full = unique_path(full)
    return full


# Interactive helpers

def choose_destination_interactive(start_dir=None, save=True):
    """Try pyRevit folder picker; do not fall back to console input under IronPython.

    Returns selected path or None.
    """
    try:
        from pyrevit import forms
    except Exception:
        forms = None  # type: ignore
    start = start_dir or get_saved_destination()
    chosen = None
    if forms is not None:
        try:
            picker = getattr(forms, 'pick_folder', None)
            if callable(picker):
                chosen = picker(title='Choisir un dossier de destination', start_dir=start)
        except Exception:
            chosen = None
    # No console fallback to avoid IronPython "unexpected indent" on input()
    if chosen:
        ok, _ = ensure_directory(chosen)
        if ok and save:
            set_saved_destination(chosen)
        return chosen
    return None


# Windows explorer dialog (FolderBrowserDialog)
try:
    from System.Windows.Forms import FolderBrowserDialog, DialogResult
except Exception:
    FolderBrowserDialog = None  # type: ignore
    DialogResult = None  # type: ignore


def choose_destination_explorer(start_dir=None, save=True, description=u"Choisir un dossier de destination"):
    if FolderBrowserDialog is not None and DialogResult is not None:
        try:
            dlg = FolderBrowserDialog()
            if description:
                try:
                    dlg.Description = description
                except Exception:
                    pass
            dlg.ShowNewFolderButton = True
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
                return None
        except Exception:
            pass
    # If WinForms dialog fails, do not fall back to console input; return None.
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
