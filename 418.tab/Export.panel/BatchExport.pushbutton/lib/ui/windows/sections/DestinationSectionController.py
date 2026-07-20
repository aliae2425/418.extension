# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os


class DestinationSectionController(object):
    def __init__(self, win, cfg, dest_store, dest_component,
                 on_destination_validity_changed=None, dest_vm=None):
        self._win = win
        self._cfg = cfg
        self._dest_store = dest_store
        self._dest_comp = dest_component
        self._on_dest_changed = on_destination_validity_changed
        self._dest_vm = dest_vm
        self._vm_events_wired = False
        self._checkboxes_event_wired = False

    def initialize(self):
        if self._dest_vm is not None:
            if not self._vm_events_wired:
                try:
                    self._dest_vm.add_on_valid_changed(self._on_valid_changed)
                except Exception:
                    pass
            self._wire_events_vm()
            # Tentative précoce (peut échouer si le template n'est pas encore rendu)
            self._try_init_checkboxes()
            self._apply_border_color(self._dest_vm.is_path_valid)
        else:
            self._dest_comp.init_controls(self._win)
            ok, _ = self._dest_comp.validate(self._win, create=True)
            self._win._dest_valid = bool(ok)
            self._apply_border_color(ok)
            self._wire_events_legacy()
            self._init_toggles_from_cfg()

        if self._on_dest_changed is not None:
            try:
                self._on_dest_changed()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Lookup robuste : attribut pré-lié OU Template.FindName en fallback
    # ------------------------------------------------------------------
    def _get_ctrl(self, name):
        ctrl = getattr(self._win, name, None)
        if ctrl is not None:
            return ctrl
        try:
            host = getattr(self._win, 'DestinationPickerHost', None)
            if host is not None:
                tmpl = getattr(host, 'Template', None)
                if tmpl is not None:
                    found = tmpl.FindName(name, host)
                    if found is not None:
                        try:
                            setattr(self._win, name, found)
                        except Exception:
                            pass
                        return found
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Initialisation des checkboxes depuis le store
    # ------------------------------------------------------------------
    def _try_init_checkboxes(self):
        """Lit le store et pousse dans IsChecked — silencieux si le contrôle n'est pas encore rendu."""
        try:
            cb = self._get_ctrl('CreateSubfoldersCheck')
            if cb is not None:
                cb.IsChecked = self._dest_store.get_create_subfolders()
        except Exception:
            pass
        try:
            cb = self._get_ctrl('SeparateByFormatCheck')
            if cb is not None:
                cb.IsChecked = self._dest_store.get_separate_formats()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Câblage des événements
    # ------------------------------------------------------------------
    def _wire_events_vm(self):
        if self._vm_events_wired:
            return
        self._vm_events_wired = True

        try:
            cb = self._get_ctrl('BrowseButton')
            if cb is not None:
                cb.Click += self._on_browse_vm
        except Exception:
            pass
        try:
            cb = self._get_ctrl('PathTextBox')
            if cb is not None:
                cb.TextChanged += self._on_path_changed_vm
        except Exception:
            pass
        # Checkboxes : câblage tenté ici ET dans _on_window_loaded (fiabilité)
        self._wire_checkbox_events()
        # Window.Loaded : garantit l'init après le premier rendu complet
        try:
            self._win.Loaded += self._on_window_loaded
        except Exception:
            pass
        # Window.Closing : sauvegarde finale indépendante des événements Checked
        try:
            self._win.Closing += self._on_window_closing
        except Exception:
            pass

    def _wire_checkbox_events(self):
        if self._checkboxes_event_wired:
            return
        wired = False
        try:
            cb = self._get_ctrl('CreateSubfoldersCheck')
            if cb is not None:
                cb.Checked += self._on_subfolder_on
                cb.Unchecked += self._on_subfolder_off
                wired = True
        except Exception:
            pass
        try:
            cb = self._get_ctrl('SeparateByFormatCheck')
            if cb is not None:
                cb.Checked += self._on_separate_on
                cb.Unchecked += self._on_separate_off
        except Exception:
            pass
        if wired:
            self._checkboxes_event_wired = True

    def _wire_events_legacy(self):
        try:
            if hasattr(self._win, 'BrowseButton'):
                self._win.BrowseButton.Click += self._on_browse_legacy
            if hasattr(self._win, 'PathTextBox'):
                self._win.PathTextBox.TextChanged += self._on_path_changed
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Handlers Window.Loaded / Window.Closing
    # ------------------------------------------------------------------
    def _on_window_loaded(self, sender, args):
        """Appelé après le premier rendu : Template.FindName est fiable ici."""
        self._try_init_checkboxes()
        if not self._checkboxes_event_wired:
            self._wire_checkbox_events()

    def _on_window_closing(self, sender, args):
        """Filet absolu : lit IsChecked directement et sauvegarde."""
        self._save_checkbox_states()

    def _save_checkbox_states(self):
        try:
            cb = self._get_ctrl('CreateSubfoldersCheck')
            if cb is not None:
                state = bool(cb.IsChecked)
                self._dest_store.set_create_subfolders(state)
                self._cfg.set('create_subfolders', '1' if state else '0')
                if self._dest_vm is not None:
                    self._dest_vm._data['create_subfolders'] = state
        except Exception:
            pass
        try:
            cb = self._get_ctrl('SeparateByFormatCheck')
            if cb is not None:
                state = bool(cb.IsChecked)
                self._dest_store.set_separate_formats(state)
                self._cfg.set('separate_format_folders', '1' if state else '0')
                if self._dest_vm is not None:
                    self._dest_vm._data['separate_formats'] = state
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Handlers VM
    # ------------------------------------------------------------------
    def _on_browse_vm(self, sender, args):
        try:
            self._dest_vm.on_browse()
        except Exception:
            pass

    def _on_path_changed_vm(self, sender, args):
        try:
            path = self._win.PathTextBox.Text or ''
        except Exception:
            path = ''
        try:
            if path:
                self._dest_store.set(path)
                self._cfg.set('PathDossier', path)
            if self._dest_vm is not None:
                self._dest_vm._data['destination_path'] = path
        except Exception:
            pass
        ok = False
        try:
            ok = bool(os.path.isdir(path))
        except Exception:
            pass
        try:
            if self._dest_vm is not None:
                old_ok = self._dest_vm._data.get('is_path_valid')
                self._dest_vm._data['is_path_valid'] = ok
                if old_ok != ok:
                    self._dest_vm.raise_property_changed('is_path_valid')
        except Exception:
            pass
        self._win._dest_valid = ok
        self._apply_border_color(ok)
        if self._on_dest_changed is not None:
            try:
                self._on_dest_changed()
            except Exception:
                pass

    def _on_subfolder_on(self, sender, args):
        try:
            self._dest_store.set_create_subfolders(True)
        except Exception:
            pass
        try:
            self._cfg.set('create_subfolders', '1')
        except Exception:
            pass
        try:
            if self._dest_vm is not None:
                self._dest_vm._data['create_subfolders'] = True
        except Exception:
            pass

    def _on_subfolder_off(self, sender, args):
        try:
            self._dest_store.set_create_subfolders(False)
        except Exception:
            pass
        try:
            self._cfg.set('create_subfolders', '0')
        except Exception:
            pass
        try:
            if self._dest_vm is not None:
                self._dest_vm._data['create_subfolders'] = False
        except Exception:
            pass

    def _on_separate_on(self, sender, args):
        try:
            self._dest_store.set_separate_formats(True)
        except Exception:
            pass
        try:
            self._cfg.set('separate_format_folders', '1')
        except Exception:
            pass
        try:
            if self._dest_vm is not None:
                self._dest_vm._data['separate_formats'] = True
        except Exception:
            pass

    def _on_separate_off(self, sender, args):
        try:
            self._dest_store.set_separate_formats(False)
        except Exception:
            pass
        try:
            self._cfg.set('separate_format_folders', '0')
        except Exception:
            pass
        try:
            if self._dest_vm is not None:
                self._dest_vm._data['separate_formats'] = False
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Handlers legacy
    # ------------------------------------------------------------------
    def _on_browse_legacy(self, sender, args):
        try:
            chosen = self._dest_store.choose_destination_explorer(save=False)
            if chosen and hasattr(self._win, 'PathTextBox'):
                self._win.PathTextBox.Text = chosen
        except Exception:
            pass

    def _on_path_changed(self, sender, args):
        try:
            path = self._win.PathTextBox.Text or ''
            if path:
                self._dest_store.set(path)
        except Exception:
            pass
        ok = False
        try:
            ok = bool(os.path.isdir(self._win.PathTextBox.Text or ''))
        except Exception:
            pass
        self._win._dest_valid = ok
        self._apply_border_color(ok)
        if self._on_dest_changed is not None:
            try:
                self._on_dest_changed()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # VM valid-changed callback
    # ------------------------------------------------------------------
    def _on_valid_changed(self):
        valid = self._dest_vm.is_path_valid if self._dest_vm is not None else False
        self._apply_border_color(valid)
        if self._on_dest_changed is not None:
            try:
                self._on_dest_changed()
            except Exception:
                pass

    def _apply_border_color(self, is_valid):
        try:
            from System.Windows.Media import Brushes
            from System.Windows.Controls import Control
        except Exception:
            return
        try:
            tb = getattr(self._win, 'PathTextBox', None)
            if tb is None:
                return
            if is_valid:
                tb.ClearValue(Control.BorderBrushProperty)
                tb.ClearValue(Control.BackgroundProperty)
            else:
                tb.BorderBrush = Brushes.Red
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Legacy helpers
    # ------------------------------------------------------------------
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
