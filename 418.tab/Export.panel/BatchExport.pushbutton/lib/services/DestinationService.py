# -*- coding: utf-8 -*-
# Service de destination : chemins/fichiers d'export + persistance du dossier.
#
# Consolide la logique historiquement portée par :
#   - lib/data/destination/DestinationStore.py
#
# Objectif : un service unique, testable hors Revit, sans dépendance UI.
# Les méthodes UI interactives (choose_destination_interactive/_explorer)
# ne sont PAS migrées ici : elles relèvent de la vue (Phase 3+).

from __future__ import unicode_literals

import os
import re
import datetime as _dt

try:
    from core.UserConfig import UserConfig  # type: ignore
except Exception:
    try:
        from lib.core.UserConfig import UserConfig  # type: ignore
    except Exception:
        UserConfig = None  # type: ignore

try:
    from lib.services.NamingService import NamingService  # type: ignore
except Exception:
    try:
        from .NamingService import NamingService  # type: ignore
    except Exception:
        NamingService = None  # type: ignore


def _as_bool(val):
    """Interprète une valeur de config booléenne de façon ROBUSTE.

    La valeur persistée peut revenir sous diverses représentations selon la
    sérialisation pyRevit ('1', 1, True, la chaîne '"1"' avec guillemets,
    'true'...). Une comparaison stricte `str(val) == '1'` casse pour True /
    '"1"' / 'true' -> le flag lu False alors qu'il a été activé (cause
    candidate de la séparation non appliquée). On normalise ici : True pour
    tout token vrai courant, False sinon (défaut sûr)."""
    try:
        s = u"{}".format(val).strip().strip('"').strip("'").strip().lower()
    except Exception:
        return False
    return s in ('1', 'true', 'yes', 'on')


class DestinationService(object):
    """Gère le dossier de destination et la construction des chemins d'export.

    - `sanitize` : nettoie une chaîne pour en faire un nom de fichier Windows valide.
    - `unique_path` : évite les collisions de fichiers existants.
    - `ensure` : crée le dossier cible si besoin.
    - `get`/`set` : persistance du dossier de destination via UserConfig.
    - `build_export_path` : construit un chemin de fichier complet à partir
      d'un pattern de nommage (rows), en s'appuyant sur `NamingService`.
    """

    DEST_FOLDER_KEY = 'PathDossier'

    def __init__(self, doc=None, config=None, namespace='batch_export', namer=None):
        if config is not None:
            self._cfg = config
        elif UserConfig is not None:
            self._cfg = UserConfig(namespace)
        else:
            self._cfg = None

        if namer is not None:
            self._namer = namer
        elif NamingService is not None:
            self._namer = NamingService(doc=doc, config=self._cfg, namespace=namespace)
        else:
            self._namer = None

    # ------------------------------------------------------------------
    # Persistance du dossier de destination
    # ------------------------------------------------------------------

    def get(self, default=None):
        """Retourne le dossier enregistré, avec fallback ~/Documents/Exports."""
        try:
            path = self._cfg.get(self.DEST_FOLDER_KEY, '') if self._cfg is not None else ''
        except Exception:
            path = ''

        if path and not os.path.exists(path):
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

    def set(self, path):
        """Enregistre le dossier de destination."""
        try:
            return bool(self._cfg.set(self.DEST_FOLDER_KEY, path or '')) if self._cfg is not None else False
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Flags (sous-dossiers / formats séparés) — passthrough UserConfig
    # ------------------------------------------------------------------

    def get_create_subfolders(self):
        try:
            val = self._cfg.get('create_subfolders', '0') if self._cfg is not None else '0'
            return _as_bool(val)
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
            return _as_bool(val)
        except Exception:
            return False

    def set_separate_formats(self, val):
        try:
            if self._cfg is not None:
                self._cfg.set('separate_format_folders', '1' if val else '0')
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Dossier
    # ------------------------------------------------------------------

    def ensure(self, path):
        """Crée le dossier `path` s'il n'existe pas. Retourne le chemin.

        Écart vs legacy : `DestinationStore.ensure` retournait `(ok: bool, err)`.
        Ici on retourne directement `path` (cf. spec Task 2). Si les méthodes
        `choose_destination_*` sont migrées en Phase 3, adapter leur
        `ok, _ = self.ensure(chosen)` à ce nouveau contrat (plus de tuple).
        """
        try:
            if not path:
                return path
            if not os.path.exists(path):
                os.makedirs(path)
        except Exception:
            pass
        return path

    # ------------------------------------------------------------------
    # Nettoyage / unicité des noms de fichiers
    # ------------------------------------------------------------------

    def sanitize(self, name, replacement="_"):
        """Nettoie `name` pour en faire un nom de fichier Windows valide.

        Retire les caractères interdits `\\ / : * ? " < > |`, tronque
        à 180 caractères. Retourne 'untitled' si vide après nettoyage.
        """
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

    def unique_path(self, path):
        """Retourne `path` inchangé s'il n'existe pas, sinon suffixe (1), (2)..."""
        if not os.path.exists(path):
            return path
        root, ext = os.path.splitext(path)
        i = 1
        while True:
            cand = u"{} ({}){}".format(root, i, ext)
            if not os.path.exists(cand):
                return cand
            i += 1

    # ------------------------------------------------------------------
    # Construction du chemin d'export (s'appuie sur NamingService)
    # ------------------------------------------------------------------

    def build_filename_from_rows(self, rows, timestamp=False, ext='pdf'):
        """Construit un nom de fichier à partir du pattern (rows) via NamingService.

        Note : `build_pattern` produit un template littéral (`{Name}` non résolu
        contre un élément concret) — comportement identique au legacy
        `DestinationStore.build_filename_from_rows`. La résolution réelle par
        élément (sheet/carnet) est reportée à la Phase 3 (branchement VM/orchestrateur).
        """
        pattern = ''
        try:
            if self._namer is not None:
                pattern = self._namer.build_pattern(rows or [])
        except Exception:
            pattern = ''
        fname = self.sanitize(pattern)
        if timestamp:
            ts = _dt.datetime.now().strftime('%Y%m%d-%H%M%S')
            fname = u"{}_{}".format(fname, ts)
        ext = (ext or '').lstrip('.')
        return u"{}.{}".format(fname, ext) if ext else fname

    def build_export_path(self, rows=None, folder=None, timestamp=False,
                           ext='pdf', ensure_dir=False, unique=False):
        """Construit un chemin de fichier complet pour l'export.

        - `rows` : pattern de nommage (list[dict]) -> template via NamingService.build_pattern.
        - `folder` : dossier cible (fallback `self.get()`).
        - `ensure_dir` : crée le dossier si absent.
        - `unique` : suffixe (1), (2)... si le chemin existe déjà.
        """
        folder = folder or self.get()
        if ensure_dir:
            self.ensure(folder)
        filename = self.build_filename_from_rows(rows or [], timestamp=timestamp, ext=ext)
        full = os.path.join(folder, filename)
        return self.unique_path(full) if unique else full
