# Design — Refonte BatchExport : socle MVVM + double mode d'export

**Date** : 2026-07-22
**Branche** : `feat/Export` (depuis `main`)
**Statut** : En validation — maquette approuvée, spec en relecture
**Maquette** : `https://claude.ai/code/artifact/0efe5935-4107-4be9-b2c0-cabfa21b5881`

## Objectif

Refondre le pushbutton `Export.panel/BatchExport.pushbutton/` en trois volets :

1. **Migration vers le socle commun** — réécriture MVVM complète sur la bibliothèque
   partagée `418.extension/lib/`, à la manière des modules Audit / Manage* / Infos.
2. **Second mode d'export « feuille par feuille »** — sélection manuelle des feuilles
   dans l'UI, en complément du mode « par jeu » préprogrammé existant.
3. **Rework des paramètres** — clarifier le rôle des paramètres Revit : ils pilotent
   *uniquement* le mode préprogrammé ; le mode manuel est sans paramètre.

## État des lieux (résumé)

L'implémentation actuelle est autonome et n'utilise pas le socle partagé :

- **Architecture** : couches maison `core/data/services/ui` (~40 fichiers), câblage
  impératif via `MainWindowController` + 9 *section controllers* + 5 *components*.
- **Helpers dupliqués** vis-à-vis du socle : `DarkMode` (identique), `UIResourceLoader`,
  `GridRowToggle`, `AppPaths`, `UserConfig`. Cas particuliers : `RelayCommand` local est un
  **stub vide** (le socle est fonctionnel), `HoverOverlay` local est spécialisé burger-menu.
- **Moteur d'export** : basé sur les `DB.SheetCollection` de Revit 2026. Pilotage par
  3 paramètres booléens Oui/Non posés sur les collections (`Exportation`, `Carnet`, `DWG`),
  mappés via 3 combos.
- **Dette technique** :
  - `PdfExporterService.build_options()` est un **stub** — les setups PDF choisis ne sont
    jamais appliqués (seul le DWG applique réellement son setup via `GetDWGExportOptions()`).
  - Boucle d'export **dupliquée** (branche per-sheet vs branche carnet, ~100 lignes).
  - **Logique métier couplée à l'UI** : `ExportOrchestrator` appelle directement les
    composants d'affichage (`CollectionPreviewComponent`).
  - Clés de config **éparpillées** entre `UserConfig`, `ConfigManagerService` et les
    services de format.

## Architecture cible (MVVM sur le socle)

```
418.tab/Export.panel/BatchExport.pushbutton/
├── script.py                       # __title__, instancie MainViewModel(doc) + MainWindowView, view.show()
├── icon.png / icon.dark.png
├── GUI/
│   ├── Views/MainWindow.xaml        # layout complet, bindings sur le VM, zéro logique
│   └── Modals/                      # ProfilManager, éditeurs de nommage/setup (au besoin)
└── lib/
    ├── models/                      # DTOs purs, wrappers Revit
    │   ├── SheetItem.py             # { num, nom, collection_id, projected_name, is_selected }
    │   ├── CollectionItem.py        # { titre, feuilles[], flag_export, flag_carnet, flag_dwg }
    │   └── ExportPlan.py            # plan d'export normalisé (indépendant du mode)
    ├── viewmodels/
    │   └── MainViewModel.py         # BaseViewModel : état UI, mode actif, commandes
    ├── services/                    # métier pur, AUCUNE dépendance UI
    │   ├── SheetCollectionService.py    # lit les SheetCollection + feuilles + flags
    │   ├── ExportOrchestrator.py        # exécute un ExportPlan (dédupliqué)
    │   ├── PdfExporterService.py        # build_options() RÉPARÉ
    │   ├── DwgExporterService.py
    │   ├── NamingService.py             # patterns + résolution (ex-NamingResolver/Store)
    │   ├── DestinationService.py        # dossier, sanitize, chemins uniques
    │   └── ProfilService.py             # profils JSON + import/export CSV (ex-ConfigManager)
    └── views/
        └── MainWindowView.py        # charge le XAML via BaseWindow
```

Réutilise le socle partagé `418.extension/lib/` (déjà sur `sys.path`) :

- `core.UserConfig` — persistance (namespace `'batch_export'`).
- `core.AppPaths`, `core.sanitize`.
- `ui.base.BaseWindow` — chargement XAML + thème + barre commune Fluent.
- `ui.base.BaseViewModel` — `INotifyPropertyChanged`, logo thème-aware.
- `ui.helpers.RelayCommand`, `DarkMode`, `UIResourceLoader`, `GridRowToggle`.

Les copies locales dans `lib/ui/helpers/` sont **supprimées**.

### Principe : les éléments WPF réutilisables vivent dans le socle

Tout élément WPF **non spécifique à l'export** produit ou généralisé pendant la migration est
placé dans `418.extension/lib/ui/` (helpers, styles, coquille) pour être **commun à toutes les
fenêtres WPF** des features (à l'image de ce que fait déjà About). Restent dans le pushbutton
uniquement les éléments **propres à l'export** (liste de feuilles, mappage des paramètres,
strip de format, etc.). Exemples de candidats à promouvoir au socle :

- `HoverOverlay` générique (le local est spécialisé burger-menu — à généraliser côté socle).
- Tout contrôle de liste/arborescence réutilisable, styles de cases à cocher, etc.
- La coquille (rail + surface + footer) est déjà dans `lib/ui/GUI/resources/Styles.xaml`.

## Coquille commune (shell) — modèle Audit

BatchExport adopte la **coquille commune Fluent** déjà utilisée par Audit, au lieu de son
chrome maison (burger menu + sidebar) :

- Fenêtre borderless arrondie (`WindowChrome`, coins 12), chargée via `ui.base.BaseWindow`.
- **Barre de titre** : titre à gauche, boutons de légende à droite (min/max/close).
- **Rail de navigation** (64px) : pastille de marque en haut, items de navigation, ⚙ Paramètres
  poussé en bas (`NavRailButtonStyle`, `BrandLogoBorderStyle`).
- **Surface de contenu flottante** (`ShellSurfaceStyle`) + **footer d'actions**
  (`PrimaryActionButtonStyle` / `SecondaryActionButtonStyle`).

**Logo de référence** : la pastille de marque affiche le logo partagé
`lib/ui/GUI/resources/logo.png` / `logo.dark.png` (via `AppPaths.logo_path` /
`BaseViewModel.BrandLogoPath`, variante claire forcée sur le fond dégradé). Ce logo est **la
référence unique pour toutes les fenêtres WPF** des features.

## Fonctionnement — les deux modes

Le mode actif se choisit par des **destinations du rail de navigation** (façon Audit), pas par
onglets de sidebar. L'item actif du rail pilote le contenu de la surface flottante. La config
commune (destination, setups, nommage, mappage des paramètres) vit dans la page **⚙ Paramètres**.

> **Note** : ceci remplace la décision initiale « onglets dans la sidebar » (voir maquette v2),
> à la demande d'adopter le fonctionnement d'Audit.

### Mode « Par jeu » (préprogrammé) — défaut

Reprend l'existant. Les collections Revit portant les paramètres Oui/Non qualifient
automatiquement l'export :

- `Exportation` = true → le jeu s'exporte.
- `Carnet` = true → PDF compilé (un seul fichier) ; false → une feuille = un PDF.
- `DWG` = true → export DWG (toujours feuille par feuille).

Zone principale : liste **en lecture seule**, groupée par collection, avec badges
`EXPORT / CARNET / DWG`. Les jeux non qualifiés sont grisés. Rien à cocher.

### Mode « Feuille par feuille » (manuel)

Sélection manuelle à la demande, pour les besoins ponctuels hors paramètres.

- Zone principale : collections dépliables → feuilles avec **cases à cocher** cliquables.
- **État initial : tout décoché** (part de zéro à chaque passage sur l'onglet).
- **Aucune persistance entre sessions** : à chaque ouverture de la fenêtre, la sélection
  manuelle repart vide. Elle est conservée en mémoire tant que la fenêtre reste ouverte
  (basculer d'onglet ne la perd pas).
- Réglages format / carnet / nommage : **globaux à la sélection** (dans la sidebar), pas
  par feuille.
- Compteur de feuilles cochées + libellé du bouton d'export mis à jour en direct.

## Rework des paramètres — décisions

| Sujet | Décision |
|-------|----------|
| Rôle des paramètres Revit | Pilotent **uniquement** le mode préprogrammé (par jeu). |
| Mode manuel | **Sans paramètre** — la sélection est la source de vérité. |
| Granularité manuelle | La sélection choisit **quelles feuilles** ; format/carnet/nommage restent **globaux**. Pas de réglage par feuille. |
| Pré-cochage du mode manuel | **Tout décoché** (aucune reprise des flags préprogrammés). |
| Persistance de la sélection manuelle | **Éphémère** — vide à chaque ouverture, non stockée en config. |

## Modèle de données & persistance

- **Réglages persistés** (`UserConfig`, namespace `batch_export`) : mappage des 3 paramètres,
  patterns de nommage (`pattern_sheet` / `pattern_set` + rows), destination
  (`PathDossier`, `create_subfolders`, `separate_format_folders`), setups PDF/DWG.
  → inchangé, mais **clés centralisées** dans les services concernés (fin de l'éparpillement).
- **Profils** (`Data/profil.json`) : conservés (save/load/delete + import/export CSV).
- **Sélection manuelle** : **non persistée** (état de session, dans le `MainViewModel`).

## Migration & impact sur l'existant

| Statut | Élément |
|--------|---------|
| ✅ Conservé | `SheetCollection`, patterns de nommage, profils/CSV, destination, options sous-dossiers |
| 🔧 Réparé | `PdfExporterService.build_options()` — les setups PDF sont enfin chargés et appliqués |
| 🔧 Refactor | Boucle d'export **dédupliquée** (un seul chemin per-sheet/carnet) ; UI **découplée** du métier (l'orchestrateur émet des events/callbacks, n'appelle plus les composants) |
| 🗑️ Supprimé | Helpers dupliqués (`DarkMode`, `RelayCommand` stub, `UIResourceLoader`, `GridRowToggle`, `AppPaths`, `UserConfig` locaux) |
| 🗑️ Supprimé | Les 9 *section controllers* + 5 *components* (remplacés par 1 ViewModel + bindings XAML) |

## Hors périmètre (YAGNI)

- Réglages d'export **par feuille** (format/nommage individuels) — explicitement écarté.
- Persistance ou profils de la sélection manuelle.
- Export de feuilles hors `SheetCollection`.
- Nouveaux formats d'export (IFC, images, etc.).

## Risques & points d'attention

- **Découplage UI/métier** : définir proprement l'interface de progression
  (callback `on_progress(sheet, status)` / events) pour que `ExportOrchestrator` ne
  connaisse plus la vue.
- **Réparation PDF** : `PDFExportOptions` doit être alimenté depuis les setups Revit
  (`DB.PDFExportSettings`) et/ou les setups custom JSON — à valider contre l'API Revit 2026.
- **Bricolage DWG temp folder + copie raster** : à préserver tel quel lors du refactor
  (fonctionne aujourd'hui), ne pas le « nettoyer » au risque de casser les XREF/images.
- **Parité fonctionnelle** : la réécriture MVVM doit atteindre l'iso-fonctionnel du mode
  par jeu avant d'exposer le mode manuel.

## Étapes (détaillées dans le plan d'implémentation)

1. Squelette MVVM branché sur le socle (script.py, View, ViewModel vides) + suppression doublons.
2. Services métier migrés et nettoyés (collection, naming, destination, orchestrator, profils).
3. Réparation `PdfExporterService.build_options()`.
4. Mode « par jeu » à iso-fonctionnel (parité avec l'existant).
5. Mode « feuille par feuille » (onglets sidebar, sélection, cases à cocher).
6. Finitions : thème, profils, destination, barre commune Fluent.
