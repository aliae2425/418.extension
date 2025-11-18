# -*- coding: utf-8 -*-
"""Gestionnaires d'événements pour la sélection de destination.

Ce module gère les événements liés à la sélection et validation du
dossier de destination d'export.
"""


class DestinationHandlers:
    """Gestionnaire des événements pour la destination d'export.
    
    Responsabilités:
        - Gestion du clic sur le bouton Browse (...)
        - Gestion du changement manuel du chemin dans la TextBox
        - Validation du chemin de destination
        - Feedback visuel (couleurs, bordures)
        - Sauvegarde de la destination valide
    
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
        """Abonne les gestionnaires d'événements aux contrôles de destination."""
        try:
            # Bouton Browse
            if hasattr(self.window, 'BrowseButton'):
                self.window.BrowseButton.Click += self._on_browse_clicked
            
            # TextBox de chemin
            if hasattr(self.window, 'PathTextBox'):
                self.window.PathTextBox.TextChanged += self._on_path_changed
        except Exception:
            pass
    
    def load_saved_destination(self):
        """Charge la destination sauvegardée dans la TextBox.
        
        Appelé lors de l'initialisation de la fenêtre pour restaurer
        le dernier dossier de destination utilisé.
        """
        try:
            from ...destination import get_saved_destination
            
            if hasattr(self.window, 'PathTextBox'):
                self.window.PathTextBox.Text = get_saved_destination()
                # Valider et créer si besoin
                self.window._validate_destination(create=True)
        except Exception:
            pass
    
    def _on_browse_clicked(self, sender, args):
        """Gestionnaire du clic sur le bouton Browse.
        
        Ouvre un dialogue de sélection de dossier et met à jour la
        destination si l'utilisateur valide un choix.
        
        Args:
            sender: Le bouton qui a déclenché l'événement
            args: Arguments de l'événement (non utilisés)
        """
        try:
            from ...destination import choose_destination_explorer
            from ...GUI import _update_export_button_state
            
            # Ouvrir le dialogue de sélection
            chosen = choose_destination_explorer(save=True)
            
            if chosen:
                try:
                    # Mettre à jour la TextBox
                    self.window.PathTextBox.Text = chosen
                except Exception:
                    pass
                
                # Valider la destination (créer si nécessaire)
                self.window._validate_destination(create=True)
                
                # Mettre à jour l'état du bouton Export
                _update_export_button_state(self.window)
                
        except Exception as e:
            print('[info] Sélection dossier échouée: {}'.format(e))
    
    def _on_path_changed(self, sender, args):
        """Gestionnaire du changement de texte dans la PathTextBox.
        
        Valide le chemin saisi (sans le créer) et met à jour l'état
        du bouton Export.
        
        Args:
            sender: La TextBox qui a déclenché l'événement
            args: Arguments de l'événement (non utilisés)
        """
        try:
            from ...GUI import _update_export_button_state
            
            # Valide à la volée sans créer le dossier
            self.window._validate_destination(create=False)
            
            # Mettre à jour l'état du bouton Export
            _update_export_button_state(self.window)
            
        except Exception:
            pass


__all__ = ['DestinationHandlers']
