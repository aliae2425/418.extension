# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from System.ComponentModel import INotifyPropertyChanged, PropertyChangedEventArgs

    class ObservableItem(INotifyPropertyChanged):
        """Classe observable pour le binding WPF avec dictionnaires"""
        def __init__(self, data_dict):
            self._data = data_dict
            self._property_changed_handlers = []

        def add_PropertyChanged(self, handler):
            self._property_changed_handlers.append(handler)

        def remove_PropertyChanged(self, handler):
            if handler in self._property_changed_handlers:
                self._property_changed_handlers.remove(handler)

        def __getitem__(self, key):
            return self._data.get(key)

        def __setitem__(self, key, value):
            if self._data.get(key) != value:
                self._data[key] = value
                self._notify_property_changed(key)

        def _notify_property_changed(self, property_name):
            for handler in self._property_changed_handlers:
                handler(self, PropertyChangedEventArgs(property_name))

        def get(self, key, default=None):
            return self._data.get(key, default)

except Exception:
    class ObservableItem(object):
        def __init__(self, data_dict):
            self._data = data_dict

        def __getitem__(self, key):
            return self._data.get(key)

        def __setitem__(self, key, value):
            self._data[key] = value

        def get(self, key, default=None):
            return self._data.get(key, default)
