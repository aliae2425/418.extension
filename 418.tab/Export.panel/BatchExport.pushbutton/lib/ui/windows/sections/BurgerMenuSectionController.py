# -*- coding: utf-8 -*-


class BurgerMenuSectionController(object):
    def __init__(self, win):
        self._win = win

    def wire(self):
        try:
            if hasattr(self._win, 'BurgerButton'):
                self._win.BurgerButton.Click += self._toggle_burger_menu
            if hasattr(self._win, 'CloseBurgerButton'):
                self._win.CloseBurgerButton.Click += self._close_burger_menu
            if hasattr(self._win, 'BurgerMenuOverlay'):
                self._win.BurgerMenuOverlay.MouseLeftButtonDown += self._close_burger_menu

            if hasattr(self._win, 'CloseWindowButton'):
                self._win.CloseWindowButton.Click += self._on_close_window
            if hasattr(self._win, 'TitleBar'):
                self._win.TitleBar.MouseLeftButtonDown += self._on_title_bar_mouse_down

            self._wire_accordion()
        except Exception:
            pass

    def _wire_accordion(self):
        expanders = []
        for name in ['CollectionExpander', 'PDFExpander', 'DWGExpander', 'NamingExpander']:
            if hasattr(self._win, name):
                expanders.append(getattr(self._win, name))

        def _on_expanded(sender, args):
            for exp in expanders:
                if exp != sender and exp.IsExpanded:
                    exp.IsExpanded = False

        for exp in expanders:
            try:
                exp.Expanded += _on_expanded
            except Exception:
                pass

    def _on_close_window(self, sender, args):
        try:
            self._win.Close()
        except Exception:
            pass

    def _on_title_bar_mouse_down(self, sender, args):
        try:
            self._win.DragMove()
        except Exception:
            pass

    def _toggle_burger_menu(self, sender, args):
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
                    if overlay:
                        overlay.Visibility = Visibility.Collapsed
                else:
                    menu.Visibility = Visibility.Visible
                    if overlay:
                        overlay.Visibility = Visibility.Visible
        except Exception:
            pass

    def _close_burger_menu(self, sender, args):
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
