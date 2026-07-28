# Modale de nommage — paramètres projet + aperçu de valeurs

Date : 2026-07-28
Périmètre : `418.tab/Export.panel/BatchExport.pushbutton` (modale NamingEditor)

## Objectif (goal utilisateur)

1. Les paramètres disponibles dans la palette doivent être les **paramètres
   du projet** (ProjectInformation), listés par nom réel.
2. L'aperçu en bas doit montrer la **valeur** du paramètre.
3. Les éléments comme la date passent dans une catégorie **Système**.
4. Les paramètres venant d'une feuille ou d'un jeu peuvent rester
   **génériques**.

## Décisions validées

- **Source « Projet »** = paramètres de l'élément `ProjectInformation`
  (énumérés dynamiquement depuis le modèle), remplaçant les 4 raccourcis
  génériques `{projet_*}` dans la palette.
- **Aperçu = « Projet seulement »** : seuls les jetons de paramètre projet
  sont résolus en valeurs ; `{numero}`/`{nom}`/`{titre}`/`{date}` restent
  **littéraux** dans l'aperçu.
- **Catégories/filtres** : Tout / Système / Feuille / Jeu / Projet
  (renommage `Carnet` → `Jeu`).
- **`{date}` reste littérale** dans l'aperçu (lecture fidèle de « Projet
  seulement ») — décision par défaut, révisable trivialement plus tard.

## Architecture

### `NamingService` (cœur)

1. **`_iter_project_params()`** (privé) — **une seule passe** sur l'élément
   `ProjectInformation` → liste de tuples `(nom, valeur)` (valeurs assainies
   via `_sanitize_resolved_value` ; on saute uniquement les noms vides et
   `_`-préfixés — PAS la liste `excluded_sheet_params`, qui ne concerne que
   les menus de mapping Oui/Non). *Source unique de vérité* pour
   nom ET valeur — évite qu'un badge apparaisse mais que sa valeur d'aperçu
   se résolve à `''` (ce qui arriverait avec deux chemins d'énumération
   distincts : `GetOrderedParameters` pour les badges vs `LookupParameter`
   pour les valeurs). `[]` sans doc / hors Revit.
2. **`project_param_tokens()`** (public) — depuis cette passe :
   `[{'token':'{param_projet:NOM}', 'label':'NOM', 'desc':'Projet — <valeur>',
   'source':'projet', 'value':<valeur>}, …]`.
3. **`available_tokens()`** réorganisé (jetons génériques statiques) :
   - `systeme` : `{date}`, `{date_jour}`, `{date_mois}`, `{date_annee}`
   - `feuille` : `{numero}`, `{nom}`, `{nom_tiret}`, `{nom_underscore}`,
     `{param:NOM}` (générique feuille)
   - `jeu` : `{titre}` (renommé depuis `carnet`)
   - **retire** les 4 `{projet_*}` et le `{param_projet:NOM}` générique de la
     liste statique (désormais dynamiques via `project_param_tokens()`).
4. **`_resolve_simple_token` conserve le support `projet_*`** : les motifs
   déjà enregistrés contenant `{projet_nom}` etc. continuent de se résoudre
   (retiré de la palette ≠ retiré du résolveur).
5. **`resolve_project_values(pattern)`** — résolveur d'**aperçu** : substitue
   uniquement les jetons de paramètre projet (`{param_projet:NOM}` + legacy
   `{projet_*}`) par leur valeur réelle (issue de la même passe / du cache
   projet) ; laisse **littéral** tout autre jeton. Ne lève jamais (repli :
   motif brut).

### `NamingEditorViewModel`

- `AvailableTokens` = `available_tokens()` (statique) **+** `project_param_tokens()`
  (dynamique), fusionnés.
- `_COULEUR_PAR_SOURCE` : `systeme`→`MediumGrayBrush`, `feuille`→`AccentBrush`,
  `jeu`→`SuccessBrush`, `projet`→`WarningBrush`.
- `_SOURCES_DISPONIBLES` : Tout / Système / Feuille / Jeu / Projet.
- `Apercu` = `naming_service.resolve_project_values(self._pattern)` (repli :
  motif brut si service absent).

### `NamingEditor.xaml`

- `DataTemplate.Triggers` des badges : ajouter `source='systeme'`→gris,
  renommer le trigger `carnet`→`jeu`. Carte d'aperçu inchangée (bind `Apercu`).

### `NamingEditorView`

- Aucun changement : `wire_filtre_source()` / `wire_tokens()` sont
  entièrement data-driven (`DataContext.valeur` / `.token`), aucun `'carnet'`
  codé en dur. Le renommage `carnet`→`jeu` se propage par les données.

## Comportement d'aperçu (explicite)

Conséquences de « Projet seulement » :
- **Nommage feuille** : l'aperçu ressemblera presque au motif brut (les
  feuilles utilisent rarement des params projet).
- **`{date}`** s'affiche littéralement `{date}` malgré sa valeur évidente.

## Wiring (déjà vérifié)

`script.py` → `MainViewModel(doc=doc)` → `NamingService(doc, config)` ; la
modale reçoit ce même service (`getattr(vm, '_naming_service', None)`), donc
`_naming_service._doc` est non-None en Revit. Énumération viable.

## Tests

- Faux `naming_service` exposant `project_param_tokens()` +
  `resolve_project_values()` avec des `(nom, valeur)` connus.
- Mise à jour des tests existants : source `carnet`→`jeu`,
  `{projet_nom}` retiré de la palette statique, `Apercu` résout les valeurs
  projet, nouvelle source/filtre `systeme`.
- Vérification hors Revit (logique VM/service). Couleurs de badge, filtre
  Système, aperçu-live : à confirmer au reload Revit.

## Fichiers touchés

- `lib/services/NamingService.py`
- `lib/viewmodels/NamingEditorViewModel.py`
- `GUI/Modals/NamingEditor.xaml`
- `tests/test_naming_service.py`, `tests/test_naming_editor_viewmodel.py`
