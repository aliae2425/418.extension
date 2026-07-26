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
    """Fenêtre racine « Renommer les vues » : rail 2 onglets
    (Sélection / Nommage)."""

    def __init__(self, view_model, views_par_id):
        super(MainWindowView, self).__init__(_xaml_path(), view_model)
        self._vm = view_model
        self._views_par_id = views_par_id

    def _load(self):
        super(MainWindowView, self)._load()
        if self._window is None:
            return
        self._mount_pages()
        self._wire_nav()
        self._wire_next_selection()
        self._wire_run()
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
        self._page_nommage = self._load_page('NamingPage.xaml', self._vm.NamingVM)
        self._show_current_page()

    def _show_current_page(self):
        host = self._window.FindName('PageHost')
        if host is None:
            return
        if self._vm.IsNommage:
            host.Content = self._page_nommage
        else:
            host.Content = self._page_selection

    def _wire_nav(self):
        nav_sel = self._window.FindName('NavSelection')
        nav_nom = self._window.FindName('NavNommage')

        if nav_sel is not None:
            def _on_sel(sender, args):
                self._vm.set_mode(u'selection')
                self._show_current_page()
            nav_sel.Checked += _on_sel

        if nav_nom is not None:
            def _on_nom(sender, args):
                self._vm.set_mode(u'nommage')
                self._show_current_page()
            nav_nom.Checked += _on_nom

    def _sync_nav(self):
        name = 'NavNommage' if self._vm.IsNommage else 'NavSelection'
        btn = self._window.FindName(name)
        if btn is not None:
            btn.IsChecked = True

    def _wire_next_selection(self):
        btn = self._page_selection.FindName('NextButton')
        if btn is None:
            return

        def _on_next(sender, args):
            nav = self._window.FindName('NavNommage')
            if nav is not None:
                nav.IsChecked = True
        btn.Click += _on_next

    def _wire_run(self):
        btn = self._page_nommage.FindName('RunButton')
        if btn is None:
            return

        def _on_run(sender, args):
            try:
                self._vm.lancer(self._views_par_id)
            finally:
                self._window.Close()
        btn.Click += _on_run
