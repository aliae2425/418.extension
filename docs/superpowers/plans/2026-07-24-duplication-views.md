# Duplication des vues (`views_duplicate`) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Réécrire l'outil `views_duplicate` sur la charte WPF du projet (MVVM + coquille à rail Sélection / Options, bouton « Suivant »), en réutilisant la fondation `core` déjà en place. Outil frère de `duplicate_sheets`, même patron, logique plus simple.

**Architecture:** Identique à `duplicate_sheets` : `script.py` → `MainViewModel` + `MainWindowView` (sur `BaseWindow`), fenêtre borderless à rail hébergeant page **Sélection** (liste des vues, pré-cochées, bouton « Suivant ») et page **Options** (option de duplication + nombre de copies + Lancer). Logique métier portée dans un service. État de sélection partagé sur le `MainViewModel`.

**Tech Stack:** IronPython 2/3 (pyRevit), WPF (XamlReader, sans code-behind), `unittest`, API Revit 2026.

## Global Constraints

- **Revit minimum** : 2026.
- **Python 2/3** : chaque fichier commence par `# -*- coding: utf-8 -*-` puis `from __future__ import unicode_literals`.
- **Imports Revit/WPF gardés** (`try/except` → `None`), importable hors Revit.
- **Langue** : UI, docstrings, commits en **français**.
- **Charte** : XAML via `XamlReader.Load` (pas de `x:Class`, pas de code-behind) ; thème en `DynamicResource` (fusionné après parse par `BaseWindow`).
- **Zéro branding EF** ; pas de `Snippets.*` / `GUI.forms` dans la chaîne.
- **Fallback `BaseViewModel`** : classe minimale avec `notify_property` no-op (JAMAIS bare `object`) — cf. `duplicate_sheets`.
- **Propriétés VM** : `@property` INLINE (getter/setter notifiant), jamais de fabrique dynamique.
- **Commit** : messages terminés par `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. `git add` CIBLÉ (jamais `-A`/`.`) — untracked `lib/Renaming/`, `lib/Selection/`, `lib/Snippets/` à la racine NE doivent PAS être commités.
- **Chemins ABSOLUS complets** : le bouton est `418.tab/Tools.panel/col1.stack/views_duplicate.pushbutton/` (jamais une variante raccourcie).
- **Tests** : `unittest`, invocation par fichier direct (`python tests/test_x.py -v`), pas de `__init__.py` dans `tests/`. sys.path bouton : shared lib = **5** niveaux au-dessus de `tests/` (`views_duplicate.pushbutton → col1.stack → Tools.panel → 418.tab → 418.extension`, puis `/lib`) puis le dossier bouton.

---

## File Structure

**Fondation partagée** (extension `lib/`) :
- Modify: `lib/core/selection.py` — ajout `all_views(doc)`.
- Modify: `lib/core/tests/test_selection.py` — test de `all_views` (via fakes) si possible, sinon note smoke.

**Outil** (`418.tab/Tools.panel/col1.stack/views_duplicate.pushbutton/`) :
- Modify: `script.py` (point d'entrée MVVM).
- Delete: `Script.xaml`.
- Create: `GUI/Views/MainWindow.xaml`, `GUI/Views/pages/SelectionPage.xaml`, `GUI/Views/pages/OptionsPage.xaml`.
- Create: `lib/__init__.py`, `lib/services/__init__.py`, `lib/viewmodels/__init__.py`, `lib/views/__init__.py`.
- Create: `lib/services/ViewsDuplicationOptions.py`, `lib/services/ViewsDuplicationService.py`.
- Create: `lib/viewmodels/ViewItemVM.py`, `SelectionPageVM.py`, `OptionsPageVM.py`, `MainViewModel.py`.
- Create: `lib/views/MainWindowView.py`.
- Create: `tests/test_views_options.py`, `tests/test_selection_page_vm.py`, `tests/test_options_page_vm.py`, `tests/test_main_viewmodel.py`.

---

## Task 1 : `all_views(doc)` dans `core/selection`

**Files:** Modify `lib/core/selection.py` ; Modify `lib/core/tests/test_selection.py`.

**Interfaces:**
- Produces: `all_views(doc)` → liste de vues « duplicables » du document (exclut les templates et les feuilles), triée par nom. Revit-couplé (via `FilteredElementCollector`) : logique de tri/filtre testée avec un faux collecteur si praticable ; sinon, tester la fonction de filtre pure `_is_duplicable_view(v)`.

- [ ] **Step 1 : Test** — ajouter dans `test_selection.py` un test de la logique de filtre. Comme `FilteredElementCollector` n'est pas simulable simplement, factoriser le prédicat de filtre en fonction pure `_is_duplicable_view(view)` et le tester avec des fakes :

```python
class TestAllViewsFilter(unittest.TestCase):
    def setUp(self):
        self._orig = (selection.View, selection.ViewSheet)
        selection.View = FakeViewBase          # défini dans le test
        selection.ViewSheet = FakeSheetType

    def tearDown(self):
        selection.View, selection.ViewSheet = self._orig

    def test_exclut_templates_et_feuilles(self):
        v_ok = FakeView(is_template=False)      # instance de FakeViewBase
        v_tpl = FakeView(is_template=True)
        sheet = FakeSheet()                     # instance de FakeSheetType
        self.assertTrue(selection._is_duplicable_view(v_ok))
        self.assertFalse(selection._is_duplicable_view(v_tpl))
        self.assertFalse(selection._is_duplicable_view(sheet))
```

Où (à ajouter en tête du test) :
```python
class FakeViewBase(object):
    pass
class FakeSheetType(FakeViewBase):
    pass
class FakeView(FakeViewBase):
    def __init__(self, is_template):
        self.IsTemplate = is_template
class FakeSheet(FakeSheetType):
    IsTemplate = False
```

- [ ] **Step 2 : Lancer, vérifier l'échec** — `python lib/core/tests/test_selection.py -v` → FAIL (`_is_duplicable_view` inexistant).

- [ ] **Step 3 : Implémenter** — dans `lib/core/selection.py`, ajouter :

```python
def _is_duplicable_view(view):
    """True si `view` est une vue duplicable : c'est une View, pas une feuille
    (ViewSheet), pas un template."""
    if View is None:
        return False
    if not isinstance(view, View):
        return False
    if ViewSheet is not None and isinstance(view, ViewSheet):
        return False
    return not getattr(view, 'IsTemplate', False)


def all_views(doc):
    """Toutes les vues duplicables du document (hors feuilles et templates),
    triées par nom."""
    if FilteredElementCollector is None or View is None:
        return []
    vues = [v for v in FilteredElementCollector(doc).OfClass(View).ToElements()
            if _is_duplicable_view(v)]
    return sorted(vues, key=lambda v: v.Name)
```

- [ ] **Step 4 : Lancer, vérifier le succès** — tous les tests de `test_selection.py` passent.
- [ ] **Step 5 : Commit** — `git add lib/core/selection.py lib/core/tests/test_selection.py` ; message `feat(core): ajoute all_views (vues duplicables, hors feuilles/templates)`.

---

## Task 2 : `ViewsDuplicationOptions`

**Files:** Create `lib/services/__init__.py` (en-tête seul), `lib/services/ViewsDuplicationOptions.py` ; Test `tests/test_views_options.py`.

**Interfaces:**
- Produces: `ViewsDuplicationOptions(view_duplicate_option=u'duplicate', count=1)` — champs : `view_duplicate_option` (str parmi `u'duplicate'`/`u'with_detailing'`/`u'as_dependent'`), `count` (int ≥ 1). Le constructeur force `count` à un entier ≥ 1 (`max(1, int(count))`, `1` si non convertible).

- [ ] **Step 1 : Test** — Create `tests/test_views_options.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os, sys, unittest
_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path: sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path: sys.path.insert(0, _BUTTON)

from lib.services.ViewsDuplicationOptions import ViewsDuplicationOptions


class TestViewsDuplicationOptions(unittest.TestCase):
    def test_defauts(self):
        o = ViewsDuplicationOptions()
        self.assertEqual(o.view_duplicate_option, u'duplicate')
        self.assertEqual(o.count, 1)

    def test_count_force_entier_min_1(self):
        self.assertEqual(ViewsDuplicationOptions(count=3).count, 3)
        self.assertEqual(ViewsDuplicationOptions(count=0).count, 1)
        self.assertEqual(ViewsDuplicationOptions(count=-5).count, 1)
        self.assertEqual(ViewsDuplicationOptions(count=u'abc').count, 1)

    def test_option(self):
        self.assertEqual(ViewsDuplicationOptions(view_duplicate_option=u'as_dependent').view_duplicate_option, u'as_dependent')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer, vérifier l'échec** — `ImportError`.
- [ ] **Step 3 : Implémenter** — `lib/services/__init__.py` (en-tête) ; `lib/services/ViewsDuplicationOptions.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class ViewsDuplicationOptions(object):
    """Options de duplication de vues : mode de duplication + nombre de copies."""

    def __init__(self, view_duplicate_option=u'duplicate', count=1):
        self.view_duplicate_option = view_duplicate_option
        try:
            c = int(count)
        except (ValueError, TypeError):
            c = 1
        self.count = c if c >= 1 else 1
```

- [ ] **Step 4 : Lancer, vérifier le succès** — 3 tests PASS.
- [ ] **Step 5 : Commit** — `feat(views_duplicate): objet de données ViewsDuplicationOptions`.

---

## Task 3 : `ViewsDuplicationService` (portage, bug d'origine corrigé)

**Files:** Create `lib/services/ViewsDuplicationService.py`. Source de référence : ancien `views_duplicate.pushbutton/script.py`, méthode `duplicate_selected_views`.

**⚠️ Correction d'un bug de l'original :** dans l'EF, `if type(view)==ViewSchedule:` et `if view.ViewType==Legend: … else:` sont des `if` SÉPARÉS → une nomenclature tombe dans la branche Schedule ET dans le `else`, donc est dupliquée **deux fois**. Le portage utilise un `if / elif / else` **exclusif** (comportement manifestement voulu).

**Interfaces:**
- Consumes: `ViewsDuplicationOptions` (Task 2), `revit_transaction` (déjà en place).
- Produces: `ViewsDuplicationService(doc)` ; `duplicate(self, views, options)` → duplique chaque vue de `views`, `options.count` fois, selon le type (ViewSchedule → `Duplicate` ; Legend → `WithDetailing` ; autre → l'option choisie). Enveloppe tout dans `with revit_transaction(self._doc, u'Dupliquer les vues'):`. Retourne la liste des `ElementId` des vues créées (vues « normales » uniquement, comme l'original). Le `script.py` (Task 8) se charge de re-sélectionner ces vues.

- [ ] **Step 1 : Implémenter** — Create `lib/services/ViewsDuplicationService.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from Autodesk.Revit.DB import ViewSchedule, ViewType, ViewDuplicateOption
except Exception:
    ViewSchedule = None
    ViewType = None
    ViewDuplicateOption = None

try:
    from core.transaction import revit_transaction
except Exception:
    revit_transaction = None

_VIEW_DUP_MAP = {
    u'duplicate': 'Duplicate',
    u'with_detailing': 'WithDetailing',
    u'as_dependent': 'AsDependent',
}


class ViewsDuplicationService(object):
    """Duplique des vues Revit selon un mode et un nombre de copies."""

    def __init__(self, doc):
        self._doc = doc

    def _view_dup_option(self, key):
        return getattr(ViewDuplicateOption, _VIEW_DUP_MAP.get(key, 'Duplicate'))

    def duplicate(self, views, options):
        """Duplique `views` (liste de View) `options.count` fois chacune.
        Retourne la liste des ElementId des vues « normales » créées."""
        new_view_ids = []
        opt = self._view_dup_option(options.view_duplicate_option)
        with revit_transaction(self._doc, u'Dupliquer les vues'):
            for view in views:
                # if/elif/else EXCLUSIF (corrige la double-duplication de l'ancien outil).
                if ViewSchedule is not None and isinstance(view, ViewSchedule):
                    for _ in range(options.count):
                        view.Duplicate(getattr(ViewDuplicateOption, 'Duplicate'))
                elif ViewType is not None and view.ViewType == ViewType.Legend:
                    for _ in range(options.count):
                        view.Duplicate(getattr(ViewDuplicateOption, 'WithDetailing'))
                else:
                    for _ in range(options.count):
                        new_view_ids.append(view.Duplicate(opt))
        return new_view_ids
```

- [ ] **Step 2 : Vérif import hors Revit** — depuis la racine, un script temporaire insérant (bouton dir, shared `lib`) importe `lib.services.ViewsDuplicationService` et instancie `ViewsDuplicationService(None)` sans exception. Coller commande + sortie dans le rapport. Smoke-test fonctionnel Revit DÉFÉRÉ à Task 8.
- [ ] **Step 3 : Commit** — `feat(views_duplicate): service de duplication de vues (if/elif/else, corrige double-dup)`.

---

## Task 4 : `ViewItemVM` + `SelectionPageVM` (variante vues)

Calqué sur `duplicate_sheets` (avec `HasSelection` + support du bouton « Suivant » d'emblée).

**Files:** Create `lib/viewmodels/__init__.py` (en-tête), `lib/viewmodels/ViewItemVM.py`, `lib/viewmodels/SelectionPageVM.py` ; Test `tests/test_selection_page_vm.py`.

**Interfaces:**
- `ViewItemVM(view_id, nom, type_label, is_selected, on_toggle)` : propriétés CLR `Nom` (str), `TypeLabel` (str), attribut `ViewId`, `IsSelected` (setter guarde le changement, notifie, appelle `on_toggle(self)`). Dérive de `BaseViewModel` (fallback classe).
- `SelectionPageVM(descripteurs, ids_selectionnes, on_selection_changed=None)` où `descripteurs` = liste de tuples `(view_id, nom, type_label)`. Property `Items` (liste de `ViewItemVM`), `selected_ids()`, `@property HasSelection` (any coché ; notifie via `_on_item_toggle`), `_on_item_toggle` notifie `HasSelection` puis appelle `on_selection_changed(selected_ids())`.

- [ ] **Step 1 : Test** — Create `tests/test_selection_page_vm.py` (miroir de celui de `duplicate_sheets`, adapté à `ViewItemVM`/`Nom`/`TypeLabel`) :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os, sys, unittest
_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path: sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path: sys.path.insert(0, _BUTTON)

from lib.viewmodels.SelectionPageVM import SelectionPageVM


class TestSelectionPageVM(unittest.TestCase):
    DESCR = [(1, u'Niveau 0', u'Plan'), (2, u'Niveau 1', u'Plan'), (3, u'Coupe A', u'Coupe')]

    def _vm(self, ids):
        self.changes = []
        return SelectionPageVM(self.DESCR, ids, on_selection_changed=lambda l: self.changes.append(list(l)))

    def test_precoche(self):
        vm = self._vm([2])
        self.assertEqual([(it.Nom, it.IsSelected) for it in vm.Items],
                         [(u'Niveau 0', False), (u'Niveau 1', True), (u'Coupe A', False)])

    def test_toggle_met_a_jour(self):
        vm = self._vm([])
        vm.Items[0].IsSelected = True
        vm.Items[2].IsSelected = True
        self.assertEqual(sorted(vm.selected_ids()), [1, 3])
        self.assertEqual(self.changes[-1], [1, 3])

    def test_has_selection(self):
        vm = self._vm([])
        self.assertFalse(vm.HasSelection)
        vm.Items[0].IsSelected = True
        self.assertTrue(vm.HasSelection)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer, vérifier l'échec** — `ImportError`.
- [ ] **Step 3 : Implémenter** — `lib/viewmodels/__init__.py` (en-tête).

`lib/viewmodels/ViewItemVM.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    class BaseViewModel(object):
        def notify_property(self, name):
            pass


class ViewItemVM(BaseViewModel):
    """Ligne de la page Sélection : une vue cochable."""

    def __init__(self, view_id, nom, type_label, is_selected, on_toggle):
        super(ViewItemVM, self).__init__()
        self.ViewId = view_id
        self._nom = nom
        self._type_label = type_label
        self._is_selected = is_selected
        self._on_toggle = on_toggle

    @property
    def Nom(self):
        return self._nom

    @property
    def TypeLabel(self):
        return self._type_label

    @property
    def IsSelected(self):
        return self._is_selected

    @IsSelected.setter
    def IsSelected(self, value):
        value = bool(value)
        if value != self._is_selected:
            self._is_selected = value
            self.notify_property('IsSelected')
            if self._on_toggle is not None:
                self._on_toggle(self)
```

`lib/viewmodels/SelectionPageVM.py` :
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
    from lib.viewmodels.ViewItemVM import ViewItemVM
except Exception:
    from viewmodels.ViewItemVM import ViewItemVM


class SelectionPageVM(BaseViewModel):
    """VM de la page Sélection : liste toutes les vues, pré-cochées selon la
    sélection courante, répercute les changements via callback."""

    def __init__(self, descripteurs, ids_selectionnes, on_selection_changed=None):
        super(SelectionPageVM, self).__init__()
        self._on_selection_changed = on_selection_changed
        selset = set(ids_selectionnes or [])
        self._items = [ViewItemVM(vid, nom, type_label, vid in selset, self._on_item_toggle)
                       for (vid, nom, type_label) in descripteurs]

    @property
    def Items(self):
        return self._items

    def selected_ids(self):
        return [it.ViewId for it in self._items if it.IsSelected]

    @property
    def HasSelection(self):
        return any(it.IsSelected for it in self._items)

    def _on_item_toggle(self, item):
        self.notify_property('HasSelection')
        if self._on_selection_changed is not None:
            self._on_selection_changed(self.selected_ids())
```

- [ ] **Step 4 : Lancer, vérifier le succès** — 3 tests PASS.
- [ ] **Step 5 : Commit** — `feat(views_duplicate): VM page Sélection (vues pré-cochées, HasSelection)`.

---

## Task 5 : `OptionsPageVM` (option de duplication + nombre de copies)

**Files:** Create `lib/viewmodels/OptionsPageVM.py` ; Test `tests/test_options_page_vm.py`.

**Interfaces:**
- Consumes: `ViewsDuplicationOptions` (Task 2).
- Produces: `OptionsPageVM()` avec propriétés CLR INLINE notifiantes : `ViewDuplicateOption` (str, défaut `u'duplicate'`), `Count` (str, défaut `u'1'` — liée à un TextBox). Method `build_options()` → `ViewsDuplicationOptions(view_duplicate_option=self._ViewDuplicateOption, count=self._Count)` (le constructeur d'options force l'entier ≥ 1).

- [ ] **Step 1 : Test** — Create `tests/test_options_page_vm.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os, sys, unittest
_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path: sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path: sys.path.insert(0, _BUTTON)

from lib.viewmodels.OptionsPageVM import OptionsPageVM


class TestOptionsPageVM(unittest.TestCase):
    def test_defauts(self):
        o = OptionsPageVM().build_options()
        self.assertEqual(o.view_duplicate_option, u'duplicate')
        self.assertEqual(o.count, 1)

    def test_modifs(self):
        vm = OptionsPageVM()
        vm.ViewDuplicateOption = u'with_detailing'
        vm.Count = u'4'
        o = vm.build_options()
        self.assertEqual(o.view_duplicate_option, u'with_detailing')
        self.assertEqual(o.count, 4)

    def test_count_invalide_retombe_sur_1(self):
        vm = OptionsPageVM()
        vm.Count = u'xyz'
        self.assertEqual(vm.build_options().count, 1)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer, vérifier l'échec** — `ImportError`.
- [ ] **Step 3 : Implémenter** — `lib/viewmodels/OptionsPageVM.py` (2 propriétés INLINE) :

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
    from lib.services.ViewsDuplicationOptions import ViewsDuplicationOptions
except Exception:
    from services.ViewsDuplicationOptions import ViewsDuplicationOptions


class OptionsPageVM(BaseViewModel):
    """VM de la page Options : mode de duplication + nombre de copies."""

    def __init__(self):
        super(OptionsPageVM, self).__init__()
        self._ViewDuplicateOption = u'duplicate'
        self._Count = u'1'

    @property
    def ViewDuplicateOption(self):
        return self._ViewDuplicateOption

    @ViewDuplicateOption.setter
    def ViewDuplicateOption(self, value):
        if value != self._ViewDuplicateOption:
            self._ViewDuplicateOption = value
            self.notify_property('ViewDuplicateOption')

    @property
    def Count(self):
        return self._Count

    @Count.setter
    def Count(self, value):
        if value != self._Count:
            self._Count = value
            self.notify_property('Count')

    def build_options(self):
        return ViewsDuplicationOptions(view_duplicate_option=self._ViewDuplicateOption,
                                       count=self._Count)
```

- [ ] **Step 4 : Lancer, vérifier le succès** — 3 tests PASS.
- [ ] **Step 5 : Commit** — `feat(views_duplicate): VM page Options (mode + nombre de copies)`.

---

## Task 6 : `MainViewModel`

Identique au patron `duplicate_sheets` (navigation + état partagé + lancement), adapté aux vues.

**Files:** Create `lib/viewmodels/MainViewModel.py` ; Test `tests/test_main_viewmodel.py`.

**Interfaces:**
- Consumes: `SelectionPageVM` (Task 4), `OptionsPageVM` (Task 5), `ViewsDuplicationService` (Task 3).
- Produces: `MainViewModel(doc=None, uidoc=None, service=None)` :
  - `Titre` = `u'418 · Dupliquer les vues'`.
  - `Mode` (`u'selection'`/`u'options'`), `IsSelection`, `IsOptions` (notifiés).
  - `SelectedViewIds` (liste, état partagé).
  - `SelectionVM`, `OptionsVM`.
  - `@staticmethod decide_initial_mode(has_selection)` → `u'options'` si `has_selection` sinon `u'selection'`.
  - `set_mode(mode)` (notifie Mode/IsSelection/IsOptions).
  - `charger(descripteurs, ids_courants)` (construit VMs avec `on_selection_changed=self._on_selection_changed`, seed `SelectedViewIds`, mode initial).
  - `_on_selection_changed(ids)` (met à jour `SelectedViewIds`).
  - `lancer(views_par_id)` → si `SelectedViewIds` non vide et `service` présent : `service.duplicate([views_par_id[i] for i in SelectedViewIds if i in views_par_id], OptionsVM.build_options())` ; retourne les ids créés (ou `[]`).

- [ ] **Step 1 : Test** — Create `tests/test_main_viewmodel.py` (miroir de `duplicate_sheets`, `SelectedViewIds`, `Titre` = vues) :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os, sys, unittest
_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path: sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path: sys.path.insert(0, _BUTTON)

from lib.viewmodels.MainViewModel import MainViewModel


class TestMainViewModel(unittest.TestCase):
    DESCR = [(1, u'Niveau 0', u'Plan'), (2, u'Coupe A', u'Coupe')]

    def test_decide_initial_mode(self):
        self.assertEqual(MainViewModel.decide_initial_mode(True), u'options')
        self.assertEqual(MainViewModel.decide_initial_mode(False), u'selection')

    def test_charger_avec_selection(self):
        vm = MainViewModel(); vm.charger(self.DESCR, [1])
        self.assertEqual(vm.Mode, u'options'); self.assertTrue(vm.IsOptions)
        self.assertEqual(vm.SelectedViewIds, [1])

    def test_charger_sans_selection(self):
        vm = MainViewModel(); vm.charger(self.DESCR, [])
        self.assertEqual(vm.Mode, u'selection')

    def test_toggle_met_a_jour_etat_partage(self):
        vm = MainViewModel(); vm.charger(self.DESCR, [])
        vm.SelectionVM.Items[1].IsSelected = True
        self.assertEqual(vm.SelectedViewIds, [2])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer, vérifier l'échec** — `ImportError`.
- [ ] **Step 3 : Implémenter** — `lib/viewmodels/MainViewModel.py` (calque `duplicate_sheets`, renommage sheets→views) :

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
    from lib.viewmodels.SelectionPageVM import SelectionPageVM
    from lib.viewmodels.OptionsPageVM import OptionsPageVM
except Exception:
    from viewmodels.SelectionPageVM import SelectionPageVM
    from viewmodels.OptionsPageVM import OptionsPageVM


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None, uidoc=None, service=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._uidoc = uidoc
        self._service = service
        self._mode = u'selection'
        self.SelectedViewIds = []
        self.SelectionVM = None
        self.OptionsVM = None

    @property
    def Titre(self):
        return u'418 · Dupliquer les vues'

    @property
    def Mode(self):
        return self._mode

    @property
    def IsSelection(self):
        return self._mode == u'selection'

    @property
    def IsOptions(self):
        return self._mode == u'options'

    @staticmethod
    def decide_initial_mode(has_selection):
        return u'options' if has_selection else u'selection'

    def set_mode(self, mode):
        if mode != self._mode:
            self._mode = mode
            self.notify_property('Mode')
            self.notify_property('IsSelection')
            self.notify_property('IsOptions')

    def charger(self, descripteurs, ids_courants):
        ids_courants = list(ids_courants or [])
        self.SelectedViewIds = list(ids_courants)
        self.SelectionVM = SelectionPageVM(descripteurs, ids_courants,
                                           on_selection_changed=self._on_selection_changed)
        self.OptionsVM = OptionsPageVM()
        self.notify_property('SelectionVM')
        self.notify_property('OptionsVM')
        self.set_mode(self.decide_initial_mode(bool(ids_courants)))

    def _on_selection_changed(self, ids):
        self.SelectedViewIds = list(ids)

    def lancer(self, views_par_id):
        if not self.SelectedViewIds or self._service is None:
            return []
        views = [views_par_id[i] for i in self.SelectedViewIds if i in views_par_id]
        return self._service.duplicate(views, self.OptionsVM.build_options())
```

- [ ] **Step 4 : Lancer, vérifier le succès** — 4 tests PASS.
- [ ] **Step 5 : Commit** — `feat(views_duplicate): MainViewModel (navigation, état partagé, lancement)`.

---

## Task 7 : XAML — coquille + pages

Calqué EXACTEMENT sur `duplicate_sheets` (mêmes styles, mêmes x:Name de coquille), adapté au contenu vues.

**Files:** Create `GUI/Views/MainWindow.xaml`, `GUI/Views/pages/SelectionPage.xaml`, `GUI/Views/pages/OptionsPage.xaml` ; Delete `Script.xaml`.
Référence : les XAML de `duplicate_sheets.pushbutton/GUI/Views/` (copier la structure, changer les libellés + bindings).

**Contrat x:Name / bindings :**
- **MainWindow.xaml** — identique à `duplicate_sheets` : `TitleBar`, `MinimizeButton`, `MaximizeRestoreButton`, `CloseButton`, rail `NavSelection`/`NavOptions` (GroupName="nav", NavRailButtonStyle), `ContentControl x:Name="PageHost"`, `Image Source="{Binding BrandLogoPath}"`. Titre affiché : `418 · Dupliquer les vues`.
- **SelectionPage.xaml** — `UserControl`, DataContext SelectionPageVM. En-tête « Vues à dupliquer ». Grille 3 lignes (Auto/*/Auto). `ScrollViewer`>`ItemsControl ItemsSource="{Binding Items}"` ; item : `TextBlock {Binding TypeLabel}` (largeur ~90, gras) + `TextBlock {Binding Nom}` + `CheckBox IsChecked="{Binding IsSelected, Mode=TwoWay}"` (CheckBoxStyle). Ligne 2 : `Button x:Name="NextButton"` Content « Suivant » (PrimaryActionButtonStyle, HorizontalAlignment Right, `IsEnabled="{Binding HasSelection}"`).
- **OptionsPage.xaml** — `UserControl`, DataContext OptionsPageVM. Carte(s) CardStyle :
  - « Option de duplication » : 3 `RadioButton` GroupName="dupopt" : `x:Name="RadioDuplicate"` Tag="duplicate" (IsChecked="True") « Dupliquer » ; `RadioDetailing` Tag="with_detailing" « Avec détails » ; `RadioDependent` Tag="as_dependent" « Dépendante ».
  - « Nombre de copies » : `TextBox Text="{Binding Count, Mode=TwoWay}"` (largeur ~60).
  - `Button x:Name="RunButton"` PrimaryActionButtonStyle « Dupliquer les vues sélectionnées ».
- Théme uniquement en `DynamicResource`. Pas de `--` dans les commentaires XML. Pas de `x:Class`. Glyphes en entités.

- [ ] **Step 1** : Créer `MainWindow.xaml` (copie adaptée de celui de `duplicate_sheets`, titre « Dupliquer les vues »).
- [ ] **Step 2** : Créer `pages/SelectionPage.xaml` (liste vues + bouton Suivant).
- [ ] **Step 3** : Créer `pages/OptionsPage.xaml` (radios + Count + Run).
- [ ] **Step 4** : `git rm` `Script.xaml`.
- [ ] **Step 5 : Vérif well-formed** — `python -c "import xml.dom.minidom,sys; xml.dom.minidom.parse(sys.argv[1]); print('well-formed')" <chemin>` pour les 3 fichiers → 3/3.
- [ ] **Step 6 : Commit** — `feat(views_duplicate): coquille XAML charte (rail + pages Sélection/Options)`.

---

## Task 8 : `MainWindowView` + `script.py` + smoke-test Revit

Calqué EXACTEMENT sur `duplicate_sheets` (BaseWindow, `_mount_pages`, `_wire_nav`, `_wire_next`, `_wire_run`, `_wire_view_dup_option`, `_sync_nav`), adapté aux vues.

**Files:** Create `lib/views/__init__.py`, `lib/__init__.py`, `lib/views/MainWindowView.py` ; Modify `script.py`.

**Interfaces:** Consumes `BaseWindow`, `MainViewModel`, `ViewsDuplicationService`, `core.selection` (`get_selected_views`, `all_views`).

- [ ] **Step 1 : `MainWindowView.py`** — copie de `duplicate_sheets/lib/views/MainWindowView.py`, en changeant :
  - `_mount_pages` : DataContext des pages = `self._vm.SelectionVM` / `self._vm.OptionsVM` (inchangé).
  - `_wire_run` : `self._vm.lancer(self._views_par_id)` puis, si des ids sont retournés, re-sélectionner dans Revit (voir script.py — mais la re-sélection touche `uidoc`; la faire dans le handler via un callback passé, ou déplacer la re-sélection dans le VM). **Décision** : `lancer()` retourne les ids ; la re-sélection Revit se fait dans le handler `_on_run` de la View (accès `uidoc` via un paramètre passé au constructeur). Constructeur : `MainWindowView(view_model, views_par_id, uidoc)`.
  - Garder `_wire_next`, `_wire_view_dup_option`, `_wire_nav`, `_sync_nav` à l'identique.
  - `_on_run` :
    ```python
    def _on_run(sender, args):
        try:
            new_ids = self._vm.lancer(self._views_par_id)
            self._reselect(new_ids)
        finally:
            self._window.Close()
    ```
    avec `_reselect(new_ids)` :
    ```python
    def _reselect(self, new_ids):
        if not new_ids or self._uidoc is None:
            return
        try:
            from System.Collections.Generic import List
            from Autodesk.Revit.DB import ElementId
            self._uidoc.Selection.SetElementIds(List[ElementId](new_ids))
        except Exception:
            pass
    ```
- [ ] **Step 2 : `script.py`** :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Dupliquer\nvues"
__doc__ = "Duplique les vues sélectionnées (nombre de copies + mode de duplication)."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

try:
    uidoc = __revit__.ActiveUIDocument  # type: ignore
    doc = __revit__.ActiveUIDocument.Document  # type: ignore
except Exception:
    uidoc = None
    doc = None

from lib.viewmodels.MainViewModel import MainViewModel
from lib.views.MainWindowView import MainWindowView
from lib.services.ViewsDuplicationService import ViewsDuplicationService
from core.selection import get_selected_views, all_views


def _type_label(view):
    try:
        return unicode(view.ViewType)
    except Exception:
        try:
            return str(view.ViewType)
        except Exception:
            return u''


if __name__ == '__main__':
    vues = all_views(doc) if doc is not None else []
    views_par_id = {}
    descripteurs = []
    for v in vues:
        views_par_id[v.Id] = v
        descripteurs.append((v.Id, v.Name, _type_label(v)))

    ids_courants = [v.Id for v in (get_selected_views(uidoc) if uidoc is not None else [])]

    service = ViewsDuplicationService(doc)
    vm = MainViewModel(doc=doc, uidoc=uidoc, service=service)
    vm.charger(descripteurs, ids_courants)

    view = MainWindowView(vm, views_par_id, uidoc)
    view.show()
```

- [ ] **Step 3 : `__init__.py`** — créer `lib/__init__.py` et `lib/views/__init__.py` (en-tête seul).
- [ ] **Step 4 : Vérif hors Revit** — script temporaire : imports OK ; `vm = MainViewModel(service=ViewsDuplicationService(None))` ; `vm.charger([(1,u'V',u'Plan')], [])` → `Mode==u'selection'` ; `vm.charger(..., [1])` → `Mode==u'options'` ; `MainWindowView(vm, {1:object()}, None)` construit sans exception (NE PAS appeler `show`/`_load`). Lancer les 4 suites du bouton → toutes vertes.
- [ ] **Step 5 : Smoke-test Revit MANUEL** (action utilisateur) : Reload ; (a) sélectionner des vues → bouton → page Options ; régler nombre=2, mode Dupliquer → Lancer → 2 copies par vue, sélection mise sur les nouvelles vues ; (b) sélection vide → page Sélection, cocher, Suivant actif → Options → Lancer ; (c) vérifier qu'une nomenclature n'est dupliquée qu'UNE fois par copie (pas deux — bug corrigé).
- [ ] **Step 6 : Commit** — `feat(views_duplicate): assemble la vue MVVM + point d'entrée (rail/pages, sans modale)`.

---

## Self-Review (effectuée)

**Couverture** : sélection via `core.selection` (+ `all_views` Task 1) ; transaction via `core.transaction` ; MVVM rail/pages + bouton Suivant (Tasks 4-8) ; logique portée avec bug double-dup corrigé (Task 3) ; FR + sans EF partout.
**Placeholders** : aucun.
**Cohérence types** : `SelectedViewIds`, `ViewId`, `Nom`/`TypeLabel`, `HasSelection`, `Count`/`ViewDuplicateOption`, `build_options`, `duplicate(views, options)`, `all_views`, `get_selected_views` — cohérents entre tâches.
**Déviation assumée** : `if/elif/else` exclusif (Task 3) au lieu des `if` séparés de l'original (corrige la double-duplication des nomenclatures).
