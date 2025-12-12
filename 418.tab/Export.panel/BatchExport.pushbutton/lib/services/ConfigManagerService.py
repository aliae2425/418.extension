# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import os

class ConfigManagerService(object):
    # List of keys to include in a profile
    KEYS = [
        'sheet_param_ExportationCombo',
        'sheet_param_CarnetCombo',
        'sheet_param_DWGCombo',
        'create_subfolders',
        'separate_format_folders',
        'naming_pattern_sheet',
        'naming_rows_sheet',
        'naming_pattern_set',
        'naming_rows_set',
        'custom_pdf_setups',
        'pdf_export_setup',
        'pdf_separate_files',
        'custom_dwg_setups',
        'dwg_export_setup',
        'dwg_separate_files',
        'export_destination_folder'
    ]
    
    PROFILES_KEY = 'saved_profiles'

    def __init__(self):
        from ..core.UserConfig import UserConfig
        self._cfg = UserConfig('batch_export')

    def get_current_config(self):
        """Returns a dict with current configuration values."""
        data = {}
        for key in self.KEYS:
            val = self._cfg.get(key)
            if val is not None:
                data[key] = val
        return data

    def apply_config(self, data):
        """Applies a configuration dict to the user config."""
        if not isinstance(data, dict):
            return False
        for key, val in data.items():
            if key in self.KEYS:
                self._cfg.set(key, val)
        return True

    def get_profiles(self):
        """Returns a dict of saved profiles {name: data}."""
        raw = self._cfg.get(self.PROFILES_KEY, '{}')
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def save_profile(self, name, data=None):
        """Saves the current config (or provided data) as a profile."""
        if data is None:
            data = self.get_current_config()
        
        profiles = self.get_profiles()
        profiles[name] = data
        self._cfg.set(self.PROFILES_KEY, json.dumps(profiles))
        return True

    def delete_profile(self, name):
        """Deletes a profile by name."""
        profiles = self.get_profiles()
        if name in profiles:
            del profiles[name]
            self._cfg.set(self.PROFILES_KEY, json.dumps(profiles))
            return True
        return False

    def load_profile(self, name):
        """Loads a profile by name and applies it."""
        profiles = self.get_profiles()
        if name in profiles:
            return self.apply_config(profiles[name])
        return False

    def export_profile_to_file(self, name, filepath):
        """Exports a specific profile to a JSON file."""
        profiles = self.get_profiles()
        if name in profiles:
            data = profiles[name]
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        return False

    def import_profile_from_file(self, filepath, name=None):
        """Imports a profile from a JSON file."""
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Validate data (basic check)
            if not isinstance(data, dict):
                return False
            
            if name is None:
                name = os.path.splitext(os.path.basename(filepath))[0]
            
            return self.save_profile(name, data)
        except Exception:
            return False
