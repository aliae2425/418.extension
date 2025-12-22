# -*- coding: utf-8 -*-

"""Helpers: overlay hover text for burger menu.

Centralizes the lookup + show/hide logic for BurgerMenuHoverText.
"""


def _find_hover_text_block(win):
    tb = None
    try:
        tb = getattr(win, 'BurgerMenuHoverText', None)
    except Exception:
        tb = None

    if tb is None and hasattr(win, 'FindName'):
        try:
            tb = win.FindName('BurgerMenuHoverText')
        except Exception:
            tb = None

    return tb


def set_hover_text(win, text):
    """Set hover overlay text. Pass empty/None to hide."""
    try:
        from System.Windows import Visibility
    except Exception:
        return

    tb = _find_hover_text_block(win)
    if tb is None:
        return

    try:
        if text:
            tb.Text = text
            tb.Visibility = Visibility.Visible
        else:
            tb.Text = ''
            tb.Visibility = Visibility.Collapsed
    except Exception:
        pass
