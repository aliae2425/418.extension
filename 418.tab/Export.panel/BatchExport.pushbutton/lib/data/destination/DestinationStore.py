# -*- coding: utf-8 -*-
# Stockage et accès au dossier de destination (logique migrée depuis lib/destination.py)
# - Accès config
# - Validation/Création dossier
# - Génération de noms/chemins d'export
# - Sélection du dossier via UI pyRevit / WinForms

import os
import re
import datetime as _dt

class DestinationStore(object):
    def __init__(self, namespace='batch_export'):
        # Config utilisateur
        try:
            from ...core.UserConfig import UserConfig
        except Exception:
            UserConfig = None  # type: ignore
        self._cfg = UserConfig(namespace) if UserConfig is not None else None
        # Nommage (rows -> pattern)
        try:
            from ..naming.NamingResolver import NamingResolver
        except Exception:
            NamingResolver = None  # type: ignore
        self._namer = NamingResolver() if NamingResolver is not None else None
        # Constantes
        self.DEST_FOLDER_KEY = 'PathDossier'

    # Retourne le dossier enregistré, avec fallback Documents/Exports
    def get(self, default=None):
        try:
            path = self._cfg.get(self.DEST_FOLDER_KEY, '') if self._cfg is not None else ''
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

    # Enregistre le dossier
    def set(self, path):
        try:
            return bool(self._cfg.set(self.DEST_FOLDER_KEY, path or '')) if self._cfg is not None else False
        except Exception:
            return False

    # Gestion des flags (sous-dossiers / formats séparés)
    def get_create_subfolders(self):
        try:
            val = self._cfg.get('create_subfolders', '0') if self._cfg is not None else '0'
            return str(val) == '1'
        except Exception:
            return False

    def set_create_subfolders(self, val):
        try:
            if self._cfg is not None:
                self._cfg.set('create_subfolders', '1' if val else '0')
        except Exception:
            pass

    def get_separate_formats(self):
        try:
            val = self._cfg.get('separate_format_folders', '0') if self._cfg is not None else '0'
            return str(val) == '1'
        except Exception:
            return False

    def set_separate_formats(self, val):
        try:
            if self._cfg is not None:
                self._cfg.set('separate_format_folders', '1' if val else '0')
        except Exception:
            pass

    # Valide/crée le dossier -> (ok: bool, err: str|None)
    def ensure(self, path):
        try:
            if not path:
                return False, 'chemin vide'
            if not os.path.exists(path):
                os.makedirs(path)
            return True, None
        except Exception as e:
            return False, str(e)

    # Nettoie un nom de fichier (Windows)
    def sanitize(self, name, replacement="_"):
        if not name:
            return "untitled"
        invalid = re.compile(r"[\\\\/:*?\"<>|]+")
        trim = re.compile(r"[\s\.]+$")
        base = name.replace(os.sep, replacement).replace('/', replacement)
        base = invalid.sub(replacement, base)
        base = base.strip()
        base = trim.sub('', base)
        if len(base) > 180:
            base = base[:180]
        return base or 'untitled'

    # Calcule un chemin unique si déjà existant
    def unique_path(self, path):
        if not os.path.exists(path):
            return path
        root, ext = os.path.splitext(path)
        i = 1
        while True:
            cand = u"{} ({}){}".format(root, i, ext)
            if not os.path.exists(cand):
                return cand
            i += 1

    # Construit un nom de fichier à partir des rows du Piker
    def build_filename_from_rows(self, rows, timestamp=False, ext='pdf'):
        pattern = ''
        try:
            if self._namer is not None:
                pattern = self._namer.build_pattern(rows)
        except Exception:
            pattern = ''
        fname = self.sanitize(pattern)
        if timestamp:
            ts = _dt.datetime.now().strftime('%Y%m%d-%H%M%S')
            fname = u"{}_{}".format(fname, ts)
        ext = (ext or '').lstrip('.')
        return u"{}.{}".format(fname, ext) if ext else fname

    # Construit un chemin de fichier complet pour l'export
    def build_export_path(self, rows=None, folder=None, timestamp=False, ext='pdf', ensure_dir=True, unique=True):
        folder = folder or self.get()
        if ensure_dir:
            self.ensure(folder)
        filename = self.build_filename_from_rows(rows or [], timestamp=timestamp, ext=ext)
        full = os.path.join(folder, filename)
        return self.unique_path(full) if unique else full

    # UI pyRevit: dialogue simple
    def choose_destination_interactive(self, start_dir=None, save=True):
        try:
            from pyrevit import forms
        except Exception:
            forms = None  # type: ignore
        start = start_dir or self.get()
        chosen = None
        if forms is not None:
            try:
                picker = getattr(forms, 'pick_folder', None)
                if callable(picker):
                    chosen = picker(title='Choisir un dossier de destination', start_dir=start)
            except Exception:
                chosen = None
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
            ok, _ = self.ensure(chosen)
            if ok and save:
                self.set(chosen)
            return chosen
        return None

    # Explorateur Windows (FolderBrowserDialog)
    def choose_destination_explorer(self, start_dir=None, save=True, description=u"Choisir un dossier de destination"):
        try:
            from System.Windows.Forms import FolderBrowserDialog, DialogResult
        except Exception:
            FolderBrowserDialog = None  # type: ignore
            DialogResult = None  # type: ignore
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
                try:
                    start = start_dir or self.get()
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
        if not chosen:
            return self.choose_destination_interactive(start_dir=start_dir, save=save)
        ok, _ = self.ensure(chosen)
        if ok and save:
            self.set(chosen)
        return chosen
