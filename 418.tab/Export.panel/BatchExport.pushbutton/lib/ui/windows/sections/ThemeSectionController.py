# -*- coding: utf-8 -*-


class ThemeSectionController(object):
    def __init__(self, win, paths):
        self._win = win
        self._paths = paths

    def apply_initial_theme(self):
        try:
            from Autodesk.Revit.UI import UIThemeManager, UITheme
            theme = UIThemeManager.CurrentTheme
        except Exception:
            return

        try:
            if theme == UITheme.Dark:
                self.apply_dark()
        except Exception:
            pass

    def wire_toggle(self):
        try:
            if hasattr(self._win, 'DarkModeToggle'):
                self._win.DarkModeToggle.Checked += self._on_dark_mode
                self._win.DarkModeToggle.Unchecked += self._on_light_mode
        except Exception:
            pass

    def apply_dark(self):
        try:
            from ...helpers.DarkMode import apply_dark_mode
            apply_dark_mode(self._win, self._paths)
        except Exception as e:
            print('MainWindowController [001]: Dark mode error: {}'.format(e))

    def apply_light(self):
        try:
            from ...helpers.DarkMode import remove_dark_mode
            remove_dark_mode(self._win)
        except Exception as e:
            print('MainWindowController [002]: Light mode error: {}'.format(e))

    def _on_dark_mode(self, sender, args):
        self.apply_dark()

    def _on_light_mode(self, sender, args):
        self.apply_light()
