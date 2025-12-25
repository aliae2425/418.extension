# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import os
import csv
import io
import sys
import datetime

try:
    from ..core.UserConfig import UserConfig
except Exception:
    UserConfig = None  # type: ignore

class Profile(object):

    def __init__(self, name, data=None):
        self.name = name
        self.data = data if data else {}

class ConfigManagerService(object):

    KEYS = [
        'separate_format_folders',
        'create_subfolders',
        'sheet_param_carnetcombo',
        'sheet_param_dwgcombo',
        'pattern_sheet',
        'pattern_set',
        'pattern_set_rows',
        'pathdossier',
        'pattern_sheet_rows',
        'pdf_setup_name',
        'dwg_setup_name'
    ]

    PROFILE_FILE_NAME = 'profil.json'
    PROFILE_SCHEMA_VERSION = 1
    ACTIVE_PROFILE_KEY_OPTION = 'active_profile_key'

    def __init__(self):
        self._cfg = UserConfig('batch_export') if UserConfig is not None else None

    # ------------------------------- Paths ------------------------------- #
    def _pushbutton_root_dir(self):
        # .../BatchExport.pushbutton/lib/services -> up 3 levels
        return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

    def _data_dir(self):
        return os.path.join(self._pushbutton_root_dir(), 'Data')

    def _profiles_json_path(self):
        return os.path.join(self._data_dir(), self.PROFILE_FILE_NAME)

    def _ensure_data_dir(self):
        data_dir = self._data_dir()
        if not os.path.isdir(data_dir):
            try:
                os.makedirs(data_dir)
            except Exception:
                # In case of race conditions or permissions, caller will fail on write
                pass

    # ------------------------------- Schema ------------------------------- #
    def _utc_now_iso(self):
        try:
            # Py3
            return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
        except Exception:
            try:
                return datetime.datetime.utcnow().isoformat() + 'Z'
            except Exception:
                return ''

    def _empty_schema(self):
        return {
            'version': self.PROFILE_SCHEMA_VERSION,
            'active_profile_key': '',
            'profiles': {}
        }

    def _read_schema(self):
        path = self._profiles_json_path()
        if not os.path.exists(path):
            return self._empty_schema()
        try:
            with io.open(path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                return self._empty_schema()
            if 'profiles' not in data or not isinstance(data.get('profiles'), dict):
                data['profiles'] = {}
            if 'version' not in data:
                data['version'] = self.PROFILE_SCHEMA_VERSION
            if 'active_profile_key' not in data:
                data['active_profile_key'] = ''
            return data
        except Exception as e:
            print('ConfigManagerService [001]: Failed to read profil.json: {}'.format(e))
            return self._empty_schema()

    def _atomic_write_json(self, path, payload):
        self._ensure_data_dir()
        tmp_path = path + '.tmp'
        try:
            with io.open(tmp_path, 'w', encoding='utf-8') as fh:
                json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
                fh.write(u'\n')
            try:
                # Py3
                os.replace(tmp_path, path)
            except Exception:
                # Py2 fallback
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
                os.rename(tmp_path, path)
            return True
        except Exception as e:
            print('ConfigManagerService [002]: Failed to write profil.json: {}'.format(e))
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return False

    def _normalize_profile_key(self, name):
        try:
            key = (name or '').strip()
        except Exception:
            key = name
        return key

    # ------------------------------- UserConfig bridge ------------------------------- #
    def _capture_current_config(self):
        data = {}
        if self._cfg is None:
            return data
        for k in self.KEYS:
            try:
                val = self._cfg.get(k, '')
            except Exception:
                val = ''
            # Always persist as string to match UserConfig behavior
            try:
                data[k] = u'{}'.format(val)
            except Exception:
                data[k] = val
        return data

    def _apply_config(self, data):
        if self._cfg is None:
            return False
        if not isinstance(data, dict):
            return False
        ok = True
        for k in self.KEYS:
            if k not in data:
                continue
            try:
                if not self._cfg.set(k, data.get(k, '')):
                    ok = False
            except Exception:
                ok = False
        return ok

    def _set_active_profile_key(self, key):
        # Persist both in JSON and UserConfig (requested)
        if self._cfg is None:
            return False
        try:
            return self._cfg.set(self.ACTIVE_PROFILE_KEY_OPTION, key)
        except Exception:
            return False

    def _get_active_profile_key(self):
        if self._cfg is None:
            return ''
        try:
            return self._cfg.get(self.ACTIVE_PROFILE_KEY_OPTION, '')
        except Exception:
            return ''

    # ------------------------------- Public API (used by UI) ------------------------------- #
    def get_profiles(self):
        """Returns mapping {profile_key: profile_payload}. UI lists keys."""
        schema = self._read_schema()
        return schema.get('profiles', {})

    def save_profile(self, name):
        """Capture current UserConfig values and save under profiles[name]."""
        key = self._normalize_profile_key(name)
        if not key:
            return False

        schema = self._read_schema()
        profiles = schema.get('profiles', {})

        profile_payload = {
            'name': name,
            'updated_at': self._utc_now_iso(),
            'data': self._capture_current_config()
        }

        profiles[key] = profile_payload
        schema['profiles'] = profiles
        schema['active_profile_key'] = key

        wrote = self._atomic_write_json(self._profiles_json_path(), schema)
        if wrote:
            self._set_active_profile_key(key)
        return wrote

    def load_profile(self, name):
        key = self._normalize_profile_key(name)
        if not key:
            return False
        schema = self._read_schema()
        profiles = schema.get('profiles', {})
        profile = profiles.get(key)
        if not isinstance(profile, dict):
            return False
        data = profile.get('data', {})
        ok = self._apply_config(data)
        if ok:
            schema['active_profile_key'] = key
            self._atomic_write_json(self._profiles_json_path(), schema)
            self._set_active_profile_key(key)
        return ok

    def delete_profile(self, name):
        key = self._normalize_profile_key(name)
        if not key:
            return False
        schema = self._read_schema()
        profiles = schema.get('profiles', {})
        if key not in profiles:
            return False
        try:
            del profiles[key]
        except Exception:
            profiles.pop(key, None)
        schema['profiles'] = profiles

        if schema.get('active_profile_key') == key:
            # Pick another, or clear
            remaining_keys = list(profiles.keys())
            new_active = remaining_keys[0] if remaining_keys else ''
            schema['active_profile_key'] = new_active
            self._set_active_profile_key(new_active)

        return self._atomic_write_json(self._profiles_json_path(), schema)

    # ------------------------------- CSV import/export (used by UI) ------------------------------- #
    def export_current_config_to_csv(self, csv_path):
        """Exports current UserConfig settings (not a stored profile) to key,value CSV."""
        try:
            current = self._capture_current_config()
            with io.open(csv_path, 'w', encoding='utf-8', newline='') as fh:
                writer = csv.writer(fh)
                writer.writerow(['key', 'value'])
                for k in self.KEYS:
                    writer.writerow([k, current.get(k, '')])
            return True
        except TypeError:
            # IronPython2 io.open doesn't accept newline
            try:
                current = self._capture_current_config()
                with io.open(csv_path, 'w', encoding='utf-8') as fh:
                    writer = csv.writer(fh)
                    writer.writerow(['key', 'value'])
                    for k in self.KEYS:
                        writer.writerow([k, current.get(k, '')])
                return True
            except Exception as e:
                print('ConfigManagerService [003]: Export CSV failed: {}'.format(e))
                return False
        except Exception as e:
            print('ConfigManagerService [004]: Export CSV failed: {}'.format(e))
            return False

    def import_config_from_csv(self, csv_path):
        """Imports key,value CSV into current UserConfig (does not create profile by itself)."""
        try:
            data = {}
            with io.open(csv_path, 'r', encoding='utf-8') as fh:
                reader = csv.reader(fh)
                rows = list(reader)
            if not rows:
                return False
            # Skip header if present
            start_idx = 1 if rows and len(rows[0]) >= 2 and rows[0][0].strip().lower() == 'key' else 0
            for row in rows[start_idx:]:
                if not row or len(row) < 2:
                    continue
                k = (row[0] or '').strip()
                v = row[1]
                if k in self.KEYS:
                    data[k] = v
            return self._apply_config(data)
        except Exception as e:
            print('ConfigManagerService [005]: Import CSV failed: {}'.format(e))
            return False
