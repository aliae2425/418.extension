# -*- coding: utf-8 -*-

try:
    from System.Windows.Input import ICommand
except Exception:
    ICommand = object  # type: ignore


class RelayCommand(ICommand):
    def __init__(self, execute, can_execute=None):
        self._execute = execute
        self._can_execute = can_execute

    def CanExecute(self, parameter):
        return self._can_execute(parameter) if self._can_execute else True

    def Execute(self, parameter):
        self._execute(parameter)

    def add_CanExecuteChanged(self, handler):
        pass

    def remove_CanExecuteChanged(self, handler):
        pass
