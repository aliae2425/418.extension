# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import os
import csv
import io
import sys


def _data_dir_from_here():
    # lib/services -> lib -> BatchExport.pushbutton
    here = os.path.dirname(__file__)
    return os.path.normpath(os.path.join(here, '..', '..', 'Data'))


def _profiles_store_path():
    return os.path.join(_data_dir_from_here(), 'profiles.json')


def _ensure_dir(path):
    try:
        d = os.path.dirname(path)
        if d and not os.path.exists(d):
            os.makedirs(d)
    except Exception:
        pass


def _load_json_file(path, default):
    if not path:
        return default
    try:
        if not os.path.exists(path):
            return default
        with io.open(path, mode='r', encoding='utf-8-sig') as f:
            raw = f.read()
        return _safe_json_loads(raw, default)
    except Exception:
        return default


def _save_json_file(path, data_obj):
    if not path:
        return False
    _ensure_dir(path)
    try:
        with io.open(path, mode='w', encoding='utf-8', newline='') as f:
            f.write(_to_text(json.dumps(data_obj, indent=2, sort_keys=True)))
        return True
    except Exception:
        return False


try:
    unicode  # type: ignore
except Exception:
    unicode = str  # type: ignore


def _to_text(value):
    try:
        return u"{}".format(value)
    except Exception:
        try:
            return str(value)
        except Exception:
            return ''


def _safe_json_loads(raw, default):
    if raw is None:
        return default
    try:
        if isinstance(raw, (str, unicode)):
            raw = raw.strip()
        if not raw:
            return default
        data = json.loads(raw)
        return data
    except Exception:
        return default

class Profile(object):

    def __init__(self, name, data=None):
        self.name = name
        self.data = data if data else {}

class ConfigManagerService(object):

    # Liste des clés de configuration qui doivent suivre un profil.
    # NB: certains modules utilisent des variantes historiques (ex: 'pathdossier')
    PROFILE_KEYS = [
        # Destination
        'PathDossier',
        'pathdossier',
        'create_subfolders',
        'separate_format_folders',
        # Paramètres (combos)
        'sheet_param_ExportationCombo',
        'sheet_param_CarnetCombo',
        'sheet_param_DWGCombo',
        # Variantes legacy
        'sheet_param_exportationcombo',
        'sheet_param_carnetcombo',
        'sheet_param_dwgcombo',
        # Nommage
        'pattern_sheet',
        'pattern_set',
        'pattern_sheet_rows',
        'pattern_set_rows',
        # Options PDF/DWG
        'pdf_setup_name',
        'dwg_setup_name',
        'pdf_separate_views',
        'dwg_separate_views',
        # Setups customs
        'custom_pdf_setups',
        'custom_dwg_setups',
        # Réservé (futur)
        'excluded_sheet_params',
    ]

    # Key stockée dans le userconfig pyRevit: seulement le profil actif
    _ACTIVE_PROFILE_KEY = 'active_profile'

    # Mapping de compat pour normaliser les clés (profil -> config)
    _KEY_ALIASES = {
        'pathdossier': 'PathDossier',
        'sheet_param_exportationcombo': 'sheet_param_ExportationCombo',
        'sheet_param_carnetcombo': 'sheet_param_CarnetCombo',
        'sheet_param_dwgcombo': 'sheet_param_DWGCombo',
    }

    def __init__(self):

        try:
            from ..core.UserConfig import UserConfig
        except Exception:
            UserConfig = None  # type: ignore
        self._cfg = UserConfig('batch_export') if UserConfig is not None else None

        # pyRevit userconfig: uniquement pour mémoriser le profil actif
        # Import dynamique pour éviter les erreurs d'analyse hors environnement pyRevit.
        _UC = None
        try:
            import importlib
            m = importlib.import_module('pyrevit.userconfig')
            _UC = getattr(m, 'user_config', None)
        except Exception:
            _UC = None  # type: ignore
        self._uc = _UC

    def _ensure_cfg(self):
        if self._cfg is None:
            return None
        return self._cfg

    def _load_profiles_store(self):
        path = _profiles_store_path()
        data = _load_json_file(path, {})
        return data if isinstance(data, dict) else {}

    def _save_profiles_store(self, store_dict):
        safe = store_dict if isinstance(store_dict, dict) else {}
        return bool(_save_json_file(_profiles_store_path(), safe))

    def _snapshot_current_config(self):
        cfg = self._ensure_cfg()
        if cfg is None:
            return {}
        snap = {}
        for k in self.PROFILE_KEYS:
            try:
                snap[k] = cfg.get(k, '')
            except Exception:
                snap[k] = ''
        return snap

    def _apply_config_dict(self, data_dict):
        cfg = self._ensure_cfg()
        if cfg is None:
            return False
        if not isinstance(data_dict, dict):
            return False
        ok = True
        for k, v in data_dict.items():
            # Normalisation clé
            nk = self._KEY_ALIASES.get(k, k)
            try:
                if nk == 'excluded_sheet_params':
                    # Accepte liste JSON ou string
                    if isinstance(v, list):
                        cfg.set(nk, json.dumps(v))
                    else:
                        cfg.set(nk, _to_text(v))
                else:
                    cfg.set(nk, _to_text(v))
            except Exception:
                ok = False

        # Cohérence: si un profil avait pathdossier mais pas PathDossier
        try:
            pd = cfg.get('PathDossier', '')
            if not pd:
                legacy = cfg.get('pathdossier', '')
                if legacy:
                    cfg.set('PathDossier', _to_text(legacy))
        except Exception:
            pass

        return ok

    def _set_active_profile_key(self, name):
        name = (name or '').strip()
        uc = getattr(self, '_uc', None)
        if uc is None:
            return False

    def get_active_profile_name(self):
        """Retourne le nom du profil actif stocké dans pyRevit userconfig (si dispo)."""
        uc = getattr(self, '_uc', None)
        if uc is None:
            return None
        try:
            try:
                uc.add_section('batch_export')
            except Exception:
                pass
            sec = uc.batch_export
            # Préférence à get_option
            if hasattr(sec, 'get_option'):
                try:
                    val = sec.get_option(self._ACTIVE_PROFILE_KEY, '')
                except Exception:
                    val = ''
            else:
                val = getattr(sec, self._ACTIVE_PROFILE_KEY, '')
            val = (val or '').strip()
            return val or None
        except Exception:
            return None
        try:
            # garantir section
            try:
                uc.add_section('batch_export')
            except Exception:
                pass
            sec = uc.batch_export
            if hasattr(sec, 'set_option'):
                sec.set_option(self._ACTIVE_PROFILE_KEY, name)
            else:
                setattr(sec, self._ACTIVE_PROFILE_KEY, name)
            try:
                uc.save_changes()
            except Exception:
                pass
            return True
        except Exception:
            return False

    # API appelée par ConfigManagerWindow
    def get_profiles(self):
        """Retourne {name: Profile} pour affichage UI."""
        store = self._load_profiles_store()
        out = {}
        for name, data in store.items():
            try:
                if not name:
                    continue
                out[_to_text(name)] = Profile(_to_text(name), data if isinstance(data, dict) else {})
            except Exception:
                continue
        return out

    def save_profile(self, name):
        """Sauvegarde la config actuelle sous un nom de profil."""
        name = (name or '').strip()
        if not name:
            return False
        store = self._load_profiles_store()
        store[name] = self._snapshot_current_config()
        ok = self._save_profiles_store(store)
        if ok:
            self._set_active_profile_key(name)
        return ok

    def load_profile(self, name):
        """Charge un profil -> applique les clés dans UserConfig."""
        name = (name or '').strip()
        if not name:
            return False
        store = self._load_profiles_store()
        data = store.get(name)
        if not isinstance(data, dict):
            return False
        return self._apply_config_dict(data)

    def delete_profile(self, name):
        name = (name or '').strip()
        if not name:
            return False
        store = self._load_profiles_store()
        if name not in store:
            return False
        try:
            del store[name]
        except Exception:
            return False
        return self._save_profiles_store(store)

    def export_current_config_to_csv(self, path):
        """Exporte la configuration courante vers un CSV (key,value)."""
        cfg = self._ensure_cfg()
        if cfg is None:
            return False
        if not path:
            return False

        try:
            # pyRevit peut renvoyer un path sans extension
            if not path.lower().endswith('.csv'):
                path = path + '.csv'
        except Exception:
            pass

        # Snapshot normalisé
        data = self._snapshot_current_config()
        try:
            with io.open(path, mode='w', encoding='utf-8', newline='') as f:
                w = csv.writer(f)
                w.writerow(['key', 'value'])
                for k in sorted(data.keys(), key=lambda s: _to_text(s).lower()):
                    v = data.get(k, '')
                    # Stocker la valeur comme string (JSON si dict/list)
                    if isinstance(v, (dict, list)):
                        v = json.dumps(v)
                    w.writerow([_to_text(k), _to_text(v)])
            return True
        except Exception as e:
            try:
                print('ConfigManagerService [export]: {}'.format(e))
            except Exception:
                pass
            return False

    def import_config_from_csv(self, path):
        """Importe un CSV (key,value) et applique la config (sans créer de profil)."""
        if not path or not os.path.exists(path):
            return False
        try:
            with io.open(path, mode='r', encoding='utf-8-sig', newline='') as f:
                r = csv.reader(f)
                rows = list(r)
        except Exception:
            return False

        if not rows:
            return False

        # Détecter header optionnel
        start_idx = 0
        try:
            head = [c.strip().lower() for c in rows[0]]
            if len(head) >= 2 and head[0] in ('key', 'clef', 'clé') and head[1] in ('value', 'valeur'):
                start_idx = 1
        except Exception:
            start_idx = 0

        data = {}
        for row in rows[start_idx:]:
            if not row or len(row) < 1:
                continue
            k = (row[0] or '').strip() if len(row) >= 1 else ''
            if not k:
                continue
            v = row[1] if len(row) >= 2 else ''
            v = '' if v is None else v
            # Essayer de parser JSON quand c'est un objet/list
            vv = v
            try:
                sv = v.strip() if isinstance(v, (str, unicode)) else v
                if isinstance(sv, (str, unicode)) and sv and sv[0] in ('{', '['):
                    parsed = json.loads(sv)
                    vv = parsed
            except Exception:
                vv = v
            data[k] = vv

        return self._apply_config_dict(data)