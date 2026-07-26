# BatchExport — Migration Phase 1 (squelette MVVM + coquille commune)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** Poser le squelette MVVM de BatchExport sur la coquille commune (façon Audit) et supprimer les helpers dupliqués, sans encore migrer le moteur d'export.

**Architecture :** `script.py` → `MainViewModel(doc)` → `MainWindowView(BaseWindow)`. La fenêtre charge un XAML monté sur la coquille commune (rail 64px + surface flottante + footer). Le ViewModel gère l'état de navigation (mode actif : par jeu / feuille par feuille / paramètres). La logique métier d'export N'EST PAS touchée dans cette phase (Phase 2).

**Tech Stack :** IronPython 2/3, WPF (XamlReader), pyRevit, socle partagé `418.extension/lib/`.

## Global Constraints

- Minimum Revit : **2026**. Python **2/3 compatible** : `from __future__ import unicode_literals` + `# -*- coding: utf-8 -*-` en tête de chaque fichier.
- Tous les imports Revit / WPF sont sous `try/except` avec fallback `None` (exécution hors Revit possible).
- Textes UI, commentaires et messages de commit en **français**.
- Réutiliser le socle `418.extension/lib/` (déjà sur `sys.path` via pyRevit) : `core.*`, `ui.base.*`, `ui.helpers.*`.
- **Ne jamais commiter automatiquement** : demander confirmation avant chaque `git commit` (préférence utilisateur).
- Tests standalone : `unittest`, exécutables hors Revit (pattern `Infos.pushbutton/tests/`).
- Éléments WPF non spécifiques à l'export → promus dans `lib/ui/`, jamais dupliqués dans le bouton.

---

## File Structure

```
418.tab/Export.panel/BatchExport.pushbutton/
├── script.py                          MODIFIER — nouveau point d'entrée MVVM
├── GUI/Views/MainWindow.xaml          CRÉER — coquille commune (rail + surface + footer)
├── lib/
│   ├── viewmodels/
│   │   ├── __init__.py                 CRÉER
│   │   └── MainViewModel.py            CRÉER — état navigation + Titre
│   ├── views/
│   │   ├── __init__.py                 CRÉER
│   │   └── MainWindowView.py           CRÉER — charge le XAML via BaseWindow
│   └── (ui/helpers/*.py dupliqués)     SUPPRIMER en fin de phase
└── tests/
    └── test_main_viewmodel.py          CRÉER — smoke test du ViewModel
```

Le code existant (`lib/services/`, `lib/data/`, `lib/ui/windows/…`) reste en place jusqu'aux phases suivantes ; seul le point d'entrée bascule sur le nouveau squelette.

---

### Task 1 : MainViewModel (état de navigation)

**Files:**
- Create: `418.tab/Export.panel/BatchExport.pushbutton/lib/viewmodels/__init__.py`
- Create: `418.tab/Export.panel/BatchExport.pushbutton/lib/viewmodels/MainViewModel.py`
- Test: `418.tab/Export.panel/BatchExport.pushbutton/tests/test_main_viewmodel.py`

**Interfaces:**
- Consumes: `ui.base.BaseViewModel` (socle) — `notify_property(name)`, propriétés `LogoPath` / `BrandLogoPath`.
- Produces:
  - `MainViewModel(doc=None)`
  - `MainViewModel.Titre` → `unicode` (`'Exportation'`)
  - `MainViewModel.ActiveMode` → `unicode` ∈ `{'auto', 'manual', 'settings'}`, défaut `'auto'` ; setter notifie `ActiveMode`, `IsAuto`, `IsManual`, `IsSettings`, `SurfaceTitre`.
  - `MainViewModel.IsAuto` / `IsManual` / `IsSettings` → `bool`
  - `MainViewModel.SurfaceTitre` → `unicode` (titre de la surface selon le mode)
  - `MainViewModel.set_mode(mode)` — méthode publique appelée par la vue.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/test_main_viewmodel.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.viewmodels.MainViewModel import MainViewModel


class TestMainViewModel(unittest.TestCase):
    def setUp(self):
        self.vm = MainViewModel(doc=None)

    def test_titre(self):
        self.assertEqual(self.vm.Titre, u'Exportation')

    def test_mode_par_defaut_auto(self):
        self.assertEqual(self.vm.ActiveMode, u'auto')
        self.assertTrue(self.vm.IsAuto)
        self.assertFalse(self.vm.IsManual)
        self.assertFalse(self.vm.IsSettings)

    def test_set_mode_manual(self):
        self.vm.set_mode(u'manual')
        self.assertEqual(self.vm.ActiveMode, u'manual')
        self.assertTrue(self.vm.IsManual)
        self.assertFalse(self.vm.IsAuto)

    def test_set_mode_invalide_ignore(self):
        self.vm.set_mode(u'auto')
        self.vm.set_mode(u'zzz')
        self.assertEqual(self.vm.ActiveMode, u'auto')

    def test_surface_titre_change_selon_mode(self):
        self.vm.set_mode(u'auto')
        self.assertIn(u'jeu', self.vm.SurfaceTitre.lower())
        self.vm.set_mode(u'settings')
        self.assertEqual(self.vm.SurfaceTitre, u'Paramètres')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `python 418.tab/Export.panel/BatchExport.pushbutton/tests/test_main_viewmodel.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'lib.viewmodels.MainViewModel'`

- [ ] **Step 3: Créer le package et le ViewModel**

`lib/viewmodels/__init__.py` : fichier vide.

`lib/viewmodels/MainViewModel.py` :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

_MODES = (u'auto', u'manual', u'settings')
_SURFACE_TITRES = {
    u'auto': u'Jeux qualifiés à l\'export',
    u'manual': u'Sélection manuelle',
    u'settings': u'Paramètres',
}


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._titre = u'Exportation'
        self._mode = u'auto'

    @property
    def Titre(self):
        return self._titre

    @property
    def ActiveMode(self):
        return self._mode

    @ActiveMode.setter
    def ActiveMode(self, value):
        if value not in _MODES:
            return
        self._mode = value
        for name in (u'ActiveMode', u'IsAuto', u'IsManual',
                     u'IsSettings', u'SurfaceTitre'):
            self.notify_property(name)

    def set_mode(self, mode):
        self.ActiveMode = mode

    @property
    def IsAuto(self):
        return self._mode == u'auto'

    @property
    def IsManual(self):
        return self._mode == u'manual'

    @property
    def IsSettings(self):
        return self._mode == u'settings'

    @property
    def SurfaceTitre(self):
        return _SURFACE_TITRES.get(self._mode, u'')
```

- [ ] **Step 4: Lancer le test, vérifier le succès**

Run: `python 418.tab/Export.panel/BatchExport.pushbutton/tests/test_main_viewmodel.py`
Expected: PASS (5 tests OK)

- [ ] **Step 5: Commit (après confirmation utilisateur)**

```bash
git add 418.tab/Export.panel/BatchExport.pushbutton/lib/viewmodels/ \
        418.tab/Export.panel/BatchExport.pushbutton/tests/test_main_viewmodel.py
git commit -m "feat(export): MainViewModel MVVM avec etat de navigation"
```

---

### Task 2 : MainWindow.xaml sur la coquille commune

**Files:**
- Create: `418.tab/Export.panel/BatchExport.pushbutton/GUI/Views/MainWindow.xaml`

**Interfaces:**
- Consumes: bindings sur `MainViewModel` (`Titre`, `BrandLogoPath`, `SurfaceTitre`) ; styles du socle (`CaptionButtonStyle`, `CaptionCloseButtonStyle`, `NavRailButtonStyle`, `BrandLogoBorderStyle`, `ShellSurfaceStyle`, `PrimaryActionButtonStyle`, `SecondaryActionButtonStyle`) fusionnés par `UIResourceLoader`.
- Produces: `x:Name` requis par `BaseWindow` (`TitleBar`, `MinimizeButton`, `MaximizeRestoreButton`, `CloseButton`) + noms nav (`NavAuto`, `NavManual`, `NavSettings`) et actions (`PrimaryActionButton`, `SecondaryActionButton`) pour câblage Python en Phase 2.

- [ ] **Step 1: Créer le XAML**

Reprendre la structure d'`Audit.pushbutton/GUI/Views/MainWindow.xaml` (WindowChrome, Border racine coins 12, TitleBar, rail DockPanel avec pastille `BrandLogoBorderStyle` liée à `{Binding BrandLogoPath}`, surface `ShellSurfaceStyle`, footer d'actions). Ajouter dans le rail 2 `RadioButton` de nav (`NavAuto` ▦ / `NavManual` ☑) + `NavSettings` ⚙ en `DockPanel.Dock="Bottom"`. Titre lié à `"418 · Export — Feuilles &amp; jeux"`. Contenu de surface : placeholder `TextBlock` (`Text="{Binding SurfaceTitre}"`). Tous les brushes/styles en `DynamicResource`.

- [ ] **Step 2: Vérification manuelle dans Revit**

Impossible de tester le XAML hors Revit. Vérification différée à la Task 3 (une fois le point d'entrée branché) : `pyRevit → Reload`, cliquer le bouton, la fenêtre s'ouvre sur la coquille commune, la pastille affiche le logo, les 3 items de rail sont présents.

- [ ] **Step 3: Commit (après confirmation utilisateur)**

```bash
git add 418.tab/Export.panel/BatchExport.pushbutton/GUI/Views/MainWindow.xaml
git commit -m "feat(export): fenetre principale sur la coquille commune"
```

---

### Task 3 : MainWindowView + bascule du point d'entrée

**Files:**
- Create: `418.tab/Export.panel/BatchExport.pushbutton/lib/views/__init__.py`
- Create: `418.tab/Export.panel/BatchExport.pushbutton/lib/views/MainWindowView.py`
- Modify: `418.tab/Export.panel/BatchExport.pushbutton/script.py`

**Interfaces:**
- Consumes: `ui.base.BaseWindow`, `core.AppPaths` (socle) ; `MainViewModel` (Task 1) ; `MainWindow.xaml` (Task 2).
- Produces:
  - `MainWindowView(view_model)` héritant de `BaseWindow`, résout le chemin du XAML via `AppPaths` local du bouton.
  - `MainWindowView.wire_navigation()` — câble les `RadioButton` de nav sur `view_model.set_mode(...)`.

- [ ] **Step 1: Créer la vue**

`lib/views/__init__.py` : vide.

`lib/views/MainWindowView.py` :

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
    def __init__(self, view_model):
        super(MainWindowView, self).__init__(_xaml_path(), view_model)
        self._vm = view_model

    def _load(self):
        super(MainWindowView, self)._load()
        self.wire_navigation()

    def wire_navigation(self):
        if self._window is None:
            return
        mapping = (('NavAuto', u'auto'),
                   ('NavManual', u'manual'),
                   ('NavSettings', u'settings'))
        for name, mode in mapping:
            btn = self._window.FindName(name)
            if btn is None:
                continue
            self._bind_nav(btn, mode)

    def _bind_nav(self, btn, mode):
        vm = self._vm

        def _on_checked(sender, args):
            try:
                vm.set_mode(mode)
            except Exception:
                pass
        try:
            btn.Checked += _on_checked
        except Exception:
            pass
```

- [ ] **Step 2: Basculer `script.py`**

Remplacer le contenu de `script.py` par le point d'entrée MVVM :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Export"
__doc__ = "Export en lot PDF/DWG des feuilles et jeux de feuilles."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

try:
    doc = __revit__.ActiveUIDocument.Document  # type: ignore
except Exception:
    doc = None

from lib.viewmodels.MainViewModel import MainViewModel
from lib.views.MainWindowView import MainWindowView

if __name__ == '__main__':
    vm = MainViewModel(doc=doc)
    view = MainWindowView(vm)
    view.show()
```

- [ ] **Step 3: Vérification d'import hors Revit**

Run: `python -c "import sys, os; sys.path.insert(0, 'lib'); sys.path.insert(0, os.path.join(os.getcwd(),'418.tab','Export.panel','BatchExport.pushbutton')); from lib.views.MainWindowView import MainWindowView; print('import OK')"`
(exécuter depuis la racine de l'extension ; adapter le `sys.path` du lib partagé si besoin)
Expected: `import OK` sans exception (les imports WPF tombent en fallback).

- [ ] **Step 4: Vérification manuelle dans Revit**

`pyRevit → Reload` → cliquer le bouton Export. Attendu : la fenêtre s'ouvre sur la coquille commune, logo en pastille, clic sur les items du rail sans erreur (le titre de surface suit le mode).

- [ ] **Step 5: Commit (après confirmation utilisateur)**

```bash
git add 418.tab/Export.panel/BatchExport.pushbutton/lib/views/ \
        418.tab/Export.panel/BatchExport.pushbutton/script.py
git commit -m "feat(export): branche le point d'entree sur la vue MVVM"
```

---

### Task 4 : Suppression des helpers dupliqués

**Files:**
- Delete: `418.tab/Export.panel/BatchExport.pushbutton/lib/ui/helpers/DarkMode.py`
- Delete: `418.tab/Export.panel/BatchExport.pushbutton/lib/ui/helpers/UIResourceLoader.py`
- Delete: `418.tab/Export.panel/BatchExport.pushbutton/lib/ui/helpers/GridRowToggle.py`
- Delete: `418.tab/Export.panel/BatchExport.pushbutton/lib/ui/helpers/RelayCommand.py`
- Delete: `418.tab/Export.panel/BatchExport.pushbutton/lib/core/AppPaths.py` **(voir note)**
- Delete: `418.tab/Export.panel/BatchExport.pushbutton/lib/core/UserConfig.py` **(voir note)**

**Interfaces:**
- Consommateurs restants (anciens `lib/ui/windows/…`) doivent importer depuis le socle : `from ui.helpers.DarkMode import ...`, `from core.UserConfig import UserConfig`, etc.

> **Note importante** : ne supprimer un fichier qu'après avoir vérifié qu'aucun module encore
> actif ne l'importe en chemin local. `AppPaths`/`UserConfig` locaux du bouton peuvent différer
> du socle — comparer avant suppression. Si l'ancien code (`lib/ui/windows/…`) les référence
> encore et n'est pas migré, **conserver** ces fichiers jusqu'à la phase qui migre ce code, ou
> repointer les imports. Ne pas casser l'ancien chemin tant qu'il sert.

- [ ] **Step 1: Recenser les usages**

Run: `grep -rn "helpers.DarkMode\|helpers.UIResourceLoader\|helpers.GridRowToggle\|helpers.RelayCommand\|core.AppPaths\|core.UserConfig" 418.tab/Export.panel/BatchExport.pushbutton/lib`
Attendu : liste des imports locaux à repointer/valider.

- [ ] **Step 2: Comparer local vs socle**

Pour chaque helper candidat, comparer le fichier local et sa version socle (`diff`). Documenter toute divergence fonctionnelle (surtout `RelayCommand` local = stub, `HoverOverlay` local = spécialisé).

Run: `diff 418.tab/Export.panel/BatchExport.pushbutton/lib/ui/helpers/DarkMode.py lib/ui/helpers/DarkMode.py`
Attendu : identiques → suppression sûre.

- [ ] **Step 3: Supprimer les doublons identiques + repointer les imports**

Supprimer les fichiers identiques au socle. Repointer les imports restants de l'ancien code vers le socle. **Ne pas** supprimer `HoverOverlay` local (spécialisé) — sa généralisation est une tâche dédiée d'une phase ultérieure.

- [ ] **Step 4: Vérification d'import**

Run: `python 418.tab/Export.panel/BatchExport.pushbutton/tests/test_main_viewmodel.py`
Expected: PASS (le nouveau chemin n'utilise que le socle).

Run: `pyRevit → Reload` → ouvrir le bouton : aucune régression.

- [ ] **Step 5: Commit (après confirmation utilisateur)**

```bash
git add -A 418.tab/Export.panel/BatchExport.pushbutton/lib
git commit -m "refactor(export): supprime les helpers dupliques au profit du socle"
```

---

## Phases suivantes (hors périmètre Phase 1, plans dédiés à venir)

- **Phase 2** — Services métier migrés (SheetCollectionService, Naming, Destination, Orchestrator dédupliqué, réparation `PdfExporterService.build_options()`).
- **Phase 3** — Mode « par jeu » à iso-fonctionnel (liste lecture seule, badges, exécution export).
- **Phase 4** — Mode « feuille par feuille » (liste à cases, sélection éphémère) + page Paramètres complète.
- **Phase 5** — Profils/CSV, généralisation `HoverOverlay` au socle, nettoyage final de l'ancien `lib/ui/windows/…`.

## Self-Review

- **Couverture spec** : Phase 1 couvre « migration MVVM sur socle » (squelette) + « coquille commune » + « suppression doublons » + « logo de référence » (pastille `BrandLogoPath`). Les modes/paramètres/moteur relèvent des phases 2-4. ✅
- **Placeholders** : aucun TODO/TBD — code et tests complets fournis. ✅
- **Cohérence des types** : `set_mode`/`ActiveMode`/`IsAuto|IsManual|IsSettings`/`SurfaceTitre` cohérents entre Task 1 (déf.), Task 3 (câblage nav) et Task 2 (bindings). ✅
