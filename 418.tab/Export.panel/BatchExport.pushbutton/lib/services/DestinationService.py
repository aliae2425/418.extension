# -*- coding: utf-8 -*-
# Service de destination : chemins/fichiers d'export + persistance du dossier.
# Source unique, testable hors Revit, sans dépendance UI. Utilisé par le
# ViewModel ET par ExportOrchestrator (même instance de config injectée).

from __future__ import unicode_literals

import os
import re

try:
    from core.UserConfig import UserConfig  # type: ignore
except Exception:
    try:
        from lib.core.UserConfig import UserConfig  # type: ignore
    except Exception:
        UserConfig = None  # type: ignore


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

    La résolution des motifs de nommage n'est PAS ici : elle appartient à
    `NamingService`, appelé directement par `ExportOrchestrator`.
    """

    DEST_FOLDER_KEY = 'PathDossier'

    def __init__(self, doc=None, config=None, namespace='batch_export'):
        if config is not None:
            self._cfg = config
        elif UserConfig is not None:
            self._cfg = UserConfig(namespace)
        else:
            self._cfg = None

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
        """Crée le dossier `path` s'il n'existe pas. Retourne le chemin."""
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
