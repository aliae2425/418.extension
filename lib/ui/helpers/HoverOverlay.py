# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def _find(win, name):
    try:
        obj = getattr(win, name, None)
        if obj is not None:
            return obj
    except Exception:
        pass
    if hasattr(win, 'FindName'):
        try:
            return win.FindName(name)
        except Exception:
            pass
    return None


def set_hover_text(win, element_name, text):
    try:
        from System.Windows import Visibility
    except Exception:
        return False
    tb = _find(win, element_name)
    if tb is None:
        return False
    try:
        if text:
            tb.Text = text
            tb.Visibility = Visibility.Visible
        else:
            tb.Text = u''
            tb.Visibility = Visibility.Collapsed
        return True
    except Exception:
        return False


def clear_hover(win, element_name):
    set_hover_text(win, element_name, u'')
