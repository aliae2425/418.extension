# -*- coding: utf-8 -*-
"""Fenêtre principale de l'application d'export.

Ce module définit la classe ExportMainWindow qui orchestre l'interface
utilisateur principale de l'extension. La fenêtre est construite à partir
du fichier XAML MainWindow.xaml et gère l'interaction utilisateur via
des gestionnaires d'événements délégués.

Architecture:
    - La fenêtre hérite de pyrevit.forms.WPFWindow
    - Les événements sont délégués à des classes Handler spécialisées
    - Les composants complexes (preview, progress) sont gérés par des classes dédiées
    - La validation est gérée par des classes Validator
"""

from pyrevit import forms
import os

try:
    from System.Windows import Visibility
except Exception:
    class _V:
        Visible = 0
        Collapsed = 2
    Visibility = _V()

try:
    from Autodesk.Revit.DB import FilteredElementCollector, ViewSheet
    REVIT_API_AVAILABLE = True
except Exception:
    REVIT_API_AVAILABLE = False

try:
    from System.Windows.Media import Brushes
except Exception:
    Brushes = None

# Imports locaux
from ...config import UserConfigStore
from ..helpers.xaml_loader import get_legacy_xaml_path

# Configuration globale
EXPORT_WINDOW_TITLE = u"418 • Exportation"


class ExportMainWindow(forms.WPFWindow):
    """Fenêtre principale de l'application d'export.
    
    Cette fenêtre gère:
        - La sélection des paramètres d'export (ComboBox)
        - La configuration de la destination
        - Le nommage des fichiers exportés
        - La prévisualisation des collections à exporter
        - Le lancement et le suivi de l'export
    
    Attributs:
        config (UserConfigStore): Store de configuration utilisateur
        _updating (bool): Flag pour éviter les boucles d'événements
        _prev_selection (dict): Sélections précédentes des ComboBox
        _dest_valid (bool): Indicateur de validité de la destination
        _preview_items (list): Items de prévisualisation des collections
    """
    
    def __init__(self):
        """Initialise la fenêtre principale."""
        # Chargement du XAML
        xaml_path = get_legacy_xaml_path('MainWindow.xaml')
        forms.WPFWindow.__init__(self, xaml_path)
        
        # Configuration du titre
        try:
            self.Title = EXPORT_WINDOW_TITLE
        except Exception:
            pass
        
        # Configuration
        self.config = UserConfigStore('batch_export')
        
        # État interne
        self._updating = False
        self._prev_selection = {}
        self._dest_valid = False
        self._preview_items = []
        
        # Initialisation de l'UI
        self._initialize_ui()
    
    def _initialize_ui(self):
        """Initialise tous les composants de l'interface.
        
        Cette méthode orchestre l'initialisation en appelant les fonctions
        d'initialisation de l'ancien module GUI.py. Dans les prochaines phases,
        ces appels seront remplacés par des composants dédiés.
        """
        # Import des fonctions de l'ancien GUI.py pour compatibilité temporaire
        from ...GUI import (
            _populate_sheet_param_combos,
            _apply_saved_selection,
            _check_and_warn_insufficient,
            _populate_sheet_sets,
            _update_export_button_state,
            _PARAM_COMBOS
        )
        
        # 1. Peupler les ComboBox des paramètres
        try:
            _populate_sheet_param_combos(self)
        except Exception as e:
            print('[info] Remplissage combos échoué: {}'.format(e))
        
        # 2. Appliquer les sélections sauvegardées
        try:
            _apply_saved_selection(self)
        except Exception as e:
            print('[info] Pré-sélection depuis config échouée: {}'.format(e))
        
        # 3. Vérifier et afficher avertissements si insuffisant
        try:
            _check_and_warn_insufficient(self)
        except Exception:
            pass
        
        # 4. Peupler le tableau récapitulatif
        try:
            _populate_sheet_sets(self)
        except Exception as e:
            print('[info] Récap jeux de feuilles échoué: {}'.format(e))
        
        # 5. Mettre à jour l'état du bouton Export
        try:
            _update_export_button_state(self)
        except Exception:
            pass
        
        # 6. Abonner les événements (temporairement via GUI.py)
        self._bind_events()
        
        # 7. Initialisation de la destination
        self._init_destination()
        
        # 8. Initialisation PDF/DWG
        self._init_pdf_dwg_controls()
        
        # 9. Rafraîchir les boutons de nommage
        self._refresh_naming_buttons()
        
        # 10. Snapshot des sélections
        try:
            from ...GUI import _get_selected_values
            self._prev_selection = _get_selected_values(self)
        except Exception:
            pass
    
    def _bind_events(self):
        """Abonne les gestionnaires d'événements aux contrôles.
        
        Cette méthode configure tous les événements (Click, SelectionChanged, etc.)
        en utilisant les handlers extraits dans des modules dédiés.
        """
        # Import des handlers
        from ..handlers import (
            ParameterHandlers,
            ExportHandlers,
            DestinationHandlers,
            NamingHandlers,
            GridHandlers
        )
        
        # Créer et bind les handlers
        self.parameter_handlers = ParameterHandlers(self)
        self.parameter_handlers.bind()
        
        self.export_handlers = ExportHandlers(self)
        self.export_handlers.bind()
        
        self.destination_handlers = DestinationHandlers(self)
        self.destination_handlers.bind()
        
        self.naming_handlers = NamingHandlers(self)
        self.naming_handlers.bind()
        
        self.grid_handlers = GridHandlers(self)
        self.grid_handlers.bind()
    
    def _init_destination(self):
        """Initialise les contrôles de destination."""
        # Utiliser le handler pour charger la destination
        if hasattr(self, 'destination_handlers'):
            self.destination_handlers.load_saved_destination()
        
        # Toggles destination
        self._init_destination_toggles()
    
    def _init_destination_toggles(self):
        """Initialise les toggles de destination (sous-dossiers, format)."""
        try:
            getv = lambda k, d=False: (self.config.get(k, '') == '1') if self.config else d
            setv = lambda k, v: self.config.set(k, '1' if v else '0') if self.config else None
            
            if hasattr(self, 'CreateSubfoldersCheck'):
                self.CreateSubfoldersCheck.IsChecked = getv('create_subfolders', False)
                self.CreateSubfoldersCheck.Checked += lambda s,a: setv('create_subfolders', True)
                self.CreateSubfoldersCheck.Unchecked += lambda s,a: setv('create_subfolders', False)
            
            if hasattr(self, 'SeparateByFormatCheck'):
                self.SeparateByFormatCheck.IsChecked = getv('separate_format_folders', False)
                self.SeparateByFormatCheck.Checked += lambda s,a: setv('separate_format_folders', True)
                self.SeparateByFormatCheck.Unchecked += lambda s,a: setv('separate_format_folders', False)
        except Exception:
            pass
    
    def _init_pdf_dwg_controls(self):
        """Initialise les contrôles PDF et DWG."""
        # Import temporaire de l'ancien module
        from ...GUI import ExportMainWindow as OldWindow
        
        # Réutiliser la méthode de l'ancienne classe
        try:
            # Appeler la méthode d'instance via le type
            OldWindow._init_pdf_dwg_controls(self)
        except Exception as e:
            print('[info] init PDF/DWG échouée:', e)
    
    def _refresh_naming_buttons(self):
        """Rafraîchit l'affichage des patterns de nommage sur les boutons."""
        # Utiliser le handler pour rafraîchir
        if hasattr(self, 'naming_handlers'):
            self.naming_handlers.refresh_naming_buttons()
    
    def _validate_destination(self, create=False):
        """Valide/Crée le dossier de destination."""
        from ...destination import ensure_directory, set_saved_destination
        
        path = ''
        try:
            path = self.PathTextBox.Text or ''
        except Exception:
            path = ''
        
        ok = False
        err = None
        if path:
            if create:
                ok, err = ensure_directory(path)
            else:
                try:
                    import os as _os
                    ok = _os.path.isdir(path)
                except Exception:
                    ok = False
        
        # Feedback visuel
        try:
            if ok:
                if Brushes is not None:
                    self.PathTextBox.BorderBrush = Brushes.Gray
                    self.PathTextBox.Background = Brushes.White
                self.PathTextBox.ToolTip = path
                set_saved_destination(path)
            else:
                if Brushes is not None:
                    self.PathTextBox.BorderBrush = Brushes.Red
                    self.PathTextBox.Background = Brushes.MistyRose if hasattr(Brushes, 'MistyRose') else self.PathTextBox.Background
                self.PathTextBox.ToolTip = err or u"Chemin invalide"
        except Exception:
            pass
        
        self._dest_valid = bool(ok)
        return self._dest_valid
    
    
    def _on_create_pdf_setup(self, sender, args):
        """Gestionnaire de création de setup PDF."""
        from ...GUI import ExportMainWindow as OldWindow
        OldWindow._on_create_pdf_setup(self, sender, args)
    
    def _on_create_dwg_setup(self, sender, args):
        """Gestionnaire de création de setup DWG."""
        from ...GUI import ExportMainWindow as OldWindow
        OldWindow._on_create_dwg_setup(self, sender, args)
    
    def _refresh_pdf_combo(self):
        """Rafraîchit la ComboBox des setups PDF."""
        from ...GUI import ExportMainWindow as OldWindow
        OldWindow._refresh_pdf_combo(self)
    
    def _refresh_dwg_combo(self):
        """Rafraîchit la ComboBox des setups DWG."""
        from ...GUI import ExportMainWindow as OldWindow
        OldWindow._refresh_dwg_combo(self)


def show():
    """Affiche la fenêtre principale de l'application.
    
    Cette fonction est le point d'entrée principal pour ouvrir l'interface.
    Elle crée une instance de ExportMainWindow et l'affiche en mode modal.
    
    Returns:
        bool: True si la fenêtre a été affichée avec succès, False sinon
    """
    try:
        win = ExportMainWindow()
        try:
            win.ShowDialog()
        except Exception:
            win.show()
        return True
    except Exception as e:
        print('[info] Erreur ouverture UI: {}'.format(e))
        return False


# Classe compatible avec l'ancienne API
class GUI:
    """Classe de compatibilité avec l'ancien code.
    
    Cette classe maintient l'API existante (GUI.show()) pour éviter
    de casser le code appelant (script.py).
    """
    
    @staticmethod
    def show():
        """Ouvre la fenêtre d'export.
        
        Returns:
            bool: True si affichée avec succès
        """
        return show()


__all__ = ['ExportMainWindow', 'show', 'GUI']
