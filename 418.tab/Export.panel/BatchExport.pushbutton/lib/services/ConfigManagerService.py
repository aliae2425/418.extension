# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import os
import csv
import io
import sys

class Profile(object):
    def __init__(self, name, data=None):
        self.name = name
        self.data = data if data else {}

    def to_json(self):
        return self.data

    @classmethod
    def from_json(cls, name, data):
        return cls(name, data)

class ConfigManagerService(object):
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
        
        profile = Profile(name, data)
        
        profiles = self.get_profiles()
        profiles[name] = profile.to_json()
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
            profile = Profile.from_json(name, profiles[name])
            return self.apply_config(profile.data)
        return False

    def export_profile_to_file(self, name, filepath):
        """Exports a specific profile to a JSON file."""
        profiles = self.get_profiles()
        if name in profiles:
            profile = Profile.from_json(name, profiles[name])
            with open(filepath, 'w') as f:
                json.dump(profile.to_json(), f, indent=2)
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

    def export_current_config_to_csv(self, filepath):
        """Exports current configuration to a CSV file."""
        data = self.get_current_config()
        try:
            if sys.version_info.major < 3:
                mode = 'wb'
                f = open(filepath, mode)
            else:
                mode = 'w'
                f = open(filepath, mode, newline='', encoding='utf-8')
            
            with f:
                writer = csv.writer(f)
                writer.writerow(['Key', 'Value'])
                for key, val in data.items():
                    if isinstance(val, (dict, list)):
                        val = json.dumps(val)
                    
                    if sys.version_info.major < 3:
                        k = key.encode('utf-8') if isinstance(key, unicode) else key
                        v = val.encode('utf-8') if isinstance(val, unicode) else val
                        writer.writerow([k, v])
                    else:
                        writer.writerow([key, val])
            return True
        except Exception:
            return False

    def import_config_from_csv(self, filepath):
        """Imports configuration from a CSV file and applies it."""
        if not os.path.exists(filepath):
            return False
        
        data = {}
        try:
            if sys.version_info.major < 3:
                f = open(filepath, 'rb')
            else:
                f = open(filepath, 'r', newline='', encoding='utf-8')
                
            with f:
                # skipinitialspace=True allows ignoring whitespace after the comma
                reader = csv.reader(f, skipinitialspace=True)
                try:
                    header = next(reader)
                except StopIteration:
                    return False
                
                for row in reader:
                    if len(row) >= 2:
                        key = row[0].strip()
                        val = row[1]
                        
                        if sys.version_info.major < 3:
                            key = key.decode('utf-8')
                            val = val.decode('utf-8')
                        
                        # Attempt to restore types
                        # Handle boolean strings 'True'/'False' by converting to '1'/'0'
                        # as this application typically uses '1'/'0' for booleans in config.
                        if val.lower() == 'true':
                            val = '1'
                        elif val.lower() == 'false':
                            val = '0'
                        elif val.startswith('{') or val.startswith('['):
                            try:
                                val = json.loads(val)
                            except:
                                pass
                        
                        data[key] = val
            
            return self.apply_config(data)
        except Exception:
            return False