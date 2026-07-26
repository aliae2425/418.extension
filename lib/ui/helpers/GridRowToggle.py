# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def unselect_row_on_preview_left_click(e):
    try:
        from System.Windows import DependencyObject
        from System.Windows.Media import VisualTreeHelper
        from System.Windows.Controls import DataGridRow
    except Exception:
        return
    try:
        src = getattr(e, 'OriginalSource', None)
        obj = src if isinstance(src, DependencyObject) else None
        row = None
        while obj is not None:
            if isinstance(obj, DataGridRow):
                row = obj
                break
            try:
                obj = VisualTreeHelper.GetParent(obj)
            except Exception:
                obj = None
        if row is not None and getattr(row, 'IsSelected', False):
            row.IsSelected = False
            e.Handled = True
    except Exception:
        pass
