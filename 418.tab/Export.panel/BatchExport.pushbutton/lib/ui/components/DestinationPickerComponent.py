# -*- coding: utf-8 -*-
# Composant UI: sélection et validation du dossier de destination

class DestinationPickerComponent(object):
    def __init__(self, dest_store):
        self._dest = dest_store

    def init_controls(self, win):
        # Valeur initiale
        try:
            if hasattr(win, 'PathTextBox'):
                win.PathTextBox.Text = self._dest.get()
            
            # Checkboxes
            if hasattr(win, 'CreateSubfoldersCheck'):
                win.CreateSubfoldersCheck.IsChecked = self._dest.get_create_subfolders()
                win.CreateSubfoldersCheck.Checked += lambda s,a: self._dest.set_create_subfolders(True)
                win.CreateSubfoldersCheck.Unchecked += lambda s,a: self._dest.set_create_subfolders(False)
            
            if hasattr(win, 'SeparateByFormatCheck'):
                win.SeparateByFormatCheck.IsChecked = self._dest.get_separate_formats()
                win.SeparateByFormatCheck.Checked += lambda s,a: self._dest.set_separate_formats(True)
                win.SeparateByFormatCheck.Unchecked += lambda s,a: self._dest.set_separate_formats(False)
        except Exception:
            pass

    def browse(self, win):
        try:
            chosen = self._dest.choose(save=True)
            if chosen and hasattr(win, 'PathTextBox'):
                win.PathTextBox.Text = chosen
            return chosen
        except Exception:
            return None

    def validate(self, win, create=False):
        path = ''
        try:
            path = win.PathTextBox.Text or ''
        except Exception:
            path = ''
        ok = False
        err = None
        try:
            if create:
                ok, err = self._dest.ensure(path)
            else:
                import os
                ok = os.path.isdir(path)
        except Exception as e:
            ok, err = False, str(e)
        return ok, err
