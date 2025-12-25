# -*- coding: utf-8 -*-


class BurgerMenuSectionController(object):
    def __init__(self, win):
        self._win = win

    def _set_profile_label_resource(self, label):
        try:
            # Preferred: DynamicResource ActiveProfileLabel in XAML
            res = getattr(self._win, 'Resources', None)
            if res is not None:
                res['ActiveProfileLabel'] = label
                return True
        except Exception:
            pass
        return False

    def update_profile_name(self):
        """Affiche la clé de profil active (active_profile_key) depuis pyRevit_config.ini."""
        label = u"Profil"
        try:
            from ....core.UserConfig import UserConfig
            cfg = UserConfig('batch_export')
            active_key = cfg.get('active_profile_key', '')
            if active_key:
                label = active_key
        except Exception:
            pass

        # Update DynamicResource (best-effort). Fallback to direct TextBlock set.
        if self._set_profile_label_resource(label):
            return
        try:
            tb = getattr(self._win, 'ProfileNameText', None)
            if tb is None and hasattr(self._win, 'FindName'):
                tb = self._win.FindName('ProfileNameText')
            if tb is not None:
                tb.Text = label
        except Exception:
            pass

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

            # Les contrôles XAML existent maintenant: set le texte une première fois.
            self.update_profile_name()

            # Rafraîchit le nom du profil à chaque ouverture du menu
            if hasattr(self._win, 'BurgerMenu'):
                try:
                    self._win.BurgerMenu.IsVisibleChanged += self._on_burger_menu_visibility_changed
                except Exception:
                    pass
        except Exception:
            pass

    def _on_burger_menu_visibility_changed(self, sender, args):
        try:
            # Si le menu devient visible, rafraîchir le nom du profil
            if hasattr(sender, 'Visibility'):
                from System.Windows import Visibility
                if sender.Visibility == Visibility.Visible:
                    self.update_profile_name()
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
            hover_layer = getattr(self._win, 'BurgerMenuHoverLayer', None)
            if hover_layer is None and hasattr(self._win, 'FindName'):
                try:
                    hover_layer = self._win.FindName('BurgerMenuHoverLayer')
                except Exception:
                    hover_layer = None
            try:
                from ...helpers.HoverOverlay import set_hover_text
            except Exception:
                set_hover_text = None

            if menu is not None:
                if menu.Visibility == Visibility.Visible:
                    menu.Visibility = Visibility.Collapsed
                    if overlay:
                        overlay.Visibility = Visibility.Collapsed
                    if hover_layer is not None:
                        try:
                            hover_layer.Visibility = Visibility.Collapsed
                        except Exception:
                            pass
                    if set_hover_text is not None:
                        set_hover_text(self._win, '')
                else:
                    # Juste avant affichage: rafraîchir le libellé du profil actif
                    self.update_profile_name()
                    menu.Visibility = Visibility.Visible
                    if overlay:
                        overlay.Visibility = Visibility.Visible
                    if hover_layer is not None:
                        try:
                            hover_layer.Visibility = Visibility.Visible
                        except Exception:
                            pass
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
            hover_layer = getattr(self._win, 'BurgerMenuHoverLayer', None)
            if hover_layer is None and hasattr(self._win, 'FindName'):
                try:
                    hover_layer = self._win.FindName('BurgerMenuHoverLayer')
                except Exception:
                    hover_layer = None
            try:
                from ...helpers.HoverOverlay import set_hover_text
            except Exception:
                set_hover_text = None

            if menu is not None:
                menu.Visibility = Visibility.Collapsed
            if overlay is not None:
                overlay.Visibility = Visibility.Collapsed
            if hover_layer is not None:
                try:
                    hover_layer.Visibility = Visibility.Collapsed
                except Exception:
                    pass
            if set_hover_text is not None:
                set_hover_text(self._win, '')
        except Exception:
            pass
