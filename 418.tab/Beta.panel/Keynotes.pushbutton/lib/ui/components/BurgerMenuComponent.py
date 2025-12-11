# -*- coding: utf-8 -*-
from pyrevit import forms
from System.Windows import Visibility

class BurgerMenuComponent(object):
    def __init__(self, window, controller):
        self._win = window
        self._controller = controller
        self._bind()

    def _bind(self):
        # Toggle button (in TitleBar)
        if hasattr(self._win, 'BurgerButton'):
            self._win.BurgerButton.Click += self._toggle_menu
        
        # Close button (in Template)
        if hasattr(self._win, 'CloseBurgerButton'):
            self._win.CloseBurgerButton.Click += self._close_menu
            
        # Overlay (in MainWindow)
        if hasattr(self._win, 'BurgerMenuOverlay'):
            self._win.BurgerMenuOverlay.MouseLeftButtonDown += self._close_menu

        # Dark Mode (in Template)
        if hasattr(self._win, 'DarkModeToggle'):
            self._win.DarkModeToggle.Checked += self._on_dark_mode
            self._win.DarkModeToggle.Unchecked += self._on_light_mode

        # Load File (in Template)
        if hasattr(self._win, 'LoadKeynoteButton'):
            self._win.LoadKeynoteButton.Click += self._load_file

    def _toggle_menu(self, sender, args):
        try:
            menu = getattr(self._win, 'BurgerMenu', None)
            overlay = getattr(self._win, 'BurgerMenuOverlay', None)
            
            if menu is not None:
                if menu.Visibility == Visibility.Visible:
                    menu.Visibility = Visibility.Collapsed
                    if overlay: overlay.Visibility = Visibility.Collapsed
                else:
                    menu.Visibility = Visibility.Visible
                    if overlay: overlay.Visibility = Visibility.Visible
        except Exception:
            pass

    def _close_menu(self, sender, args):
        try:
            menu = getattr(self._win, 'BurgerMenu', None)
            overlay = getattr(self._win, 'BurgerMenuOverlay', None)
            
            if menu is not None:
                menu.Visibility = Visibility.Collapsed
            if overlay is not None:
                overlay.Visibility = Visibility.Collapsed
        except Exception:
            pass

    def _on_dark_mode(self, sender, args):
        if hasattr(self._controller, 'enable_dark_mode'):
            self._controller.enable_dark_mode()

    def _on_light_mode(self, sender, args):
        if hasattr(self._controller, 'disable_dark_mode'):
            self._controller.disable_dark_mode()

    def _load_file(self, sender, args):
        path = forms.pick_file(file_ext='txt', title="Sélectionner un fichier Keynotes")
        if path:
            self.update_path(path)
            if hasattr(self._controller, 'load_keynotes'):
                self._controller.load_keynotes(path)

    def update_path(self, path):
        if hasattr(self._win, 'CurrentKeynotePath'):
            self._win.CurrentKeynotePath.Text = path
            self._win.CurrentKeynotePath.ToolTip = path
