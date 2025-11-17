# Architecture Complète de l'Application 418.extension

## 📐 Vue d'Ensemble de l'Architecture

Cette extension pyRevit suit une architecture **Model-View-ViewModel (MVVM)** adaptée pour WPF/IronPython, avec une séparation claire des responsabilités entre l'interface utilisateur, la logique métier et l'accès aux données Revit.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Couche Présentation                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ MainWindow   │  │  Piker       │  │ SetupEditor  │          │
│  │ (XAML/Python)│  │ (XAML/Python)│  │ (XAML/Python)│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                        Couche Logique Métier                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  UI Handlers │  │   Exporter   │  │  Validation  │          │
│  │  & Helpers   │  │   Manager    │  │  Manager     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                        Couche Données                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    Sheets    │  │    Naming    │  │ Destination  │          │
│  │   Manager    │  │   Manager    │  │   Manager    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                    Couche Configuration & Utilitaires            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ UserConfig   │  │  PDF/DWG     │  │   Revit API  │          │
│  │    Store     │  │  Exporters   │  │   Wrappers   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Structure des Dossiers Proposée

```
418.tab/Export.panel/BatchExport.pushbutton/
│
├── script.py                           # Point d'entrée principal
├── icon.png / icon.dark.png           # Icônes du bouton
│
├── GUI/                                # 🆕 XAML subdivisé
│   ├── Resources/                      # Ressources réutilisables
│   │   ├── Styles.xaml                # Styles globaux (bordures, boutons, etc.)
│   │   ├── Colors.xaml                # Palette de couleurs
│   │   └── Templates.xaml             # Templates de données réutilisables
│   │
│   ├── Views/                          # Fenêtres principales
│   │   ├── MainWindow.xaml            # Fenêtre principale restructurée
│   │   ├── Piker.xaml                 # Dialogue de sélection de paramètres
│   │   └── SetupEditor.xaml           # Éditeur de configuration PDF/DWG
│   │
│   └── Controls/                       # 🆕 Contrôles utilisateur réutilisables
│       ├── ParameterSelector.xaml     # Sélecteur de paramètres (ComboBox + Label)
│       ├── DestinationPicker.xaml     # Contrôle de sélection de destination
│       ├── NamingConfig.xaml          # Configuration du nommage
│       ├── CollectionPreview.xaml     # Grille de prévisualisation
│       └── ExportOptions.xaml         # Options d'export (PDF/DWG expandeurs)
│
└── lib/                                # Code Python
    ├── __init__.py                     # Exports principaux simplifiés
    │
    ├── ui/                             # 🔹 Interface Utilisateur
    │   ├── __init__.py                # Exports: MainWindow, DialogManager
    │   │
    │   ├── windows/                    # Fenêtres principales
    │   │   ├── __init__.py
    │   │   ├── main_window.py         # Classe ExportMainWindow (base)
    │   │   ├── piker_window.py        # Classe PikerWindow
    │   │   └── setup_editor_window.py # Classe SetupEditorWindow
    │   │
    │   ├── handlers/                   # Gestionnaires d'événements
    │   │   ├── __init__.py
    │   │   ├── parameter_handlers.py  # Événements ComboBox (paramètres)
    │   │   ├── export_handlers.py     # Événements bouton Export
    │   │   ├── destination_handlers.py # Événements destination/browse
    │   │   ├── naming_handlers.py     # Événements boutons nommage
    │   │   └── grid_handlers.py       # Événements DataGrid (preview)
    │   │
    │   ├── components/                 # Composants UI réutilisables
    │   │   ├── __init__.py
    │   │   ├── collection_preview.py  # Gestion du DataGrid de collections
    │   │   ├── progress_tracker.py    # Gestion de la barre de progression
    │   │   └── status_display.py      # Affichage des statuts et messages
    │   │
    │   ├── helpers/                    # Utilitaires UI
    │   │   ├── __init__.py
    │   │   ├── combo_helpers.py       # Remplissage et gestion des ComboBox
    │   │   ├── state_manager.py       # Gestion d'état (boutons, contrôles)
    │   │   └── xaml_loader.py         # Chargement et localisation XAML
    │   │
    │   └── validation/                 # Validation UI
    │       ├── __init__.py
    │       ├── parameter_validator.py # Validation des paramètres sélectionnés
    │       ├── destination_validator.py # Validation des chemins
    │       └── naming_validator.py    # Validation des patterns de nommage
    │
    ├── export/                         # 🔹 Logique d'Export
    │   ├── __init__.py                # Exports: ExportManager, PDFExporter, DWGExporter
    │   │
    │   ├── core/                       # Orchestration principale
    │   │   ├── __init__.py
    │   │   ├── export_manager.py      # Orchestrateur principal (execute_exports)
    │   │   ├── export_planner.py      # Planification des exports (ExportPlan)
    │   │   └── export_executor.py     # Exécution des plans d'export
    │   │
    │   ├── formats/                    # Exportateurs par format
    │   │   ├── __init__.py
    │   │   ├── pdf_exporter.py        # Logique export PDF
    │   │   ├── dwg_exporter.py        # Logique export DWG
    │   │   └── base_exporter.py       # Classe de base pour exportateurs
    │   │
    │   ├── options/                    # Configuration des options d'export
    │   │   ├── __init__.py
    │   │   ├── pdf_options.py         # Options et setups PDF
    │   │   ├── dwg_options.py         # Options et setups DWG
    │   │   └── options_builder.py     # Construction des options Revit
    │   │
    │   └── helpers/                    # Utilitaires d'export
    │       ├── __init__.py
    │       ├── path_builder.py        # Construction des chemins de fichiers
    │       ├── file_namer.py          # Génération des noms de fichiers
    │       └── revit_export_wrapper.py # Wrapper pour API Export Revit
    │
    ├── data/                           # 🔹 Gestion des Données
    │   ├── __init__.py                # Exports: SheetsManager, NamingManager
    │   │
    │   ├── sheets/                     # Gestion des feuilles Revit
    │   │   ├── __init__.py
    │   │   ├── sheet_collector.py     # Collection des feuilles
    │   │   ├── sheet_collection_manager.py # Gestion des jeux de feuilles
    │   │   ├── parameter_collector.py # Collection des paramètres
    │   │   └── sheet_filter.py        # Filtrage des feuilles
    │   │
    │   ├── naming/                     # Patterns de nommage
    │   │   ├── __init__.py
    │   │   ├── pattern_manager.py     # Gestion des patterns (save/load)
    │   │   ├── pattern_builder.py     # Construction de patterns
    │   │   ├── pattern_resolver.py    # Résolution des tokens {Param}
    │   │   └── token_parser.py        # Analyse des tokens
    │   │
    │   └── destination/                # Gestion des destinations
    │       ├── __init__.py
    │       ├── destination_manager.py # Gestion du dossier de destination
    │       ├── path_sanitizer.py      # Nettoyage des chemins/noms
    │       ├── folder_creator.py      # Création de dossiers
    │       └── path_resolver.py       # Résolution des chemins complets
    │
    ├── core/                           # 🔹 Configuration & Utilitaires
    │   ├── __init__.py
    │   ├── config.py                   # UserConfigStore (persistance)
    │   ├── constants.py                # Constantes globales
    │   └── exceptions.py               # Exceptions personnalisées
    │
    └── utils/                          # 🔹 Utilitaires généraux
        ├── __init__.py
        ├── revit_api_helpers.py        # Helpers pour API Revit
        ├── wpf_helpers.py              # Helpers pour WPF/IronPython
        └── logger.py                   # Logger simple pour debug
```

---

## 🎨 Subdivision des XAML

### Avant (Monolithique)
```
GUI/
├── MainWindow.xaml         (298 lignes)
├── Piker.xaml              (109 lignes)
└── SetupEditor.xaml        (117 lignes)
```

### Après (Modulaire)
```
GUI/
├── Resources/              # 🆕 Ressources partagées
│   ├── Styles.xaml        # Styles globaux réutilisables
│   ├── Colors.xaml        # Palette de couleurs
│   └── Templates.xaml     # DataTemplates partagés
│
├── Views/                  # Fenêtres principales (restructurées)
│   ├── MainWindow.xaml    # Structure principale uniquement (~150 lignes)
│   ├── Piker.xaml         # Dialogue simplifié (~80 lignes)
│   └── SetupEditor.xaml   # Dialogue simplifié (~90 lignes)
│
└── Controls/               # 🆕 Contrôles utilisateur réutilisables
    ├── ParameterSelector.xaml      # Sélecteur de paramètre
    ├── DestinationPicker.xaml      # Sélection destination
    ├── NamingConfig.xaml           # Configuration nommage
    ├── CollectionPreview.xaml      # DataGrid de preview
    └── ExportOptions.xaml          # Options PDF/DWG
```

### Bénéfices de la Subdivision XAML

1. **Réutilisabilité**
   - Contrôles utilisateur (`UserControl`) réutilisables dans plusieurs fenêtres
   - Styles et templates centralisés dans `Resources/`
   
2. **Maintenabilité**
   - Modifications isolées par composant
   - Fichiers plus courts et focalisés
   
3. **Testabilité**
   - Chaque contrôle testable indépendamment
   - Prévisualisation en design-time facilitée

4. **Séparation des préoccupations**
   - `Views/` = structure de fenêtre
   - `Controls/` = composants métier réutilisables
   - `Resources/` = apparence et style

---

## 🏗️ Principes d'Architecture

### 1. Séparation des Responsabilités (SoC)

Chaque module a une responsabilité unique et bien définie:

- **ui/** → Interface utilisateur et interaction
- **export/** → Logique d'export vers PDF/DWG
- **data/** → Accès et manipulation des données Revit
- **core/** → Configuration et utilitaires transverses

### 2. Injection de Dépendances

```python
# Exemple: Le gestionnaire d'export reçoit ses dépendances
class ExportManager:
    def __init__(self, pdf_exporter, dwg_exporter, path_builder, logger):
        self.pdf_exporter = pdf_exporter
        self.dwg_exporter = dwg_exporter
        self.path_builder = path_builder
        self.logger = logger
```

### 3. Classes au lieu de Modules Fonctionnels

**Avant:**
```python
# destination.py - fonctions isolées
def get_saved_destination():
    ...
def set_saved_destination(path):
    ...
def ensure_directory(path):
    ...
```

**Après:**
```python
# destination_manager.py - classe cohérente
class DestinationManager:
    """Gestionnaire de destination d'export."""
    
    def __init__(self, config_store):
        self.config = config_store
    
    def get_saved_destination(self):
        """Retourne le dossier de destination enregistré."""
        ...
    
    def set_saved_destination(self, path):
        """Enregistre le dossier de destination."""
        ...
    
    def ensure_directory(self, path):
        """Crée le dossier s'il n'existe pas."""
        ...
```

### 4. Imports Simplifiés via `__init__.py`

**Avant:**
```python
from lib.GUI import GUI
from lib.destination import get_saved_destination, ensure_directory
from lib.naming import load_pattern, save_pattern
from lib.exporter import execute_exports
```

**Après:**
```python
from lib.ui import MainWindow
from lib.data import DestinationManager, NamingManager
from lib.export import ExportManager
```

### 5. Documentation en Français

Tous les modules, classes et fonctions sont documentés en français avec:
- Description de la responsabilité
- Paramètres d'entrée
- Valeurs de retour
- Exemples d'usage (si pertinent)

```python
class ExportManager:
    """Gestionnaire principal des exports PDF et DWG.
    
    Responsabilités:
        - Planification des exports par collection
        - Orchestration des exportateurs de format
        - Gestion de la progression et des callbacks UI
        - Gestion des erreurs d'export
    
    Attributs:
        pdf_exporter (PDFExporter): Exportateur PDF
        dwg_exporter (DWGExporter): Exportateur DWG
        config (UserConfigStore): Configuration utilisateur
    """
    
    def execute_exports(self, doc, export_plan, callbacks=None):
        """Exécute les exports selon le plan défini.
        
        Args:
            doc (Document): Document Revit actif
            export_plan (ExportPlan): Plan d'export à exécuter
            callbacks (dict, optional): Callbacks pour progression/log
                - progress_cb: function(current, total, message)
                - log_cb: function(message)
                - status_cb: function(kind, payload)
        
        Returns:
            bool: True si l'export a réussi, False sinon
        
        Raises:
            ExportException: Si une erreur critique survient
        """
        ...
```

---

## 🔄 Flux de Données

### Démarrage de l'Application

```
script.py
    ↓
MainWindow.__init__()
    ↓
┌─────────────────────────────────────┐
│ Initialisation des composants       │
├─────────────────────────────────────┤
│ 1. Chargement XAML                  │
│ 2. Initialisation des managers      │
│    - DestinationManager             │
│    - NamingManager                  │
│    - SheetsManager                  │
│ 3. Population des contrôles         │
│    - ComboBox paramètres            │
│    - Configuration sauvegardée      │
│ 4. Abonnement aux événements        │
│ 5. Validation initiale              │
└─────────────────────────────────────┘
    ↓
Affichage de la fenêtre (ShowDialog)
```

### Exécution d'un Export

```
User clique "Exporter"
    ↓
ExportHandlers._on_export_clicked()
    ↓
ParameterValidator.validate_selections()
    ↓ (si valide)
ExportPlanner.build_export_plan(doc, selections)
    ↓
ExportManager.execute_exports(doc, plan, callbacks)
    ↓
┌──────────────────────────────────┐
│ Pour chaque collection du plan   │
├──────────────────────────────────┤
│ 1. Callback: status = 'progress'│
│ 2. Récupération des feuilles    │
│ 3. Génération des noms          │
│ 4. Export PDF (si activé)       │
│    - PDFExporter.export_*()     │
│ 5. Export DWG (si activé)       │
│    - DWGExporter.export_*()     │
│ 6. Callback: status = 'ok'      │
└──────────────────────────────────┘
    ↓
Callback: progress = 100%
```

---

## 📝 Exemples de Code Refactorisé

### Exemple 1: DestinationManager (Classe)

```python
# lib/data/destination/destination_manager.py
# -*- coding: utf-8 -*-
"""Gestionnaire de destination d'export.

Ce module centralise la gestion du dossier de destination pour les exports.
"""

import os
from ...core.config import UserConfigStore


class DestinationManager:
    """Gestionnaire du dossier de destination des exports.
    
    Responsabilités:
        - Chargement/sauvegarde du dossier de destination
        - Validation et création de dossiers
        - Construction de chemins avec sous-dossiers
    """
    
    DEST_FOLDER_KEY = 'PathDossier'
    
    def __init__(self, config_store=None):
        """Initialise le gestionnaire.
        
        Args:
            config_store (UserConfigStore, optional): Store de configuration.
                Si None, un nouveau store est créé.
        """
        self.config = config_store or UserConfigStore('batch_export')
    
    def get_saved_destination(self, default=None):
        """Retourne le dossier de destination enregistré.
        
        Args:
            default (str, optional): Valeur par défaut si aucune config.
        
        Returns:
            str: Chemin du dossier de destination
        """
        path = self.config.get(self.DEST_FOLDER_KEY, '') or ''
        if path:
            return path
        if default:
            return default
        # Fallback: Documents/Exports
        return self._get_default_destination()
    
    def set_saved_destination(self, path):
        """Enregistre le dossier de destination.
        
        Args:
            path (str): Chemin à enregistrer
        
        Returns:
            bool: True si la sauvegarde a réussi
        """
        return bool(self.config.set(self.DEST_FOLDER_KEY, path or ''))
    
    def ensure_directory(self, path):
        """Crée le dossier s'il n'existe pas.
        
        Args:
            path (str): Chemin du dossier
        
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            if not path:
                return False, 'Chemin vide'
            if not os.path.exists(path):
                os.makedirs(path)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def build_destination_path(self, format_name=None, collection_name=None):
        """Construit le chemin de destination avec sous-dossiers optionnels.
        
        Args:
            format_name (str, optional): Nom du format (PDF, DWG)
            collection_name (str, optional): Nom de la collection
        
        Returns:
            str: Chemin complet de destination
        """
        base = self.get_saved_destination()
        
        # Sous-dossiers par collection ?
        if self.config.get('create_subfolders', '') == '1' and collection_name:
            base = os.path.join(base, collection_name)
        
        # Dossiers séparés par format ?
        if self.config.get('separate_format_folders', '') == '1' and format_name:
            base = os.path.join(base, format_name)
        
        self.ensure_directory(base)
        return base
    
    def _get_default_destination(self):
        """Retourne le chemin de destination par défaut."""
        try:
            home = os.path.expanduser('~')
            docs = os.path.join(home, 'Documents')
            return os.path.join(docs, 'Exports')
        except Exception:
            return os.getcwd()
```

### Exemple 2: MainWindow (Structure)

```python
# lib/ui/windows/main_window.py
# -*- coding: utf-8 -*-
"""Fenêtre principale de l'application d'export.

Ce module définit la classe ExportMainWindow qui orchestre l'interface
utilisateur principale de l'extension.
"""

from pyrevit import forms
from ...core.config import UserConfigStore
from ...data import DestinationManager, NamingManager, SheetsManager
from ..handlers import (
    ParameterHandlers,
    ExportHandlers,
    DestinationHandlers,
    NamingHandlers,
    GridHandlers
)
from ..components import CollectionPreview, ProgressTracker
from ..helpers import ComboHelpers, StateManager, XamlLoader
from ..validation import ParameterValidator, DestinationValidator


class ExportMainWindow(forms.WPFWindow):
    """Fenêtre principale de l'application d'export.
    
    Cette fenêtre gère:
        - La sélection des paramètres d'export
        - La configuration de la destination
        - Le nommage des fichiers
        - La prévisualisation des collections
        - Le lancement de l'export
    
    Architecture:
        - Utilise des gestionnaires (handlers) pour les événements
        - Utilise des composants pour les parties complexes (preview, progress)
        - Utilise des validateurs pour maintenir l'état cohérent
    """
    
    WINDOW_TITLE = u"418 • Exportation"
    
    def __init__(self):
        """Initialise la fenêtre principale."""
        # Chargement XAML
        xaml_path = XamlLoader.get_xaml_path('Views/MainWindow.xaml')
        forms.WPFWindow.__init__(self, xaml_path)
        
        # Configuration
        self.config = UserConfigStore('batch_export')
        
        # Managers de données
        self.destination_manager = DestinationManager(self.config)
        self.naming_manager = NamingManager(self.config)
        self.sheets_manager = SheetsManager()
        
        # Composants UI
        self.preview = CollectionPreview(self)
        self.progress = ProgressTracker(self)
        
        # Gestionnaires d'événements
        self.parameter_handlers = ParameterHandlers(self)
        self.export_handlers = ExportHandlers(self)
        self.destination_handlers = DestinationHandlers(self)
        self.naming_handlers = NamingHandlers(self)
        self.grid_handlers = GridHandlers(self)
        
        # Validateurs
        self.param_validator = ParameterValidator(self)
        self.dest_validator = DestinationValidator(self)
        
        # État interne
        self._updating = False
        self._dest_valid = False
        
        # Initialisation
        self._initialize_ui()
        self._bind_events()
        self._load_saved_state()
        self._update_state()
    
    def _initialize_ui(self):
        """Initialise les contrôles de l'interface."""
        self.Title = self.WINDOW_TITLE
        ComboHelpers.populate_parameter_combos(self)
        self.preview.populate()
    
    def _bind_events(self):
        """Abonne les gestionnaires d'événements aux contrôles."""
        self.parameter_handlers.bind()
        self.export_handlers.bind()
        self.destination_handlers.bind()
        self.naming_handlers.bind()
        self.grid_handlers.bind()
    
    def _load_saved_state(self):
        """Charge l'état sauvegardé depuis la configuration."""
        ComboHelpers.apply_saved_selections(self)
        self.destination_handlers.load_saved_destination()
        self.naming_handlers.refresh_naming_buttons()
    
    def _update_state(self):
        """Met à jour l'état de tous les contrôles."""
        self.param_validator.check_and_warn()
        StateManager.update_export_button_state(self)
```

### Exemple 3: Imports Simplifiés

```python
# lib/__init__.py
"""Extension 418 - Export des jeux de feuilles Revit.

Ce package fournit une interface pour exporter les jeux de feuilles
Revit en PDF et DWG avec nommage personnalisable.
"""

# Exports principaux pour un usage simple
from .ui import MainWindow
from .export import ExportManager
from .data import DestinationManager, NamingManager, SheetsManager

__version__ = '0.5.0'
__all__ = [
    'MainWindow',
    'ExportManager',
    'DestinationManager',
    'NamingManager',
    'SheetsManager',
]
```

```python
# lib/ui/__init__.py
"""Module interface utilisateur."""

from .windows.main_window import ExportMainWindow as MainWindow
from .windows.piker_window import PikerWindow
from .windows.setup_editor_window import SetupEditorWindow

__all__ = ['MainWindow', 'PikerWindow', 'SetupEditorWindow']
```

```python
# script.py (point d'entrée simplifié)
# -*- coding: utf-8 -*-
"""Point d'entrée de l'extension d'export."""

__title__ = "Exportation"
__doc__ = """Export les feuilles par jeu avec configuration avancée."""
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from lib.ui import MainWindow

if __name__ == "__main__":
    if not MainWindow.show():
        print('[erreur] UI non affichée')
```

---

## 🎯 Bénéfices de l'Architecture

### Maintenabilité ⚙️
- Fichiers courts et focalisés (~150-300 lignes max)
- Responsabilités clairement définies
- Modifications isolées sans effet de bord

### Lisibilité 📖
- Structure logique par domaine fonctionnel
- Documentation en français complète
- Nommage explicite et cohérent

### Réutilisabilité ♻️
- Composants UI et classes métier réutilisables
- Styles et templates XAML centralisés
- Managers de données indépendants

### Testabilité 🧪
- Injection de dépendances facilitant les tests
- Composants isolés testables unitairement
- Séparation UI/logique permettant tests sans Revit

### Évolutivité 📈
- Ajout de nouvelles fonctionnalités facilité
- Architecture extensible (nouveaux formats, options, etc.)
- Migration progressive sans réécriture complète

### Collaboration 👥
- Zones de travail claires (moins de conflits git)
- Onboarding facilité par structure claire
- Revues de code simplifiées

---

## 📋 Plan de Migration

### Phase 1: Préparation (1-2h)
- [ ] Créer la structure de dossiers
- [ ] Créer les `__init__.py` vides
- [ ] Créer ARCHITECTURE.md (ce document)

### Phase 2: XAML (2-3h)
- [ ] Extraire les styles vers `Resources/Styles.xaml`
- [ ] Extraire les couleurs vers `Resources/Colors.xaml`
- [ ] Extraire les templates vers `Resources/Templates.xaml`
- [ ] Créer les UserControls dans `Controls/`
- [ ] Restructurer les Views pour utiliser les contrôles

### Phase 3: Python - Données (2-3h)
- [ ] Migrer et refactoriser `sheets.py` → `data/sheets/`
- [ ] Migrer et refactoriser `naming.py` → `data/naming/`
- [ ] Migrer et refactoriser `destination.py` → `data/destination/`
- [ ] Créer les classes managers avec documentation

### Phase 4: Python - Export (2-3h)
- [ ] Subdiviser `exporter.py` → `export/core/`, `export/formats/`
- [ ] Migrer `pdf_export.py` → `export/options/pdf_options.py`
- [ ] Migrer `dwg_export.py` → `export/options/dwg_options.py`
- [ ] Créer les helpers d'export

### Phase 5: Python - UI (3-4h)
- [ ] Subdiviser `GUI.py` → `ui/windows/`, `ui/handlers/`, etc.
- [ ] Créer les classes de gestionnaires d'événements
- [ ] Créer les composants (preview, progress)
- [ ] Créer les helpers et validateurs

### Phase 6: Dialogues (1-2h)
- [ ] Migrer `piker.py` → `dialogs/piker_window.py`
- [ ] Migrer `setup_editor.py` → `dialogs/setup_editor_window.py`
- [ ] Adapter pour nouvelle structure

### Phase 7: Finalisation (1-2h)
- [ ] Mettre à jour `script.py` avec nouveaux imports
- [ ] Compléter tous les `__init__.py`
- [ ] Ajouter documentation française complète
- [ ] Tests manuels de toutes les fonctionnalités

### Phase 8: Tests & Validation (2h)
- [ ] Test: Ouverture de l'interface
- [ ] Test: Sélection de paramètres
- [ ] Test: Configuration destination
- [ ] Test: Configuration nommage
- [ ] Test: Prévisualisation
- [ ] Test: Export PDF
- [ ] Test: Export DWG
- [ ] Test: Persistance configuration

**Temps estimé total: 14-20 heures**

---

## 🔍 Points d'Attention

### Compatibilité
- IronPython 2.7 (limitations Python 2)
- API Revit multi-versions (2022-2026+)
- WPF/XAML avec pyRevit

### Performance
- Chargement XAML initial
- Collection des feuilles Revit (peut être lent)
- Export de gros volumes (gestion asynchrone)

### Maintenance
- Documentation à jour
- Tests après modifications API Revit
- Gestion des configurations legacy

---

## 📚 Ressources & Références

- **pyRevit Documentation**: https://pyrevitlabs.notion.site/pyRevit-bd907d6292ed4ce997c46e84b6ef67a0
- **Revit API Documentation**: https://www.revitapidocs.com/
- **WPF/XAML**: Microsoft Documentation
- **MVVM Pattern**: https://learn.microsoft.com/fr-fr/dotnet/architecture/maui/mvvm

---

*Document créé le: 2025-11-17*  
*Version: 1.0*  
*Auteur: @copilot*
