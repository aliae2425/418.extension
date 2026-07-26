# BatchExport — Migration Phase 2 (services métier testables)

> **For agentic workers:** exécuté via subagent-driven-development. Objectif : extraire la logique métier réutilisable en services purs, testés hors Revit, prêts à être consommés par le MVVM en Phase 3.

**Goal :** Créer trois services métier propres et testés (`NamingService`, `DestinationService`, `SheetCollectionService`) et découpler l'orchestrateur de l'ancien UI.

**Architecture :** Services flat sous `lib/services/*.py`, sans dépendance UI. Logique consolidée depuis l'ancien `lib/data/`. L'ancien `lib/data/` + `lib/services/core|formats/` restent en **legacy** (consommés seulement par l'ancien `ExportOrchestrator`, lui-même legacy jusqu'à la Phase 3 qui le réécrit sur ces nouveaux services et supprime le legacy).

## Global Constraints

- Revit 2026, Python 2/3 (`from __future__ import unicode_literals`, `# -*- coding: utf-8 -*-`).
- Imports Revit/WPF sous `try/except` → fallback `None`. Aucun `import` obligatoire d'`Autodesk.Revit.DB`.
- Français partout. NE PAS commiter (commits en fin de migration).
- Tests standalone `unittest`, pattern `Infos.pushbutton/tests/` (ajout socle + button au `sys.path`).
- La logique nommage/destination doit être **100% testable sans Revit** (doc fictif / éléments factices).

---

### Task 1 : NamingService (consolidation nommage, testé)

**Files:** Create `lib/services/__init__.py`, `lib/services/NamingService.py`, `tests/test_naming_service.py`

Lire d'abord `lib/data/naming/NamingResolver.py` et `lib/data/naming/NamingPatternStore.py`. Consolider en un `NamingService` :
- `resolve_for_element(elem, rows)` → chaîne résolue (substitue `{Name}` par valeur du paramètre ; gère `Date: Jour/Mois/Année` ; nettoie les repr .NET invalides).
- `build_pattern(rows)` → template `{Name}` concaténé avec préfixes/suffixes.
- `save(kind, pattern, rows)` / `load(kind)` / `has_saved(kind)` (kind ∈ {'sheet','set'}), via `core.UserConfig` (socle).
- Extraction paramètre robuste : `LookupParameter` → itération `.Parameters` → propriété directe → ProjectInformation (fallback), comme l'existant.

**Tests** (sans Revit — utiliser des objets factices exposant `.Parameters` / `LookupParameter`) :
- résolution d'un pattern simple `[{Name:'X',Prefix:'a-',Suffix:'-b'}]` contre un faux elem dont le param `X`='42' → `'a-42-b'`.
- `Date: Année` résout vers une année à 4 chiffres (regex `\d{4}`).
- valeur .NET invalide (`Autodesk.Revit.DB.Foo object at 0x...`) → nettoyée/vide.
- `save`/`load` round-trip de rows (mock `UserConfig` ou namespace de test).

Lancer `python tests/test_naming_service.py` → doit passer. Rapporter la sortie exacte.

---

### Task 2 : DestinationService (chemins & sanitize, testé)

**Files:** Create `lib/services/DestinationService.py`, `tests/test_destination_service.py`

Lire `lib/data/destination/DestinationStore.py`. Consolider (sans les méthodes UI interactives `choose_destination_*`, qui relèvent de la vue) :
- `sanitize(name, replacement='_')` → retire `\ / : * ? " < > |`, max 180 chars.
- `unique_path(path)` → suffixe `(1)`, `(2)`… si collision.
- `ensure(path)` → crée le dossier.
- `get()` / `set(path)` via `core.UserConfig`, fallback `~/Documents/Exports`.
- `build_export_path(rows, folder, timestamp, ext, ensure_dir, unique)` s'appuyant sur `NamingService` (Task 1).

**Tests** (sans Revit) :
- `sanitize('a/b:c*?')` ne contient aucun caractère interdit.
- `sanitize('x'*300)` ≤ 180 chars.
- `unique_path` sur un dossier temp : 2e appel avec même nom → suffixe `(1)`.

Lancer les tests, rapporter la sortie.

---

### Task 3 : SheetCollectionService (lecture doc, testé avec faux doc)

**Files:** Create `lib/services/SheetCollectionService.py`, `tests/test_sheet_collection_service.py`

Lire `lib/data/sheets/SheetSetRepository.py` et `lib/data/sheets/SheetParameterRepository.py`. Consolider :
- `list_collections(doc)` → `list[dict]` `{'Titre', 'Id', 'Feuilles': int}` (via `DB.SheetCollection` + comptage `ViewSheet` par `SheetCollectionId`).
- `list_sheets(doc, collection_id=None)` → `list[dict]` `{'Numero','Nom','CollectionId'}`.
- `list_boolean_params(doc)` → paramètres Oui/Non modifiables des collections (pour le mappage).
- `read_flag(elem, param_name)` → bool.
- Tout accès Revit sous `try/except`; si `doc is None` → listes vides.

**Tests** (sans Revit — `doc=None` renvoie des listes vides sans lever ; faux objets pour `read_flag`) :
- `list_collections(None) == []`, `list_sheets(None) == []`, `list_boolean_params(None) == []`.
- `read_flag(fake_elem, 'P')` où le faux param P (AsInteger=1) → `True`.

Lancer les tests, rapporter la sortie.

---

### Task 4 : Découpler ExportOrchestrator de l'ancien UI

**Files:** Modify `lib/services/core/ExportOrchestrator.py`

- Supprimer l'import `from ...ui.components.CollectionPreviewComponent import CollectionPreviewComponent` (module inexistant) et le bloc `ui_comp` associé.
- Remplacer les mises à jour UI directes (`ui_comp.*`) par les callbacks déjà présents dans la signature (`progress_cb`, `log_cb`) — si un statut par collection était poussé à l'UI, le router via `progress_cb`. Ne PAS changer la logique d'export elle-même.
- Objectif minimal : le module se charge sans référence à `lib/ui/`, et l'export ne dépend plus de composants d'affichage.

**Vérif** : `python -c "..."` important le module → OK (déjà le cas via fallback, mais ici l'import mort doit être *retiré*, pas juste gardé). Relancer les tests des tasks 1-3 + `tests/test_main_viewmodel.py` (non-régression). Rapporter.

> Note : la réécriture/déduplication complète de la boucle per-sheet/carnet et le branchement VM→services→orchestrator relèvent de la Phase 3 (validation dans Revit). Ici on se limite au découplage UI.

---

## Hors périmètre Phase 2
- `PdfExporterService.build_options()` (Revit-API-shaped) → Phase 3, best-effort, à valider dans Revit.
- Suppression de l'ancien `lib/data/` et réécriture orchestrateur → Phase 3.
- Wiring UI → Phase 3/4.
