# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = object


def _xaml_path():
    here = os.path.dirname(os.path.abspath(__file__))
    button = os.path.abspath(os.path.join(here, '..', '..'))
    return os.path.join(button, 'GUI', 'Views', 'MainWindow.xaml')


class MainWindowView(BaseWindow):
    """Fenêtre racine « Dupliquer les vues » : coquille à rail (Sélection
    / Options), sans modale bloquante. Monte les 2 pages, câble la
    navigation, le bouton Run et les radios d'option de duplication de vue.
    """

    def __init__(self, view_model, views_par_id, uidoc):
        super(MainWindowView, self).__init__(_xaml_path(), view_model)
        self._vm = view_model
        self._views_par_id = views_par_id
        self._uidoc = uidoc

    def _load(self):
        super(MainWindowView, self)._load()
        if self._window is None:
            return
        self._mount_pages()
        self._wire_nav()
        self._wire_next()
        self._wire_run()
        self._wire_view_dup_option()
        self._sync_nav()

    def _load_page(self, filename, data_context):
        from System.Windows.Markup import XamlReader
        from System.IO import FileStream, FileMode, FileAccess
        here = os.path.dirname(os.path.abspath(__file__))
        button = os.path.abspath(os.path.join(here, '..', '..'))
        path = os.path.join(button, 'GUI', 'Views', 'pages', filename)
        stream = FileStream(path, FileMode.Open, FileAccess.Read)
        try:
            page = XamlReader.Load(stream)
        finally:
            stream.Close()
        page.DataContext = data_context
        return page

    def _mount_pages(self):
        self._page_selection = self._load_page('SelectionPage.xaml', self._vm.SelectionVM)
        self._page_options = self._load_page('OptionsPage.xaml', self._vm.OptionsVM)
        self._show_current_page()

    def _show_current_page(self):
        host = self._window.FindName('PageHost')
        if host is None:
            return
        host.Content = self._page_options if self._vm.IsOptions else self._page_selection

    def _wire_nav(self):
        nav_sel = self._window.FindName('NavSelection')
        nav_opt = self._window.FindName('NavOptions')
        if nav_sel is not None:
            def _on_sel(sender, args):
                self._vm.set_mode(u'selection')
                self._show_current_page()
            nav_sel.Checked += _on_sel
        if nav_opt is not None:
            def _on_opt(sender, args):
                self._vm.set_mode(u'options')
                self._show_current_page()
            nav_opt.Checked += _on_opt

    def _sync_nav(self):
        # Coche le RadioButton correspondant au mode initial décidé par le VM.
        name = 'NavOptions' if self._vm.IsOptions else 'NavSelection'
        btn = self._window.FindName(name)
        if btn is not None:
            btn.IsChecked = True

    def _wire_next(self):
        # Bouton « Suivant » de la page Sélection : mène à la page Options.
        btn = self._page_selection.FindName('NextButton')
        if btn is None:
            return

        def _on_next(sender, args):
            nav_opt = self._window.FindName('NavOptions')
            if nav_opt is not None:
                nav_opt.IsChecked = True
        btn.Click += _on_next

    def _wire_run(self):
        # Le bouton Run vit dans OptionsPage : le retrouver dans l'arbre de la page.
        btn = self._page_options.FindName('RunButton')
        if btn is None:
            return

        def _on_run(sender, args):
            try:
                new_ids = self._vm.lancer(self._views_par_id)
                self._reselect(new_ids)
            finally:
                self._window.Close()
        btn.Click += _on_run

    def _reselect(self, new_ids):
        """Sélectionne les vues dupliquées dans l'interface Revit."""
        if not new_ids or self._uidoc is None:
            return
        try:
            from System.Collections.Generic import List
            from Autodesk.Revit.DB import ElementId
            self._uidoc.Selection.SetElementIds(List[ElementId](new_ids))
        except Exception:
            pass

    def _wire_view_dup_option(self):
        # Câblage obligatoire : sans lui, les radios restent inertes et
        # l'option de duplication reste silencieusement 'duplicate'.
        for name in ('RadioDuplicate', 'RadioDetailing', 'RadioDependent'):
            rb = self._page_options.FindName(name)
            if rb is None:
                continue

            def _on_checked(sender, args):
                self._vm.OptionsVM.ViewDuplicateOption = sender.Tag
            rb.Checked += _on_checked
