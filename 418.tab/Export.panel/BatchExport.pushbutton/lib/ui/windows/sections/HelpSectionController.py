# -*- coding: utf-8 -*-


class HelpSectionController(object):
    def __init__(self, win):
        self._win = win

    def wire(self):
        try:
            if hasattr(self._win, 'HelpButton'):
                self._win.HelpButton.MouseEnter += self._on_help_hover_enter
                self._win.HelpButton.MouseLeave += self._on_help_hover_leave
        except Exception:
            pass

    def _on_help_hover_enter(self, sender, args):
        try:
            from ...helpers.HoverOverlay import set_hover_xaml, set_hover_text
            ok = set_hover_xaml(self._win, 'hover/HelpHover.xaml')
            if not ok:
                set_hover_text(self._win, u"Aide : paramètres d'export")
        except Exception:
            pass

    def _on_help_hover_leave(self, sender, args):
        try:
            from ...helpers.HoverOverlay import clear_hover
            clear_hover(self._win)
        except Exception:
            pass

    # Note: ouverture de la modale désactivée volontairement (hover uniquement).
