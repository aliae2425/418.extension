# BatchExport — Migration Phase 3 (mode « par jeu » de bout en bout)

> Exécuté via subagent-driven-development. Objectif : rendre le mode préprogrammé « par jeu » fonctionnel sur le MVVM, en s'appuyant sur les services de la Phase 2.

**Goal :** Le mode « par jeu » affiche les collections qualifiées (pilotées par les paramètres Oui/Non) et lance l'export via `ExportOrchestrator`.

**Architecture :** `MainViewModel` consomme `SheetCollectionService` / `NamingService` / `DestinationService` (Phase 2) pour construire la liste des collections et leurs feuilles, puis délègue l'export à `ExportOrchestrator`. Le XAML « par jeu » lie cette liste (lecture seule, badges). Legacy `lib/data/` supprimé une fois superseded.

## Global Constraints

- Revit 2026, Python 2/3 (`unicode_literals`, utf-8). Imports Revit/WPF sous try/except → None.
- Français. Commit par phase après validation Revit. Tests standalone `unittest`.
- Injection de services dans `MainViewModel` pour tests hors Revit (fakes).
- `PdfExporterService.build_options()` = best-effort (API Revit) → NE PAS annoncer « réparé/fonctionne » ; marquer « à valider dans Revit ».

---

### Task 1 : MainViewModel — données « par jeu » + mapping paramètres (testable)

**Files:** Modify `lib/viewmodels/MainViewModel.py`, `tests/test_main_viewmodel.py`

Étendre `MainViewModel.__init__` pour accepter des services injectables :
`__init__(self, doc=None, sheet_service=None, naming_service=None, destination_service=None)` — défaut : instancier les vrais (`SheetCollectionService(doc)`, `NamingService(doc)`, `DestinationService(doc)`) sous try/except → None.

Ajouter :
- Propriétés mapping (lues via `core.UserConfig` namespace `batch_export`, clés existantes) : `ParamExport`, `ParamCarnet`, `ParamDwg` (noms de paramètres) + setters qui persistent.
- `refresh_par_jeu()` : via `sheet_service.list_collections()` + `list_sheets(id)` + `read_flag(collection, ParamX)` construit `self.collections` = liste de dicts :
  `{'Titre', 'Id', 'FlagExport': bool, 'FlagCarnet': bool, 'FlagDwg': bool, 'Qualified': bool(FlagExport), 'Sheets': [{'Numero','Nom','NomProjete'}]}` où `NomProjete` via `naming_service.resolve_for_element(sheet, rows_sheet)` (rows chargés via `naming_service.load('sheet')`).
- `collections` (propriété bindable) + `nb_jeux_qualifies` / `nb_feuilles_qualifiees` (pour le badge).

**Tests** : injecter un faux `sheet_service` (retourne 2 collections, l'une avec FlagExport True, l'autre False ; feuilles factices) + faux `naming_service`. Appeler `refresh_par_jeu()`, asserter : `len(collections)==2`, flags corrects, `nb_jeux_qualifies==1`, `NomProjete` renseigné. Garder les 5 tests existants verts.

Lancer `python tests/test_main_viewmodel.py`. Rapporter.

---

### Task 2 : XAML « par jeu » — liste liée (vérif Revit)

**Files:** Modify `GUI/Views/MainWindow.xaml`

Remplacer le placeholder de la surface (mode par jeu) par un `ItemsControl`/`ListView` lié à `Collections` : par collection, un en-tête (Titre + badges EXPORT/CARNET/DWG selon Flag*), et les feuilles (`Numero`, `Nom`, `NomProjete`). Collections non qualifiées grisées (style/opacity via trigger sur `Qualified`). Lecture seule (pas de cases à cocher en mode par jeu). Réutiliser les brushes/styles du socle en `DynamicResource`. Badge de compte lié à `nb_jeux_qualifies`/`nb_feuilles_qualifiees`.

Non testable hors Revit → vérif : `pyRevit → Reload`, la liste s'affiche, jeux non qualifiés grisés.

---

### Task 3 : Coordination export (VM → ExportOrchestrator) (vérif Revit)

**Files:** Modify `lib/viewmodels/MainViewModel.py` ; lire `lib/services/core/ExportOrchestrator.py` pour son interface publique.

Ajouter une commande `exporter_cmd` (RelayCommand du socle) qui, en mode par jeu, appelle `ExportOrchestrator` avec les entrées issues du VM (mapping paramètres, destination via `DestinationService`, patterns via `NamingService`) et branche `progress_cb`/`log_cb` sur des propriétés bindables de progression (`ProgressValue`, `StatusText`). Adapter l'ancien mécanisme `get_ctrl()` de l'orchestrateur : soit fournir un adaptateur qui expose les valeurs attendues depuis le VM, soit ajouter à l'orchestrateur une entrée directe (dict de config) — choisir le moins invasif après lecture. Ne pas casser les 42 tests.

Vérif Revit : lancer un export réel sur un petit jeu.

---

### Task 4 : PdfExporterService.build_options() — best-effort (vérif Revit)

**Files:** Modify `lib/services/formats/PdfExporterService.py`

Implémenter `build_options(doc, setup_name=None)` pour charger un setup PDF Revit (`DB.PDFExportSettings` par nom) et l'appliquer aux `DB.PDFExportOptions`, sur le modèle de ce que fait déjà `DwgExporterService` (`GetDWGExportOptions`). Gérer les setups custom JSON si présents. TOUT sous try/except.

⚠️ API Revit 2026 non validable hors Revit → livrer en best-effort, documenter les hypothèses, marquer « à valider dans Revit ». Ne pas prétendre que ça fonctionne tant que non testé.

---

### Task 5 : Migration patterns + suppression legacy

**Files:** Modify `lib/services/NamingService.py` (load tolérant) ; Delete `lib/data/` (naming, destination, sheets) une fois qu'aucun code actif ne l'importe.

- `NamingService.load(kind)` : si la valeur stockée est dans l'ancien format texte `[ "name": ... ]` (pas du JSON), la parser en fallback puis ré-enregistrer en JSON (migration transparente). Test : load d'une valeur au format legacy → rows corrects.
- Vérifier (grep) qu'aucun module actif n'importe `lib/data/` ni les anciens `lib/services/core|formats` non utilisés. Supprimer `lib/data/`. Si `ExportOrchestrator` (encore sous `lib/services/core/`) importe `lib/data/`, ne le supprimer qu'après avoir repointé l'orchestrateur sur les services Phase 2 (dans le cadre de la Task 3).

---

## Hors périmètre → Phase 4/5
- Mode « feuille par feuille » + page Paramètres complète (P4).
- Profils/CSV, HoverOverlay générique, tutoriel premier lancement (P5).
