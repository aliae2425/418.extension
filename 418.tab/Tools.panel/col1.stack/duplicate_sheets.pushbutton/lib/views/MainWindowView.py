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
    """Fenêtre racine « Dupliquer les feuilles » : rail 3 onglets
    (Sélection / Paramètres / Nommage), sans modale bloquante."""

    def __init__(self, view_model, sheets_par_id):
        super(MainWindowView, self).__init__(_xaml_path(), view_model)
        self._vm = view_model
        self._sheets_par_id = sheets_par_id

    def _load(self):
        super(MainWindowView, self)._load()
        if self._window is None:
            return
        self._mount_pages()
        self._wire_nav()
        self._wire_next_selection()
        self._wire_selection_interactions()
        self._wire_next_params()
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
        self._page_params = self._load_page('ParamsPage.xaml', self._vm.OptionsVM)
        self._page_nommage = self._load_page('OptionsPage.xaml', self._vm.OptionsVM)
        self._show_current_page()

    def _show_current_page(self):
        host = self._window.FindName('PageHost')
        if host is None:
            return
        if self._vm.IsOptions:
            host.Content = self._page_nommage
        elif self._vm.IsParams:
            host.Content = self._page_params
        else:
            host.Content = self._page_selection

    def _wire_nav(self):
        nav_sel = self._window.FindName('NavSelection')
        nav_par = self._window.FindName('NavParams')
        nav_opt = self._window.FindName('NavOptions')

        if nav_sel is not None:
            def _on_sel(sender, args):
                self._vm.set_mode(u'selection')
                self._show_current_page()
            nav_sel.Checked += _on_sel

        if nav_par is not None:
            def _on_par(sender, args):
                self._vm.set_mode(u'params')
                self._show_current_page()
            nav_par.Checked += _on_par

        if nav_opt is not None:
            def _on_opt(sender, args):
                self._vm.set_mode(u'options')
                self._show_current_page()
            nav_opt.Checked += _on_opt

    def _sync_nav(self):
        if self._vm.IsOptions:
            name = 'NavOptions'
        elif self._vm.IsParams:
            name = 'NavParams'
        else:
            name = 'NavSelection'
        btn = self._window.FindName(name)
        if btn is not None:
            btn.IsChecked = True

    def _wire_next_selection(self):
        # « Suivant » de la page Sélection → Paramètres.
        btn = self._page_selection.FindName('NextButton')
        if btn is None:
            return

        def _on_next(sender, args):
            nav = self._window.FindName('NavParams')
            if nav is not None:
                nav.IsChecked = True
        btn.Click += _on_next

    def _wire_selection_interactions(self):
        # Barre de recherche + boutons de masse + clic unique sur la liste
        # (page Sélection). Cf. note en tête de SelectionPage.xaml.
        page = self._page_selection
        vm = self._vm.SelectionVM

        # Boutons de masse
        btn_all = page.FindName('SelectAllButton')
        if btn_all is not None:
            btn_all.Click += lambda s, a: vm.select_all()
        btn_none = page.FindName('DeselectAllButton')
        if btn_none is not None:
            btn_none.Click += lambda s, a: vm.deselect_all()

        # Un seul handler de clic sur la liste : remonte (index affiché + modificateurs)
        lst = page.FindName('ItemsList')
        if lst is None:
            return

        def _on_row_click(sender, args):
            from System.Windows.Input import Keyboard, ModifierKeys
            src = args.OriginalSource
            item = getattr(src, 'DataContext', None)
            filtered = list(vm.FilteredItems)
            if item is None or item not in filtered:
                return
            index = filtered.index(item)
            mods = Keyboard.Modifiers
            shift = bool(int(mods) & int(ModifierKeys.Shift))
            ctrl = bool(int(mods) & int(ModifierKeys.Control))
            vm.handle_row_click(index, shift, ctrl)

        lst.PreviewMouseLeftButtonDown += _on_row_click

    def _wire_next_params(self):
        # « Suivant » de la page Paramètres → Nommage.
        btn = self._page_params.FindName('NextToNommageButton')
        if btn is None:
            return

        def _on_next(sender, args):
            nav = self._window.FindName('NavOptions')
            if nav is not None:
                nav.IsChecked = True
        btn.Click += _on_next

    def _wire_run(self):
        # RunButton dans la page Nommage.
        btn = self._page_nommage.FindName('RunButton')
        if btn is None:
            return

        def _on_run(sender, args):
            try:
                self._vm.lancer(self._sheets_par_id)
            finally:
                self._window.Close()
        btn.Click += _on_run

    def _wire_view_dup_option(self):
        # Les radios vivent dans ParamsPage.
        for name in ('RadioDuplicate', 'RadioDetailing', 'RadioDependent'):
            rb = self._page_params.FindName(name)
            if rb is None:
                continue

            def _on_checked(sender, args):
                self._vm.OptionsVM.ViewDuplicateOption = sender.Tag
            rb.Checked += _on_checked
