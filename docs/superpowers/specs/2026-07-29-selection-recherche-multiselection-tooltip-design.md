# Design — Recherche, multi-sélection Shift/Ctrl et tooltip Fluent sur les pages de sélection

**Date** : 2026-07-29
**Branche** : `Feature/PowerRename-Duplicate`
**Statut** : Approuvé (design), en attente de relecture spec

## Contexte

Quatre pushbuttons partagent une page de sélection d'éléments (feuilles ou vues)
construite à l'identique par copier-coller :

| Outil | Chemin | Item VM | Colonnes |
|-------|--------|---------|----------|
| `duplicate_sheets` | `418.tab/Tools.panel/col1.stack/duplicate_sheets.pushbutton` | `SheetItemVM` | N° + Nom |
| `views_duplicate` | `418.tab/Tools.panel/col1.stack/views_duplicate.pushbutton` | `ViewItemVM` | Type + Nom |
| `FindReplace - Views` | `418.tab/Tools.panel/col1.stack/Rename.pulldown/FindReplace - Views.pushbutton` | `ViewItemVM` | Type + Nom |
| `FindReplace_Sheets` | `418.tab/Tools.panel/col1.stack/Rename.pulldown/FindReplace_Sheets.pushbutton` | `SheetItemVM` | N° + Nom |

Chaque outil possède sa propre copie de :
`GUI/Views/pages/SelectionPage.xaml`, `lib/viewmodels/SelectionPageVM.py`,
`lib/views/MainWindowView.py`, `lib/services/RenameService.py`,
`lib/services/TokenExpander.py`.

État actuel de la page de sélection : `ItemsControl ItemsSource="{Binding Items}"`
avec une `CheckBox IsChecked="{Binding IsSelected, Mode=TwoWay}"` par ligne.
Aucun filtre, aucune notion d'index de ligne ni de modificateur clavier.

Services existants réutilisables (extension-level, `lib/core/`) :

- `ListSelectionService` (`lib/core/list_selection.py`) — gère shift/ctrl,
  16 tests OK, **branché nulle part** aujourd'hui.
- `BulkEditService` (`lib/core/bulk_edit.py`) — `select_all` / `deselect_all` /
  `apply` / `toggle`, 39 tests OK.

## Objectifs

1. Barre de recherche filtrant les éléments affichés.
2. Multi-sélection Shift/Ctrl via un service dédié (déjà existant).
3. Tooltip lisible et stylisé « Fluent » en thème clair **et** sombre.
4. (Dette, isolée) Mutualiser `RenameService` / `TokenExpander` dupliqués.

## Décisions de cadrage (validées avec l'utilisateur)

- **Modèle de sélection** : les cases à cocher restent le contrôle ; le clic-ligne
  est enrichi pour fournir index + modificateurs au service.
- **Filtre** : simple, sans mémoire — « Tout sélectionner » agit sur la liste
  complète, y compris les éléments masqués par le filtre.
- **Refactor** : mutualiser au passage `RenameService` / `TokenExpander` dans le
  lib partagé de l'extension.

## Constat de faisabilité (vérifié par lecture directe)

- `ListSelectionService.handle_click(items, index, shift, ctrl)` :
  - clic simple (aucun modificateur) → **sélection exclusive** (désélectionne
    tout, garde `index`), déplace l'ancre ;
  - `ctrl=True` → **bascule** `items[index]` uniquement, déplace l'ancre ;
  - `shift=True` (ancre ≥ 0) → sélectionne la plage `[ancre, index]` inclusive,
    n'efface pas hors plage, ancre inchangée.
  La branche « clic simple » fait de l'exclusif : incompatible avec un modèle
  « cases à cocher qui s'accumulent ». Voir résolution ci-dessous.
- Les 4 copies de `RenameService.py` et les 4 copies de `TokenExpander.py` sont
  **identiques au code exécutable près** — elles ne diffèrent que par les
  docstrings (version la plus complète : `duplicate_sheets`). Le déplacement est
  donc un *safe isolated move*.

## Architecture cible

### Chantier 1 — Multi-sélection Shift/Ctrl

**Résolution du conflit de sémantique** (modèle « cases à cocher qui
s'accumulent ») :

- La `CheckBox` de chaque ligne devient un **indicateur visuel** :
  `IsHitTestVisible="False"`. Elle n'est plus cliquable indépendamment → pas de
  double-déclenchement (checkbox + handler ligne).
- **Tout le clic passe par un handler de ligne** posé sur le conteneur de la
  ligne (`Border`/`Grid` du `DataTemplate`), via
  `PreviewMouseLeftButtonDown`. Le handler :
  1. récupère l'item cliqué (`sender.DataContext`) et son **index dans la liste
     affichée** (`FilteredItems`) ;
  2. lit `System.Windows.Input.Keyboard.Modifiers` (Shift / Control) ;
  3. appelle le VM :
     - **Shift** → `handle_click(FilteredItems, index, shift=True)` (plage sur
       les éléments visibles) ;
     - **Ctrl** ou **aucun modificateur** →
       `handle_click(FilteredItems, index, ctrl=True)` (bascule 1 item + ancre).

- ✅ **Aucune modification de `ListSelectionService`.** La branche « exclusive »
  (clic simple) n'est simplement pas utilisée par ces pages ; elle reste
  disponible pour un futur consommateur `ListBox`.

Le VM détient **une** instance de `ListSelectionService(prop='IsSelected')`.
`reset()` de l'ancre est appelé au chargement de la liste **et** à chaque
changement de filtre (voir chantier 2).

### Chantier 2 — Barre de recherche (filtre)

- `SelectionPageVM` expose :
  - `FilterText` (property notifiante, `TwoWay` depuis un `TextBox`) ;
  - `FilteredItems` (`ObservableCollection`) reconstruite à chaque changement de
    `FilterText` ;
  - `Items` / `_all_items` : la **liste complète** reste intacte (source de
    vérité pour `selected_ids()` et le « Tout sélectionner »).
- Filtrage : substring **insensible à la casse et aux accents**, appliqué au N°,
  au Type et au Nom selon l'outil. Filtre vide → tous les éléments.
- `ItemsSource` du `ItemsControl` → `FilteredItems`.
- À chaque changement de `FilterText` : reconstruire `FilteredItems` **et**
  appeler `selection_service.reset()` (ancre invalidée car les index changent).
- **Portées distinctes, par conception** :
  - Shift-range et clics → opèrent sur `FilteredItems` (éléments visibles) ;
  - « Tout sélectionner » / « Tout désélectionner » → opèrent sur la liste
    complète via `BulkEditService.select_all/deselect_all(_all_items,
    'IsSelected')`.
- `HasSelection` et `selected_ids()` continuent de se calculer sur la liste
  complète.

### Chantier 3 — Tooltip Fluent + dark mode

- Ajouter un **style implicite** `TargetType="ToolTip"` (sans `x:Key`) dans
  `lib/ui/GUI/resources/Styles.xaml` **et** `lib/ui/GUI/resources/StylesDark.xaml`.
- Le style fixe explicitement **Background**, **Foreground** et **BorderBrush**
  via `DynamicResource` (le bug dark vient d'un fond clair par défaut sous un
  texte clair hérité), plus : `CornerRadius`, padding, bordure fine, ombre
  légère → rendu Fluent.
- ✅ S'applique à **tous** les tooltips automatiquement (aide tokens des
  `NamingPage.xaml`, futurs tooltips, etc.).

### Chantier 4 — Mutualisation (dette isolée) + bonus

- Créer `lib/core/rename_service.py` et `lib/core/token_expander.py` à partir de
  la version la plus documentée (`duplicate_sheets`).
- Mettre à jour les imports dans les 4 outils pour pointer vers le lib partagé,
  puis **supprimer les 4 copies** de chaque service.
- **Séquencé en commit(s) séparé(s), AVANT la feature**, pour rendre toute
  régression attribuable.
- **Bonus** : ajouter l'icône d'aide tokens (ⓘ) + tooltip manquante sur
  `OptionsPage.xaml` de `duplicate_sheets`, alignée sur les `NamingPage.xaml`.

## Impact fichiers

| Portée | Fichiers | Nature |
|--------|----------|--------|
| Partagé ×1 | `lib/core/rename_service.py`, `lib/core/token_expander.py` *(nouveaux)* | Move |
| Partagé ×1 | `lib/ui/GUI/resources/Styles.xaml`, `lib/ui/GUI/resources/StylesDark.xaml` | Style ToolTip |
| Par outil ×4 | `GUI/Views/pages/SelectionPage.xaml` | CheckBox display-only + TextBox recherche + handler ligne |
| Par outil ×4 | `lib/viewmodels/SelectionPageVM.py` | FilterText/FilteredItems + wiring ListSelectionService + BulkEditService |
| Par outil ×4 | `lib/views/MainWindowView.py` | Câblage event ligne → VM |
| Par outil ×4 | imports `RenameService` / `TokenExpander` | Pointer vers lib partagé |
| ×1 | `duplicate_sheets/GUI/Views/pages/OptionsPage.xaml` | Bonus icône d'aide |
| Tests | `lib/core/tests/` | Tests de la logique de filtre (Python pur) |

## Risques et points de vigilance

1. **Import du lib partagé** — 1re étape d'implémentation : confirmer à
   l'exécution que `from core.xxx import …` (ou l'import équivalent) se résout
   depuis chaque pushbutton (pyRevit ajoute `<extension>/lib` au `sys.path`).
   Si ce n'est pas le cas, revoir le mécanisme de partage avant tout déplacement.
2. **Double-fire clic** — neutralisé par `IsHitTestVisible="False"` sur la
   CheckBox ; tout passe par le handler de ligne.
3. **Cohérence index × filtre** — le handler passe toujours `FilteredItems` et un
   index relatif à cette liste ; l'ancre est réinitialisée à chaque changement de
   filtre.
4. **Pas de test runner Revit** — la logique testable (filtre, sélection) est en
   Python pur, couverte par des tests standalone ; la partie WPF est validée
   manuellement (Reload pyRevit + clic).

## Tests

- Étendre `lib/core/tests/` avec des tests de la logique de filtre (normalisation
  casse/accents, filtre vide, sous-ensemble).
- Réutiliser les tests existants `test_list_selection.py` / `test_bulk_edit.py`
  (inchangés).
- Validation manuelle par outil : recherche, Shift/Ctrl, Tout (dé)sélectionner,
  tooltip en clair et sombre.

## Hors périmètre

- Refonte MVVM plus large des pages.
- Passage à un `ListBox`/`DataGrid` avec modèle de sélection WPF natif.
- Toute modification fonctionnelle du renommage/duplication elle-même.
