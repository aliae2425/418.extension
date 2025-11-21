# Documentation API - 418 Extension

Cette documentation détaille toutes les classes, méthodes et interfaces publiques de l'extension.

## Table des matières

1. [Core - Configuration](#core-configuration)
2. [Data - Repositories](#data-repositories)
3. [Services - Logique métier](#services-logique-métier)
4. [UI - Composants interface](#ui-composants-interface)
5. [Utils - Utilitaires](#utils-utilitaires)

---

## Core - Configuration

### AppPaths

**Module**: `lib.core.AppPaths`

Gestion centralisée des chemins de fichiers de l'application.

```python
class AppPaths(object):
    def __init__(self)
```

#### Méthodes

##### `script_dir() -> str`
Retourne le répertoire du script principal.

**Returns**: Chemin absolu vers le dossier du pushbutton

##### `main_xaml() -> str`
Retourne le chemin complet vers la fenêtre principale.

**Returns**: Chemin absolu vers `GUI/Views/index.xaml`

##### `resources_dir() -> str`
Retourne le répertoire des ressources XAML.

**Returns**: Chemin absolu vers `GUI/resources/`

##### `controls_dir() -> str`
Retourne le répertoire des contrôles XAML.

**Returns**: Chemin absolu vers `GUI/Controls/`

##### `modals_dir() -> str`
Retourne le répertoire des fenêtres modales.

**Returns**: Chemin absolu vers `GUI/Modals/`

**Exemple d'usage**:
```python
paths = AppPaths()
main_window_path = paths.main_xaml()
resources = paths.resources_dir()
```

---

### UserConfig

**Module**: `lib.core.UserConfig`

Interface unifiée pour accéder à la configuration utilisateur via pyRevit.

```python
class UserConfig(object):
    def __init__(self, namespace='batch_export')
```

**Paramètres**:
- `namespace` (str): Namespace de configuration (par défaut: 'batch_export')

#### Méthodes

##### `get(key, default=None) -> str`
Récupère une valeur de configuration.

**Paramètres**:
- `key` (str): Clé de configuration
- `default` (any): Valeur par défaut si non trouvée

**Returns**: Valeur sous forme de chaîne, ou default

**Exemple**:
```python
cfg = UserConfig('batch_export')
dest = cfg.get('destination_path', 'C:\\Exports')
```

##### `set(key, value) -> bool`
Sauvegarde une valeur de configuration.

**Paramètres**:
- `key` (str): Clé de configuration
- `value` (any): Valeur à sauvegarder (convertie en str)

**Returns**: True si succès, False sinon

**Exemple**:
```python
cfg.set('destination_path', 'C:\\MesExports')
cfg.set('create_subfolders', '1')
```

##### `get_list(key, default=None) -> list`
Récupère une liste de valeurs (format CSV).

**Paramètres**:
- `key` (str): Clé de configuration
- `default` (list): Liste par défaut

**Returns**: Liste de chaînes

**Exemple**:
```python
params = cfg.get_list('selected_params', [])
# Si stocké: "Param1,Param2,Param3"
# Retourne: ['Param1', 'Param2', 'Param3']
```

**Clés de configuration standard**:
- `destination_path`: Chemin d'export
- `create_subfolders`: '0' ou '1'
- `separate_format_folders`: '0' ou '1'
- `sheet_param_ExportationCombo`: Nom du paramètre
- `sheet_param_CarnetCombo`: Nom du paramètre
- `sheet_param_DWGCombo`: Nom du paramètre
- `pdf_setup_name`: Configuration PDF
- `dwg_setup_name`: Configuration DWG
- `pdf_separate`: '0' ou '1'
- `dwg_separate`: '0' ou '1'
- `naming_sheet_pattern`: Pattern de nommage feuilles
- `naming_sheet_rows`: JSON sérialisé des rows
- `naming_set_pattern`: Pattern de nommage carnets
- `naming_set_rows`: JSON sérialisé des rows

---

## Data - Repositories

### DestinationStore

**Module**: `lib.data.destination.DestinationStore`

Gestion du dossier de destination des exports.

```python
class DestinationStore(object):
    def __init__(self)
```

#### Méthodes

##### `get() -> str`
Récupère le chemin de destination sauvegardé.

**Returns**: Chemin absolu ou None

##### `set(path) -> bool`
Sauvegarde le chemin de destination.

**Paramètres**:
- `path` (str): Chemin à sauvegarder

**Returns**: True si succès

##### `validate(path) -> tuple(bool, str)`
Valide qu'un chemin est utilisable.

**Paramètres**:
- `path` (str): Chemin à valider

**Returns**: (valide, message_erreur)

**Exemple**:
```python
store = DestinationStore()
ok, err = store.validate('C:\\Exports')
if not ok:
    print("Erreur:", err)
```

##### `ensure(path) -> bool`
Crée le dossier s'il n'existe pas.

**Paramètres**:
- `path` (str): Chemin à créer

**Returns**: True si existant ou créé

##### `choose_destination_explorer(save=True) -> str`
Ouvre un dialogue de sélection de dossier.

**Paramètres**:
- `save` (bool): Sauvegarder automatiquement le choix

**Returns**: Chemin sélectionné ou None

##### `sanitize(name) -> str`
Nettoie un nom pour le système de fichiers.

**Paramètres**:
- `name` (str): Nom à nettoyer

**Returns**: Nom sans caractères interdits

**Exemple**:
```python
safe = store.sanitize('Plan/Coupe*A101')
# Retourne: 'Plan_Coupe_A101'
```

##### `unique_path(base_path) -> str`
Génère un chemin unique avec suffixe si collision.

**Paramètres**:
- `base_path` (str): Chemin de base avec extension

**Returns**: Chemin unique (ex: file_001.pdf)

---

### NamingPatternStore

**Module**: `lib.data.naming.NamingPatternStore`

Stockage des patterns de nommage.

```python
class NamingPatternStore(object):
    def __init__(self)
```

#### Méthodes

##### `load(kind) -> tuple(str, list)`
Charge un pattern sauvegardé.

**Paramètres**:
- `kind` (str): Type de pattern ('sheet' ou 'set')

**Returns**: (pattern_string, rows_list)

**Exemple**:
```python
store = NamingPatternStore()
pattern, rows = store.load('sheet')
# pattern: "{SheetNumber}_{SheetName}"
# rows: [
#     {'Name': 'SheetNumber', 'Prefix': '', 'Suffix': '_'},
#     {'Name': 'SheetName', 'Prefix': '', 'Suffix': ''}
# ]
```

##### `save(kind, pattern, rows) -> bool`
Sauvegarde un pattern.

**Paramètres**:
- `kind` (str): Type ('sheet' ou 'set')
- `pattern` (str): Pattern formaté
- `rows` (list): Liste de dicts avec Name/Prefix/Suffix

**Returns**: True si succès

**Format des rows**:
```python
[
    {
        'Name': 'ParamName',      # Nom du paramètre Revit
        'Prefix': 'prefix_',      # Texte avant
        'Suffix': '_suffix'       # Texte après
    }
]
```

---

### NamingResolver

**Module**: `lib.data.naming.NamingResolver`

Résolution des patterns de nommage pour éléments Revit.

```python
class NamingResolver(object):
    def __init__(self, doc)
```

**Paramètres**:
- `doc` (Document): Document Revit actif

#### Méthodes

##### `resolve_for_element(elem, rows, empty_fallback=True) -> str`
Résout un pattern pour un élément donné.

**Paramètres**:
- `elem` (Element): Élément Revit (ViewSheet, etc.)
- `rows` (list): Configuration du pattern
- `empty_fallback` (bool): Utiliser fallback si vide

**Returns**: Chaîne résolue

**Exemple**:
```python
resolver = NamingResolver(doc)
rows = [
    {'Name': 'SheetNumber', 'Prefix': '', 'Suffix': '_'},
    {'Name': 'SheetName', 'Prefix': '', 'Suffix': ''}
]
name = resolver.resolve_for_element(sheet, rows)
# Retourne: "A101_Plan RDC"
```

**Résolution hiérarchique**:
1. Cherche le paramètre sur l'élément
2. Si non trouvé, cherche dans les paramètres projet
3. Utilise chaîne vide si non trouvé

##### `build_pattern(rows) -> str`
Construit un pattern d'affichage.

**Paramètres**:
- `rows` (list): Configuration du pattern

**Returns**: Pattern formaté avec placeholders

**Exemple**:
```python
pattern = resolver.build_pattern(rows)
# Retourne: "{SheetNumber}_{SheetName}"
```

##### `_get_param_value(elem, param_name) -> str`
Récupère la valeur d'un paramètre (méthode interne).

**Paramètres**:
- `elem` (Element): Élément Revit
- `param_name` (str): Nom du paramètre

**Returns**: Valeur sous forme de chaîne

##### `_get_project_param_value(param_name) -> str`
Récupère un paramètre du projet (méthode interne).

**Paramètres**:
- `param_name` (str): Nom du paramètre projet

**Returns**: Valeur depuis ProjectInformation

**Cache**: Les paramètres projet sont mis en cache lors de la première requête.

---

### SheetParameterRepository

**Module**: `lib.data.sheets.SheetParameterRepository`

Gestion des paramètres disponibles sur les jeux de feuilles.

```python
class SheetParameterRepository(object):
    def __init__(self, config)
```

**Paramètres**:
- `config` (UserConfig): Instance de configuration

#### Méthodes

##### `collect_for_collections(doc) -> list`
Collecte tous les paramètres disponibles sur les jeux.

**Paramètres**:
- `doc` (Document): Document Revit

**Returns**: Liste de noms de paramètres uniques

**Exemple**:
```python
repo = SheetParameterRepository(cfg)
params = repo.collect_for_collections(doc)
# Retourne: ['Export', 'Carnet', 'Export DWG', ...]
```

##### `get_saved_selections() -> dict`
Récupère les sélections sauvegardées.

**Returns**: Dict {combo_name: param_name}

##### `save_selections(selections) -> bool`
Sauvegarde les sélections de paramètres.

**Paramètres**:
- `selections` (dict): {combo_name: param_name}

**Returns**: True si succès

---

### SheetSetRepository

**Module**: `lib.data.sheets.SheetSetRepository`

Accès aux jeux de feuilles Revit.

```python
class SheetSetRepository(object):
    def __init__(self)
```

#### Méthodes

##### `get_all(doc) -> list`
Récupère tous les jeux de feuilles.

**Paramètres**:
- `doc` (Document): Document Revit

**Returns**: Liste de tuples (SheetCollection, nom)

##### `get_sheets(doc, collection) -> list`
Récupère les feuilles d'un jeu.

**Paramètres**:
- `doc` (Document): Document Revit
- `collection` (SheetCollection): Jeu de feuilles

**Returns**: Liste de ViewSheet

##### `read_param_flag(elem, param_name, default=False) -> bool`
Lit un paramètre booléen.

**Paramètres**:
- `elem` (Element): Élément Revit
- `param_name` (str): Nom du paramètre
- `default` (bool): Valeur par défaut

**Returns**: Valeur booléenne (0→False, 1→True)

---

## Services - Logique métier

### ExportOrchestrator

**Module**: `lib.services.core.ExportOrchestrator`

Orchestrateur central du processus d'export.

```python
class ExportOrchestrator(object):
    def __init__(self, namespace='batch_export')
```

#### Structures de données

##### ExportPlan (namedtuple)
```python
ExportPlan(
    collection_name: str,    # Nom du jeu
    do_export: bool,        # Exporter?
    per_sheet: bool,        # Feuilles séparées?
    do_dwg: bool,          # Export DWG?
    do_pdf: bool           # Export PDF?
)
```

#### Méthodes principales

##### `plan_exports_for_collections(doc, get_ctrl) -> list`
Analyse les jeux et crée un plan d'export.

**Paramètres**:
- `doc` (Document): Document Revit
- `get_ctrl` (callable): Fonction pour récupérer un contrôle UI par nom

**Returns**: Liste d'ExportPlan

**Exemple**:
```python
orch = ExportOrchestrator()
def get_ctrl(name):
    return getattr(window, name, None)

plans = orch.plan_exports_for_collections(doc, get_ctrl)
for plan in plans:
    print(f"{plan.collection_name}: PDF={plan.do_pdf}, DWG={plan.do_dwg}")
```

##### `run(doc, get_ctrl, progress_cb=None, log_cb=None, ui_win=None) -> bool`
Exécute le processus d'export complet.

**Paramètres**:
- `doc` (Document): Document Revit
- `get_ctrl` (callable): Fonction pour récupérer contrôles
- `progress_cb` (callable): Callback progression (i, total, message)
- `log_cb` (callable): Callback logging (message)
- `ui_win` (Window): Fenêtre pour mise à jour statuts

**Returns**: True si succès

**Callbacks**:
```python
def progress_callback(current, total, message):
    # Mise à jour barre de progression
    progressbar.Value = current
    progressbar.Maximum = total

def log_callback(message):
    # Affichage message
    print(message)

orch.run(doc, get_ctrl, progress_cb=progress_callback, log_cb=log_callback)
```

#### Méthodes d'export

##### `_export_pdf_sheet(doc, sheet, rows, base_folder, options, separate=True) -> str`
Exporte une feuille en PDF.

**Returns**: Chemin du fichier créé

##### `_export_dwg_sheet(doc, sheet, rows, base_folder, options) -> str`
Exporte une feuille en DWG.

**Returns**: Chemin du fichier créé

##### `_export_pdf_collection(doc, sheets, rows, base_folder, options) -> str`
Exporte un carnet PDF multi-feuilles.

**Returns**: Chemin du fichier créé

---

### PdfExporterService

**Module**: `lib.services.formats.PdfExporterService`

Service d'export PDF.

```python
class PdfExporterService(object):
    def __init__(self)
```

#### Méthodes

##### `build_options(doc, setup_name=None) -> PDFExportOptions`
Construit les options d'export PDF.

**Paramètres**:
- `doc` (Document): Document Revit
- `setup_name` (str): Nom de la configuration

**Returns**: Instance PDFExportOptions configurée

##### `list_setups(doc) -> list`
Liste les configurations PDF disponibles.

**Paramètres**:
- `doc` (Document): Document Revit

**Returns**: Liste de noms de configurations

##### `get_saved_setup() -> str`
Récupère le nom de configuration sauvegardé.

**Returns**: Nom de configuration ou None

##### `get_separate(default=False) -> bool`
Vérifie si le mode séparé est activé.

**Returns**: True si export séparé

---

### DwgExporterService

**Module**: `lib.services.formats.DwgExporterService`

Service d'export DWG.

```python
class DwgExporterService(object):
    def __init__(self)
```

#### Méthodes

Identiques à `PdfExporterService` mais pour DWG:

- `build_options(doc, setup_name=None) -> DWGExportOptions`
- `list_setups(doc) -> list`
- `get_saved_setup() -> str`
- `get_separate(default=False) -> bool`

---

## UI - Composants interface

### MainWindowController

**Module**: `lib.ui.windows.MainWindowController`

Contrôleur principal de l'application.

```python
class MainWindowController(object):
    def __init__(self)
```

#### Méthodes publiques

##### `initialize() -> None`
Initialise tous les composants de l'interface.

**Actions**:
1. Charge les ressources XAML
2. Lie les templates aux hosts
3. Remplit les contrôles
4. Branche les événements

##### `show() -> bool`
Affiche la fenêtre principale.

**Returns**: True si fenêtre affichée

**Exemple**:
```python
ctrl = MainWindowController()
ctrl.show()  # Bloquant (modal)
```

#### Méthodes internes

##### `_merge_and_bind() -> None`
Charge et lie les ressources XAML.

##### `_load_param_combos() -> None`
Remplit les dropdowns de paramètres.

##### `_update_export_button_state() -> None`
Active/désactive le bouton d'export selon les conditions.

##### `_wire_*_events() -> None`
Branche les gestionnaires d'événements.

---

### Components - Composants UI

#### ParameterSelectorComponent

**Module**: `lib.ui.components.ParameterSelectorComponent`

Gestion de la sélection de paramètres.

```python
class ParameterSelectorComponent(object):
    def __init__(self, sheet_param_repo)
```

##### `populate(window) -> None`
Remplit les ComboBox de paramètres.

**Paramètres**:
- `window` (Window): Fenêtre contenant les contrôles

##### `validate_unique(window) -> bool`
Vérifie que les 3 paramètres sont différents.

**Returns**: True si tous uniques

---

#### DestinationPickerComponent

**Module**: `lib.ui.components.DestinationPickerComponent`

Gestion de la sélection du dossier de destination.

```python
class DestinationPickerComponent(object):
    def __init__(self, dest_store)
```

##### `init_controls(window) -> None`
Initialise l'UI du sélecteur.

##### `validate(window, create=False) -> tuple(bool, str)`
Valide le chemin de destination.

**Paramètres**:
- `window` (Window): Fenêtre
- `create` (bool): Créer le dossier si nécessaire

**Returns**: (valide, message_erreur)

##### `browse_folder(window) -> None`
Ouvre le dialogue de sélection.

---

#### ExportOptionsComponent

**Module**: `lib.ui.components.ExportOptionsComponent`

Gestion des options PDF/DWG.

```python
class ExportOptionsComponent(object):
    def __init__(self, pdf_service, dwg_service)
```

##### `populate_pdf(window) -> None`
Remplit les options PDF.

##### `populate_dwg(window) -> None`
Remplit les options DWG.

##### `save_selections(window) -> None`
Sauvegarde les choix utilisateur.

---

#### NamingConfigComponent

**Module**: `lib.ui.components.NamingConfigComponent`

Gestion de la configuration de nommage.

```python
class NamingConfigComponent(object):
    def __init__(self, naming_store)
```

##### `refresh_buttons(window) -> None`
Met à jour les labels des boutons.

##### `open_editor(kind) -> bool`
Ouvre l'éditeur de nommage.

**Paramètres**:
- `kind` (str): 'sheet' ou 'set'

**Returns**: True si modifications appliquées

---

#### CollectionPreviewComponent

**Module**: `lib.ui.components.CollectionPreviewComponent`

Gestion de la grille de prévisualisation.

```python
class CollectionPreviewComponent(object):
    def __init__(self)
```

##### `populate(window, selections) -> None`
Remplit la grille avec les jeux de feuilles.

**Paramètres**:
- `window` (Window): Fenêtre
- `selections` (dict): Paramètres sélectionnés

##### `set_collection_status(window, collection_name, status) -> None`
Met à jour le statut d'un jeu.

**Paramètres**:
- `status` (str): 'pending', 'progress', 'ok', 'error'

##### `set_detail_status(window, collection, sheet_name, format, status) -> None`
Met à jour le statut d'une feuille.

**Paramètres**:
- `collection` (str): Nom du jeu
- `sheet_name` (str): Nom de la feuille
- `format` (str): 'PDF' ou 'DWG'
- `status` (str): 'pending', 'progress', 'ok', 'error'

##### `refresh_grid(window) -> None`
Force le rafraîchissement visuel.

---

## Utils - Utilitaires

### FileSystem

**Module**: `lib.utils.FileSystem`

Utilitaires de gestion de fichiers.

**Fonctions** (à documenter selon implémentation):
- Manipulation de chemins
- Création de dossiers
- Vérification d'existence

---

### RevitApi

**Module**: `lib.utils.RevitApi`

Wrappers autour de l'API Revit.

**Fonctions** (à documenter selon implémentation):
- Helpers pour transactions
- Accès simplifié aux collections
- Utilitaires de paramètres

---

### Text

**Module**: `lib.utils.Text`

Utilitaires de manipulation de texte.

**Fonctions** (à documenter selon implémentation):
- Sanitization de chaînes
- Formatage
- Conversion de casse

---

## Exemples d'utilisation complets

### 1. Export simple

```python
from lib.ui.windows.MainWindowController import MainWindowController

# Afficher l'interface
ctrl = MainWindowController()
ctrl.show()
```

### 2. Export programmatique

```python
from lib.services.core.ExportOrchestrator import ExportOrchestrator
from lib.core.UserConfig import UserConfig

# Configuration
cfg = UserConfig('batch_export')
cfg.set('destination_path', 'C:\\Exports')

# Orchestration
orch = ExportOrchestrator()

def get_ctrl(name):
    # Retourner contrôles mockés ou réels
    pass

# Exécution
orch.run(__revit__.ActiveUIDocument.Document, get_ctrl)
```

### 3. Configuration de nommage

```python
from lib.data.naming.NamingPatternStore import NamingPatternStore
from lib.data.naming.NamingResolver import NamingResolver

# Définir pattern
store = NamingPatternStore()
rows = [
    {'Name': 'Project Name', 'Prefix': '', 'Suffix': '_'},
    {'Name': 'SheetNumber', 'Prefix': '', 'Suffix': '_'},
    {'Name': 'SheetName', 'Prefix': '', 'Suffix': ''}
]
pattern = "{Project Name}_{SheetNumber}_{SheetName}"
store.save('sheet', pattern, rows)

# Utiliser resolver
doc = __revit__.ActiveUIDocument.Document
resolver = NamingResolver(doc)
name = resolver.resolve_for_element(sheet, rows)
```

### 4. Gestion de destination

```python
from lib.data.destination.DestinationStore import DestinationStore

store = DestinationStore()

# Sélection interactive
path = store.choose_destination_explorer(save=True)

# Validation
ok, err = store.validate(path)
if ok:
    store.ensure(path)  # Créer si nécessaire
```

---

## Notes de version

### Version 0.4
- Support des paramètres projet dans le nommage
- Cache des paramètres pour optimisation
- Amélioration de la robustesse d'erreurs
- Mise à jour UI en temps réel

### Compatibilité

- **IronPython**: 2.7
- **Revit API**: 2026+
- **.NET**: 4.8+

### Limitations connues

1. Pas de threading (IronPython)
2. Export séquentiel uniquement
3. Chemins limités à 260 caractères (Windows)

---

*Documentation API générée pour la version 0.4*
