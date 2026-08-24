# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A [pyRevit](https://github.com/eirannejad/pyRevit) extension for Revit: export en lot PDF/DWG, duplication et renommage de feuilles/vues, audit de modèle. All UI text, comments, and commit messages are in **French**.

- **Minimum Revit version**: 2026
- **Python**: 2/3 compatible (`from __future__ import unicode_literals` at top of files, `# -*- coding: utf-8 -*-` header)

## Agent behavior
Always use agent teams for tasks involving more than one file.
Lead must use delegate mode. Require plan approval before writing code.

## Status line
Show context percentage, session cost, git branch.

## Development workflow

There is no build step, compiler, or linter. The development cycle is:

1. Edit files directly in the pyRevit extensions folder (this repo).
2. In Revit: **pyRevit tab → Reload** (or `Ctrl+F5` with pyRevit hotkeys enabled).
3. Click the button to test.

To test a single pushbutton without reloading all of pyRevit, right-click its button → **Run script**.

**Tests**: plain `unittest` scripts under each pushbutton's `tests/` (plus `lib/core/tests/`, `lib/ui/tests/`). They bootstrap `sys.path` themselves — run one with `python tests/test_x.py` from the pushbutton folder. No test runner, no framework, no fixtures. Revit imports are wrapped in `try/except` so pure-Python logic runs outside Revit.

Le bootstrap de test insère **`<bouton>/lib`** et le socle `lib/` — les deux mêmes racines qu'en régime pyRevit. Les tests utilisent donc exactement la même forme d'import que le code (`from services.X import Y`).

## Extension layout

```
418.tab/
├── Export.panel/BatchExport.pushbutton/      ← export PDF/DWG en lot (principal)
├── Audit.panel/Audit.pushbutton/             ← audit de santé du modèle + dashboard
├── Tools.panel/
│   ├── ImageCrop.pushbutton/
│   └── col1.stack/
│       ├── duplicate_sheets.pushbutton/
│       ├── views_duplicate.pushbutton/
│       └── Rename.pulldown/{FindReplace_Sheets, FindReplace - Views}.pushbutton/
└── 418.panel/Infos.pushbutton/               ← modale « À propos »
```

Each pushbutton is self-contained: `script.py` is the entry point, `GUI/` holds XAML, `lib/` holds Python logic split `services/` (métier) · `viewmodels/` · `views/` · `models/`.

## Shared socle (`lib/` at the extension root)

pyRevit puts this on `sys.path`, so it is imported as `core.X` / `ui.X` from any pushbutton.

```
lib/
├── core/   AppPaths, UserConfig, sanitize, transaction, selection,
│           bulk_edit, list_selection, text_filter, token_expander,
│           rename_service
└── ui/
    ├── base/     BaseViewModel, BaseWindow, RailWindow,
    │             SelectionPageVM, SelectionItemVM
    ├── helpers/  UIResourceLoader, RelayCommand, DarkMode, wpf_runtime
    ├── GUI/resources/  Colors/Styles + variantes Dark (SEULE copie des thèmes)
    └── GUI/pages/      SelectionPage.xaml (SEULE copie, partagée par 4 outils)
```

**Put shared logic here, not in a pushbutton.** Anything duplicated across two tools belongs in the socle.

## Important patterns

**MVVM**: `script.py` → `MainViewModel` → `MainWindowView` (hérite de `BaseWindow`). Les services sont instanciés par le VM et **injectés** aux couches basses — elles n'en créent jamais.

**UserConfig**: `lib/core/UserConfig.py`, unique implémentation. Persiste en JSON dans `418.extension/data/<namespace>.json` (indépendant de `pyrevit.userconfig`, qui ne persiste rien en mode admin). Clés insensibles à la casse. BatchExport utilise le namespace `'batch_export'`. Le VM crée UNE instance et l'injecte à tous les services.

**AppPaths**: Never hardcode paths to XAML or resources. `AppPaths().resources_dir()` / `.pages_dir()` / `.data_dir()`.

**Imports — UNE seule forme.** Toujours `from core.X import Y`, `from services.X import Y`, jamais de préfixe `lib.`, jamais de garde `try/except` autour d'un import du dépôt. Chaque `script.py` insère `<bouton>/lib` dans `sys.path` avant ses imports (bootstrap explicite en tête de fichier) ; les tests font de même. Un même fichier importé sous deux noms de module donnerait deux objets distincts, donc deux états séparés — c'est exactement le bug que la double forme provoquait sur `UserConfig`. Ne JAMAIS utiliser d'import relatif profond (`from ...core.X`). Réserver `try/except ImportError` aux seuls imports **externes** : `Autodesk.Revit`, `System.*`, `pyrevit`, `clr`.

**Naming patterns**: `NamingService` résout les motifs à jetons (`{numero}`, `{titre}`, `{param:NOM}`, `{param_projet:NOM}`) contre un élément Revit. C'est la SEULE source de nommage — l'ancien système de `rows` (`[{"Name":…, "Prefix":…, "Suffix":…}]`) et `NamingResolver` ont été supprimés.

**Sanitization**: `lib/core/sanitize.py`, source unique. `sanitize()` pour les noms de fichiers (max 180, retire `\/:*?"<>|` + espaces/points finaux, `fallback` paramétrable) ; `sanitize_revit_name()` pour les noms d'éléments Revit. `DestinationService.sanitize()` n'est qu'un passe-plat avec `fallback='untitled'`.

**Destination**: `DestinationService` est la source unique (dossier, flags sous-dossiers/séparation formats, unicité). Utilisée par le VM ET par `ExportOrchestrator`.

**Outils à rail**: les 4 outils de `Tools.panel` héritent de `RailWindow` (socle) et ne déclarent que de la donnée — `ONGLETS`, `SUIVANTS`, `RUN`, `RADIOS`. Contrat côté VM : `Mode` (chaîne) + `set_mode()` + un attribut par onglet. La page Sélection est partagée (`lib/ui/GUI/pages/SelectionPage.xaml` + `SelectionPageVM.depuis_descripteurs()`) ; un outil peut la surcharger en déposant un `SelectionPage.xaml` dans son propre `GUI/Views/pages/`.

**WPF loading**: `UIResourceLoader` merges resource dictionaries into the window before loading XAML. Always load resources before loading a window that references them.
