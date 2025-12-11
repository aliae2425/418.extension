# -*- coding: utf-8 -*-
from pyrevit import forms
from ...core.AppPaths import AppPaths
from ..helpers.UIResourceLoader import UIResourceLoader

class MainWindow(forms.WPFWindow):
    def __init__(self, xaml_path):
        forms.WPFWindow.__init__(self, xaml_path)

class MainWindowController(object):
    def __init__(self):
        self._paths = AppPaths()
        self._win = MainWindow(self._paths.main_xaml())
        
        # Load resources (Styles, Colors)
        loader = UIResourceLoader(self._win, self._paths)
        loader.merge_all()

        # Bind events
        self._bind_events()
        self._wire_burger_menu()

    def _bind_events(self):
        # Title Bar events
        if hasattr(self._win, 'CloseWindowButton'):
            self._win.CloseWindowButton.Click += self._close_window
        
        if hasattr(self._win, 'TitleBar'):
            self._win.TitleBar.MouseLeftButtonDown += self._drag_window

        # Footer buttons
        if hasattr(self._win, 'CancelButton'):
            self._win.CancelButton.Click += self._close_window
        
        if hasattr(self._win, 'SaveButton'):
            self._win.SaveButton.Click += self._save_action

    def _wire_burger_menu(self):
        """Configure le menu burger"""
        try:
            if hasattr(self._win, 'BurgerButton'):
                self._win.BurgerButton.Click += self._toggle_burger_menu
            if hasattr(self._win, 'CloseBurgerButton'):
                self._win.CloseBurgerButton.Click += self._close_burger_menu
            if hasattr(self._win, 'BurgerMenuOverlay'):
                self._win.BurgerMenuOverlay.MouseLeftButtonDown += self._close_burger_menu
        except Exception:
            pass

    def _toggle_burger_menu(self, sender, args):
        """Ouvre/ferme le menu burger"""
        try:
            from System.Windows import Visibility
        except Exception:
            return
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

    def _close_burger_menu(self, sender, args):
        """Ferme le menu burger"""
        try:
            from System.Windows import Visibility
        except Exception:
            return
        try:
            menu = getattr(self._win, 'BurgerMenu', None)
            overlay = getattr(self._win, 'BurgerMenuOverlay', None)
            
            if menu is not None:
                menu.Visibility = Visibility.Collapsed
            if overlay is not None:
                overlay.Visibility = Visibility.Collapsed
        except Exception:
            pass

    def _close_window(self, sender, args):
        self._win.Close()

    def _drag_window(self, sender, args):
        try:
            self._win.DragMove()
        except Exception:
            pass

    def _save_action(self, sender, args):
        # Placeholder for save logic
        print("Save button clicked")
        self._win.Close()

    def show(self):
        self._win.ShowDialog()
        return True
