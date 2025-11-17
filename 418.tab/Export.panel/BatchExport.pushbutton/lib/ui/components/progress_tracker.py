# -*- coding: utf-8 -*-
"""Composant de suivi de progression des exports.

Ce module gère la barre de progression et l'affichage des messages
de progression pendant l'export.
"""


class ProgressTracker:
    """Composant de suivi de progression.
    
    Ce composant gère:
        - La barre de progression (ProgressBar)
        - L'affichage des messages de progression
        - La mise à jour en temps réel pendant l'export
    
    Responsabilités:
        - Initialisation de la barre de progression
        - Mise à jour de la valeur et du maximum
        - Gestion des messages de statut
        - Réinitialisation après export
    
    Attributs:
        window: Instance de la fenêtre principale (ExportMainWindow)
    """
    
    def __init__(self, window):
        """Initialise le composant.
        
        Args:
            window: Instance de ExportMainWindow
        """
        self.window = window
        self._progress_bar = None
        self._status_text = None
        
        # Récupérer les contrôles
        try:
            self._progress_bar = getattr(self.window, 'ExportProgressBar', None)
        except Exception:
            pass
        
        try:
            self._status_text = getattr(self.window, 'ExportStatusText', None)
        except Exception:
            pass
    
    def reset(self):
        """Réinitialise la barre de progression à zéro."""
        if self._progress_bar is not None:
            try:
                self._progress_bar.Value = 0
                self._progress_bar.Maximum = 100
            except Exception:
                pass
    
    def set_range(self, minimum=0, maximum=100):
        """Définit la plage de valeurs de la barre de progression.
        
        Args:
            minimum (int): Valeur minimale (défaut: 0)
            maximum (int): Valeur maximale (défaut: 100)
        """
        if self._progress_bar is not None:
            try:
                self._progress_bar.Minimum = minimum
                self._progress_bar.Maximum = max(maximum, 1)
            except Exception:
                pass
    
    def set_value(self, value):
        """Définit la valeur actuelle de la barre de progression.
        
        Args:
            value (int): Valeur à afficher
        """
        if self._progress_bar is not None:
            try:
                self._progress_bar.Value = value
            except Exception:
                pass
    
    def update(self, current, total, message=None):
        """Met à jour la progression avec un message optionnel.
        
        Cette méthode est conçue pour être utilisée comme callback
        pendant l'export.
        
        Args:
            current (int): Valeur actuelle (index)
            total (int): Valeur totale
            message (str, optional): Message de progression à afficher
        
        Example:
            >>> tracker.update(5, 10, "Export de la collection 5/10")
        """
        # Mettre à jour la barre
        if self._progress_bar is not None:
            try:
                self._progress_bar.Maximum = max(total, 1)
                self._progress_bar.Value = current
            except Exception:
                pass
        
        # Afficher le message
        if message:
            self.set_status_message(message)
            print('[info]', message)
    
    def set_status_message(self, message):
        """Affiche un message de statut.
        
        Args:
            message (str): Message à afficher
        """
        if self._status_text is not None:
            try:
                self._status_text.Text = message
            except Exception:
                pass
    
    def complete(self, message=u"Export terminé"):
        """Marque l'export comme terminé.
        
        Args:
            message (str): Message de complétion (défaut: "Export terminé")
        """
        if self._progress_bar is not None:
            try:
                self._progress_bar.Value = self._progress_bar.Maximum
            except Exception:
                pass
        
        self.set_status_message(message)
    
    def error(self, message=u"Erreur lors de l'export"):
        """Marque l'export comme en erreur.
        
        Args:
            message (str): Message d'erreur
        """
        self.set_status_message(message)
    
    def get_callback(self):
        """Retourne une fonction callback compatible avec execute_exports.
        
        Returns:
            function: Callback de progression (current, total, message)
        
        Example:
            >>> progress_cb = tracker.get_callback()
            >>> execute_exports(doc, get_ctrl, progress_cb=progress_cb)
        """
        def callback(current, total, message=None):
            self.update(current, total, message)
        
        return callback


__all__ = ['ProgressTracker']
