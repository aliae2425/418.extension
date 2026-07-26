# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A [pyRevit](https://github.com/eirannejad/pyRevit) extension for Revit that automates batch export of sheets to PDF and DWG. All UI text, comments, and commit messages are in **French**.

- **Minimum Revit version**: 2026
- **Python**: 2/3 compatible (`from __future__ import unicode_literals` at top of files, `# -*- coding: utf-8 -*-` header)

## Agent behavior
Always use agent teams for tasks involving more than one file.
Lead must use delegate mode. Require plan approval before writing code.

## Status line
Show context percentage, session cost, git branch.

## Development workflow

There is no build step, compiler, linter, or test runner configured. The development cycle is:

1. Edit files directly in the pyRevit extensions folder (this repo).
2. In Revit: **pyRevit tab → Reload** (or `Ctrl+F5` with pyRevit hotkeys enabled).
3. Click the button to test.

To test a single pushbutton without reloading all of pyRevit, right-click its button → **Run script**.

For logic that doesn't need Revit (pure Python), you can run scripts directly with `python script.py` — all Revit imports are wrapped in `try/except` blocks so they degrade gracefully when `Autodesk.Revit.DB` is unavailable.

## Extension layout

```
418.tab/
├── Export.panel/BatchExport.pushbutton/   ← main feature (v0.3, active development)
├── Beta.panel/Keynotes.pushbutton/        ← keynote editor (v0.5, beta)
├── Beta.panel/ColorSplasher.pushbutton/   ← planned, not functional
└── layout.panel/                          ← planned tools (Reperage, ReplaceMaterial)
```

Each pushbutton is self-contained: `script.py` is the entry point, `GUI/` holds XAML, `lib/` holds all Python logic.

## BatchExport architecture

The `BatchExport.pushbutton/` is the only fully implemented feature. Its `lib/` follows a strict layered structure:

```
lib/
├── core/           AppPaths (XAML path resolution), UserConfig (pyRevit config wrapper)
├── data/           Repositories and stores — read/write Revit data and user settings
│   ├── sheets/     SheetParameterRepository, SheetSetRepository
│   ├── destination/DestinationStore
│   └── naming/     NamingPatternStore, NamingResolver
├── services/       Business logic, no UI dependencies
│   ├── core/       ExportOrchestrator (main export logic)
│   └── formats/    PdfExporterService, DwgExporterService
└── ui/
    ├── components/  Reusable UI pieces — each wraps a XAML Control + its Python logic
    ├── helpers/     UIResourceLoader, UITemplateBinder, DarkMode, HoverOverlay, etc.
    └── windows/
        ├── MainWindow.py / MainWindowController.py   ← root WPF window
        └── sections/   One controller per logical section of the main window
```

**Key flow**: `script.py` → `MainWindowController` (wires everything together) → `ExportOrchestrator` (executes exports).

**XAML layout** (`GUI/`):
- `Views/index.xaml` — root window layout
- `Controls/` — one `.xaml` per Component class in `ui/components/`
- `Modals/` — secondary windows (ConfigManager, OrderManager, Tutorial, SetupEditor)
- `resources/Colors.xaml`, `Styles.xaml` + `ColorsDark.xaml`, `StylesDark.xaml` — light/dark theme pairs

## Important patterns

**UserConfig**: All persistent settings go through `UserConfig(namespace)` which wraps `pyrevit.userconfig`. BatchExport uses namespace `'batch_export'`. Config keys are plain strings (e.g. `'PathDossier'`, `'create_subfolders'`).

**AppPaths**: Never hardcode paths to XAML files. Use `AppPaths()` which resolves paths relative to `lib/core/` up to `GUI/`.

**Import guards**: Every cross-layer import uses `try/except` and assigns `None` as fallback. Check for `None` before use. This is intentional — it allows running modules outside Revit for testing.

**Naming patterns**: A naming pattern is a list of row dicts: `[{"Name": "param_name", "Prefix": "…", "Suffix": "…"}, …]`. `NamingResolver` resolves these against a Revit element (sheet, collection, project info) or system values (date parts).

**Sanitization**: `DestinationStore.sanitize()` is the canonical method for cleaning strings into valid Windows filenames. Max 180 chars, removes `\/:*?"<>|`.

**WPF loading**: `UIResourceLoader` merges resource dictionaries into the window before loading XAML. Always load resources before loading a window that references them.

**Section controllers**: Each `*SectionController` owns one logical slice of the UI (parameters, destination, naming, preview, export, etc.). They receive shared service/data instances from `MainWindowController` — they do not instantiate their own.
