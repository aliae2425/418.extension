# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from .ViewModelBase import ViewModelBase
except Exception:
    try:
        from lib.ui.viewmodels.ViewModelBase import ViewModelBase
    except Exception:
        class ViewModelBase(object):
            def __init__(self):
                self._data = {}
            def _get(self, key, default=None):
                return self._data.get(key, default)
            def _set(self, key, value):
                self._data[key] = value
            def raise_property_changed(self, name):
                pass


class DestinationViewModel(ViewModelBase):
    def __init__(self, dest_store):
        ViewModelBase.__init__(self)
        self._dest_store = dest_store
        self._on_valid_changed_callbacks = []
        self._load_from_store()

    def _load_from_store(self):
        path = self._dest_store.get() or ''
        self._data['destination_path'] = path
        self._data['create_subfolders'] = self._dest_store.get_create_subfolders()
        self._data['separate_formats'] = self._dest_store.get_separate_formats()
        self._data['is_path_valid'] = self._compute_validity(path)

    def _compute_validity(self, path):
        if not path:
            return False
        try:
            return os.path.isdir(path)
        except Exception:
            return False

    def _fire_valid_changed(self):
        for cb in self._on_valid_changed_callbacks:
            try:
                cb()
            except Exception:
                pass

    def add_on_valid_changed(self, callback):
        self._on_valid_changed_callbacks.append(callback)

    def reload(self):
        self._load_from_store()
        self.raise_property_changed('destination_path')
        self.raise_property_changed('create_subfolders')
        self.raise_property_changed('separate_formats')
        self.raise_property_changed('is_path_valid')

    @property
    def destination_path(self):
        return self._get('destination_path', '')

    @destination_path.setter
    def destination_path(self, value):
        value = value or ''
        if self._data.get('destination_path') == value:
            return
        self._data['destination_path'] = value
        self.raise_property_changed('destination_path')
        if value:
            try:
                self._dest_store.set(value)
            except Exception:
                pass
        valid = self._compute_validity(value)
        old_valid = self._data.get('is_path_valid')
        self._data['is_path_valid'] = valid
        if old_valid != valid:
            self.raise_property_changed('is_path_valid')
        self._fire_valid_changed()

    @property
    def is_path_valid(self):
        return self._get('is_path_valid', False)

    @property
    def create_subfolders(self):
        return self._get('create_subfolders', False)

    @create_subfolders.setter
    def create_subfolders(self, value):
        v = bool(value)
        self._set('create_subfolders', v)
        try:
            self._dest_store.set_create_subfolders(v)
        except Exception:
            pass

    @property
    def separate_formats(self):
        return self._get('separate_formats', False)

    @separate_formats.setter
    def separate_formats(self, value):
        v = bool(value)
        self._set('separate_formats', v)
        try:
            self._dest_store.set_separate_formats(v)
        except Exception:
            pass

    def on_browse(self):
        try:
            chosen = self._dest_store.choose_destination_explorer(save=False)
            if chosen:
                self.destination_path = chosen
        except Exception:
            pass
