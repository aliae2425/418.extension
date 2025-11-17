# -*- coding: utf-8 -*-
"""Gestionnaires d'événements pour les ComboBox de paramètres.

Ce module gère les événements liés aux ComboBox de sélection des paramètres
(Exportation, Carnet, DWG). Il gère la sauvegarde automatique des sélections,
la validation et la mise à jour de l'interface.
"""

# Liste des ComboBox de paramètres à gérer
PARAM_COMBOS = ["ExportationCombo", "CarnetCombo", "DWGCombo"]


class ParameterHandlers:
    """Gestionnaire des événements pour les ComboBox de paramètres.
    
    Responsabilités:
        - Gestion du changement de sélection dans les ComboBox
        - Sauvegarde automatique des sélections
        - Mise à jour de l'état de l'interface (avertissements, boutons)
        - Rafraîchissement de la prévisualisation
    
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
        """Abonne les gestionnaires d'événements aux ComboBox.
        
        Cette méthode connecte le gestionnaire _on_param_combo_changed
        à l'événement SelectionChanged de chaque ComboBox de paramètres.
        """
        for combo_name in PARAM_COMBOS:
            try:
                ctrl = getattr(self.window, combo_name, None)
                if ctrl is not None:
                    ctrl.SelectionChanged += self._on_param_combo_changed
            except Exception:
                pass
    
    def _on_param_combo_changed(self, sender, args):
        """Gestionnaire de changement de sélection dans une ComboBox paramètre.
        
        Appelé automatiquement quand l'utilisateur change la sélection dans
        une des ComboBox (ExportationCombo, CarnetCombo, DWGCombo).
        
        Actions effectuées:
            1. Vérifie qu'on n'est pas dans une boucle de mise à jour
            2. Sauvegarde la nouvelle sélection dans la configuration
            3. Met à jour l'instantané des sélections précédentes
            4. Vérifie et affiche les avertissements si nécessaire
            5. Met à jour l'état du bouton Export
            6. Rafraîchit la prévisualisation des collections
        
        Args:
            sender: Le contrôle ComboBox qui a déclenché l'événement
            args: Arguments de l'événement (non utilisés)
        """
        # Éviter les boucles de mise à jour
        if getattr(self.window, '_updating', False):
            return
        
        try:
            self.window._updating = True
            
            # Import des fonctions helpers nécessaires
            from ...GUI import (
                _get_selected_values,
                _save_param_selection,
                _check_and_warn_insufficient,
                _update_export_button_state,
                _populate_sheet_sets
            )
            
            # Mettre à jour l'instantané "avant"
            self.window._prev_selection = _get_selected_values(self.window)
            
            # Auto-save: persister la valeur du sender
            name = getattr(sender, 'Name', None) or 'Unknown'
            val = getattr(sender, 'SelectedItem', None)
            if val is not None:
                _save_param_selection(name, str(val))
            
            # Mettre à jour l'avertissement si insuffisant
            _check_and_warn_insufficient(self.window)
            
            # Mettre à jour l'état du bouton Export
            _update_export_button_state(self.window)
            
            # Rafraîchir l'aperçu des collections
            _populate_sheet_sets(self.window)
            
        except Exception as e:
            print('[info] Erreur dans _on_param_combo_changed:', e)
        finally:
            self.window._updating = False


__all__ = ['ParameterHandlers', 'PARAM_COMBOS']
