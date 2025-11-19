# -*- coding: utf-8 -*-
# Gestionnaires liés au DataGrid (toggle des RowDetails par clic)

class GridHandlers(object):
    def __init__(self):
        pass

    # Désélectionner une ligne si déjà sélectionnée (pour fermer les détails)
    def on_preview_left_click(self, sender, e):
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
