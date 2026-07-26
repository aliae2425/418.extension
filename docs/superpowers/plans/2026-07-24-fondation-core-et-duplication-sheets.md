# Fondation `core` + Duplication des feuilles — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Poser la fondation `lib/core` partagée (transaction, sélection, sanitize Revit) et réécrire l'outil `duplicate_sheets` sur la charte WPF du projet (MVVM + coquille à rail avec pages Sélection / Options), sans modale bloquante.

**Architecture:** Trois utilitaires `core` neufs (charte, sans dépendance EF) servent de socle. `duplicate_sheets` devient une app MVVM à la manière d'`Audit` : `script.py` → `MainViewModel` + `MainWindowView` (sur `BaseWindow`), fenêtre borderless à rail hébergeant deux pages. L'état de sélection vit sur le `MainViewModel` et est partagé par les deux pages. La logique métier de duplication (API Revit) est portée verbatim dans un service piloté par le VM.

**Tech Stack:** IronPython 2/3 (pyRevit), WPF (XamlReader, pas de code-behind), `unittest` stdlib pour la logique pure, API Revit 2026.

## Global Constraints

- **Revit minimum** : 2026 (`__min_revit_ver__ = 2026`).
- **Python 2/3** : chaque fichier commence par `# -*- coding: utf-8 -*-` puis `from __future__ import unicode_literals`.
- **Imports Revit/WPF gardés** : tout import `Autodesk.Revit.*` / `System.*` est dans un `try/except` avec fallback `None`, pour rester importable hors Revit (tests standalone).
- **Langue** : tout le texte UI, les docstrings et les messages de commit sont en **français**.
- **Charte** : XAML chargé via `XamlReader.Load` (pas de `x:Class`, pas de code-behind) ; brushes/styles de thème référencés en `DynamicResource` ; thème fusionné par `BaseWindow` après parse.
- **Zéro branding EF** : aucun hyperlien « EF-Tools », bannière ASCII, footer version EF, ni palette EF (bleu foncé/magenta/aqua).
- **Pas de dépendance EF dans la chaîne duplication** : aucun import `Snippets.*` / `GUI.forms` / `Renaming.*` dans le code de `duplicate_sheets` ni dans les `core.*` qu'il consomme.
- **Commit** : messages terminés par la ligne `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Ne pas commiter sans confirmation de l'utilisateur (consigne projet) — les étapes « Commit » ci-dessous préparent le commit ; grouper/valider selon le mode d'exécution choisi.
- **Convention de test** : `unittest`, fichier `<button>/tests/test_*.py`. En tête de test, insérer dans `sys.path` la lib partagée puis le dossier bouton. Objets Revit simulés par des *fakes*. **Invocation par fichier direct** (chaque test insère son `sys.path` et finit par `unittest.main()`) : `python <chemin>/test_x.py -v` — plus robuste que `python -m unittest <dotted>` (règles de packages divergentes Py2/Py3, et pas de `__init__.py` dans les dossiers `tests/`). Confirmer que le 1er test tourne au vert avant d'enchaîner.

---

## File Structure

**Fondation partagée (`lib/`)** :
- Modify: `lib/core/sanitize.py` — ajout de `sanitize_revit_name()`.
- Create: `lib/core/transaction.py` — context manager de transaction Revit.
- Create: `lib/core/selection.py` — lecture de la sélection courante (feuilles/vues) + énumération, sans UI.
- Create: `lib/core/tests/test_sanitize.py`, `lib/core/tests/test_transaction.py`, `lib/core/tests/test_selection.py`.

**Outil `duplicate_sheets`** (`418.tab/Tools.panel/col1.stack/duplicate_sheets.pushbutton/`) :
- Modify: `script.py` — point d'entrée MVVM.
- Delete: `Script.xaml` (ancienne fenêtre EF).
- Create: `GUI/Views/MainWindow.xaml` — coquille borderless + rail + hôte de pages.
- Create: `GUI/Views/pages/SelectionPage.xaml` — page Sélection.
- Create: `GUI/Views/pages/OptionsPage.xaml` — page Options.
- Create: `lib/__init__.py`, `lib/viewmodels/__init__.py`, `lib/views/__init__.py`, `lib/services/__init__.py`.
- Create: `lib/services/DuplicationOptions.py` — objet de données des options.
- Create: `lib/services/DuplicationSheetsService.py` — logique métier portée.
- Create: `lib/viewmodels/SheetItemVM.py` — item de liste (Numero/Nom/IsSelected).
- Create: `lib/viewmodels/SelectionPageVM.py` — VM page Sélection.
- Create: `lib/viewmodels/OptionsPageVM.py` — VM page Options.
- Create: `lib/viewmodels/MainViewModel.py` — VM racine (navigation + état de sélection partagé + lancement).
- Create: `lib/views/MainWindowView.py` — vue racine (sur `BaseWindow`), chargement des pages, câblage.
- Create: `tests/test_sanitize_revit_name.py` n/a (couvert en fondation), `tests/test_main_viewmodel.py`, `tests/test_selection_page_vm.py`, `tests/test_options_page_vm.py`.

---

## PARTIE A — Fondation `lib/core`

### Task 1 : `sanitize_revit_name()` dans `core/sanitize`

Revit interdit dans les noms : `\ : { } [ ] | ; < > ? \` ~`. `sanitize()` (fichiers Windows) ne les couvre pas tous. On ajoute une fonction dédiée.

**Files:**
- Modify: `lib/core/sanitize.py`
- Test: `lib/core/tests/test_sanitize.py`

**Interfaces:**
- Produces: `sanitize_revit_name(name)` → `unicode`. Retire tout caractère interdit Revit ; si le résultat est vide, retourne `u'SansNom'`. Ne tronque pas (les noms Revit n'ont pas la limite 180 des fichiers).

- [ ] **Step 1 : Écrire le test qui échoue**

Create `lib/core/tests/test_sanitize.py` :

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

from core.sanitize import sanitize_revit_name


class TestSanitizeRevitName(unittest.TestCase):
    def test_retire_caracteres_interdits(self):
        self.assertEqual(sanitize_revit_name(u'A{B}[C];D'), u'ABCD')

    def test_retire_backtick_et_tilde(self):
        self.assertEqual(sanitize_revit_name(u'X`Y~Z'), u'XYZ')

    def test_retire_slash_colon_pipe(self):
        self.assertEqual(sanitize_revit_name(u'a\\b:c|d'), u'abcd')

    def test_conserve_texte_valide(self):
        self.assertEqual(sanitize_revit_name(u'Plan RDC 1-100'), u'Plan RDC 1-100')

    def test_vide_donne_sansnom(self):
        self.assertEqual(sanitize_revit_name(u'{}'), u'SansNom')
        self.assertEqual(sanitize_revit_name(u''), u'SansNom')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer le test, vérifier l'échec**

Run: `python lib/core/tests/test_sanitize.py -v` (depuis la racine `418.extension`)
Expected: FAIL — `ImportError: cannot import name 'sanitize_revit_name'`.

- [ ] **Step 3 : Implémenter**

Ajouter dans `lib/core/sanitize.py` (après la fonction `sanitize`) :

```python
_INVALID_REVIT = re.compile(r'[\\/:{}\[\]|;<>?`~]')


def sanitize_revit_name(name):
    """Nettoie un nom d'élément Revit : retire les caractères interdits par
    Revit (`\\ : { } [ ] | ; < > ? \` ~`). Retourne `u'SansNom'` si le
    résultat est vide. Ne tronque pas (contrairement à `sanitize`, dédié aux
    noms de fichiers)."""
    if not name:
        return u'SansNom'
    cleaned = _INVALID_REVIT.sub(u'', name)
    return cleaned if cleaned else u'SansNom'
```

- [ ] **Step 4 : Lancer le test, vérifier le succès**

Run: `python -m unittest lib.core.tests.test_sanitize -v`
Expected: PASS (5 tests).

- [ ] **Step 5 : Commit**

```bash
git add lib/core/sanitize.py lib/core/tests/test_sanitize.py
git commit -m "feat(core): ajoute sanitize_revit_name pour les noms d'éléments Revit"
```

---

### Task 2 : `core/transaction.py`

**Files:**
- Create: `lib/core/transaction.py`
- Test: `lib/core/tests/test_transaction.py`

**Interfaces:**
- Produces: `revit_transaction(doc, name)` — context manager. `Start()` à l'entrée, `Commit()` en sortie normale, `RollBack()` si une exception traverse le bloc (puis ré-émet). Remplace `ef_Transaction`.

- [ ] **Step 1 : Écrire le test qui échoue**

Create `lib/core/tests/test_transaction.py` :

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

from core.transaction import revit_transaction


class FakeTransaction(object):
    """Enregistre la séquence d'appels pour vérifier le flux."""
    def __init__(self, doc, name):
        self.name = name
        self.calls = []
        FakeTransaction.last = self

    def Start(self):
        self.calls.append('Start')

    def Commit(self):
        self.calls.append('Commit')

    def RollBack(self):
        self.calls.append('RollBack')


class TestRevitTransaction(unittest.TestCase):
    def setUp(self):
        import core.transaction as mod
        self._mod = mod
        self._orig = mod.Transaction
        mod.Transaction = FakeTransaction

    def tearDown(self):
        self._mod.Transaction = self._orig

    def test_commit_en_sortie_normale(self):
        with revit_transaction(object(), u'T'):
            pass
        self.assertEqual(FakeTransaction.last.calls, ['Start', 'Commit'])

    def test_rollback_puis_reeleve_sur_exception(self):
        with self.assertRaises(ValueError):
            with revit_transaction(object(), u'T'):
                raise ValueError('boom')
        self.assertEqual(FakeTransaction.last.calls, ['Start', 'RollBack'])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer le test, vérifier l'échec**

Run: `python lib/core/tests/test_transaction.py -v`
Expected: FAIL — `ImportError` (module inexistant).

- [ ] **Step 3 : Implémenter**

Create `lib/core/transaction.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import contextlib

try:
    from Autodesk.Revit.DB import Transaction
except Exception:
    Transaction = None


@contextlib.contextmanager
def revit_transaction(doc, name):
    """Context manager de transaction Revit.

    Ouvre une `Transaction`, la valide (`Commit`) en sortie normale, ou
    l'annule (`RollBack`) puis ré-émet si une exception traverse le bloc.

        with revit_transaction(doc, u'Dupliquer les feuilles'):
            ...  # modifications du document
    """
    if Transaction is None:
        raise RuntimeError(u'API Revit indisponible : Transaction introuvable.')
    t = Transaction(doc, name)
    t.Start()
    try:
        yield t
    except Exception:
        t.RollBack()
        raise
    else:
        t.Commit()
```

- [ ] **Step 4 : Lancer le test, vérifier le succès**

Run: `python lib/core/tests/test_transaction.py -v`
Expected: PASS (2 tests). Le fake remplace `Transaction`, donc le garde `None` ne bloque pas.

- [ ] **Step 5 : Commit**

```bash
git add lib/core/transaction.py lib/core/tests/test_transaction.py
git commit -m "feat(core): ajoute revit_transaction (context manager de transaction)"
```

---

### Task 3 : `core/selection.py`

Réécriture (pas un portage) des lecteurs de sélection : ils retournent la sélection **courante** filtrée (liste, possiblement vide) et **ne font aucune UI** — le cas « vide » est désormais géré par la page Sélection. Plus aucun appel à `select_from_dict`.

**Files:**
- Create: `lib/core/selection.py`
- Test: `lib/core/tests/test_selection.py`

**Interfaces:**
- Produces:
  - `get_selected_sheets(uidoc)` → `list` de `ViewSheet` sélectionnés (vide si aucun).
  - `get_selected_views(uidoc)` → `list` de vues sélectionnées, hors feuilles et hors templates.
  - `all_sheets(doc)` → `list` de toutes les `ViewSheet` du document, triées par `SheetNumber`. (Revit-couplé : testé en smoke-test Revit, pas en unitaire.)

- [ ] **Step 1 : Écrire le test qui échoue** (cible : `get_selected_sheets`, plomberie + filtrage)

Create `lib/core/tests/test_selection.py` :

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

import core.selection as selection


class FakeSheet(object):
    def __init__(self, sid):
        self.Id = sid


class FakeOther(object):
    def __init__(self, oid):
        self.Id = oid


class FakeSelection(object):
    def __init__(self, ids):
        self._ids = ids

    def GetElementIds(self):
        return self._ids


class FakeDoc(object):
    def __init__(self, by_id):
        self._by_id = by_id

    def GetElement(self, eid):
        return self._by_id[eid]


class FakeUIDoc(object):
    def __init__(self, ids, by_id):
        self.Selection = FakeSelection(ids)
        self.Document = FakeDoc(by_id)


class TestGetSelectedSheets(unittest.TestCase):
    def setUp(self):
        self._orig = selection.ViewSheet
        selection.ViewSheet = FakeSheet  # substitue le type filtré

    def tearDown(self):
        selection.ViewSheet = self._orig

    def test_ne_retient_que_les_feuilles(self):
        s1, s2, other = FakeSheet(1), FakeSheet(2), FakeOther(3)
        by_id = {1: s1, 2: s2, 3: other}
        uidoc = FakeUIDoc([1, 3, 2], by_id)
        result = selection.get_selected_sheets(uidoc)
        self.assertEqual(result, [s1, s2])

    def test_selection_vide_donne_liste_vide(self):
        uidoc = FakeUIDoc([], {})
        self.assertEqual(selection.get_selected_sheets(uidoc), [])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer le test, vérifier l'échec**

Run: `python lib/core/tests/test_selection.py -v`
Expected: FAIL — `ImportError` (module inexistant).

- [ ] **Step 3 : Implémenter**

Create `lib/core/selection.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from Autodesk.Revit.DB import ViewSheet, View, ViewType, FilteredElementCollector
except Exception:
    ViewSheet = None
    View = None
    ViewType = None
    FilteredElementCollector = None


def _selected_elements(uidoc):
    """Éléments actuellement sélectionnés dans l'UI Revit (liste brute)."""
    doc = uidoc.Document
    return [doc.GetElement(eid) for eid in uidoc.Selection.GetElementIds()]


def get_selected_sheets(uidoc):
    """Feuilles (`ViewSheet`) actuellement sélectionnées. Liste possiblement
    vide. Aucune UI : le cas vide est traité par la page Sélection."""
    if ViewSheet is None:
        return []
    return [e for e in _selected_elements(uidoc) if isinstance(e, ViewSheet)]


def get_selected_views(uidoc):
    """Vues sélectionnées, hors feuilles et hors templates de vue."""
    if View is None:
        return []
    out = []
    for e in _selected_elements(uidoc):
        if isinstance(e, View) and not isinstance(e, ViewSheet):
            if not getattr(e, 'IsTemplate', False):
                out.append(e)
    return out


def all_sheets(doc):
    """Toutes les `ViewSheet` du document, triées par `SheetNumber`."""
    if FilteredElementCollector is None or ViewSheet is None:
        return []
    sheets = list(FilteredElementCollector(doc)
                  .OfClass(ViewSheet)
                  .WhereElementIsNotElementType()
                  .ToElements())
    return sorted(sheets, key=lambda s: s.SheetNumber)
```

- [ ] **Step 4 : Lancer le test, vérifier le succès**

Run: `python lib/core/tests/test_selection.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5 : Commit**

```bash
git add lib/core/selection.py lib/core/tests/test_selection.py
git commit -m "feat(core): ajoute core.selection (lecture sélection feuilles/vues, sans UI)"
```

---

## PARTIE B — Outil `duplicate_sheets` (MVVM, rail/pages)

> Répertoire de travail des tâches B : `418.tab/Tools.panel/col1.stack/duplicate_sheets.pushbutton/`.
> En tête de chaque test de cette partie, `sys.path` reçoit la lib partagée (5 niveaux au-dessus de `tests/` : `duplicate_sheets.pushbutton → col1.stack → Tools.panel → 418.tab → 418.extension`, puis `/lib`) puis `..` (le bouton). Confirmer au 1er test.

### Task 4 : `DuplicationOptions` (objet de données)

Contrat de données entre `OptionsPageVM` (producteur) et `DuplicationSheetsService` (consommateur).

**Files:**
- Create: `lib/services/__init__.py` (contenu : les 2 lignes d'en-tête uniquement)
- Create: `lib/services/DuplicationOptions.py`
- Test: `tests/test_duplication_options.py`

**Interfaces:**
- Produces: classe `DuplicationOptions` avec constructeur à mots-clés et valeurs par défaut. Champs exacts (tous lus par le service en Task 5) :
  - Nommage vues : `view_find, view_replace, view_prefix, view_suffix` (str, défaut `u''`).
  - Nommage n° feuille : `number_find, number_replace, number_prefix, number_suffix` (str, défaut `u''`).
  - Nommage nom feuille : `name_find, name_replace, name_prefix, name_suffix` (str, défaut `u''`).
  - Inclusions (bool) : `include_views(=True), include_legends(=True), include_schedules(=True), include_images(=True), include_lines(=True), include_text(=True), include_clouds(=False), include_dwgs(=False), include_symbols(=False), include_dimensions(=False), include_additional_revisions(=False)`.
  - Réutilisation (bool) : `use_existing_legends(=True), use_existing_schedules(=True)`.
  - Option de duplication de vue : `view_duplicate_option` (str parmi `u'duplicate'`, `u'with_detailing'`, `u'as_dependent'` ; défaut `u'duplicate'`).

- [ ] **Step 1 : Écrire le test qui échoue**

Create `tests/test_duplication_options.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.services.DuplicationOptions import DuplicationOptions


class TestDuplicationOptions(unittest.TestCase):
    def test_defauts(self):
        o = DuplicationOptions()
        self.assertTrue(o.include_views)
        self.assertFalse(o.include_dimensions)
        self.assertTrue(o.use_existing_legends)
        self.assertEqual(o.view_duplicate_option, u'duplicate')
        self.assertEqual(o.view_prefix, u'')

    def test_surcharge_par_mots_cles(self):
        o = DuplicationOptions(view_prefix=u'DUP_', include_dimensions=True,
                               view_duplicate_option=u'as_dependent')
        self.assertEqual(o.view_prefix, u'DUP_')
        self.assertTrue(o.include_dimensions)
        self.assertEqual(o.view_duplicate_option, u'as_dependent')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer, vérifier l'échec** — `ImportError`.

Run (depuis le dossier bouton) : `python tests/test_duplication_options.py -v`

- [ ] **Step 3 : Implémenter**

Create `lib/services/__init__.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
```

Create `lib/services/DuplicationOptions.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class DuplicationOptions(object):
    """Options de duplication de feuilles. Contrat entre OptionsPageVM et
    DuplicationSheetsService. Tous les champs ont une valeur par défaut."""

    def __init__(self,
                 view_find=u'', view_replace=u'', view_prefix=u'', view_suffix=u'',
                 number_find=u'', number_replace=u'', number_prefix=u'', number_suffix=u'',
                 name_find=u'', name_replace=u'', name_prefix=u'', name_suffix=u'',
                 include_views=True, include_legends=True, include_schedules=True,
                 include_images=True, include_lines=True, include_text=True,
                 include_clouds=False, include_dwgs=False, include_symbols=False,
                 include_dimensions=False, include_additional_revisions=False,
                 use_existing_legends=True, use_existing_schedules=True,
                 view_duplicate_option=u'duplicate'):
        self.view_find = view_find
        self.view_replace = view_replace
        self.view_prefix = view_prefix
        self.view_suffix = view_suffix
        self.number_find = number_find
        self.number_replace = number_replace
        self.number_prefix = number_prefix
        self.number_suffix = number_suffix
        self.name_find = name_find
        self.name_replace = name_replace
        self.name_prefix = name_prefix
        self.name_suffix = name_suffix
        self.include_views = include_views
        self.include_legends = include_legends
        self.include_schedules = include_schedules
        self.include_images = include_images
        self.include_lines = include_lines
        self.include_text = include_text
        self.include_clouds = include_clouds
        self.include_dwgs = include_dwgs
        self.include_symbols = include_symbols
        self.include_dimensions = include_dimensions
        self.include_additional_revisions = include_additional_revisions
        self.use_existing_legends = use_existing_legends
        self.use_existing_schedules = use_existing_schedules
        self.view_duplicate_option = view_duplicate_option
```

- [ ] **Step 4 : Lancer, vérifier le succès** — PASS (2 tests).
- [ ] **Step 5 : Commit**

```bash
git add lib/services/__init__.py lib/services/DuplicationOptions.py tests/test_duplication_options.py
git commit -m "feat(duplicate_sheets): ajoute l'objet de données DuplicationOptions"
```

---

### Task 5 : `DuplicationSheetsService` (portage de la logique métier)

Portage **verbatim** des méthodes de duplication de l'ancien `script.py` EF dans un service. Aucune nouvelle logique. Fortement couplé à l'API Revit → **testé en smoke-test Revit** (pas de faux test unitaire qui n'exerce ni `Viewport.Create` ni `ViewSheet.Create`).

**Files:**
- Create: `lib/services/DuplicationSheetsService.py`
- Source de référence (à porter) : l'ancien `duplicate_sheets.pushbutton/script.py` **avant modification** (méthodes `update_view_name`, `update_sheet_name`, `update_sheet_number`, `duplicate_schedules`, `duplicate_legends`, `duplicate_views`, `duplicate_elements`, `duplicate_lines`, `duplicate_clouds`, `duplicate_images`, `duplicate_text`, `duplicate_dimensons`, `duplicate_symbols`, `duplicate_dwgs`, `duplicate_selected_sheets`, `set_additional_revisions_on_sheet`, `get_sheet_title_block`). Récupérer le contenu via `git show HEAD:'418.tab/Tools.panel/col1.stack/duplicate_sheets.pushbutton/script.py'` si `script.py` est déjà modifié.

**Interfaces:**
- Consumes: `DuplicationOptions` (Task 4), `revit_transaction` (Task 2), `sanitize_revit_name` (Task 1).
- Produces: classe `DuplicationSheetsService`
  - `__init__(self, doc)` → stocke `self._doc = doc`.
  - `duplicate(self, sheets, options)` → duplique chaque feuille de `sheets` (list de `ViewSheet`) selon `options` (`DuplicationOptions`). Enveloppe TOUT le travail dans `with revit_transaction(self._doc, u'Dupliquer les feuilles'):`. Retourne le nombre de feuilles créées (int).

- [ ] **Step 1 : Créer le squelette du service**

Create `lib/services/DuplicationSheetsService.py` avec l'en-tête, les imports gardés, et la structure :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from Autodesk.Revit.DB import (FilteredElementCollector, BuiltInCategory,
                                    ElementId, ViewSheet, ViewType,
                                    ViewDuplicateOption, Viewport,
                                    ScheduleSheetInstance, ImportInstance,
                                    ElementTransformUtils, CopyPasteOptions,
                                    ElementMulticategoryFilter)
    from System.Collections.Generic import List
except Exception:
    FilteredElementCollector = None  # (+ tous les autres = None)

try:
    from core.transaction import revit_transaction
except Exception:
    revit_transaction = None

try:
    from core.sanitize import sanitize_revit_name
except Exception:
    def sanitize_revit_name(x):
        return x or u'SansNom'


_VIEW_DUP_MAP = {
    u'duplicate': 'Duplicate',
    u'with_detailing': 'WithDetailing',
    u'as_dependent': 'AsDependent',
}


class DuplicationSheetsService(object):
    def __init__(self, doc):
        self._doc = doc

    def _view_dup_option(self, key):
        """Traduit la clé d'option (str) en ViewDuplicateOption."""
        name = _VIEW_DUP_MAP.get(key, 'Duplicate')
        return getattr(ViewDuplicateOption, name)

    def duplicate(self, sheets, options):
        created = 0
        with revit_transaction(self._doc, u'Dupliquer les feuilles'):
            for sheet in sheets:
                self._duplicate_one(sheet, options)
                created += 1
        return created

    # ... méthodes portées ci-dessous (Step 2) ...
```

- [ ] **Step 2 : Porter les méthodes selon la table de substitution**

Copier chaque méthode listée depuis la source de référence dans la classe, en appliquant **exhaustivement** ces substitutions (aucune autre modification de logique) :

| Dans la source EF | Devient dans le service |
|---|---|
| `doc` (variable globale) | `self._doc` |
| `self.selected_sheets` | le paramètre `sheets` (boucle dans `duplicate()`) |
| `self.remove_special_charachter(x)` | `sanitize_revit_name(x)` |
| `self.view_find / view_replace / view_prefix / view_suffix` | `options.view_find / view_replace / view_prefix / view_suffix` |
| `self.sheet_number_find / _replace / _prefix / _suffix` | `options.number_find / number_replace / number_prefix / number_suffix` |
| `self.sheet_name_find / _replace / _prefix / _suffix` | `options.name_find / name_replace / name_prefix / name_suffix` |
| `self.checkbox_views` | `options.include_views` |
| `self.checkbox_legends` | `options.include_legends` |
| `self.checkbox_schedules` | `options.include_schedules` |
| `self.checkbox_images` | `options.include_images` |
| `self.checkbox_lines` | `options.include_lines` |
| `self.checkbox_text` | `options.include_text` |
| `self.checkbox_clouds` | `options.include_clouds` |
| `self.checkbox_dwgs` | `options.include_dwgs` |
| `self.checkbox_symbols` | `options.include_symbols` |
| `self.checkbox_dimensions` | `options.include_dimensions` |
| `self.checkbox_additional_revisions` | `options.include_additional_revisions` |
| `self.use_existing_legends` | `options.use_existing_legends` |
| `self.use_existing_schedules` | `options.use_existing_schedules` |
| `self.view_dupicate_option` | `self._view_dup_option(options.view_duplicate_option)` |

Règles supplémentaires :
- Les méthodes de nommage/duplication (`update_*`, `duplicate_*`, `set_additional_revisions_on_sheet`, `get_sheet_title_block`) gardent leur signature `(self, ...)` et leur corps, transformés selon la table.
- Le corps de `duplicate_selected_sheets` (ancienne boucle `for sheet in self.selected_sheets:`) devient la méthode **`_duplicate_one(self, sheet, options)`** : le corps par feuille (title block, `ViewSheet.Create`, appels conditionnels `if options.include_*: self.duplicate_X(sheet, new_sheet)`) — **sans** la transaction (gérée par `duplicate()`).
- Ne PAS porter : `__init__` EF, les `@property` GUI, les `button_*/header_drag/Hyperlink_RequestNavigate/radiobutton_*`, `get_selected_sheets`. Ils appartiennent au VM/View.
- Retirer les `print(...)` de debug EF.

- [ ] **Step 3 : Smoke-test Revit** (honnête : le service touche l'API Revit)

Ce test se fait dans Revit après la Task 10 (l'outil complet). Le noter ici comme critère de sortie du service :
1. Ouvrir un projet avec ≥1 feuille contenant vues + légende + nomenclature + texte.
2. Lancer l'outil, sélectionner cette feuille, cocher Views/Legends/Schedules/Text, Lancer.
3. **Observer** : une nouvelle feuille est créée ; ses vues sont dupliquées (pas de doublon de nom → suffixe `*` si collision) ; la légende est placée ; aucune exception dans la console pyRevit.

- [ ] **Step 4 : Commit**

```bash
git add lib/services/DuplicationSheetsService.py
git commit -m "feat(duplicate_sheets): porte la logique de duplication dans un service charte"
```

---

### Task 6 : `SheetItemVM` + `SelectionPageVM`

État de sélection **partagé** : le `MainViewModel` (Task 8) détient la liste de travail `SelectedSheets`. `SelectionPageVM` liste **toutes** les feuilles, **pré-cochées** selon la sélection courante, et répercute les changements dans l'état partagé.

**Files:**
- Create: `lib/viewmodels/__init__.py` (en-tête seul)
- Create: `lib/viewmodels/SheetItemVM.py`
- Create: `lib/viewmodels/SelectionPageVM.py`
- Test: `tests/test_selection_page_vm.py`

**Interfaces:**
- `SheetItemVM(sheet_id, numero, nom, is_selected, on_toggle)` : propriétés CLR `Numero` (str), `Nom` (str), `IsSelected` (bool, setter notifie et appelle `on_toggle(self)`), attribut `SheetId`.
- `SelectionPageVM(descripteurs, ids_selectionnes, on_selection_changed)` où :
  - `descripteurs` = list de tuples `(sheet_id, numero, nom)` (fournis par MainVM via `all_sheets`).
  - `ids_selectionnes` = set/list d'`Id` initialement cochés.
  - `on_selection_changed(list_ids)` = callback appelé à chaque toggle avec la liste des `SheetId` cochés.
  - Property CLR `Items` = list de `SheetItemVM`.
  - Method `selected_ids()` → list des `SheetId` cochés.

- [ ] **Step 1 : Écrire le test qui échoue**

Create `tests/test_selection_page_vm.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.viewmodels.SelectionPageVM import SelectionPageVM


class TestSelectionPageVM(unittest.TestCase):
    def setUp(self):
        self.descripteurs = [(1, u'A101', u'RDC'), (2, u'A102', u'R+1'), (3, u'A103', u'R+2')]
        self.changes = []

    def _vm(self, ids):
        return SelectionPageVM(self.descripteurs, ids,
                               on_selection_changed=lambda l: self.changes.append(list(l)))

    def test_items_precoches_selon_selection(self):
        vm = self._vm([2])
        etats = [(it.Numero, it.IsSelected) for it in vm.Items]
        self.assertEqual(etats, [(u'A101', False), (u'A102', True), (u'A103', False)])

    def test_toggle_met_a_jour_selection_et_notifie(self):
        vm = self._vm([])
        vm.Items[0].IsSelected = True
        vm.Items[2].IsSelected = True
        self.assertEqual(sorted(vm.selected_ids()), [1, 3])
        self.assertEqual(self.changes[-1], [1, 3])

    def test_decoche_retire_de_la_selection(self):
        vm = self._vm([1, 2])
        vm.Items[0].IsSelected = False
        self.assertEqual(vm.selected_ids(), [2])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer, vérifier l'échec** — `ImportError`.

- [ ] **Step 3 : Implémenter**

Create `lib/viewmodels/__init__.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
```

Create `lib/viewmodels/SheetItemVM.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object


class SheetItemVM(BaseViewModel):
    """Ligne de la page Sélection : une feuille cochable."""

    def __init__(self, sheet_id, numero, nom, is_selected, on_toggle):
        super(SheetItemVM, self).__init__()
        self.SheetId = sheet_id
        self._numero = numero
        self._nom = nom
        self._is_selected = is_selected
        self._on_toggle = on_toggle

    @property
    def Numero(self):
        return self._numero

    @property
    def Nom(self):
        return self._nom

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

Create `lib/viewmodels/SelectionPageVM.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

try:
    from lib.viewmodels.SheetItemVM import SheetItemVM
except Exception:
    from viewmodels.SheetItemVM import SheetItemVM


class SelectionPageVM(BaseViewModel):
    """VM de la page Sélection : liste toutes les feuilles, pré-cochées selon
    la sélection courante, et répercute les changements via callback."""

    def __init__(self, descripteurs, ids_selectionnes, on_selection_changed=None):
        super(SelectionPageVM, self).__init__()
        self._on_selection_changed = on_selection_changed
        selset = set(ids_selectionnes or [])
        self._items = [SheetItemVM(sid, numero, nom, sid in selset, self._on_item_toggle)
                       for (sid, numero, nom) in descripteurs]

    @property
    def Items(self):
        return self._items

    def selected_ids(self):
        return [it.SheetId for it in self._items if it.IsSelected]

    def _on_item_toggle(self, item):
        if self._on_selection_changed is not None:
            self._on_selection_changed(self.selected_ids())
```

- [ ] **Step 4 : Lancer, vérifier le succès** — PASS (3 tests).
- [ ] **Step 5 : Commit**

```bash
git add lib/viewmodels/__init__.py lib/viewmodels/SheetItemVM.py lib/viewmodels/SelectionPageVM.py tests/test_selection_page_vm.py
git commit -m "feat(duplicate_sheets): VM page Sélection (feuilles pré-cochées, état partagé)"
```

---

### Task 7 : `OptionsPageVM`

Expose les champs de nommage + inclusions + option de duplication, et produit un `DuplicationOptions`.

**Files:**
- Create: `lib/viewmodels/OptionsPageVM.py`
- Test: `tests/test_options_page_vm.py`

**Interfaces:**
- Consumes: `DuplicationOptions` (Task 4).
- Produces: `OptionsPageVM()` avec propriétés CLR bindables correspondant 1:1 aux champs de `DuplicationOptions` (mêmes noms en PascalCase pour le binding : `ViewFind`, `ViewReplace`, `ViewPrefix`, `ViewSuffix`, `NumberFind`, …, `NameSuffix`, `IncludeViews`, …, `IncludeAdditionalRevisions`, `UseExistingLegends`, `UseExistingSchedules`, `ViewDuplicateOption`). Method `build_options()` → `DuplicationOptions` peuplé depuis l'état courant.

> ⚠️ **Risque à lever tôt (binding WPF).** Cette VM attache ses propriétés dynamiquement (`setattr(OptionsPageVM, _pas, _prop(_pas))`), contrairement aux autres VMs (`@property` inline, patron que le projet déclare fiable). Les tests unitaires **ne peuvent pas** valider ce point : en CPython, `BaseViewModel` retombe sur `object` et `notify_property` est inerte, donc aucun test n'exerce le binding réel. **Avant de généraliser la fabrique aux 27 champs**, faire un spike Revit sur **un seul** champ (ex. `ViewPrefix`) : saisir dans son TextBox et vérifier que la valeur arrive dans `build_options()`. Si le binding TwoWay ne voit pas les descripteurs `property` attachés dynamiquement, **repli sur des `@property` inline** (verbeux mais éprouvé — 27 blocs getter/setter notifiants sur le modèle de `SheetItemVM.IsSelected`).

- [ ] **Step 1 : Écrire le test qui échoue**

Create `tests/test_options_page_vm.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.viewmodels.OptionsPageVM import OptionsPageVM


class TestOptionsPageVM(unittest.TestCase):
    def test_defauts_mappent_vers_options(self):
        o = OptionsPageVM().build_options()
        self.assertEqual(o.view_prefix, u'')
        self.assertTrue(o.include_views)
        self.assertFalse(o.include_dimensions)
        self.assertEqual(o.view_duplicate_option, u'duplicate')

    def test_modifs_se_refletent_dans_options(self):
        vm = OptionsPageVM()
        vm.ViewPrefix = u'DUP_'
        vm.NumberSuffix = u'-b'
        vm.IncludeDimensions = True
        vm.UseExistingLegends = False
        vm.ViewDuplicateOption = u'as_dependent'
        o = vm.build_options()
        self.assertEqual(o.view_prefix, u'DUP_')
        self.assertEqual(o.number_suffix, u'-b')
        self.assertTrue(o.include_dimensions)
        self.assertFalse(o.use_existing_legends)
        self.assertEqual(o.view_duplicate_option, u'as_dependent')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer, vérifier l'échec** — `ImportError`.

- [ ] **Step 3 : Implémenter**

Create `lib/viewmodels/OptionsPageVM.py`. Chaque propriété suit le patron getter/setter notifiant. Pour rester concis mais complet, utiliser une fabrique de propriétés :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

try:
    from lib.services.DuplicationOptions import DuplicationOptions
except Exception:
    from services.DuplicationOptions import DuplicationOptions


def _prop(attr):
    """Fabrique une property CLR notifiante sur l'attribut privé _<attr>."""
    priv = '_' + attr

    def getter(self):
        return getattr(self, priv)

    def setter(self, value):
        if getattr(self, priv) != value:
            setattr(self, priv, value)
            self.notify_property(attr)
    return property(getter, setter)


class OptionsPageVM(BaseViewModel):
    """VM de la page Options : nommage + inclusions + option de duplication."""

    # Mapping propriété PascalCase -> champ DuplicationOptions
    _MAP = {
        'ViewFind': 'view_find', 'ViewReplace': 'view_replace',
        'ViewPrefix': 'view_prefix', 'ViewSuffix': 'view_suffix',
        'NumberFind': 'number_find', 'NumberReplace': 'number_replace',
        'NumberPrefix': 'number_prefix', 'NumberSuffix': 'number_suffix',
        'NameFind': 'name_find', 'NameReplace': 'name_replace',
        'NamePrefix': 'name_prefix', 'NameSuffix': 'name_suffix',
        'IncludeViews': 'include_views', 'IncludeLegends': 'include_legends',
        'IncludeSchedules': 'include_schedules', 'IncludeImages': 'include_images',
        'IncludeLines': 'include_lines', 'IncludeText': 'include_text',
        'IncludeClouds': 'include_clouds', 'IncludeDwgs': 'include_dwgs',
        'IncludeSymbols': 'include_symbols', 'IncludeDimensions': 'include_dimensions',
        'IncludeAdditionalRevisions': 'include_additional_revisions',
        'UseExistingLegends': 'use_existing_legends',
        'UseExistingSchedules': 'use_existing_schedules',
        'ViewDuplicateOption': 'view_duplicate_option',
    }

    def __init__(self):
        super(OptionsPageVM, self).__init__()
        # Initialise chaque attribut privé depuis les défauts de DuplicationOptions.
        defaults = DuplicationOptions()
        for pas, field in self._MAP.items():
            setattr(self, '_' + pas, getattr(defaults, field))

    def build_options(self):
        kwargs = {}
        for pas, field in self._MAP.items():
            kwargs[field] = getattr(self, '_' + pas)
        return DuplicationOptions(**kwargs)


# Attache les propriétés notifiantes à la classe (après définition).
for _pas in list(OptionsPageVM._MAP.keys()):
    setattr(OptionsPageVM, _pas, _prop(_pas))
```

- [ ] **Step 4 : Lancer, vérifier le succès** — PASS (2 tests).
- [ ] **Step 5 : Commit**

```bash
git add lib/viewmodels/OptionsPageVM.py tests/test_options_page_vm.py
git commit -m "feat(duplicate_sheets): VM page Options (nommage/inclusions -> DuplicationOptions)"
```

---

### Task 8 : `MainViewModel` (navigation + état partagé + lancement)

VM racine : détient l'état de sélection partagé, décide de la page initiale, expose le mode courant, et orchestre le lancement.

**Files:**
- Create: `lib/viewmodels/MainViewModel.py`
- Test: `tests/test_main_viewmodel.py`

**Interfaces:**
- Consumes: `SelectionPageVM` (Task 6), `OptionsPageVM` (Task 7), `DuplicationSheetsService` (Task 5), `core.selection` (Task 3).
- Produces: `MainViewModel(doc=None, uidoc=None, service=None)`
  - Property CLR `Titre` (str) = `u'418 · Dupliquer les feuilles'`.
  - Property CLR `Mode` (str : `u'selection'` | `u'options'`, notifie ; expose aussi `IsSelection`/`IsOptions` bool notifiés pour la visibilité XAML).
  - `SelectedSheetIds` (list) = état de sélection partagé (ids de feuilles cochées).
  - `SelectionVM` / `OptionsVM` : instances des VMs de page (construites au chargement des données).
  - `@staticmethod decide_initial_mode(has_selection)` → `u'options'` si `has_selection` sinon `u'selection'`.
  - `set_mode(mode)` → change `Mode` (+ IsSelection/IsOptions).
  - `charger(descripteurs, ids_courants)` → construit `SelectionVM`/`OptionsVM`, initialise `SelectedSheetIds = list(ids_courants)`, fixe le mode via `decide_initial_mode(bool(ids_courants))`.
  - `_on_selection_changed(ids)` → met à jour `SelectedSheetIds`.
  - `lancer(sheets_par_id)` → si `SelectedSheetIds` non vide, appelle `service.duplicate([sheets_par_id[i] for i in SelectedSheetIds], OptionsVM.build_options())`.

- [ ] **Step 1 : Écrire le test qui échoue** (cible : `decide_initial_mode`, `charger`, `set_mode`, propagation sélection)

Create `tests/test_main_viewmodel.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.viewmodels.MainViewModel import MainViewModel


class TestMainViewModel(unittest.TestCase):
    DESCR = [(1, u'A101', u'RDC'), (2, u'A102', u'R+1')]

    def test_decide_initial_mode(self):
        self.assertEqual(MainViewModel.decide_initial_mode(True), u'options')
        self.assertEqual(MainViewModel.decide_initial_mode(False), u'selection')

    def test_charger_avec_selection_ouvre_options(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [1])
        self.assertEqual(vm.Mode, u'options')
        self.assertTrue(vm.IsOptions)
        self.assertFalse(vm.IsSelection)
        self.assertEqual(vm.SelectedSheetIds, [1])

    def test_charger_sans_selection_ouvre_selection(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [])
        self.assertEqual(vm.Mode, u'selection')
        self.assertTrue(vm.IsSelection)

    def test_toggle_dans_page_met_a_jour_etat_partage(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [])
        vm.SelectionVM.Items[1].IsSelected = True  # coche A102 (id 2)
        self.assertEqual(vm.SelectedSheetIds, [2])

    def test_set_mode(self):
        vm = MainViewModel()
        vm.charger(self.DESCR, [1])
        vm.set_mode(u'selection')
        self.assertEqual(vm.Mode, u'selection')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2 : Lancer, vérifier l'échec** — `ImportError`.

- [ ] **Step 3 : Implémenter**

Create `lib/viewmodels/MainViewModel.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

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
        self.SelectedSheetIds = []
        self.SelectionVM = None
        self.OptionsVM = None

    @property
    def Titre(self):
        return u'418 · Dupliquer les feuilles'

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
        self.SelectedSheetIds = list(ids_courants)
        self.SelectionVM = SelectionPageVM(descripteurs, ids_courants,
                                           on_selection_changed=self._on_selection_changed)
        self.OptionsVM = OptionsPageVM()
        self.notify_property('SelectionVM')
        self.notify_property('OptionsVM')
        self.set_mode(self.decide_initial_mode(bool(ids_courants)))

    def _on_selection_changed(self, ids):
        self.SelectedSheetIds = list(ids)

    def lancer(self, sheets_par_id):
        if not self.SelectedSheetIds or self._service is None:
            return 0
        sheets = [sheets_par_id[i] for i in self.SelectedSheetIds if i in sheets_par_id]
        return self._service.duplicate(sheets, self.OptionsVM.build_options())
```

- [ ] **Step 4 : Lancer, vérifier le succès** — PASS (5 tests).
- [ ] **Step 5 : Commit**

```bash
git add lib/viewmodels/MainViewModel.py tests/test_main_viewmodel.py
git commit -m "feat(duplicate_sheets): MainViewModel (navigation, état partagé, lancement)"
```

---

### Task 9 : XAML — coquille + pages

Fenêtre borderless à rail, calquée sur `418.tab/Audit.panel/Audit.pushbutton/GUI/Views/MainWindow.xaml`. Pas de code-behind. Deux pages chargées séparément et injectées dans un `ContentControl` hôte (patron `_load_page` de `BatchExport/lib/views/MainWindowView.py`).

**Files:**
- Create: `GUI/Views/MainWindow.xaml`
- Create: `GUI/Views/pages/SelectionPage.xaml`
- Create: `GUI/Views/pages/OptionsPage.xaml`
- Delete: `Script.xaml`
- Référence de style : `Audit/GUI/Views/MainWindow.xaml` (WindowChrome, TitleBar, `NavRailButtonStyle`, `CaptionButtonStyle`, `CaptionCloseButtonStyle`, `ShellSurfaceStyle`, `BrandLogoBorderStyle`).

**Interfaces (noms requis par la View en Task 10) :**
- `x:Name="TitleBar"` (DragMove), `MinimizeButton`, `MaximizeRestoreButton`, `CloseButton` (câblés par `BaseWindow`).
- Rail : deux `RadioButton` `GroupName="nav"` nommés `NavSelection` et `NavOptions`.
- `x:Name="PageHost"` (`ContentControl`) : reçoit la page courante.
- Bouton `x:Name="RunButton"` (dans OptionsPage) : lance la duplication.

- [ ] **Step 1 : Créer `MainWindow.xaml`**

Reprendre la structure d'`Audit/GUI/Views/MainWindow.xaml` (en-tête `Window` + `WindowChrome` + `Border` racine + `TitleBar` + boutons de légende + rail) et remplacer le corps de contenu par un `ContentControl x:Name="PageHost"`. Points obligatoires :
- `Title="{Binding Titre}"`, `WindowStyle="None"`, `AllowsTransparency="True"`, `Background="{DynamicResource TransparentBrush}"`.
- `TitleBar` avec texte `418 · Dupliquer les feuilles`.
- Rail (colonne 64px) : `RadioButton x:Name="NavSelection"` (ToolTip « Sélection ») et `RadioButton x:Name="NavOptions"` (ToolTip « Options »), tous deux `Style="{DynamicResource NavRailButtonStyle}"`, `GroupName="nav"`.
- Surface : `Border Style="{DynamicResource ShellSurfaceStyle}"` contenant `<ContentControl x:Name="PageHost"/>`.
- Aucune couleur en dur : tout en `DynamicResource`.

- [ ] **Step 2 : Créer `pages/SelectionPage.xaml`**

`UserControl` (racine) chargé via `XamlReader`, `DataContext` = `SelectionPageVM`. Contenu :
- Un `DataGrid` ou `ItemsControl` lié à `{Binding Items}`.
- Par item : `CheckBox IsChecked="{Binding IsSelected, Mode=TwoWay}"`, `TextBlock {Binding Numero}`, `TextBlock {Binding Nom}`.
- Styles de thème en `DynamicResource` (fond, texte). En-tête « Feuilles à dupliquer ».

- [ ] **Step 3 : Créer `pages/OptionsPage.xaml`**

`UserControl`, `DataContext` = `OptionsPageVM`. Contenu (bindings `Mode=TwoWay`) :
- Section « Nommage » : 3 colonnes (Vue / N° feuille / Nom feuille), chacune 4 `TextBox` liés à `ViewFind/Replace/Prefix/Suffix`, `NumberFind/…`, `NameFind/…`.
- Section « Éléments inclus » : `CheckBox` pour `IncludeViews … IncludeAdditionalRevisions`.
- Section « Réutiliser l'existant » : `CheckBox` `UseExistingLegends`, `UseExistingSchedules`.
- Section « Option de duplication de vue » : 3 `RadioButton` (Duplicate / Avec détails / Dépendante) pilotant `ViewDuplicateOption` (câblage côté View en Task 10, ou converter — voir Task 10).
- Bouton `x:Name="RunButton"` : « Dupliquer les feuilles sélectionnées ».

- [ ] **Step 4 : Supprimer l'ancien XAML**

```bash
git rm "418.tab/Tools.panel/col1.stack/duplicate_sheets.pushbutton/Script.xaml"
```

- [ ] **Step 5 : Commit**

```bash
git add "418.tab/Tools.panel/col1.stack/duplicate_sheets.pushbutton/GUI"
git commit -m "feat(duplicate_sheets): coquille XAML charte (rail + pages Sélection/Options)"
```

---

### Task 10 : `MainWindowView` + `script.py` + smoke-test bout-en-bout

Assemble tout : charge la fenêtre via `BaseWindow`, lit la sélection Revit, construit les descripteurs, charge le VM, injecte les pages, câble la navigation, le bouton Run et les radios d'option.

**Files:**
- Create: `lib/views/__init__.py` (en-tête seul), `lib/__init__.py` (en-tête seul)
- Create: `lib/views/MainWindowView.py`
- Modify: `script.py`

**Interfaces:**
- Consumes: `BaseWindow`, `MainViewModel`, `DuplicationSheetsService`, `core.selection`.

- [ ] **Step 1 : Implémenter `MainWindowView`**

Create `lib/views/MainWindowView.py` (patron : `BatchExport/lib/views/MainWindowView.py` pour `_load_page` et le câblage) :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = object


def _xaml_path():
    here = os.path.dirname(os.path.abspath(__file__))
    button = os.path.abspath(os.path.join(here, '..', '..'))
    return os.path.join(button, 'GUI', 'Views', 'MainWindow.xaml')


class MainWindowView(BaseWindow):
    def __init__(self, view_model, sheets_par_id):
        super(MainWindowView, self).__init__(_xaml_path(), view_model)
        self._vm = view_model
        self._sheets_par_id = sheets_par_id

    def _load(self):
        super(MainWindowView, self)._load()
        if self._window is None:
            return
        self._mount_pages()
        self._wire_nav()
        self._wire_run()
        self._sync_nav()

    def _load_page(self, filename, data_context):
        from System.Windows.Markup import XamlReader
        from System.IO import FileStream, FileMode, FileAccess
        here = os.path.dirname(os.path.abspath(__file__))
        button = os.path.abspath(os.path.join(here, '..', '..'))
        path = os.path.join(button, 'GUI', 'Views', 'pages', filename)
        stream = FileStream(path, FileMode.Open, FileAccess.Read)
        try:
            page = XamlReader.Load(stream)
        finally:
            stream.Close()
        page.DataContext = data_context
        return page

    def _mount_pages(self):
        self._page_selection = self._load_page('SelectionPage.xaml', self._vm.SelectionVM)
        self._page_options = self._load_page('OptionsPage.xaml', self._vm.OptionsVM)
        self._show_current_page()

    def _show_current_page(self):
        host = self._window.FindName('PageHost')
        if host is None:
            return
        host.Content = self._page_options if self._vm.IsOptions else self._page_selection

    def _wire_nav(self):
        nav_sel = self._window.FindName('NavSelection')
        nav_opt = self._window.FindName('NavOptions')
        if nav_sel is not None:
            def _on_sel(sender, args):
                self._vm.set_mode(u'selection')
                self._show_current_page()
            nav_sel.Checked += _on_sel
        if nav_opt is not None:
            def _on_opt(sender, args):
                self._vm.set_mode(u'options')
                self._show_current_page()
            nav_opt.Checked += _on_opt

    def _sync_nav(self):
        # Coche le RadioButton correspondant au mode initial décidé par le VM.
        name = 'NavOptions' if self._vm.IsOptions else 'NavSelection'
        btn = self._window.FindName(name)
        if btn is not None:
            btn.IsChecked = True

    def _wire_run(self):
        # Le bouton Run vit dans OptionsPage : le retrouver dans l'arbre de la page.
        btn = self._page_options.FindName('RunButton')
        if btn is None:
            return

        def _on_run(sender, args):
            try:
                self._vm.lancer(self._sheets_par_id)
            finally:
                self._window.Close()
        btn.Click += _on_run
```

Câblage **obligatoire** des radios d'option de vue (sinon les radios sont inertes et l'option reste silencieusement `'duplicate'`). Dans le XAML (Task 9 Step 3), chaque `RadioButton` porte un `Tag` (`duplicate` / `with_detailing` / `as_dependent`) et `x:Name` (`RadioDuplicate` / `RadioDetailing` / `RadioDependent`). Ajouter dans `MainWindowView` une méthode câblée depuis `_load` (après `_wire_run`) :

```python
    def _wire_view_dup_option(self):
        for name in ('RadioDuplicate', 'RadioDetailing', 'RadioDependent'):
            rb = self._page_options.FindName(name)
            if rb is None:
                continue

            def _on_checked(sender, args):
                self._vm.OptionsVM.ViewDuplicateOption = sender.Tag
            rb.Checked += _on_checked
```

Appeler `self._wire_view_dup_option()` dans `_load` juste après `self._wire_run()`.

- [ ] **Step 2 : Implémenter `script.py`**

Modify `script.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Dupliquer\nfeuilles"
__doc__ = "Duplique les feuilles sélectionnées (vues, légendes, nomenclatures, éléments) avec renommage."
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
from lib.services.DuplicationSheetsService import DuplicationSheetsService
from core.selection import get_selected_sheets, all_sheets

if __name__ == '__main__':
    sheets = all_sheets(doc) if doc is not None else []
    sheets_par_id = {}
    descripteurs = []
    for s in sheets:
        sheets_par_id[s.Id] = s
        descripteurs.append((s.Id, s.SheetNumber, s.Name))

    ids_courants = [s.Id for s in (get_selected_sheets(uidoc) if uidoc is not None else [])]

    service = DuplicationSheetsService(doc)
    vm = MainViewModel(doc=doc, uidoc=uidoc, service=service)
    vm.charger(descripteurs, ids_courants)

    view = MainWindowView(vm, sheets_par_id)
    view.show()
```

- [ ] **Step 3 : Créer les `__init__.py` manquants**

```bash
printf '# -*- coding: utf-8 -*-\nfrom __future__ import unicode_literals\n' > lib/__init__.py
printf '# -*- coding: utf-8 -*-\nfrom __future__ import unicode_literals\n' > lib/views/__init__.py
```

- [ ] **Step 4 : Smoke-test Revit bout-en-bout** (critère de sortie du plan)

1. pyRevit → **Reload**.
2. **Cas sélection non vide** : sélectionner 1–2 feuilles dans l'arborescence, cliquer le bouton. **Attendu** : la fenêtre s'ouvre directement sur la page **Options** ; le rail « Options » est actif ; thème correct (clair/sombre selon Revit).
3. Régler quelques options (préfixe de nom, cocher Views + Legends), cliquer **Dupliquer**. **Attendu** : la fenêtre se ferme ; de nouvelles feuilles apparaissent avec le préfixe ; vues et légendes reportées ; aucune exception en console.
4. **Cas sélection vide** : tout désélectionner, relancer. **Attendu** : la fenêtre s'ouvre sur la page **Sélection** (⚠️ pas de modale bloquante) listant toutes les feuilles, aucune pré-cochée. Cocher 2 feuilles → aller sur Options via le rail → Dupliquer. **Attendu** : les 2 feuilles cochées sont dupliquées.
5. **Cas pré-cochage** : sélectionner 1 feuille, lancer, aller sur la page **Sélection** via le rail. **Attendu** : la feuille sélectionnée dans Revit est déjà cochée.

- [ ] **Step 5 : Commit**

```bash
git add "418.tab/Tools.panel/col1.stack/duplicate_sheets.pushbutton"
git commit -m "feat(duplicate_sheets): assemble la vue MVVM + point d'entrée (rail/pages, sans modale)"
```

---

## Self-Review (effectuée)

**Couverture spec :**
- §3.b promotion `core` : `transaction` (Task 2), `selection` (Task 3) couverts. `units` → **hors périmètre de ce plan** (consommé par LevelsElevation/Phase 2 uniquement ; noté ci-dessous).
- §3.a `GUI.forms` : résolu par contournement (core.selection neuf, sans `select_from_dict`). Élimination *complète* dans Snippets/Rename = Phase 2 (spec §7).
- §4 duplication : coquille rail/pages (Task 9), MVVM (Tasks 6–8, 10), logique préservée (Task 5), sélection via core (Task 3), transaction via core (Task 2), sanitize Revit (Task 1), FR + sans branding (partout). ✔
- §4.d résolu : `sanitize_revit_name` (Task 1) au lieu de `sanitize` (fichiers).

**Hors périmètre (plans/vagues suivants), volontairement :**
- `views_duplicate` : plan frère, même patron (Tasks 4–10 transposées : logique triviale, pas de page Options complexe).
- `core/units`, modale de sélection charte, nettoyage Snippets/Selection (Vagues 2+), socle `Renaming` charte, Phase 2 Rename.

**Placeholders :** aucun `TBD`/`TODO`/« add error handling ». Le portage Task 5 renvoie à une source réelle avec table de substitution exhaustive (pas « similar to »).

**Cohérence des types :** `DuplicationOptions` (champs snake_case) ↔ `OptionsPageVM._MAP` (PascalCase → snake_case) ↔ substitutions Task 5 : vérifiées identiques. `SelectedSheetIds`, `charger`, `set_mode`, `decide_initial_mode`, `lancer`, `Items`, `IsSelected`, `SheetId`, `build_options`, `duplicate`, `revit_transaction`, `sanitize_revit_name`, `get_selected_sheets`, `all_sheets` : noms utilisés de façon cohérente entre tâches.

**Point d'attention exécution :** profondeur `sys.path` de la Partie B = **5** `..` puis `/lib` (`duplicate_sheets.pushbutton → col1.stack → Tools.panel → 418.tab → 418.extension`). Confirmer au 1er test avant d'enchaîner.
