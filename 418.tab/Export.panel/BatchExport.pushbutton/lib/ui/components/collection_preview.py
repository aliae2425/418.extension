# -*- coding: utf-8 -*-
"""Composant de prévisualisation des collections à exporter.

Ce module gère l'affichage et la mise à jour du DataGrid qui montre
la prévisualisation des collections de feuilles à exporter avec leurs
détails (feuilles, formats PDF/DWG, statuts).
"""

try:
    from Autodesk.Revit import DB
    REVIT_API_AVAILABLE = True
except Exception:
    DB = None
    REVIT_API_AVAILABLE = False

try:
    from System.Windows.Media import Brushes
except Exception:
    Brushes = None


class CollectionPreview:
    """Composant de prévisualisation des collections.
    
    Ce composant gère le DataGrid qui affiche:
        - Les collections de feuilles avec leurs paramètres (Export, Carnet, DWG)
        - Le nombre de feuilles par collection
        - Les détails (RowDetails) avec les feuilles individuelles et formats
        - Les statuts d'export en temps réel
    
    Responsabilités:
        - Population initiale du DataGrid
        - Mise à jour dynamique des statuts pendant l'export
        - Comptage des collections et éléments
        - Tri et organisation des données
    
    Attributs:
        window: Instance de la fenêtre principale (ExportMainWindow)
    """
    
    def __init__(self, window):
        """Initialise le composant.
        
        Args:
            window: Instance de ExportMainWindow
        """
        self.window = window
    
    def populate(self):
        """Remplit le DataGrid avec les collections et leurs détails.
        
        Structure des données:
            - Colonnes principales: Nom | Feuilles | Export | Carnet | DWG | Statut
            - Détails (expand): Nom | Format | Statut (pour chaque feuille/export)
        
        Le DataGrid utilise RowDetailsVisibilityMode=VisibleWhenSelected pour
        afficher les détails quand une ligne est sélectionnée.
        """
        # Import des fonctions helpers de GUI.py
        from ...GUI import (
            _populate_sheet_sets,
            _get_selected_values,
            _refresh_collection_grid,
            _set_collection_status,
            _set_detail_status
        )
        
        # Déléguer à la fonction existante
        _populate_sheet_sets(self.window)
    
    def refresh(self):
        """Rafraîchit l'affichage du DataGrid.
        
        Force une mise à jour visuelle du DataGrid pour refléter les
        changements d'état (statuts, sélections, etc.).
        """
        from ...GUI import _refresh_collection_grid
        _refresh_collection_grid(self.window)
    
    def set_collection_status(self, collection_name, state):
        """Met à jour le statut d'une collection.
        
        Args:
            collection_name (str): Nom de la collection
            state (str): État à afficher ('progress', 'ok', 'error')
        """
        from ...GUI import _set_collection_status, _refresh_collection_grid
        _set_collection_status(self.window, collection_name, state)
        _refresh_collection_grid(self.window)
    
    def set_detail_status(self, collection_name, detail_name, detail_format, state):
        """Met à jour le statut d'un détail (feuille/export).
        
        Args:
            collection_name (str): Nom de la collection parente
            detail_name (str): Nom de la feuille/export
            detail_format (str): Format (PDF, DWG, PDF (combiné))
            state (str): État à afficher ('progress', 'ok', 'error')
        """
        from ...GUI import _set_detail_status, _refresh_collection_grid
        _set_detail_status(self.window, collection_name, detail_name, detail_format, state)
        _refresh_collection_grid(self.window)
    
    def get_preview_items(self):
        """Retourne la liste des items de prévisualisation.
        
        Returns:
            list: Liste des dictionnaires représentant les collections
        """
        return getattr(self.window, '_preview_items', [])
    
    def update_counter(self):
        """Met à jour le compteur de collections et éléments.
        
        Affiche dans PreviewCounterText le nombre de collections et
        le nombre total d'éléments (exports) à traiter.
        """
        try:
            counter = getattr(self.window, 'PreviewCounterText', None)
            if counter is None:
                return
            
            items = self.get_preview_items()
            ncoll = len(items)
            nelems = sum(len(it.get('Details', []) or []) for it in items)
            
            counter.Text = u"Collections: {} • Éléments: {}".format(ncoll, nelems)
        except Exception:
            pass


__all__ = ['CollectionPreview']
