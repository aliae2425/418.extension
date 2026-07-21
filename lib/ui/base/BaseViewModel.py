# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from System.ComponentModel import INotifyPropertyChanged, PropertyChangedEventArgs
    _has_wpf = True
except Exception:
    INotifyPropertyChanged = object
    _has_wpf = False


if _has_wpf:
    class BaseViewModel(INotifyPropertyChanged):
        def __init__(self):
            self._pc_handlers = []

        def add_PropertyChanged(self, handler):
            self._pc_handlers.append(handler)

        def remove_PropertyChanged(self, handler):
            try:
                self._pc_handlers.remove(handler)
            except ValueError:
                pass

        def notify_property(self, name):
            if not self._pc_handlers:
                return
            args = PropertyChangedEventArgs(name)
            for h in list(self._pc_handlers):
                try:
                    h(self, args)
                except Exception:
                    pass
else:
    class BaseViewModel(object):
        def __init__(self):
            pass

        def notify_property(self, name):
            pass
