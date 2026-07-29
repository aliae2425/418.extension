# Recherche + multi-sélection + tooltip Fluent — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une barre de recherche et la multi-sélection Shift/Ctrl aux 4 pages de sélection (dupliquer/renommer feuilles/vues), corriger le tooltip en dark mode (style Fluent), et mutualiser les services dupliqués.

**Architecture:** Toute la logique testable vit dans le lib partagé de l'extension (`lib/core/`, déjà sur `sys.path` — les pushbuttons importent déjà `from ui.base…` et `from core…`). Un unique `SelectionListController` (Python pur) compose `ListSelectionService` (existant), `TextFilterService` (nouveau) et `BulkEditService` (existant). Chaque `SelectionPageVM` par outil devient un mince adaptateur WPF qui délègue au controller. La vue (`MainWindowView`) pose **un seul** handler `PreviewMouseLeftButtonDown` sur l'`ItemsControl` et remonte (index affiché + modificateurs) au VM.

**Tech Stack:** Python 2/3 (`from __future__ import unicode_literals`), IronPython sous pyRevit, WPF/XAML chargé via `XamlReader.Load` (pas de code-behind), tests `unittest` standalone.

## Global Constraints

- Chaque fichier Python commence par `# -*- coding: utf-8 -*-` puis `from __future__ import unicode_literals`. (verbatim)
- Tout texte UI, commentaire et message de commit en **français**.
- Aucun build/linter/test-runner : les tests sont des scripts `unittest` lancés par `python <fichier>.py`.
- Imports inter-couches en `try/except` avec fallback ; ne jamais casser l'exécution hors Revit.
- Tout brush/style de thème via `DynamicResource` (jamais `StaticResource` de couleur).
- Cible Revit 2026 minimum.
- **Ne jamais committer sans accord explicite de l'utilisateur** (préférence utilisateur). Les étapes « Commit » ci-dessous sont préparées mais exécutées seulement après feu vert.
- `lib/core/` = snake_case pour les fichiers, CamelCase pour les classes (ex. `list_selection.py` → `ListSelectionService`).

## Périmètre — 4 outils concernés

| Clé | Racine (`418.tab/Tools.panel/col1.stack/…`) | Item VM | Getters colonnes | id |
|-----|----|----|----|----|
| `dup_sheets` | `duplicate_sheets.pushbutton` | `SheetItemVM` | `Numero`, `Nom` | `SheetId` |
| `dup_views` | `views_duplicate.pushbutton` | `ViewItemVM` | `TypeLabel`, `Nom` | `ViewId` |
| `ren_views` | `Rename.pulldown/FindReplace - Views.pushbutton` | `ViewItemVM` | `TypeLabel`, `Nom` | `ViewId` |
| `ren_sheets` | `Rename.pulldown/FindReplace_Sheets.pushbutton` | `SheetItemVM` | `Numero`, `Nom` | `SheetId` |

## Structure des fichiers

**Créés (partagés) :**
- `lib/core/text_filter.py` — `TextFilterService` (filtrage insensible casse/accents)
- `lib/core/selection_list.py` — `SelectionListController` (intègre sélection + filtre + bulk)
- `lib/core/rename_service.py` — `RenameService` (déplacé depuis les copies)
- `lib/core/token_expander.py` — `TokenExpander` (déplacé depuis les copies)
- `lib/core/tests/test_text_filter.py`, `test_selection_list.py`, `test_rename_service.py`, `test_token_expander.py`

**Modifiés (partagés) :**
- `lib/ui/GUI/resources/Styles.xaml`, `lib/ui/GUI/resources/StylesDark.xaml` — style implicite `ToolTip`

**Modifiés (×4 outils) :**
- `lib/viewmodels/SelectionPageVM.py` — délègue au controller, expose `FilterText`, `FilteredItems`, `SelectAllCommand`
- `GUI/Views/pages/SelectionPage.xaml` — TextBox recherche + boutons tout (dé)sélectionner + CheckBox display-only + `x:Name` sur l'ItemsControl
- `lib/views/MainWindowView.py` — handler unique de clic ligne + câblage recherche/boutons
- imports `RenameService`/`TokenExpander` des consommateurs → `from core.…`

**Supprimés :** les 4 copies de `lib/services/RenameService.py` et `lib/services/TokenExpander.py`, et les tests per-tool `views_duplicate.pushbutton/tests/test_rename_service.py` + `test_token_expander.py`.

---

## PHASE 1 — Mutualisation des services (isolée, AVANT la feature)

### Task 1 : Déplacer TokenExpander dans le lib partagé

**Files:**
- Create: `lib/core/token_expander.py`
- Create: `lib/core/tests/test_token_expander.py`
- Modify (imports): `…/{dup_sheets,dup_views,ren_views,ren_sheets}/lib/services/RenameService.py:6-8`
- Delete (après validation) : les 4 `…/lib/services/TokenExpander.py`, `dup_views/tests/test_token_expander.py`

**Interfaces:**
- Produces: `from core.token_expander import TokenExpander` ; API inchangée : `TokenExpander().expand(template, index=1, context=None)` et la méthode listant les tokens reconnus.

- [ ] **Step 1 : Créer le fichier partagé**

Copier **à l'identique** le contenu de `…/duplicate_sheets.pushbutton/lib/services/TokenExpander.py` (version la plus documentée) vers `lib/core/token_expander.py`. Ne rien changer au code.

- [ ] **Step 2 : Écrire le test partagé**

Créer `lib/core/tests/test_token_expander.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.token_expander import TokenExpander


class TestTokenExpander(unittest.TestCase):

    def test_token_inconnu_reste_intact(self):
        self.assertEqual(TokenExpander().expand(u'{inconnu}'), u'{inconnu}')

    def test_index_alimente_n(self):
        self.assertEqual(TokenExpander().expand(u'p{n}', index=2), u'p2')

    def test_context_resout_token_custom(self):
        out = TokenExpander().expand(u'{type}', context={u'type': u'Plan'})
        self.assertEqual(out, u'Plan')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3 : Lancer le test (doit passer, code inchangé)**

Run: `python lib/core/tests/test_token_expander.py`
Expected: `OK` (3 tests). Si un token diffère (ex. `{n}` non supporté), lire `lib/core/token_expander.py` et aligner l'assertion sur le comportement réel — ne pas modifier le service.

- [ ] **Step 4 : Repointer les imports de RenameService**

Dans chacune des 4 copies de `lib/services/RenameService.py`, remplacer le bloc (lignes 5-8) :

```python
try:
    from lib.services.TokenExpander import TokenExpander
except Exception:
    from services.TokenExpander import TokenExpander
```
par :
```python
try:
    from core.token_expander import TokenExpander
except Exception:
    from lib.core.token_expander import TokenExpander
```

- [ ] **Step 5 : Supprimer les copies TokenExpander + test per-tool**

Supprimer les 4 `…/lib/services/TokenExpander.py` et `dup_views/tests/test_token_expander.py`.

- [ ] **Step 6 : Vérifier**

Run: `python lib/core/tests/test_token_expander.py`
Expected: `OK`. Vérifier qu'aucun `TokenExpander.py` ne subsiste dans les outils :
Run: `git ls-files "*services/TokenExpander.py"` → **aucune sortie**.

- [ ] **Step 7 : Commit** *(après accord utilisateur)*

```bash
git add lib/core/token_expander.py lib/core/tests/test_token_expander.py "418.tab"
git commit -m "refactor(core): mutualise TokenExpander dans lib/core partagé"
```

### Task 2 : Déplacer RenameService dans le lib partagé

**Files:**
- Create: `lib/core/rename_service.py`, `lib/core/tests/test_rename_service.py`
- Modify (imports consommateurs) :
  - `dup_sheets/lib/viewmodels/OptionsPageVM.py:20-22`
  - `dup_sheets/lib/services/DuplicationSheetsService.py:39-42`
  - `dup_views/lib/viewmodels/OptionsPageVM.py:20-22`
  - `dup_views/lib/services/ViewsDuplicationService.py:19-22`
  - `ren_views/lib/viewmodels/NamingPageVM.py:20-22`, `ren_views/lib/services/RenameViewsService.py:16-18`
  - `ren_sheets/lib/viewmodels/NamingPageVM.py:20-22`, `ren_sheets/lib/services/RenameSheetsService.py:16-18`
- Delete: les 4 `…/lib/services/RenameService.py`, `dup_views/tests/test_rename_service.py`

**Interfaces:**
- Consumes: `from core.token_expander import TokenExpander` (Task 1)
- Produces: `from core.rename_service import RenameService` ; API inchangée : `RenameService(prefixe, rechercher, remplacer, suffixe, use_regex, expander).apply(name, index=1, context=None)`, `.regex_error`, `.is_valid`.

- [ ] **Step 1 : Créer le fichier partagé**

Copier `…/duplicate_sheets.pushbutton/lib/services/RenameService.py` vers `lib/core/rename_service.py`. Puis, dans ce nouveau fichier, remplacer l'import TokenExpander (lignes 5-8) par celui de Task 1 Step 4.

- [ ] **Step 2 : Écrire le test partagé**

Créer `lib/core/tests/test_rename_service.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.rename_service import RenameService


class TestRenameService(unittest.TestCase):

    def test_litteral_replace(self):
        svc = RenameService(rechercher=u'A', remplacer=u'B')
        self.assertEqual(svc.apply(u'AAA'), u'BBB')

    def test_prefixe_suffixe(self):
        svc = RenameService(prefixe=u'[', suffixe=u']')
        self.assertEqual(svc.apply(u'x'), u'[x]')

    def test_regex_invalide_retourne_nom_intact(self):
        svc = RenameService(rechercher=u'(', use_regex=True)
        self.assertEqual(svc.apply(u'abc'), u'abc')
        self.assertTrue(svc.regex_error)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3 : Lancer le test**

Run: `python lib/core/tests/test_rename_service.py`
Expected: `OK` (3 tests). Ajuster les assertions au comportement réel si besoin (ne pas modifier le service).

- [ ] **Step 4 : Repointer les 8 imports consommateurs**

Dans chaque fichier listé (Files), remplacer le bloc :
```python
    from lib.services.RenameService import RenameService
except ...:
    from services.RenameService import RenameService
```
par :
```python
    from core.rename_service import RenameService
except Exception:
    from lib.core.rename_service import RenameService
```
(Conserver la structure `try/except` locale existante de chaque fichier.)

- [ ] **Step 5 : Supprimer les copies**

Supprimer les 4 `…/lib/services/RenameService.py` et `dup_views/tests/test_rename_service.py`.

- [ ] **Step 6 : Vérifier**

Run: `python lib/core/tests/test_rename_service.py` → `OK`
Run: `git ls-files "*services/RenameService.py"` → **aucune sortie**

- [ ] **Step 7 : Validation Revit (manuelle)**

Reload pyRevit → ouvrir chacun des 4 outils → vérifier que la fenêtre s'ouvre et que l'aperçu de renommage fonctionne (preuve que les imports partagés se résolvent à l'exécution).

- [ ] **Step 8 : Commit** *(après accord)*

```bash
git add lib/core/rename_service.py lib/core/tests/test_rename_service.py "418.tab"
git commit -m "refactor(core): mutualise RenameService dans lib/core partagé"
```

---

## PHASE 2 — Services partagés de filtre et de liste

### Task 3 : TextFilterService (filtrage insensible casse/accents)

**Files:**
- Create: `lib/core/text_filter.py`, `lib/core/tests/test_text_filter.py`

**Interfaces:**
- Produces:
  - `from core.text_filter import TextFilterService`
  - `TextFilterService().filter(items, text, getters)` → liste des items dont **au moins un** `getter(item)` contient `text` (comparaison normalisée). `text` vide/`None` → renvoie `list(items)`. `getters` = liste de callables `item -> unicode`.
  - `TextFilterService.normalize(s)` → `unicode` minuscule sans accents.

- [ ] **Step 1 : Écrire les tests**

Créer `lib/core/tests/test_text_filter.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.text_filter import TextFilterService


class _Row(object):
    def __init__(self, a, b):
        self.A = a
        self.B = b


def _getters():
    return [lambda r: r.A, lambda r: r.B]


class TestTextFilter(unittest.TestCase):

    def setUp(self):
        self.svc = TextFilterService()
        self.rows = [_Row(u'A-101', u'Plan RDC'),
                     _Row(u'A-102', u'Élévation'),
                     _Row(u'B-201', u'Coupe AA')]

    def test_texte_vide_renvoie_tout(self):
        self.assertEqual(len(self.svc.filter(self.rows, u'', _getters())), 3)

    def test_none_renvoie_tout(self):
        self.assertEqual(len(self.svc.filter(self.rows, None, _getters())), 3)

    def test_filtre_substring_insensible_casse(self):
        out = self.svc.filter(self.rows, u'plan', _getters())
        self.assertEqual([r.A for r in out], [u'A-101'])

    def test_filtre_insensible_accents(self):
        # 'elevation' (sans accent) doit trouver 'Élévation'
        out = self.svc.filter(self.rows, u'elevation', _getters())
        self.assertEqual([r.A for r in out], [u'A-102'])

    def test_filtre_sur_second_getter(self):
        out = self.svc.filter(self.rows, u'coupe', _getters())
        self.assertEqual([r.A for r in out], [u'B-201'])

    def test_aucun_match(self):
        self.assertEqual(self.svc.filter(self.rows, u'zzz', _getters()), [])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer (doit échouer)**

Run: `python lib/core/tests/test_text_filter.py`
Expected: FAIL — `ImportError: No module named text_filter`.

- [ ] **Step 3 : Implémenter le service**

Créer `lib/core/text_filter.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unicodedata


class TextFilterService(object):
    """Filtre une liste d'items par sous-chaîne, insensible à la casse et aux
    accents. Aucune dépendance Revit/WPF — testable en Python pur."""

    @staticmethod
    def normalize(value):
        """Minuscule, sans accents. Tolère None et non-chaînes."""
        if value is None:
            return u''
        try:
            text = value if isinstance(value, type(u'')) else u'{0}'.format(value)
        except Exception:
            return u''
        decomposed = unicodedata.normalize('NFKD', text)
        stripped = u''.join(c for c in decomposed if not unicodedata.combining(c))
        return stripped.lower()

    def filter(self, items, text, getters):
        """Renvoie les items dont au moins un getter contient ``text``.

        text vide/None → tous les items. getters = callables item -> texte.
        """
        items = list(items or [])
        needle = self.normalize(text).strip()
        if not needle:
            return items
        out = []
        for item in items:
            for getter in getters:
                try:
                    hay = self.normalize(getter(item))
                except Exception:
                    hay = u''
                if needle in hay:
                    out.append(item)
                    break
        return out
```

- [ ] **Step 4 : Lancer (doit passer)**

Run: `python lib/core/tests/test_text_filter.py`
Expected: `OK` (6 tests).

- [ ] **Step 5 : Commit** *(après accord)*

```bash
git add lib/core/text_filter.py lib/core/tests/test_text_filter.py
git commit -m "feat(core): TextFilterService (filtre insensible casse/accents)"
```

### Task 4 : SelectionListController (intègre sélection + filtre + bulk)

**Files:**
- Create: `lib/core/selection_list.py`, `lib/core/tests/test_selection_list.py`

**Interfaces:**
- Consumes: `ListSelectionService` (`core.list_selection`), `TextFilterService` (Task 3), `BulkEditService` (`core.bulk_edit`).
- Produces: `from core.selection_list import SelectionListController` avec :
  - `__init__(self, items, id_getter, filter_getters, prop=u'IsSelected')`
  - `all_items` (property) → liste complète
  - `filtered_items` (property) → sous-ensemble courant (= tout si filtre vide)
  - `filter_text` (property get/set ; set reconstruit `filtered_items` et **reset l'ancre**)
  - `handle_row_click(index, shift=False, ctrl=False)` → applique la sélection sur `filtered_items` ; **clic simple et Ctrl** basculent 1 item (branche `ctrl=True`), **Shift** sélectionne la plage
  - `select_all()` / `deselect_all()` → sur `all_items`
  - `selected_ids()` → `[id_getter(it) for it in all_items if getattr(it, prop)]`
  - `has_selection()` → bool

- [ ] **Step 1 : Écrire les tests**

Créer `lib/core/tests/test_selection_list.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.selection_list import SelectionListController


class _Item(object):
    def __init__(self, iid, a, b):
        self.Id = iid
        self.A = a
        self.B = b
        self.IsSelected = False


def _make():
    return [_Item(1, u'A-101', u'Plan RDC'),
            _Item(2, u'A-102', u'Plan R+1'),
            _Item(3, u'B-201', u'Coupe AA')]


def _ctrl(items):
    return SelectionListController(
        items,
        id_getter=lambda it: it.Id,
        filter_getters=[lambda it: it.A, lambda it: it.B])


class TestSelectionList(unittest.TestCase):

    def test_clic_simple_bascule_un_item(self):
        c = _ctrl(_make())
        c.handle_row_click(0)
        self.assertEqual(c.selected_ids(), [1])
        c.handle_row_click(1)              # accumule (pas d'exclusif)
        self.assertEqual(c.selected_ids(), [1, 2])

    def test_clic_simple_rebascule(self):
        c = _ctrl(_make())
        c.handle_row_click(0)
        c.handle_row_click(0)
        self.assertEqual(c.selected_ids(), [])

    def test_shift_selectionne_la_plage(self):
        c = _ctrl(_make())
        c.handle_row_click(0)             # ancre 0
        c.handle_row_click(2, shift=True)
        self.assertEqual(c.selected_ids(), [1, 2, 3])

    def test_filtre_restreint_filtered_items(self):
        c = _ctrl(_make())
        c.filter_text = u'plan'
        self.assertEqual([it.Id for it in c.filtered_items], [1, 2])

    def test_shift_agit_sur_le_sous_ensemble_filtre(self):
        c = _ctrl(_make())
        c.filter_text = u'plan'           # visibles : items 1,2
        c.handle_row_click(0)             # -> item 1
        c.handle_row_click(1, shift=True) # plage sur filtré -> 1,2
        self.assertEqual(c.selected_ids(), [1, 2])

    def test_changement_de_filtre_reset_ancre(self):
        c = _ctrl(_make())
        c.handle_row_click(0)             # ancre 0 sur liste complète
        c.filter_text = u'plan'           # reset ancre
        c.handle_row_click(1, shift=True) # ancre perdue -> clic simple sur index 1
        self.assertEqual(c.selected_ids(), [1, 2])  # item 1 restait coché + bascule item 2

    def test_select_all_agit_sur_liste_complete_meme_filtree(self):
        c = _ctrl(_make())
        c.filter_text = u'plan'           # n'affiche que 1,2
        c.select_all()
        self.assertEqual(c.selected_ids(), [1, 2, 3])  # inclut le masqué

    def test_deselect_all(self):
        c = _ctrl(_make())
        c.select_all()
        c.deselect_all()
        self.assertEqual(c.selected_ids(), [])

    def test_has_selection(self):
        c = _ctrl(_make())
        self.assertFalse(c.has_selection())
        c.handle_row_click(0)
        self.assertTrue(c.has_selection())


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer (doit échouer)**

Run: `python lib/core/tests/test_selection_list.py`
Expected: FAIL — `ImportError`.

- [ ] **Step 3 : Implémenter le controller**

Créer `lib/core/selection_list.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from core.list_selection import ListSelectionService
from core.text_filter import TextFilterService
from core.bulk_edit import BulkEditService


class SelectionListController(object):
    """Orchestre la sélection multi-items (shift/ctrl), le filtrage texte et les
    actions de masse pour une page de sélection. Python pur, testable.

    - clic simple  : bascule l'item (accumulation, pas d'exclusif)
    - Ctrl+clic    : bascule l'item
    - Shift+clic   : plage [ancre, index] sur les items AFFICHÉS (filtrés)
    - select_all / deselect_all : sur la liste COMPLÈTE (y compris masqués)
    """

    def __init__(self, items, id_getter, filter_getters, prop=u'IsSelected'):
        self._all = list(items or [])
        self._id_getter = id_getter
        self._filter_getters = list(filter_getters or [])
        self._prop = prop
        self._selection = ListSelectionService(prop=prop)
        self._filter = TextFilterService()
        self._bulk = BulkEditService()
        self._filter_text = u''
        self._filtered = list(self._all)

    @property
    def all_items(self):
        return self._all

    @property
    def filtered_items(self):
        return self._filtered

    @property
    def filter_text(self):
        return self._filter_text

    @filter_text.setter
    def filter_text(self, value):
        self._filter_text = value or u''
        self._filtered = self._filter.filter(
            self._all, self._filter_text, self._filter_getters)
        self._selection.reset()   # index invalidés -> ancre perdue

    def handle_row_click(self, index, shift=False, ctrl=False):
        if shift:
            self._selection.handle_click(self._filtered, index, shift=True)
        else:
            # clic simple ET ctrl -> bascule ponctuelle (case reste le contrôle)
            self._selection.handle_click(self._filtered, index, ctrl=True)

    def select_all(self):
        self._bulk.select_all(self._all, self._prop)

    def deselect_all(self):
        self._bulk.deselect_all(self._all, self._prop)

    def selected_ids(self):
        return [self._id_getter(it) for it in self._all
                if getattr(it, self._prop, False)]

    def has_selection(self):
        return any(getattr(it, self._prop, False) for it in self._all)
```

- [ ] **Step 4 : Lancer (doit passer)**

Run: `python lib/core/tests/test_selection_list.py`
Expected: `OK` (9 tests). Si `BulkEditService.select_all` attend un autre nom d'argument, lire `lib/core/bulk_edit.py` et ajuster l'appel (la signature documentée est `select_all(items, prop)`).

- [ ] **Step 5 : Commit** *(après accord)*

```bash
git add lib/core/selection_list.py lib/core/tests/test_selection_list.py
git commit -m "feat(core): SelectionListController (sélection shift/ctrl + filtre + bulk)"
```

---

## PHASE 3 — Tooltip Fluent (clair + sombre) + bonus icône

### Task 5 : Style implicite ToolTip dans Styles.xaml et StylesDark.xaml

**Files:**
- Modify: `lib/ui/GUI/resources/Styles.xaml`
- Modify: `lib/ui/GUI/resources/StylesDark.xaml`
- Modify: `dup_sheets/GUI/Views/pages/OptionsPage.xaml` (bonus icône d'aide)

**Interfaces:**
- Produces: un `Style` implicite (`TargetType="ToolTip"`, sans `x:Key`) appliqué automatiquement à tous les `<ToolTip>`. Requiert que les brushes `CardBackgroundBrush` (ou équivalent fond de surface), `TextPrimaryBrush`, `ControlBorderBrush` existent dans les deux thèmes — sinon utiliser les noms réellement présents (vérifier `Colors.xaml` / `ColorsDark.xaml`).

- [ ] **Step 1 : Vérifier les noms de brushes disponibles**

Lire `lib/ui/GUI/resources/Colors.xaml` et `ColorsDark.xaml`. Noter le brush de fond de surface (carte/popup) et le brush de bordure exacts présents dans **les deux** fichiers. Utiliser ces noms à l'étape suivante.

- [ ] **Step 2 : Ajouter le style dans Styles.xaml**

Ajouter, avant la balise fermante `</ResourceDictionary>` de `lib/ui/GUI/resources/Styles.xaml` :

```xml
  <!-- ToolTip Fluent : fond/texte/bordure pilotés par le thème (corrige le
       rendu illisible en dark mode), coins arrondis, ombre légère. -->
  <Style TargetType="ToolTip">
    <Setter Property="Background" Value="{DynamicResource CardBackgroundBrush}"/>
    <Setter Property="Foreground" Value="{DynamicResource TextPrimaryBrush}"/>
    <Setter Property="BorderBrush" Value="{DynamicResource ControlBorderBrush}"/>
    <Setter Property="BorderThickness" Value="1"/>
    <Setter Property="Padding" Value="10,8"/>
    <Setter Property="MaxWidth" Value="360"/>
    <Setter Property="HasDropShadow" Value="True"/>
    <Setter Property="Template">
      <Setter.Value>
        <ControlTemplate TargetType="ToolTip">
          <Border Background="{TemplateBinding Background}"
                  BorderBrush="{TemplateBinding BorderBrush}"
                  BorderThickness="{TemplateBinding BorderThickness}"
                  CornerRadius="6"
                  Padding="{TemplateBinding Padding}">
            <Border.Effect>
              <DropShadowEffect BlurRadius="12" ShadowDepth="2" Opacity="0.25"/>
            </Border.Effect>
            <ContentPresenter/>
          </Border>
        </ControlTemplate>
      </Setter.Value>
    </Setter>
  </Style>
```

Remplacer `CardBackgroundBrush` / `ControlBorderBrush` par les noms confirmés au Step 1.

- [ ] **Step 3 : Ajouter le même style dans StylesDark.xaml**

Coller le bloc identique avant `</ResourceDictionary>` de `lib/ui/GUI/resources/StylesDark.xaml`. Les `DynamicResource` résolvent vers les couleurs sombres automatiquement — le XML est identique.

- [ ] **Step 4 : Bonus — icône d'aide sur OptionsPage de duplicate_sheets**

Lire `ren_views/GUI/Views/pages/NamingPage.xaml` (lignes ~43-70, l'icône ⓘ + `<TextBlock.ToolTip>`). Reproduire ce `StackPanel`/icône à côté de l'en-tête « Remplacer » dans `dup_sheets/GUI/Views/pages/OptionsPage.xaml` (actuellement sans icône). Réutiliser le même contenu de tooltip (liste des tokens).

- [ ] **Step 5 : Validation Revit (manuelle)**

Reload pyRevit. Ouvrir un outil de renommage, survoler l'icône ⓘ **en thème clair puis sombre** : le tooltip doit être lisible (fond contrasté, texte lisible, coins arrondis, ombre). Vérifier aussi l'icône ajoutée sur duplicate_sheets.

- [ ] **Step 6 : Commit** *(après accord)*

```bash
git add lib/ui/GUI/resources/Styles.xaml lib/ui/GUI/resources/StylesDark.xaml "418.tab"
git commit -m "fix(ui): tooltip Fluent lisible en dark mode + icône d'aide sur duplicate_sheets"
```

---

## PHASE 4 — Câblage feature dans les 4 outils

> Chaque tâche modifie **un** outil et se termine par une validation Revit indépendante. On commence par `dup_sheets` (référence complète), puis on applique le même patron aux 3 autres avec les deltas exacts fournis.

### Task 6 : duplicate_sheets — recherche + multi-sélection (RÉFÉRENCE)

**Files:**
- Modify: `dup_sheets/lib/viewmodels/SelectionPageVM.py`
- Modify: `dup_sheets/GUI/Views/pages/SelectionPage.xaml`
- Modify: `dup_sheets/lib/views/MainWindowView.py`

**Interfaces:**
- Consumes: `SelectionListController` (Task 4), `SheetItemVM`.
- Produces (VM public, consommé par la vue) : `FilterText` (property notifiante), `FilteredItems` (property notifiante, liste), `HasSelection`, `selected_ids()`, `handle_row_click(index, shift, ctrl)`, `select_all()`, `deselect_all()`.

- [ ] **Step 1 : Réécrire SelectionPageVM pour déléguer au controller**

Remplacer le contenu de `dup_sheets/lib/viewmodels/SelectionPageVM.py` par :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    class BaseViewModel(object):
        def notify_property(self, name):
            pass

try:
    from lib.viewmodels.SheetItemVM import SheetItemVM
except Exception:
    from viewmodels.SheetItemVM import SheetItemVM

try:
    from core.selection_list import SelectionListController
except Exception:
    from lib.core.selection_list import SelectionListController


class SelectionPageVM(BaseViewModel):
    """VM de la page Sélection : liste les feuilles, recherche + multi-sélection
    (shift/ctrl) déléguées à SelectionListController."""

    def __init__(self, descripteurs, ids_selectionnes, on_selection_changed=None):
        super(SelectionPageVM, self).__init__()
        self._on_selection_changed = on_selection_changed
        selset = set(ids_selectionnes or [])
        items = [SheetItemVM(sid, numero, nom, sid in selset, self._on_item_toggle)
                 for (sid, numero, nom) in descripteurs]
        self._ctrl = SelectionListController(
            items,
            id_getter=lambda it: it.SheetId,
            filter_getters=[lambda it: it.Numero, lambda it: it.Nom])

    # --- Recherche -----------------------------------------------------------
    @property
    def FilterText(self):
        return self._ctrl.filter_text

    @FilterText.setter
    def FilterText(self, value):
        self._ctrl.filter_text = value
        self.notify_property('FilterText')
        self.notify_property('FilteredItems')

    @property
    def FilteredItems(self):
        return self._ctrl.filtered_items

    # --- Sélection -----------------------------------------------------------
    def handle_row_click(self, index, shift=False, ctrl=False):
        self._ctrl.handle_row_click(index, shift, ctrl)
        self._after_selection_change()

    def select_all(self):
        self._ctrl.select_all()
        self._after_selection_change()

    def deselect_all(self):
        self._ctrl.deselect_all()
        self._after_selection_change()

    def selected_ids(self):
        return self._ctrl.selected_ids()

    @property
    def HasSelection(self):
        return self._ctrl.has_selection()

    # --- Interne -------------------------------------------------------------
    def _on_item_toggle(self, item):
        self._after_selection_change()

    def _after_selection_change(self):
        self.notify_property('HasSelection')
        if self._on_selection_changed is not None:
            self._on_selection_changed(self.selected_ids())
```

- [ ] **Step 2 : Mettre à jour SelectionPage.xaml (recherche + boutons + row-click + checkbox display-only)**

Dans `dup_sheets/GUI/Views/pages/SelectionPage.xaml` :

1. Ajouter une ligne de recherche au-dessus de la liste. Modifier `Grid.RowDefinitions` pour insérer une ligne `Auto` après le titre :

```xml
    <Grid.RowDefinitions>
      <RowDefinition Height="Auto"/>   <!-- titre -->
      <RowDefinition Height="Auto"/>   <!-- recherche + actions -->
      <RowDefinition Height="*"/>      <!-- liste -->
      <RowDefinition Height="Auto"/>   <!-- bouton Suivant -->
    </Grid.RowDefinitions>
```

2. Insérer, en `Grid.Row="1"`, la barre recherche + boutons de masse :

```xml
    <Grid Grid.Row="1" Margin="0,0,0,10">
      <Grid.ColumnDefinitions>
        <ColumnDefinition Width="*"/>
        <ColumnDefinition Width="Auto"/>
        <ColumnDefinition Width="Auto"/>
      </Grid.ColumnDefinitions>
      <TextBox Grid.Column="0"
               x:Name="SearchBox"
               Text="{Binding FilterText, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
               Style="{DynamicResource TextBoxStyle}"/>
      <Button Grid.Column="1" x:Name="SelectAllButton" Content="Tout"
              Style="{DynamicResource SecondaryButtonStyle}" Margin="8,0,0,0"/>
      <Button Grid.Column="2" x:Name="DeselectAllButton" Content="Aucun"
              Style="{DynamicResource SecondaryButtonStyle}" Margin="8,0,0,0"/>
    </Grid>
```
(Si `TextBoxStyle`/`SecondaryButtonStyle` n'existent pas sous ces noms, utiliser les styles réels de `Styles.xaml` ; à défaut retirer l'attribut `Style`.)

3. Passer le `ScrollViewer` en `Grid.Row="2"`, l'`ItemsControl` reçoit `x:Name="ItemsList"` et `ItemsSource="{Binding FilteredItems}"` (au lieu de `Items`).

4. Dans le `DataTemplate`, rendre la ligne cliquable et la case display-only : sur le `Border`, ajouter `Background="{DynamicResource TransparentBrush}"` (pour capter le clic sur toute la largeur) ; sur la `CheckBox`, ajouter `IsHitTestVisible="False"` et passer le binding en `Mode=OneWay`.

5. Passer le bouton « Suivant » en `Grid.Row="3"`.

- [ ] **Step 3 : Câbler la vue (handler unique de clic + recherche + boutons)**

Dans `dup_sheets/lib/views/MainWindowView.py`, ajouter l'appel dans `_load()` après `self._wire_next_selection()` :

```python
        self._wire_selection_interactions()
```

Puis ajouter la méthode :

```python
    def _wire_selection_interactions(self):
        page = self._page_selection
        vm = self._vm.SelectionVM

        # Boutons de masse
        btn_all = page.FindName('SelectAllButton')
        if btn_all is not None:
            btn_all.Click += lambda s, a: vm.select_all()
        btn_none = page.FindName('DeselectAllButton')
        if btn_none is not None:
            btn_none.Click += lambda s, a: vm.deselect_all()

        # Un seul handler de clic sur la liste : remonte (index affiché + modificateurs)
        lst = page.FindName('ItemsList')
        if lst is None:
            return

        def _on_row_click(sender, args):
            from System.Windows.Input import Keyboard, ModifierKeys
            src = args.OriginalSource
            item = getattr(src, 'DataContext', None)
            filtered = list(vm.FilteredItems)
            if item is None or item not in filtered:
                return
            index = filtered.index(item)
            mods = Keyboard.Modifiers
            shift = bool(int(mods) & int(ModifierKeys.Shift))
            ctrl = bool(int(mods) & int(ModifierKeys.Control))
            vm.handle_row_click(index, shift, ctrl)

        lst.PreviewMouseLeftButtonDown += _on_row_click
```

Note : `SearchBox` est câblé par binding `FilterText` (TwoWay) — aucun code Python nécessaire pour la recherche. Le rafraîchissement de la liste se fait via `notify_property('FilteredItems')` déclenché dans le setter `FilterText`.

- [ ] **Step 4 : Validation Revit (manuelle)**

Reload pyRevit → ouvrir « Dupliquer les feuilles ». Vérifier :
1. La barre de recherche filtre la liste en direct (insensible casse/accents).
2. Clic sur une ligne = coche/décoche cette feuille (la case suit).
3. Ctrl+clic = ajoute/retire sans effacer les autres.
4. Shift+clic = sélectionne la plage entre la dernière et la ligne cliquée (parmi les visibles).
5. « Tout » / « Aucun » agissent sur toute la liste (même filtrée).
6. Le bouton « Suivant » s'active dès qu'au moins une feuille est cochée.

- [ ] **Step 5 : Commit** *(après accord)*

```bash
git add "418.tab/Tools.panel/col1.stack/duplicate_sheets.pushbutton"
git commit -m "feat(duplicate_sheets): recherche + multi-sélection shift/ctrl sur la page sélection"
```

### Task 7 : views_duplicate — recherche + multi-sélection

**Files:**
- Modify: `dup_views/lib/viewmodels/SelectionPageVM.py`, `dup_views/GUI/Views/pages/SelectionPage.xaml`, `dup_views/lib/views/MainWindowView.py`

**Interfaces:** identiques à Task 6, mais item = `ViewItemVM` (id `ViewId`, getters `TypeLabel` + `Nom`).

- [ ] **Step 1 : Réécrire le VM**

Même code que Task 6 Step 1 avec ces **deltas exacts** :
- import : `from lib.viewmodels.ViewItemVM import ViewItemVM` (fallback `from viewmodels.ViewItemVM import ViewItemVM`).
- construction des items : conserver l'ordre de descripteur réel du fichier existant (lire d'abord `dup_views/lib/viewmodels/SelectionPageVM.py`). Pour `ViewItemVM(view_id, nom, type_label, is_selected, on_toggle)` :
  ```python
  items = [ViewItemVM(vid, nom, type_label, vid in selset, self._on_item_toggle)
           for (vid, nom, type_label) in descripteurs]
  ```
  (Adapter l'unpacking `(vid, nom, type_label)` à l'ordre réellement fourni par le script/MainViewModel de cet outil.)
- controller :
  ```python
  self._ctrl = SelectionListController(
      items,
      id_getter=lambda it: it.ViewId,
      filter_getters=[lambda it: it.TypeLabel, lambda it: it.Nom])
  ```
- Le reste du fichier (properties FilterText/FilteredItems/HasSelection, handle_row_click, select_all, deselect_all, selected_ids, _on_item_toggle, _after_selection_change) est **identique** à Task 6.

- [ ] **Step 2 : Mettre à jour le XAML**

Appliquer les 5 modifications de Task 6 Step 2 à `dup_views/GUI/Views/pages/SelectionPage.xaml`. Les colonnes affichent `TypeLabel` puis `Nom` (le `DataTemplate` de cet outil référence déjà `TypeLabel`/`Nom` — ne pas changer les getters, seulement ajouter `IsHitTestVisible="False"`/`OneWay` sur la CheckBox, `x:Name="ItemsList"`, `ItemsSource="{Binding FilteredItems}"`, la barre recherche+boutons, et le décalage des `Grid.Row`).

- [ ] **Step 3 : Câbler la vue**

Ajouter `_wire_selection_interactions` (code **identique** à Task 6 Step 3) à `dup_views/lib/views/MainWindowView.py` et l'appeler dans `_load()`. Vérifier que le nom de l'attribut VM de la page sélection est bien `self._vm.SelectionVM` (sinon adapter au nom réel).

- [ ] **Step 4 : Validation Revit**

Reload → « Dupliquer les vues » → mêmes 6 vérifications que Task 6 Step 4 (recherche sur Type/Nom).

- [ ] **Step 5 : Commit** *(après accord)*

```bash
git add "418.tab/Tools.panel/col1.stack/views_duplicate.pushbutton"
git commit -m "feat(views_duplicate): recherche + multi-sélection shift/ctrl sur la page sélection"
```

### Task 8 : FindReplace - Views (renommage vues) — recherche + multi-sélection

**Files:**
- Modify: `ren_views/lib/viewmodels/SelectionPageVM.py`, `ren_views/GUI/Views/pages/SelectionPage.xaml`, `ren_views/lib/views/MainWindowView.py`

**Interfaces:** identiques à Task 7 (item `ViewItemVM`, id `ViewId`, getters `TypeLabel` + `Nom`).

- [ ] **Step 1 : Réécrire le VM** — identique à Task 7 Step 1 (lire d'abord le VM existant pour respecter l'ordre du descripteur et le nom de classe d'item).
- [ ] **Step 2 : Mettre à jour le XAML** — identique à Task 7 Step 2 (titre « Vues à renommer » conservé).
- [ ] **Step 3 : Câbler la vue** — `_wire_selection_interactions` identique ; vérifier le nom réel de l'attribut VM de page sélection et du chargement de page dans ce `MainWindowView.py`.
- [ ] **Step 4 : Validation Revit** — Reload → outil de renommage des vues → 6 vérifications (le bouton « Suivant » de cet outil peut se nommer différemment ; ne pas y toucher).
- [ ] **Step 5 : Commit** *(après accord)*

```bash
git add "418.tab/Tools.panel/col1.stack/Rename.pulldown/FindReplace - Views.pushbutton"
git commit -m "feat(rename_views): recherche + multi-sélection shift/ctrl sur la page sélection"
```

### Task 9 : FindReplace_Sheets (renommage feuilles) — recherche + multi-sélection

**Files:**
- Modify: `ren_sheets/lib/viewmodels/SelectionPageVM.py`, `ren_sheets/GUI/Views/pages/SelectionPage.xaml`, `ren_sheets/lib/views/MainWindowView.py`

**Interfaces:** identiques à Task 6 (item `SheetItemVM`, id `SheetId`, getters `Numero` + `Nom`).

- [ ] **Step 1 : Réécrire le VM** — identique à Task 6 Step 1 (lire d'abord le VM existant pour respecter l'ordre du descripteur).
- [ ] **Step 2 : Mettre à jour le XAML** — identique à Task 6 Step 2.
- [ ] **Step 3 : Câbler la vue** — `_wire_selection_interactions` identique ; vérifier les noms réels (`SelectionVM`, `ItemsList`, chargement de page).
- [ ] **Step 4 : Validation Revit** — Reload → outil de renommage des feuilles → 6 vérifications.
- [ ] **Step 5 : Commit** *(après accord)*

```bash
git add "418.tab/Tools.panel/col1.stack/Rename.pulldown/FindReplace_Sheets.pushbutton"
git commit -m "feat(rename_sheets): recherche + multi-sélection shift/ctrl sur la page sélection"
```

---

## Self-review (couverture spec)

- Chantier 1 (multi-sélection shift/ctrl) → Task 4 (controller) + Tasks 6-9 (câblage). CheckBox display-only + handler unique = anti double-fire. ✔
- Chantier 2 (recherche/filtre, sans mémoire, select-all sur liste complète) → Task 3 + Task 4 + Tasks 6-9. ✔
- Chantier 3 (tooltip Fluent clair+sombre) → Task 5 (+ bonus icône duplicate_sheets). ✔
- Chantier 4 (mutualisation RenameService/TokenExpander) → Tasks 1-2, séquencées avant la feature. ✔
- Risque « import lib partagé » → confirmé (les VMs importent déjà `from ui.base…`), re-vérifié en Task 2 Step 7. ✔
- Cohérence index × filtre (reset ancre au changement de filtre, index relatif au filtré) → `SelectionListController.filter_text` setter + `handle_row_click` sur `_filtered`, testé (Task 4). ✔

## Notes de vigilance pour l'exécutant

- **Lire chaque fichier avant de le réécrire** : les 4 outils sont des copies quasi identiques mais l'ordre des descripteurs et le nom des attributs VM (`SelectionVM`, boutons de nav) peuvent varier — adapter, ne pas présumer.
- Ne pas modifier `ListSelectionService` : sa branche « clic simple exclusif » n'est volontairement pas utilisée ici.
- Si un style XAML référencé (`TextBoxStyle`, `SecondaryButtonStyle`, `CardBackgroundBrush`) n'existe pas sous ce nom, utiliser le nom réel du dépôt (vérifié via `Styles.xaml`/`Colors.xaml`) plutôt que d'inventer.
- Tests : lancer depuis la racine du dépôt avec `python lib/core/tests/test_*.py`.
