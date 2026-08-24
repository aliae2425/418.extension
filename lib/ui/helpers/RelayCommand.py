# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from ui.helpers.wpf_runtime import ensure_wpf as _ensure_wpf
_ensure_wpf()

try:
    from System.Windows.Input import ICommand, CommandManager
    _has_cm = True
except Exception:
    ICommand = object
    CommandManager = None
    _has_cm = False


class RelayCommand(ICommand):
    def __init__(self, execute, can_execute=None):
        self._execute = execute
        self._can_execute = can_execute

    def CanExecute(self, parameter):
        return self._can_execute(parameter) if self._can_execute else True

    def Execute(self, parameter):
        self._execute(parameter)

    def add_CanExecuteChanged(self, handler):
        if _has_cm and CommandManager:
            CommandManager.RequerySuggested += handler

    def remove_CanExecuteChanged(self, handler):
        if _has_cm and CommandManager:
            CommandManager.RequerySuggested -= handler
