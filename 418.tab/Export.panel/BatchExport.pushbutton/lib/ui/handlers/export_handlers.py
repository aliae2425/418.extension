# -*- coding: utf-8 -*-
"""Gestionnaires d'événements pour l'export.

Ce module gère les événements liés au bouton d'export et à l'exécution
des exports (PDF et DWG).
"""


class ExportHandlers:
    """Gestionnaire des événements pour l'export.
    
    Responsabilités:
        - Gestion du clic sur le bouton Export
        - Orchestration de l'export (préparation, exécution, callbacks)
        - Mise à jour de la barre de progression
        - Mise à jour du statut dans le tableau de prévisualisation
    
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
        """Abonne le gestionnaire d'événement au bouton Export."""
        try:
            if hasattr(self.window, 'ExportButton'):
                self.window.ExportButton.Click += self._on_export_clicked
        except Exception:
            pass
    
    def _on_export_clicked(self, sender, args):
        """Gestionnaire du clic sur le bouton Export.
        
        Lance l'export des collections sélectionnées avec les paramètres
        configurés (destination, nommage, PDF/DWG).
        
        Actions effectuées:
            1. Récupère les sélections utilisateur
            2. Récupère le document Revit actif
            3. Configure les callbacks pour progression et statut
            4. Lance l'export via le module exporter
        
        Args:
            sender: Le bouton qui a déclenché l'événement
            args: Arguments de l'événement (non utilisés)
        """
        try:
            # Import des fonctions helpers
            from ...GUI import _get_selected_values, _set_collection_status, _set_detail_status, _refresh_collection_grid
            
            # Récupérer les sélections
            selected = _get_selected_values(self.window)
            print('[info] Export lancé avec paramètres:', selected)
            
            # Récupérer le document Revit
            try:
                doc = __revit__.ActiveUIDocument.Document  # type: ignore
            except Exception:
                doc = None
            
            if doc is None:
                print('[info] Document Revit introuvable')
                return
            
            # Importer le module d'export
            from ...exporter import execute_exports
            
            # Créer les callbacks
            def _progress(i, n, text):
                """Callback de progression pour la barre de progression."""
                try:
                    if hasattr(self.window, 'ExportProgressBar'):
                        self.window.ExportProgressBar.Maximum = max(n, 1)
                        self.window.ExportProgressBar.Value = i
                except Exception:
                    pass
                if text:
                    print('[info]', text)
            
            def _log(msg):
                """Callback de log pour afficher les messages."""
                print('[info]', msg)
            
            def _get_ctrl(name):
                """Callback pour récupérer un contrôle par son nom."""
                return getattr(self.window, name, None)
            
            def _status(kind, payload):
                """Callback de statut pour mettre à jour le tableau en direct.
                
                Args:
                    kind (str): Type de mise à jour ('collection' ou 'sheet')
                    payload (dict): Données de mise à jour
                        - Pour 'collection': {state: str, name: str}
                        - Pour 'sheet': {state: str, collection: str, name: str, format: str}
                """
                try:
                    if kind == 'collection':
                        state = payload.get('state')
                        name = payload.get('name')
                        _set_collection_status(self.window, name, state)
                        _refresh_collection_grid(self.window)
                    elif kind == 'sheet':
                        state = payload.get('state')
                        cname = payload.get('collection')
                        nm = payload.get('name')
                        fmt = payload.get('format')
                        _set_detail_status(self.window, cname, nm, fmt, state)
                        _refresh_collection_grid(self.window)
                except Exception:
                    pass
            
            # Lancer l'export
            execute_exports(
                doc,
                _get_ctrl,
                progress_cb=_progress,
                log_cb=_log,
                ui_win=self.window
            )
            
        except Exception as e:
            print('[info] Erreur export:', e)


__all__ = ['ExportHandlers']
