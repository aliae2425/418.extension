# Architecture Technique - 418 Extension

## Vue d'ensemble

L'extension 418 suit une architecture modulaire en couches, séparant clairement les responsabilités entre l'interface utilisateur, la logique métier, et l'accès aux données.

## Principes architecturaux

### 1. Séparation des responsabilités
- **UI Layer**: Interfaces XAML et contrôleurs WPF
- **Service Layer**: Orchestration et logique métier
- **Data Layer**: Gestion de la persistance et des repositories
- **Core Layer**: Configuration et utilitaires partagés

### 2. Pattern MVC adapté
- **Model**: Classes de données dans `lib/data/`
- **View**: Fichiers XAML dans `GUI/`
- **Controller**: Contrôleurs dans `lib/ui/windows/` et `lib/ui/handlers/`

### 3. Injection de dépendances manuelle
Les contrôleurs instancient et injectent leurs dépendances pour faciliter les tests et la maintenance.

## Structure détaillée

### Core (`lib/core/`)

#### AppPaths.py
**Responsabilité**: Gestion centralisée des chemins de fichiers

```python
class AppPaths:
    - main_xaml() -> str          # Chemin vers la fenêtre principale
    - resources_dir() -> str       # Dossier des ressources XAML
    - controls_dir() -> str        # Dossier des contrôles XAML
```

**Usage**:
- Résolution des chemins relatifs depuis le script
- Accès unifié aux ressources UI
- Indépendant du répertoire d'exécution

#### UserConfig.py
**Responsabilité**: Interface unifiée avec la configuration pyRevit

```python
class UserConfig:
    - get(key, default) -> str           # Lecture valeur
    - set(key, value) -> bool            # Écriture valeur
    - get_list(key, default) -> list     # Lecture liste CSV
```

**Implémentation**:
- Utilise `pyrevit.userconfig` en backend
- Namespace: `batch_export`
- Persistance automatique via pyRevit
- Gestion d'erreurs robuste

**Données stockées**:
- Paramètres sélectionnés (ExportationCombo, CarnetCombo, DWGCombo)
- Chemin de destination
- Options de dossiers (create_subfolders, separate_format_folders)
- Configurations PDF/DWG

### Data Layer (`lib/data/`)

#### Destination (`data/destination/`)

**DestinationStore.py**
```python
class DestinationStore:
    - get() -> str                           # Récupère le chemin sauvegardé
    - set(path) -> bool                      # Sauvegarde le chemin
    - ensure(path) -> bool                   # Crée le dossier si nécessaire
    - validate(path) -> (bool, str)          # Valide le chemin
    - choose_destination_explorer() -> str   # Dialogue de sélection
    - sanitize(name) -> str                  # Nettoie les noms de fichiers
    - unique_path(base) -> str               # Génère un chemin unique
```

**Fonctionnalités**:
- Validation de chemins Windows
- Création récursive de dossiers
- Génération de noms uniques (suffixes numériques)
- Sanitization des caractères interdits

#### Naming (`data/naming/`)

**NamingPatternStore.py**
```python
class NamingPatternStore:
    - load(kind) -> (str, list)              # Charge pattern + rows
    - save(kind, pattern, rows) -> bool      # Sauvegarde configuration
```

**Format des rows**:
```python
[
    {'Name': 'SheetNumber', 'Prefix': '', 'Suffix': '_'},
    {'Name': 'SheetName', 'Prefix': '', 'Suffix': ''}
]
```

**NamingResolver.py**
```python
class NamingResolver:
    def __init__(self, doc):
        # Initialise avec le document Revit pour accéder aux paramètres
    
    - resolve_for_element(elem, rows, empty_fallback) -> str
        # Résout le pattern pour un élément donné
    
    - build_pattern(rows) -> str
        # Construit un pattern d'affichage depuis les rows
    
    - _get_param_value(elem, param_name) -> str
        # Récupère la valeur d'un paramètre (élément ou projet)
    
    - _get_project_param_value(param_name) -> str
        # Récupère un paramètre du projet (ProjectInformation)
```

**Fonctionnalités avancées**:
- Cache des paramètres projet pour optimisation
- Fallback vers paramètres projet si non trouvé sur l'élément
- Support des préfixes et suffixes
- Gestion des paramètres vides
- Résolution hiérarchique: élément → projet

**Exemple de résolution**:
```python
rows = [
    {'Name': 'Project Name', 'Prefix': '', 'Suffix': '_'},
    {'Name': 'SheetNumber', 'Prefix': '', 'Suffix': '_'},
    {'Name': 'SheetName', 'Prefix': '', 'Suffix': ''}
]

# Résultat: "MonProjet_A101_PlanRDC"
# Où "MonProjet" vient des paramètres projet
```

#### Sheets (`data/sheets/`)

**SheetParameterRepository.py**
```python
class SheetParameterRepository:
    - collect_for_collections(doc) -> list    # Liste paramètres disponibles
    - get_saved_selections() -> dict          # Récupère sélections sauvegardées
    - save_selections(selections) -> bool     # Sauvegarde sélections
```

**SheetSetRepository.py**
```python
class SheetSetRepository:
    - get_all(doc) -> list                    # Récupère tous les jeux
    - get_sheets(doc, collection) -> list     # Feuilles d'un jeu
    - read_param_flag(elem, name) -> bool     # Lit un paramètre booléen
```

### Services Layer (`lib/services/`)

#### Core Services (`services/core/`)

**ExportOrchestrator.py**
```python
class ExportOrchestrator:
    def __init__(self, namespace='batch_export'):
        # Initialise tous les services nécessaires
    
    - plan_exports_for_collections(doc, get_ctrl) -> list[ExportPlan]
        # Analyse les jeux et planifie les exports
    
    - run(doc, get_ctrl, progress_cb, log_cb, ui_win) -> bool
        # Exécute le processus d'export complet
    
    # Méthodes privées
    - _get_destination_base(fmt_subfolder, collection_name) -> str
    - _get_pdf_options(doc) -> PDFExportOptions
    - _get_dwg_options(doc) -> DWGExportOptions
    - _export_pdf_sheet(doc, sheet, rows, base_folder, options, separate)
    - _export_dwg_sheet(doc, sheet, rows, base_folder, options)
    - _export_pdf_collection(doc, sheets, rows, base_folder, options)
```

**ExportPlan** (namedtuple):
```python
ExportPlan(
    collection_name: str,    # Nom du jeu de feuilles
    do_export: bool,        # Exporter ce jeu?
    per_sheet: bool,        # Feuilles séparées?
    do_dwg: bool,          # Exporter en DWG?
    do_pdf: bool           # Exporter en PDF?
)
```

**Flux d'exécution**:
1. **Planification**: Analyse des paramètres des jeux de feuilles
2. **Validation**: Vérification des chemins et options
3. **Résolution**: Calcul des noms de fichiers
4. **Export**: Exécution PDF/DWG avec gestion d'erreurs
5. **Reporting**: Mise à jour UI et logs

#### Format Services (`services/formats/`)

**PdfExporterService.py**
```python
class PdfExporterService:
    - build_options(doc, setup_name) -> PDFExportOptions
        # Construit les options depuis une configuration
    
    - get_saved_setup() -> str
        # Récupère la configuration sauvegardée
    
    - get_separate(default) -> bool
        # Mode export séparé activé?
    
    - list_setups(doc) -> list
        # Liste toutes les configurations disponibles
```

**DwgExporterService.py**
```python
class DwgExporterService:
    - build_options(doc, setup_name) -> DWGExportOptions
        # Construit les options DWG
    
    - get_saved_setup() -> str
    - get_separate(default) -> bool
    - list_setups(doc) -> list
```

**Gestion des exports**:
- Utilisation des API natives Revit (`doc.Export()`)
- Fallback vers `PrintManager` pour PDF si nécessaire
- Gestion des fichiers temporaires pour DWG
- Nommage unique avec collision handling

### UI Layer (`lib/ui/`)

#### Windows (`ui/windows/`)

**MainWindowController.py**
**Responsabilité**: Contrôleur principal de l'application

```python
class MainWindowController:
    def __init__(self):
        # Initialise tous les composants et services
    
    - initialize() -> None
        # Configure l'UI complète
    
    - show() -> bool
        # Affiche la fenêtre modale
    
    # Méthodes privées
    - _merge_and_bind()              # Charge XAML et templates
    - _load_param_combos()           # Remplit les dropdowns
    - _update_export_button_state()  # Active/désactive export
    - _wire_[*]_events()            # Branche les événements
```

**Cycle de vie**:
1. Construction des dépendances
2. Chargement des ressources XAML
3. Binding des templates WPF
4. Population des contrôles
5. Branchement des événements
6. Affichage modal

**PikerWindow.py & PikerWindowController.py**
Fenêtre modale pour la configuration du nommage avec prévisualisation en direct.

**SetupEditorWindow.py & SetupEditorWindowController.py**
Éditeur de configurations d'export PDF/DWG.

#### Components (`ui/components/`)

**Rôle**: Encapsulation de la logique UI par zone fonctionnelle

**ParameterSelectorComponent.py**
```python
class ParameterSelectorComponent:
    - populate(window) -> None           # Remplit les ComboBox
    - validate_unique() -> bool          # Vérifie l'unicité
```

**DestinationPickerComponent.py**
```python
class DestinationPickerComponent:
    - init_controls(window) -> None      # Initialise l'UI
    - validate(window, create) -> (bool, str)
    - browse_folder(window) -> None      # Ouvre l'explorateur
```

**ExportOptionsComponent.py**
```python
class ExportOptionsComponent:
    - populate_pdf(window) -> None       # Remplit options PDF
    - populate_dwg(window) -> None       # Remplit options DWG
    - save_selections(window) -> None    # Sauvegarde choix
```

**NamingConfigComponent.py**
```python
class NamingConfigComponent:
    - refresh_buttons(window) -> None    # Met à jour labels
    - open_editor(kind) -> bool         # Ouvre éditeur modal
```

**CollectionPreviewComponent.py**
```python
class CollectionPreviewComponent:
    - populate(window, selections) -> None
        # Remplit la grille de prévisualisation
    
    - set_collection_status(window, name, status) -> None
        # Met à jour le statut d'un jeu
    
    - set_detail_status(window, coll, sheet, fmt, status) -> None
        # Met à jour le statut d'une feuille
    
    - refresh_grid(window) -> None
        # Force le rafraîchissement visuel
```

**États de statut**:
- `pending`: En attente
- `progress`: En cours
- `ok`: Réussi
- `error`: Échec

#### Handlers (`ui/handlers/`)

**Rôle**: Gestionnaires d'événements spécialisés

- **DestinationHandlers.py**: Événements de sélection de dossier
- **ExportHandlers.py**: Logique de déclenchement d'export
- **GridHandlers.py**: Interactions avec la grille de prévisualisation
- **NamingHandlers.py**: Édition des patterns de nommage

#### Helpers (`ui/helpers/`)

**UIResourceLoader.py**
```python
class UIResourceLoader:
    - merge_all() -> bool                # Charge toutes les ressources
    - _merge_file(path) -> bool          # Charge un fichier XAML
```

**Charge**:
- `Colors.xaml`: Palette de couleurs
- `Styles.xaml`: Styles WPF
- `Templates.xaml`: Templates de contrôles

**UITemplateBinder.py**
```python
class UITemplateBinder:
    - bind(hosts_map) -> None            # Lie les templates aux hosts
```

**Principe**: Utilise `ContentControl` et `ContentTemplate` pour injecter des sous-arbres XAML dans des conteneurs hôtes.

### Utils (`lib/utils/`)

**FileSystem.py**
- Opérations sur les fichiers et dossiers
- Gestion des chemins Windows
- Utilitaires de nommage

**RevitApi.py**
- Wrappers autour de l'API Revit
- Helpers pour les opérations courantes
- Gestion des transactions

**Text.py**
- Manipulation de chaînes
- Sanitization de noms
- Formatage de texte

## Flux de données

### 1. Chargement initial

```
script.py
    ↓
MainWindowController.__init__()
    ↓
    ├─ AppPaths (chemins)
    ├─ UserConfig (configuration)
    ├─ Repositories (données)
    ├─ Services (logique)
    └─ Components (UI)
    ↓
initialize()
    ↓
    ├─ _merge_and_bind() → Charge XAML
    ├─ _load_param_combos() → Remplit UI
    ├─ _init_destination() → Configure dossier
    ├─ _init_pdf_dwg() → Configure export
    └─ _wire_*_events() → Branche événements
    ↓
show() → Fenêtre affichée
```

### 2. Configuration de l'export

```
Utilisateur sélectionne paramètres
    ↓
_on_param_changed()
    ↓
    ├─ UserConfig.set() → Sauvegarde
    ├─ _check_and_warn_insufficient() → Validation
    ├─ _update_export_button_state() → UI update
    └─ CollectionPreviewComponent.populate() → Grille
```

### 3. Exécution de l'export

```
Utilisateur clique "Exporter"
    ↓
_on_export()
    ↓
ExportOrchestrator.run()
    ↓
    ├─ plan_exports_for_collections() → ExportPlan[]
    │   ↓
    │   ├─ _collect_collections() → Récupère jeux
    │   ├─ _read_flag_from_param() → Lit paramètres
    │   └─ Retourne liste de plans
    ↓
    ├─ _get_pdf_options() → Options PDF
    ├─ _get_dwg_options() → Options DWG
    ├─ _get_destination_base() → Chemins
    ↓
    └─ Pour chaque plan:
        ↓
        ├─ _get_collection_sheets() → Liste feuilles
        ├─ _get_rows_for_sheet() → Pattern nommage
        ├─ NamingResolver.resolve_for_element() → Nom
        ↓
        ├─ Si per_sheet:
        │   └─ _export_pdf_sheet() / _export_dwg_sheet()
        │       ↓
        │       ├─ _unique_with_ext() → Chemin unique
        │       ├─ doc.Export() → API Revit
        │       └─ CollectionPreviewComponent.set_detail_status()
        │
        └─ Si carnet:
            └─ _export_pdf_collection()
                ↓
                ├─ options.Combine = True
                ├─ doc.Export(views) → Multi-feuilles
                └─ CollectionPreviewComponent.set_collection_status()
```

## Patterns de conception utilisés

### 1. Repository Pattern
Les classes `*Repository` encapsulent l'accès aux données Revit et à la configuration.

### 2. Service Layer Pattern
Les classes `*Service` encapsulent la logique métier complexe.

### 3. Component Pattern (UI)
Les `*Component` encapsulent des zones UI réutilisables.

### 4. Observer Pattern
Les événements WPF permettent la communication UI ↔ logique.

### 5. Strategy Pattern
Les services d'export utilisent différentes stratégies selon le format.

## Gestion d'erreurs

### Principe général
```python
try:
    # Opération risquée
except Exception:
    # Fallback ou valeur par défaut
    pass
```

### Zones critiques
1. **Accès API Revit**: Toujours dans try/except (IronPython)
2. **IO Fichiers**: Vérification d'existence avant accès
3. **Parsing XAML**: Fallback sur valeurs par défaut
4. **Configuration utilisateur**: Valeurs par défaut si absentes

### Logging
- Utilise `print()` pour les messages (capturés par pyRevit)
- Préfixes: `[info]`, `[warning]`, `[PDF]`, `[DWG]`
- Pas de logging fichier (contraintes IronPython)

## Performance

### Optimisations implémentées
1. **Cache paramètres projet**: Évite récupération répétée
2. **Lazy loading UI**: Chargement progressif des composants
3. **Batch operations**: Traitement par lots si possible
4. **Éviter les transactions inutiles**: Lecture seule autant que possible

### Limitations connues
1. **IronPython 2.7**: Pas de multithreading réel
2. **API Revit**: Export séquentiel obligatoire
3. **WPF rendering**: UI thread bloqué pendant export

## Extensibilité

### Ajout d'un nouveau format d'export

1. Créer `lib/services/formats/XxxExporterService.py`
2. Implémenter `build_options()`, `list_setups()`
3. Ajouter méthodes dans `ExportOrchestrator`
4. Étendre UI dans `ExportOptionsComponent`

### Ajout d'un nouveau type de nommage

1. Ajouter kind dans `NamingPatternStore`
2. Créer interface dans `PikerWindow`
3. Utiliser `NamingResolver` pour résolution

### Ajout d'une nouvelle fenêtre

1. Créer XAML dans `GUI/Views/` ou `GUI/Modals/`
2. Créer `*Window.py` et `*WindowController.py`
3. Charger ressources via `UIResourceLoader`
4. Ouvrir avec `ShowDialog()` ou `show()`

## Tests et validation

### Tests manuels recommandés
1. Export PDF seul
2. Export DWG seul
3. Export combiné PDF+DWG
4. Export par feuilles vs carnet
5. Sous-dossiers et séparation format
6. Nommage avec paramètres projet
7. Configurations réutilisables

### Cas limites
- Jeux vides (sans feuilles)
- Paramètres manquants sur éléments
- Chemins très longs (> 260 caractères)
- Caractères spéciaux dans les noms
- Conflits de noms de fichiers
- Configurations d'export invalides

## Dépendances externes

### Obligatoires
- **pyRevit**: Framework hôte
- **Autodesk Revit API**: Accès document
- **.NET Framework 4.8+**: WPF et System.*

### Optionnelles
- Aucune dépendance externe Python

---

*Architecture validée pour la version 0.4*
