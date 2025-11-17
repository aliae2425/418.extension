# -*- coding: utf-8 -*-
"""Gestionnaires d'événements pour le nommage des fichiers.

Ce module gère les événements liés aux boutons de configuration du
nommage des feuilles et des carnets.
"""


class NamingHandlers:
    """Gestionnaire des événements pour le nommage.
    
    Responsabilités:
        - Gestion du clic sur le bouton de nommage des feuilles
        - Gestion du clic sur le bouton de nommage des carnets
        - Ouverture des dialogues modaux de configuration
        - Rafraîchissement de l'affichage des patterns sur les boutons
    
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
        """Abonne les gestionnaires d'événements aux boutons de nommage."""
        try:
            if hasattr(self.window, 'SheetNamingButton'):
                self.window.SheetNamingButton.Click += self._on_open_sheet_naming
            
            if hasattr(self.window, 'SetNamingButton'):
                self.window.SetNamingButton.Click += self._on_open_set_naming
        except Exception:
            pass
    
    def refresh_naming_buttons(self):
        """Rafraîchit l'affichage des patterns de nommage sur les boutons.
        
        Charge les patterns sauvegardés depuis la configuration et met à jour
        le texte (Content) des boutons pour afficher le pattern actuel.
        """
        try:
            from ...naming import load_pattern
        except Exception:
            return
        
        # Charger le pattern des feuilles
        try:
            sheet_patt, _ = load_pattern('sheet')
        except Exception:
            sheet_patt = ''
        
        # Charger le pattern des carnets
        try:
            set_patt, _ = load_pattern('set')
        except Exception:
            set_patt = ''
        
        # Mettre à jour le bouton feuilles
        try:
            if hasattr(self.window, 'SheetNamingButton'):
                self.window.SheetNamingButton.Content = sheet_patt or '...'
        except Exception:
            pass
        
        # Mettre à jour le bouton carnets
        try:
            if hasattr(self.window, 'SetNamingButton'):
                self.window.SetNamingButton.Content = set_patt or '...'
        except Exception:
            pass
    
    def _on_open_sheet_naming(self, sender, args):
        """Gestionnaire d'ouverture du dialogue de nommage des feuilles.
        
        Ouvre la fenêtre modale Piker pour configurer le pattern de nommage
        des feuilles exportées.
        
        Args:
            sender: Le bouton qui a déclenché l'événement
            args: Arguments de l'événement (non utilisés)
        """
        try:
            from ...piker import open_modal
            
            # Ouvrir le dialogue modal
            open_modal(kind='sheet', title=u"Nommage des feuilles")
            
            # Rafraîchir l'affichage du bouton avec le nouveau pattern
            self.refresh_naming_buttons()
            
        except Exception as e:
            print('[info] Ouverture Piker (feuilles) échouée: {}'.format(e))
    
    def _on_open_set_naming(self, sender, args):
        """Gestionnaire d'ouverture du dialogue de nommage des carnets.
        
        Ouvre la fenêtre modale Piker pour configurer le pattern de nommage
        des carnets (sets de feuilles) exportés.
        
        Args:
            sender: Le bouton qui a déclenché l'événement
            args: Arguments de l'événement (non utilisés)
        """
        try:
            from ...piker import open_modal
            
            # Ouvrir le dialogue modal
            open_modal(kind='set', title=u"Nommage des carnets")
            
            # Rafraîchir l'affichage du bouton avec le nouveau pattern
            self.refresh_naming_buttons()
            
        except Exception as e:
            print('[info] Ouverture Piker (carnets) échouée: {}'.format(e))


__all__ = ['NamingHandlers']
