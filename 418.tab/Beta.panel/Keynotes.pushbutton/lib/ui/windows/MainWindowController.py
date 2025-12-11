# -*- coding: utf-8 -*-
from pyrevit import forms
from ...core.AppPaths import AppPaths
from ..helpers.UIResourceLoader import UIResourceLoader
from ..helpers.UITemplateBinder import UITemplateBinder

# Components
from ..components.BurgerMenuComponent import BurgerMenuComponent
from ..components.KeynoteTreeComponent import KeynoteTreeComponent
from ..components.KeynoteDetailsComponent import KeynoteDetailsComponent

class MainWindow(forms.WPFWindow):
    def __init__(self, xaml_path):
        forms.WPFWindow.__init__(self, xaml_path)

class MainWindowController(object):
    def __init__(self):
        self._paths = AppPaths()
        self._win = MainWindow(self._paths.main_xaml())
        self._current_keynote_path = None
        
        # Load resources (Styles, Colors)
        loader = UIResourceLoader(self._win, self._paths)
        loader.merge_all()

        # Bind Templates (Apply templates and find named parts)
        binder = UITemplateBinder(self._win)
        binder.bind({
            'BurgerMenuHost': ['CloseBurgerButton', 'LoadKeynoteButton', 'CurrentKeynotePath', 'DarkModeToggle'],
            'KeynoteTreeHost': ['MainTreeView'],
            'KeynoteDetailsHost': ['MainListView']
        })

        # Initialize Components
        self.burger_menu = BurgerMenuComponent(self._win, self)
        self.tree_component = KeynoteTreeComponent(self._win, self)
        self.details_component = KeynoteDetailsComponent(self._win, self)

        # Bind Window events
        self._bind_window_events()
        
        # Initial State
        self._check_revit_theme()
        self._init_current_keynote()

    def _bind_window_events(self):
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

    # --- Callbacks for Components ---

    def enable_dark_mode(self):
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

    def disable_dark_mode(self):
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

    def load_keynotes(self, path):
        try:
            from ...data.KeynoteParser import KeynoteParser
            from ...services.KeynoteUsageService import KeynoteUsageService
            
            # Parse file
            parser = KeynoteParser()
            items = parser.parse(path)
            
            # Get counts
            doc = __revit__.ActiveUIDocument.Document
            usage_service = KeynoteUsageService(doc)
            counts = usage_service.get_usage_counts()
            
            # Apply counts
            self._apply_counts(items, counts)
            
            self.tree_component.set_items(items)
            # Update path in burger menu
            self.burger_menu.update_path(path)
            self._current_keynote_path = path
        except Exception as e:
            print('Error loading keynotes: {}'.format(e))

    def _apply_counts(self, items, counts):
        for item in items:
            if item.Key in counts:
                item.Count = counts[item.Key]
            
            if item.Children:
                self._apply_counts(item.Children, counts)

    def on_keynote_selected(self, keynote_item):
        self.details_component.show_details(keynote_item)

    # --- Internal Helpers ---

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
                    self.load_keynotes(user_path)
        except Exception:
            pass

    def _check_revit_theme(self):
        try:
            from Autodesk.Revit.UI import UIThemeManager, UITheme
            theme = UIThemeManager.CurrentTheme
            if theme == UITheme.Dark:
                # We need to check the toggle in the burger menu
                if hasattr(self._win, 'DarkModeToggle'):
                    self._win.DarkModeToggle.IsChecked = True
                else:
                    self.enable_dark_mode()
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
        try:
            if self._current_keynote_path:
                from pyrevit import revit, DB
                doc = __revit__.ActiveUIDocument.Document
                
                with revit.Transaction("Reload Keynotes"):
                    table = DB.KeynoteTable.GetKeynoteTable(doc)
                    if table:
                        # Convert user path to ModelPath
                        model_path = DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(self._current_keynote_path)
                        # Load from the path
                        table.LoadFrom(model_path, DB.KeynoteTableLoadOption())
                        print("Keynotes reloaded from: {}".format(self._current_keynote_path))
        except Exception as e:
            print("Error reloading keynotes: {}".format(e))
        finally:
            self._win.Close()

    def show(self):
        self._win.ShowDialog()
        return True
