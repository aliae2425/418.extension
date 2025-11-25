# -*- coding: utf-8 -*-
from pyrevit import forms
import os

class MainWindow(forms.WPFWindow):
    def __init__(self, xaml_path):
        forms.WPFWindow.__init__(self, xaml_path)

class MainWindowController(object):
    def __init__(self):
        from ...core.AppPaths import AppPaths
        self._paths = AppPaths()
        
        from ..helpers.UIResourceLoader import UIResourceLoader
        self._res_loader_cls = UIResourceLoader

        from ...services.KeynoteParser import KeynoteParser
        self._parser = KeynoteParser()

        self._win = MainWindow(self._paths.main_xaml())
        self._current_file = None
        self._roots = [] # List of KeynoteItem
        self._selected_item = None

    def initialize(self):
        # Load resources
        self._res_loader_cls(self._win, self._paths).merge_all()
        
        # Wire events
        if hasattr(self._win, 'LoadButton'):
            self._win.LoadButton.Click += self._on_load
        if hasattr(self._win, 'SaveButton'):
            self._win.SaveButton.Click += self._on_save
        
        if hasattr(self._win, 'KeynoteTree'):
            self._win.KeynoteTree.SelectedItemChanged += self._on_selection_changed
            
        if hasattr(self._win, 'ApplyButton'):
            self._win.ApplyButton.Click += self._on_apply_changes
            
        if hasattr(self._win, 'AddChildButton'):
            self._win.AddChildButton.Click += self._on_add_child
        if hasattr(self._win, 'AddSiblingButton'):
            self._win.AddSiblingButton.Click += self._on_add_sibling
        if hasattr(self._win, 'DeleteButton'):
            self._win.DeleteButton.Click += self._on_delete

        # Try to load from current project
        self._try_load_from_project()

    def _try_load_from_project(self):
        try:
            from Autodesk.Revit import DB
            doc = __revit__.ActiveUIDocument.Document
            if not doc:
                return
            
            table = DB.KeynoteTable.GetKeynoteTable(doc)
            if not table:
                return
                
            ref = table.GetExternalFileReference()
            if not ref:
                return
                
            path = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(ref.GetPath())
            if path and os.path.exists(path):
                self._load_file(path)
        except Exception:
            # Silent fail if not in Revit context or other error
            pass


    def show(self):
        self.initialize()
        self._win.ShowDialog()
        return True

    def _on_load(self, sender, args):
        path = forms.pick_file(file_ext='txt', title='Sélectionner le fichier Keynotes')
        if path:
            self._load_file(path)

    def _load_file(self, path):
        try:
            self._roots = self._parser.parse(path)
            self._current_file = path
            self._win.KeynoteTree.ItemsSource = self._roots
            self._win.FilePathText.Text = path
            self._win.DetailPanel.IsEnabled = False
        except Exception as e:
            forms.alert('Erreur lors du chargement: {}'.format(e))

    def _on_save(self, sender, args):
        if not self._current_file:
            forms.alert('Aucun fichier chargé.')
            return
        
        try:
            self._parser.save(self._current_file, self._roots)
            forms.alert('Fichier enregistré avec succès.')
        except Exception as e:
            forms.alert('Erreur lors de l\'enregistrement: {}'.format(e))

    def _on_selection_changed(self, sender, args):
        item = self._win.KeynoteTree.SelectedItem
        self._selected_item = item
        
        if item:
            self._win.DetailPanel.IsEnabled = True
            self._win.KeyBox.Text = item.Key
            self._win.DescBox.Text = item.Description
            self._win.ParentBox.Text = item.ParentKey if item.ParentKey else ""
        else:
            self._win.DetailPanel.IsEnabled = False
            self._win.KeyBox.Text = ""
            self._win.DescBox.Text = ""
            self._win.ParentBox.Text = ""

    def _on_apply_changes(self, sender, args):
        if not self._selected_item:
            return
            
        # Update object
        self._selected_item.Key = self._win.KeyBox.Text
        self._selected_item.Description = self._win.DescBox.Text
        self._selected_item.ParentKey = self._win.ParentBox.Text or None
        
        # Refresh TreeView (hacky way: reset ItemsSource)
        # Ideally we should implement INotifyPropertyChanged on KeynoteItem
        # or use ObservableCollection but for now this is simple
        self._refresh_tree()

    def _refresh_tree(self):
        # Save current expansion state? Too complex for now.
        # Just rebind
        self._win.KeynoteTree.ItemsSource = None
        self._win.KeynoteTree.ItemsSource = self._roots

    def _on_add_child(self, sender, args):
        if not self._selected_item:
            return
            
        from ...data.KeynoteItem import KeynoteItem
        new_item = KeynoteItem("NEW.KEY", "Nouvelle note", self._selected_item.Key)
        self._selected_item.Children.append(new_item)
        self._refresh_tree()

    def _on_add_sibling(self, sender, args):
        # Finding the parent list is tricky without back-references in the object model
        # or a search.
        # Let's do a search for the parent of selected_item
        if not self._selected_item:
            return
            
        parent_list = self._find_list_containing(self._selected_item, self._roots)
        if parent_list is not None:
            from ...data.KeynoteItem import KeynoteItem
            new_item = KeynoteItem("NEW.KEY", "Nouvelle note", self._selected_item.ParentKey)
            parent_list.append(new_item)
            self._refresh_tree()

    def _on_delete(self, sender, args):
        if not self._selected_item:
            return
            
        if forms.alert("Supprimer cet élément et ses enfants ?", yes=True, no=True):
            parent_list = self._find_list_containing(self._selected_item, self._roots)
            if parent_list is not None:
                parent_list.remove(self._selected_item)
                self._selected_item = None
                self._win.DetailPanel.IsEnabled = False
                self._refresh_tree()

    def _find_list_containing(self, target_item, current_list):
        if target_item in current_list:
            return current_list
        
        for item in current_list:
            found_list = self._find_list_containing(target_item, item.Children)
            if found_list is not None:
                return found_list
        return None
