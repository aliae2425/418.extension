# Refactor des outils `Tools.panel/col1.stack` — Design

- **Date** : 2026-07-24
- **Périmètre** : les 9 outils EF-Tools de `418.tab/Tools.panel/col1.stack` (2 duplication + 7 Rename) et la lib EF rapatriée (`lib/Renaming`, `lib/Selection`, `lib/Snippets`).
- **Objectif** : réécrire ces outils sur la charte WPF du projet (coquille commune `BaseWindow` + thème partagé + MVVM), en nettoyant la lib EF rapatriée et en promouvant les utilitaires transverses vers `lib/core`.

---

## 1. Contexte et constat

Les outils de `col1.stack` sont des scripts **EF-Tools** (Erik Frits) mono-fichier, basés sur `pyrevit.forms.WPFWindow`, avec branding EF (bannières ASCII, hyperliens « EF-Tools », palette bleu foncé/magenta/aqua) et textes anglais.

**Ils sont tous cassés en l'état** : ils dépendent d'un framework EF dont une partie a été rapatriée dans `lib/` (`Renaming`, `Selection`, `Snippets`) mais dont le 4ᵉ package, **`GUI.forms`, reste manquant**. Or `lib/Snippets/_selection.py` fait un import top-level non gardé `from GUI.forms import select_from_dict` (ligne 23) : c'est un blocker qui empêche même les outils de duplication de se charger.

Cible du projet (référence : `418.tab/Audit.panel/Audit.pushbutton`, « 1er consommateur de la coquille commune ») :
- Chargement XAML via `XamlReader.Load` (pas de `x:Class`, pas de code-behind).
- `lib/ui/base/BaseWindow` fusionne les dictionnaires de thème après parse, câble `TitleBar` (DragMove) + boutons Min/Max/Close.
- Thème partagé `lib/ui/GUI/resources/` (`Colors/Styles` + variantes `Dark`), référencé en `DynamicResource`.
- MVVM : `script.py` → `MainViewModel` + `MainWindowView`, VM dérivant de `lib/ui/base/BaseViewModel`.
- `lib/core/AppPaths` résout `resources_dir()` vers le thème partagé.

**Découverte** : `418.tab/Manage.panel` contient déjà `ManageView / ManageSheet / ManageFiltre / ManageMatérial` en MVVM charte mais **vides** (VM de 29 lignes, zéro logique rename). Destination probable de la refonte Rename — **à confirmer au Lot B**.

---

## 2. Décisions cadrées (validées)

| Sujet | Décision |
|---|---|
| Structure globale | **Un seul refactor, 3 phases** ; la lib nettoyée est la fondation des 2 lots d'outils. |
| `GUI.forms` | **Refactorer / supprimer** : remplacer `select_from_dict` / `my_WPF` / `ListItem` / `FindReplace` par `pyrevit.forms.SelectFromList` + une petite modale charte. Éliminer la dépendance EF. |
| Duplication | **MVVM complet**, calqué sur Audit. 2 outils distincts, **même patron**. |
| Rename | **Refonte fonctionnelle**, mais **haute altitude** dans ce spec (décisions produit reportées à un brainstorming Lot B dédié). |
| Ampleur Phase 0 | **Nettoyage complet** de la lib EF (21 modules : Snippets 18 + Selection 3 + Renaming), séquencé **par vagues** (surface consommée d'abord). |
| Promotion `core` | `_context_manager` → `core/transaction`, `_convert` → `core/units`, `_selection` → `core/selection`. |
| UX duplication | Coquille **à rail** avec pages **Sélection** / **Options** ; plus de modale bloquante. |

---

## 3. Phase 0 — Fondation `lib` / `core`

### 3.a Éliminer `GUI.forms` (blocker prioritaire)
- Créer une **modale de sélection charte** (sur `BaseWindow`) reproduisant le service rendu par `select_from_dict` : sélection simple/multiple depuis un dictionnaire `{libellé: élément}`. Alternative légère quand une simple liste suffit : `pyrevit.forms.SelectFromList`.
- Remplacer `my_WPF` / `ListItem` / `FindReplace` (fenêtres EF) par les équivalents charte au moment où leurs consommateurs sont portés.
- Purger l'import top-level cassé dans `lib/Snippets/_selection.py` et `lib/Snippets/_groups.py`.
- **Critère de succès** : plus aucune occurrence de `from GUI.forms` / `from GUI import forms` dans le repo ; `import lib.core.selection` réussit hors contexte EF.

### 3.b Promotion vers `core`
Créer trois modules `core`, chacun avec en-tête projet (`from __future__ import unicode_literals`, `# -*- coding: utf-8 -*-`), gardes d'import `try/except` (fallback `None`), docstrings FR, zéro branding EF :

| Module cible | Source EF | API principale | Consommateurs |
|---|---|---|---|
| `lib/core/transaction.py` | `Snippets/_context_manager` | `ef_Transaction` (context manager de transaction), `try_except` | tous les Rename, duplication |
| `lib/core/units.py` | `Snippets/_convert` | `convert_internal_to_m`, conversions d'unités | LevelsElevation |
| `lib/core/selection.py` | `Snippets/_selection` | `get_selected_sheets` / `get_selected_views` / `get_selected_elements`, pickers | duplication + Rename |

- Chaque module isole une responsabilité claire, testable hors Revit (imports Revit gardés).
- Les anciens chemins `Snippets/_*` **restent en place** : ils ne sont consommés que par les outils de renommage (Phase 2, refactorés plus tard). En Phase 0/1 on **duplique la logique vers `core.*`** et on redirige les consommateurs duplication ; le nettoyage/suppression des chemins EF se fait quand la Phase 2 porte les Rename.

### 3.c Socle Rename charte
- `lib/Renaming/BaseClass_FindReplace` + `lib/Renaming/GUI_BaseRename.xaml` → rebasés sur `BaseWindow` + thème partagé. Suppression du branding EF (hyperlien, footer version EF, header custom).
- Ce socle sert la Phase 2 (Rename). Il est refactoré en Phase 0 mais **consommé** en Phase 2.

### 3.d Nettoyage complet du reste (par vagues)
Normaliser les modules EF restants (Snippets 18, Selection 3) à la convention projet : en-têtes, gardes d'import, retrait des bannières ASCII EF / hyperliens / textes UI anglais, docstrings FR sur les parties touchées.

**Séquencement par vagues** (livrer tôt, ne pas tout bloquer) :
1. **Vague 1 — surface consommée** par les 9 outils : `_selection`, `_context_manager`, `_convert`, `_variables` (dépendance de `_selection`), `Renaming/*`. → débloque Phases 1 et 2.
2. **Vague 2+** — reste de Snippets/Selection module par module, chacun sa passe de test.

Chaque vague est **testable** (`python module.py` hors Revit pour la logique pure ; smoke-test Revit après Reload pour l'UI).

---

## 4. Phase 1 — Duplication (MVVM complet)

Deux outils distincts, **même patron** : `duplicate_sheets.pushbutton` et `views_duplicate.pushbutton`.

### 4.a Architecture (par outil)
```
<outil>.pushbutton/
├── script.py                 → instancie VM + View (patron Audit)
├── GUI/Views/MainWindow.xaml → coquille borderless + rail + host de pages
├── GUI/Views/pages/
│   ├── SelectionPage.xaml    → page « Sélection »
│   └── OptionsPage.xaml       → page « Options de duplication »
└── lib/
    ├── viewmodels/  (MainViewModel + sous-VM par page)
    ├── views/       (MainWindowView)
    └── services/    (logique de duplication)
```

### 4.b Coquille à rail (UX validée)
- Fenêtre borderless (`WindowChrome`, `TitleBar` draggable, boutons Min/Max/Close), tout en `DynamicResource`, thème clair/sombre — calquée sur `Audit/GUI/Views/MainWindow.xaml`.
- **Rail** avec deux entrées : **Sélection** et **Options de duplication** (toutes deux accessibles à tout moment).
- **Comportement au lancement** :
  - Sélection Revit non vide → ouvrir directement la page **Options**.
  - Sélection vide → ouvrir la page **Sélection** (⚠️ **remplace l'ancienne modale bloquante**).
- La page Sélection alimente la liste des éléments à dupliquer ; la page Options lit cette sélection.

### 4.c Pages
- **Sélection** :
  - `duplicate_sheets` → sélection de feuilles.
  - `views_duplicate` → sélection de vues.
  - S'appuie sur `core/selection` (et la modale charte de §3.a si besoin d'une liste enrichie).
- **Options** :
  - `duplicate_sheets` : nommage (find/replace/préfixe/suffixe pour ViewName, SheetNumber, SheetName), éléments inclus (vues, légendes, nomenclatures, images, lignes, texte, nuages, DWG, symboles, cotes, révisions additionnelles), options « utiliser existant / dupliquer » (légendes, nomenclatures), options de duplication de vue (Duplicate / WithDetailing / AsDependent), bouton **Lancer**.
  - `views_duplicate` : options de duplication + nombre de copies, bouton **Lancer**.

### 4.d Logique métier
- **Préservée fonctionnellement** ; déplacée des `MyWindow` EF vers un **service de duplication** (`lib/services/`) piloté par le VM.
- Transactions via `core/transaction` ; sélection via `core/selection`.
- Nettoyage de noms via `lib/core/sanitize` (canonique projet) au lieu du `remove_special_charachter` EF.
- Textes FR ; branding EF supprimé.

### 4.e Critères de succès Phase 1
- Les 2 outils se chargent et s'affichent à la charte (clair + sombre).
- Le flux rail/pages fonctionne (lancement selon sélection, navigation).
- La duplication produit le même résultat qu'avant (feuilles + vues + éléments inclus + nommage).
- Aucun import EF résiduel (`Snippets.*`, `GUI.forms`, hyperlien EF).

---

## 5. Phase 2 — Rename (haute altitude)

**Non spécifié en détail** : nécessite un brainstorming Lot B dédié (décisions produit). Ce spec fixe seulement le périmètre et les dépendances.

- **Périmètre** : 6 FindReplace (Views, Sheets, Types, RoomNames, Materials, Filters) + LevelsElevation.
- **Dépendances Phase 0** : socle `Renaming/BaseClass_FindReplace` charte (§3.c), `core/transaction`, `core/selection`, `core/units` (Levels), modale de sélection charte (§3.a).
- **Questions ouvertes à trancher au Lot B** :
  1. Destination : remplir les outils **`Manage.panel`** existants (vides) **ou** rester dans `Tools.panel/Rename.pulldown` ?
  2. Fusion des 6 FindReplace en **un outil unifié** (sélecteur de type dans le rail) **ou** outils séparés ?
  3. Fonctionnalités : regex ? aperçu avant/après ? undo ?
  4. Couverture de Types / RoomNames / Levels qui n'ont **pas** d'équivalent `Manage.panel`.

---

## 6. Séquencement & tests

1. **Phase 0 Vague 1** (surface consommée + `GUI.forms` éliminé + 3 modules `core`) → débloque tout.
2. **Phase 1** (duplication MVVM, 2 outils).
3. **Phase 0 Vagues 2+** (reste du nettoyage EF) — peut avancer en parallèle après la Vague 1.
4. **Phase 2** (Rename) — après son brainstorming dédié.

**Stratégie de test** (« on fera des vagues de test ») : chaque vague / phase est validée isolément — logique pure via `python module.py` hors Revit ; UI via **pyRevit → Reload** puis clic (ou clic droit → Run script sur le bouton). Pas de build/lint/test-runner configuré (cf. `CLAUDE.md`).

---

## 7. Risques & points d'attention

- **Nettoyage complet (21 modules)** = le plus gros poste ; maîtrisé par le séquencement en vagues (valeur livrée dès la Vague 1).
- **Double régime d'import** (pyRevit vs standalone) : conserver le patron `try/except` du projet (cf. `MainViewModel.py` / `BaseWindow.py`).
- **Suppression de la modale bloquante** en duplication : changement de comportement voulu — à re-tester explicitement (sélection vide → page Sélection, pas d'`alert` bloquant).
- **Anciens chemins `Snippets/_*`** : consommés uniquement par les outils de renommage (Phase 2). Ils restent en place jusqu'à la Phase 2 ; en Phase 0/1 on promeut la logique vers `core.*` sans supprimer les chemins EF (pas de consommateurs externes à `col1.stack`).
