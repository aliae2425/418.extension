# -*- coding: utf-8 -*-


class DestinationSectionController(object):
    def __init__(self, win, cfg, dest_store, dest_component, on_destination_validity_changed=None):
        self._win = win
        self._cfg = cfg
        self._dest_store = dest_store
        self._dest_comp = dest_component
        self._on_dest_changed = on_destination_validity_changed

    def initialize(self):
        try:
            from System.Windows.Media import Brushes
            from System.Windows.Controls import Control
        except Exception:
            Brushes = None
            Control = None

        self._dest_comp.init_controls(self._win)

        ok, err = self._dest_comp.validate(self._win, create=True)
        self._win._dest_valid = bool(ok)

        try:
            if hasattr(self._win, 'PathTextBox'):
                if ok:
                    if Control:
                        self._win.PathTextBox.ClearValue(Control.BorderBrushProperty)
                        self._win.PathTextBox.ClearValue(Control.BackgroundProperty)
                else:
                    if Brushes:
                        self._win.PathTextBox.BorderBrush = Brushes.Red
        except Exception:
            pass

        self._wire_events()
        self._init_toggles_from_cfg()

        if self._on_dest_changed is not None:
            try:
                self._on_dest_changed()
            except Exception:
                pass

    def _wire_events(self):
        try:
            if hasattr(self._win, 'BrowseButton'):
                self._win.BrowseButton.Click += self._on_browse
            if hasattr(self._win, 'PathTextBox'):
                self._win.PathTextBox.TextChanged += self._on_path_changed
        except Exception:
            pass

    def _init_toggles_from_cfg(self):
        try:
            def getv(k, d=False):
                try:
                    return self._cfg.get(k, '') == '1'
                except Exception:
                    return d

            def setv(k, v):
                try:
                    self._cfg.set(k, '1' if v else '0')
                except Exception:
                    pass

            if hasattr(self._win, 'CreateSubfoldersCheck'):
                self._win.CreateSubfoldersCheck.IsChecked = getv('create_subfolders', False)
                self._win.CreateSubfoldersCheck.Checked += lambda s, a: setv('create_subfolders', True)
                self._win.CreateSubfoldersCheck.Unchecked += lambda s, a: setv('create_subfolders', False)

            if hasattr(self._win, 'SeparateByFormatCheck'):
                self._win.SeparateByFormatCheck.IsChecked = getv('separate_format_folders', False)
                self._win.SeparateByFormatCheck.Checked += lambda s, a: setv('separate_format_folders', True)
                self._win.SeparateByFormatCheck.Unchecked += lambda s, a: setv('separate_format_folders', False)
        except Exception:
            pass

    def _on_browse(self, sender, args):
        try:
            chosen = self._dest_store.choose_destination_explorer(save=True)
        except Exception:
            chosen = None

        if chosen:
            try:
                self._win.PathTextBox.Text = chosen
            except Exception:
                pass
            self._on_path_changed(None, None)

    def _on_path_changed(self, sender, args):
        try:
            from System.Windows.Media import Brushes
            from System.Windows.Controls import Control
        except Exception:
            Brushes = None
            Control = None

        ok, err = self._dest_comp.validate(self._win, create=False)
        self._win._dest_valid = bool(ok)

        try:
            if hasattr(self._win, 'PathTextBox'):
                if ok:
                    if Control:
                        self._win.PathTextBox.ClearValue(Control.BorderBrushProperty)
                        self._win.PathTextBox.ClearValue(Control.BackgroundProperty)
                else:
                    if Brushes:
                        self._win.PathTextBox.BorderBrush = Brushes.Red
        except Exception:
            pass

        if self._on_dest_changed is not None:
            try:
                self._on_dest_changed()
            except Exception:
                pass
