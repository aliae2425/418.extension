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
        self._wire_dark_mode()
        self._wire_load_keynote()
        self._check_revit_theme()
        self._init_current_keynote()

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

    def _wire_dark_mode(self):
        try:
            if hasattr(self._win, 'DarkModeToggle'):
                self._win.DarkModeToggle.Checked += self._on_dark_mode
                self._win.DarkModeToggle.Unchecked += self._on_light_mode
        except Exception:
            pass

    def _wire_load_keynote(self):
        try:
            if hasattr(self._win, 'LoadKeynoteButton'):
                self._win.LoadKeynoteButton.Click += self._on_load_keynote
        except Exception:
            pass

    def _on_load_keynote(self, sender, args):
        try:
            path = forms.pick_file(file_ext='txt', title="Sélectionner un fichier Keynotes")
            if path:
                self._update_path_display(path)
                self._load_keynotes(path)
        except Exception:
            pass

    def _init_current_keynote(self):
        try:
            doc = __revit__.ActiveUIDocument.Document
            from Autodesk.Revit.DB import KeynoteTable, ModelPathUtils
            table = KeynoteTable.GetKeynoteTable(doc)
            if table:
                ref = table.GetExternalFileReference()
                if ref:
                    path = ref.GetPath()
                    user_path = ModelPathUtils.ConvertModelPathToUserVisiblePath(path)
                    self._update_path_display(user_path)
                    self._load_keynotes(user_path)
        except Exception:
            pass

    def _load_keynotes(self, path):
        try:
            from ...data.KeynoteParser import KeynoteParser
            parser = KeynoteParser()
            items = parser.parse(path)
            if hasattr(self._win, 'MainTreeView'):
                self._win.MainTreeView.ItemsSource = items
        except Exception as e:
            print('Error loading keynotes: {}'.format(e))

    def _update_path_display(self, path):
        if hasattr(self._win, 'CurrentKeynotePath'):
            self._win.CurrentKeynotePath.Text = path
            self._win.CurrentKeynotePath.ToolTip = path

    def _check_revit_theme(self):
        try:
            from Autodesk.Revit.UI import UIThemeManager, UITheme
            theme = UIThemeManager.CurrentTheme
            if theme == UITheme.Dark:
                if hasattr(self._win, 'DarkModeToggle'):
                    self._win.DarkModeToggle.IsChecked = True
                else:
                    self._on_dark_mode(None, None)
        except Exception:
            pass

    def _on_dark_mode(self, sender, args):
        try:
            from System.Windows import ResourceDictionary
            from System import Uri, UriKind
            # Load dark theme resources
            dark_colors = self._paths.resource_path('ColorsDark.xaml')
            dark_styles = self._paths.resource_path('StylesDark.xaml')
            for path in [dark_colors, dark_styles]:
                rd = ResourceDictionary()
                rd.Source = Uri(path, UriKind.Absolute)
                self._win.Resources.MergedDictionaries.Add(rd)
        except Exception as e:
            print('MainWindowController: Dark mode error: {}'.format(e))

    def _on_light_mode(self, sender, args):
        try:
            # Remove dark theme resources (assume last two dictionaries are dark)
            md = self._win.Resources.MergedDictionaries
            # We expect at least 2 base dictionaries (Colors, Styles) + potentially others
            # If we added 2 for dark mode, we remove the last 2
            if len(md) >= 4: # Base Colors, Styles + Dark Colors, Styles
                md.RemoveAt(md.Count-1)
                md.RemoveAt(md.Count-1)
        except Exception as e:
            print('MainWindowController: Light mode error: {}'.format(e))

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
