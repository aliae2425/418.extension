# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from System.ComponentModel import INotifyPropertyChanged, PropertyChangedEventArgs
    _HAS_INPC = True
except Exception:
    _HAS_INPC = False

if _HAS_INPC:
    class ViewModelBase(INotifyPropertyChanged):
        def __init__(self):
            self._property_changed_handlers = []
            self._data = {}

        def add_PropertyChanged(self, handler):
            self._property_changed_handlers.append(handler)

        def remove_PropertyChanged(self, handler):
            if handler in self._property_changed_handlers:
                self._property_changed_handlers.remove(handler)

        def raise_property_changed(self, name):
            args = PropertyChangedEventArgs(name)
            for h in self._property_changed_handlers:
                h(self, args)

        def _get(self, key, default=None):
            return self._data.get(key, default)

        def _set(self, key, value):
            if self._data.get(key) != value:
                self._data[key] = value
                self.raise_property_changed(key)
else:
    class ViewModelBase(object):
        def __init__(self):
            self._data = {}

        def raise_property_changed(self, name):
            pass

        def _get(self, key, default=None):
            return self._data.get(key, default)

        def _set(self, key, value):
            self._data[key] = value
