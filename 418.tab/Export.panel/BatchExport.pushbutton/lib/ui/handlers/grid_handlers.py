# -*- coding: utf-8 -*-
"""Gestionnaires d'événements pour le DataGrid de prévisualisation.

Ce module gère les événements liés au DataGrid qui affiche la prévisualisation
des collections à exporter (avec détails expand/collapse).
"""


class GridHandlers:
    """Gestionnaire des événements pour le DataGrid de prévisualisation.
    
    Responsabilités:
        - Gestion du clic sur les lignes du DataGrid
        - Toggle expand/collapse des détails (RowDetails)
        - Désélection pour refermer les détails
    
    Attributs:
        window: Instance de la fenêtre principale (ExportMainWindow)
    """
    
    def __init__(self, window):
        """Initialise le gestionnaire.
        
        Args:
            window: Instance de ExportMainWindow
        """
        self.window = window
    
    def bind(self):
        """Abonne le gestionnaire d'événement au DataGrid."""
        try:
            if hasattr(self.window, 'CollectionGrid') and self.window.CollectionGrid is not None:
                self.window.CollectionGrid.PreviewMouseLeftButtonDown += self._on_grid_preview_mouse_left_button_down
        except Exception:
            pass
    
    def _on_grid_preview_mouse_left_button_down(self, sender, e):
        """Gestionnaire de clic sur le DataGrid pour toggle expand/collapse.
        
        Permet de désélectionner une ligne déjà sélectionnée par un clic,
        ce qui referme les RowDetails (car RowDetailsVisibilityMode=VisibleWhenSelected).
        
        Comportement:
            - Si la ligne cliquée est déjà sélectionnée: la désélectionner
            - Sinon: comportement par défaut (sélection normale)
        
        Args:
            sender: Le DataGrid qui a déclenché l'événement
            e: Arguments de l'événement contenant OriginalSource
        """
        try:
            # Imports WPF nécessaires
            from System.Windows import DependencyObject
            from System.Windows.Media import VisualTreeHelper
            from System.Windows.Controls import DataGridRow
        except Exception:
            return
        
        try:
            # Récupérer la source de l'événement
            src = getattr(e, 'OriginalSource', None)
            obj = src if isinstance(src, DependencyObject) else None
            row = None
            
            # Remonter l'arbre visuel jusqu'à trouver un DataGridRow
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
            
            # Si la ligne est déjà sélectionnée, la désélectionner
            if getattr(row, 'IsSelected', False):
                try:
                    row.IsSelected = False
                    # Marquer l'événement comme traité pour éviter le comportement par défaut
                    e.Handled = True
                except Exception:
                    pass
                    
        except Exception:
            pass


__all__ = ['GridHandlers']
