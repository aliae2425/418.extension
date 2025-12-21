# -*- coding: utf-8 -*-


def unselect_row_on_preview_left_click(e):
    """If the user clicks an already-selected DataGridRow, unselect it.

    Used to collapse RowDetails when re-clicking the same row.
    """
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
            try:
                if isinstance(obj, DataGridRow):
                    row = obj
                    break
            except Exception:
                pass
            try:
                obj = VisualTreeHelper.GetParent(obj)
            except Exception:
                obj = None

        if row is None:
            return

        if getattr(row, 'IsSelected', False):
            try:
                row.IsSelected = False
                e.Handled = True
            except Exception:
                pass
    except Exception:
        pass
