# Workspace 418.extension — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer la lib partagée `418.extension/lib/`, 7 branches feature avec scaffolds MVVM complets, supprimer `Beta.panel` et `418.tab/lib/`, mettre à jour le README.

**Architecture:** `418.extension/lib/` est ajouté automatiquement au `sys.path` par pyRevit — tous les pushbuttons importent `from core.UserConfig import UserConfig` sans manipulation de path. Chaque feature WPF suit MVVM strict : `MainViewModel(BaseViewModel)` expose propriétés notifiantes et `RelayCommand`s ; `MainWindow.xaml` se bind dessus ; `script.py` assemble les deux. Les ressources XAML de thème (Colors, Styles, *Dark) vivent dans `418.extension/lib/ui/GUI/resources/`.

**Tech Stack:** Python 2/3 (IronPython), WPF (`System.Windows`, `System.ComponentModel`), pyRevit `userconfig`, XAML bindings.

## Global Constraints

- Chaque fichier `.py` commence par `# -*- coding: utf-8 -*-` puis `from __future__ import unicode_literals`
- Tous les imports Revit/WPF dans des blocs `try/except` avec fallback `None` ou classe vide
- Revit minimum : 2026
- Commentaires et messages en français
- Pas de test runner — vérification syntaxique : `python -c "import ast; ast.parse(open('fichier.py').read())"`
- Commits fréquents, préfixes : `feat:`, `chore:`, `refactor:`, `docs:`
- Tout le travail sur la branche `Developpement` jusqu'à la Task 6

---

## Fichiers créés / modifiés

```
418.extension/lib/                           ← NOUVEAU dossier
  __init__.py
  core/
    __init__.py
    AppPaths.py
    UserConfig.py
    sanitize.py
  ui/
    __init__.py
    base/
      __init__.py
      BaseViewModel.py
      BaseWindow.py
    helpers/
      __init__.py
      RelayCommand.py
      DarkMode.py
      UIResourceLoader.py
      HoverOverlay.py
      GridRowToggle.py
    GUI/
      resources/
        Colors.xaml           ← copié depuis BatchExport/GUI/resources/
        ColorsDark.xaml       ← copié
        Styles.xaml           ← copié
        StylesDark.xaml       ← copié

418.tab/Beta.panel/           ← SUPPRIMÉ (git rm)
418.tab/lib/                  ← SUPPRIMÉ (git rm)
README.md                     ← MIS À JOUR

418.tab/Audit.panel/Audit.pushbutton/           ← NOUVEAU (feat/Audit)
418.tab/Manage.panel/ManageFiltre.pushbutton/   ← NOUVEAU (feat/ManageFiltre)
418.tab/Manage.panel/ManageMatérial.pushbutton/ ← NOUVEAU (feat/ManageMatérial)
418.tab/Manage.panel/ManageSheet.pushbutton/    ← NOUVEAU (feat/ManageSheet)
418.tab/Manage.panel/ManageView.pushbutton/     ← NOUVEAU (feat/ManageView)
418.tab/Tools.panel/ImageCrop.pushbutton/       ← NOUVEAU (feat/ImageCrop)
```

---

## Task 1 : Lib partagée — `core/`

**Fichiers :**
- Créer : `418.extension/lib/__init__.py`
- Créer : `418.extension/lib/core/__init__.py`
- Créer : `418.extension/lib/core/AppPaths.py`
- Créer : `418.extension/lib/core/UserConfig.py`
- Créer : `418.extension/lib/core/sanitize.py`

**Interfaces :**
- Produit : `AppPaths().resource_path(filename) -> str`, `AppPaths().resources_dir() -> str`
- Produit : `UserConfig(namespace).get(key, default) -> str`, `.set(key, value) -> bool`, `.get_list(key, default) -> list`
- Produit : `sanitize(name, max_len=180) -> str`

- [ ] **Étape 1 : Créer les `__init__.py` vides**

```python
# 418.extension/lib/__init__.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
```

```python
# 418.extension/lib/core/__init__.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
```

- [ ] **Étape 2 : Créer `AppPaths.py`**

```python
# 418.extension/lib/core/AppPaths.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

# _lib_dir = 418.extension/lib/
_lib_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AppPaths(object):
    def resources_dir(self):
        return os.path.join(_lib_dir, 'ui', 'GUI', 'resources')

    def resource_path(self, filename):
        return os.path.join(self.resources_dir(), filename)
```

- [ ] **Étape 3 : Créer `UserConfig.py`**

La différence clé avec la version BatchExport : la section pyRevit est dérivée dynamiquement depuis `self._ns`, pas hardcodée sur `batch_export`.

```python
# 418.extension/lib/core/UserConfig.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from pyrevit.userconfig import user_config as _UC
except Exception:
    _UC = None


class UserConfig(object):
    def __init__(self, namespace='418_extension'):
        self._ns = namespace or '418_extension'

    def _section(self):
        if _UC is None:
            return None
        try:
            _UC.add_section(self._ns)
        except Exception:
            pass
        try:
            return getattr(_UC, self._ns)
        except Exception as e:
            print('UserConfig [001]: section {} introuvable: {}'.format(self._ns, e))
            return None

    def get(self, key, default=None):
        sec = self._section()
        if sec is None:
            return default
        try:
            return sec.get_option(key, default)
        except Exception:
            pass
        try:
            return getattr(sec, key)
        except Exception:
            return default

    def set(self, key, value):
        sec = self._section()
        if sec is None:
            return False
        sval = u'{}'.format(value)
        saved = False
        if hasattr(sec, 'set_option'):
            try:
                sec.set_option(key, sval)
                saved = True
            except Exception:
                pass
        if not saved:
            try:
                setattr(sec, key, sval)
                saved = True
            except Exception:
                pass
        if saved and _UC is not None:
            try:
                _UC.save_changes()
            except Exception:
                pass
        return saved

    def get_list(self, key, default=None):
        if default is None:
            default = []
        val = self.get(key, None)
        if val is None:
            return list(default)
        try:
            if isinstance(val, list):
                return list(val)
            s = val.strip()
            if not s:
                return list(default)
            return [p.strip() for p in s.split(',') if p.strip()]
        except Exception:
            return list(default)
```

- [ ] **Étape 4 : Créer `sanitize.py`**

```python
# 418.extension/lib/core/sanitize.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

_INVALID = re.compile(r'[\\/:*?"<>|]')
_MAX_LEN = 180


def sanitize(name, max_len=_MAX_LEN):
    if not name:
        return u'export'
    name = _INVALID.sub(u'_', name)
    return name[:max_len]
```

- [ ] **Étape 5 : Vérifier la syntaxe**

```bash
python -c "import ast; ast.parse(open('lib/core/AppPaths.py').read()); print('OK AppPaths')"
python -c "import ast; ast.parse(open('lib/core/UserConfig.py').read()); print('OK UserConfig')"
python -c "import ast; ast.parse(open('lib/core/sanitize.py').read()); print('OK sanitize')"
```

Résultat attendu : `OK AppPaths`, `OK UserConfig`, `OK sanitize`

- [ ] **Étape 6 : Commit**

```bash
git add 418.extension/lib/__init__.py 418.extension/lib/core/
git commit -m "feat(lib): core partagé — AppPaths, UserConfig, sanitize"
```

---

## Task 2 : Lib partagée — `ui/base/` (BaseViewModel, BaseWindow)

**Fichiers :**
- Créer : `418.extension/lib/ui/__init__.py`
- Créer : `418.extension/lib/ui/base/__init__.py`
- Créer : `418.extension/lib/ui/base/BaseViewModel.py`
- Créer : `418.extension/lib/ui/base/BaseWindow.py`

**Interfaces :**
- Consomme : `core.AppPaths`, `ui.helpers.UIResourceLoader`, `ui.helpers.DarkMode`
- Produit : `class BaseViewModel` avec `notify_property(name)` — base pour tous les ViewModels
- Produit : `class BaseWindow(xaml_path, view_model=None)` avec méthode `.show()`

- [ ] **Étape 1 : Créer les `__init__.py` vides**

```python
# 418.extension/lib/ui/__init__.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
```

```python
# 418.extension/lib/ui/base/__init__.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
```

- [ ] **Étape 2 : Créer `BaseViewModel.py`**

IronPython implémente les événements .NET via `add_EventName`/`remove_EventName`. WPF lit `PropertyChanged` via cette interface pour les bindings.

```python
# 418.extension/lib/ui/base/BaseViewModel.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from System.ComponentModel import INotifyPropertyChanged, PropertyChangedEventArgs
    _has_wpf = True
except Exception:
    INotifyPropertyChanged = object
    _has_wpf = False


if _has_wpf:
    class BaseViewModel(INotifyPropertyChanged):
        def __init__(self):
            self._pc_handlers = []

        def add_PropertyChanged(self, handler):
            self._pc_handlers.append(handler)

        def remove_PropertyChanged(self, handler):
            try:
                self._pc_handlers.remove(handler)
            except ValueError:
                pass

        def notify_property(self, name):
            if not self._pc_handlers:
                return
            args = PropertyChangedEventArgs(name)
            for h in list(self._pc_handlers):
                try:
                    h(self, args)
                except Exception:
                    pass
else:
    class BaseViewModel(object):
        def __init__(self):
            pass

        def notify_property(self, name):
            pass
```

- [ ] **Étape 3 : Créer `BaseWindow.py`**

`BaseWindow` charge un fichier XAML via `XamlReader`, merge le thème partagé, puis associe le ViewModel comme `DataContext`.

```python
# 418.extension/lib/ui/base/BaseWindow.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from System.Windows.Markup import XamlReader
    from System.IO import FileStream, FileMode, FileAccess
    _has_wpf = True
except Exception:
    XamlReader = None
    FileStream = None
    _has_wpf = False

try:
    from ui.helpers.UIResourceLoader import UIResourceLoader
except Exception:
    UIResourceLoader = None

try:
    from ui.helpers.DarkMode import is_dark as _is_dark
except Exception:
    def _is_dark():
        return False


class BaseWindow(object):
    def __init__(self, xaml_path, view_model=None):
        self._xaml_path = xaml_path
        self._vm = view_model
        self._window = None

    def _load(self):
        if not _has_wpf:
            print('BaseWindow: WPF non disponible')
            return
        stream = None
        try:
            stream = FileStream(self._xaml_path, FileMode.Open, FileAccess.Read)
            self._window = XamlReader.Load(stream)
        except Exception as e:
            print('BaseWindow [001]: Impossible de charger le XAML: {}'.format(e))
            return
        finally:
            if stream is not None:
                try:
                    stream.Close()
                except Exception:
                    pass
        if UIResourceLoader is not None:
            loader = UIResourceLoader(self._window, dark=_is_dark())
            loader.merge_theme()
        if self._vm is not None:
            self._window.DataContext = self._vm

    def show(self):
        if self._window is None:
            self._load()
        if self._window is not None:
            self._window.ShowDialog()
```

- [ ] **Étape 4 : Vérifier la syntaxe**

```bash
python -c "import ast; ast.parse(open('lib/ui/base/BaseViewModel.py').read()); print('OK BaseViewModel')"
python -c "import ast; ast.parse(open('lib/ui/base/BaseWindow.py').read()); print('OK BaseWindow')"
```

- [ ] **Étape 5 : Commit**

```bash
git add 418.extension/lib/ui/
git commit -m "feat(lib): ui/base — BaseViewModel (INotifyPropertyChanged) et BaseWindow"
```

---

## Task 3 : Lib partagée — `ui/helpers/`

**Fichiers :**
- Créer : `418.extension/lib/ui/helpers/__init__.py`
- Créer : `418.extension/lib/ui/helpers/RelayCommand.py`
- Créer : `418.extension/lib/ui/helpers/DarkMode.py`
- Créer : `418.extension/lib/ui/helpers/UIResourceLoader.py`
- Créer : `418.extension/lib/ui/helpers/HoverOverlay.py`
- Créer : `418.extension/lib/ui/helpers/GridRowToggle.py`

**Interfaces :**
- Produit : `RelayCommand(execute, can_execute=None)` — implémente `ICommand`
- Produit : `is_dark() -> bool`, `apply_dark_mode(win, paths)`
- Produit : `UIResourceLoader(window, dark=False).merge_theme() -> bool`
- Produit : `set_hover_text(win, name, text)`, `clear_hover(win, name)`
- Produit : `unselect_row_on_preview_left_click(e)`

- [ ] **Étape 1 : Créer `__init__.py`**

```python
# 418.extension/lib/ui/helpers/__init__.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
```

- [ ] **Étape 2 : Créer `RelayCommand.py`**

```python
# 418.extension/lib/ui/helpers/RelayCommand.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from System.Windows.Input import ICommand
except Exception:
    ICommand = object


class RelayCommand(ICommand):
    def __init__(self, execute, can_execute=None):
        self._execute = execute
        self._can_execute = can_execute

    def CanExecute(self, parameter):
        return self._can_execute(parameter) if self._can_execute else True

    def Execute(self, parameter):
        self._execute(parameter)

    def add_CanExecuteChanged(self, handler):
        pass

    def remove_CanExecuteChanged(self, handler):
        pass
```

- [ ] **Étape 3 : Créer `DarkMode.py`**

```python
# 418.extension/lib/ui/helpers/DarkMode.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from pyrevit.userconfig import user_config as _UC
    def is_dark():
        try:
            theme = _UC.core.get_option('colorize_docs', 'default')
            return str(theme).lower() in ('dark', 'true', '1')
        except Exception:
            return False
except Exception:
    def is_dark():
        return False


def apply_dark_mode(win, paths):
    try:
        from System.Windows import ResourceDictionary
        from System import Uri, UriKind
    except Exception as e:
        print('DarkMode: WPF non disponible: {}'.format(e))
        return
    for name in ('ColorsDark.xaml', 'StylesDark.xaml'):
        path = paths.resource_path(name)
        try:
            rd = ResourceDictionary()
            uri_str = 'file:///' + path.replace('\\', '/').replace(':', ':/')
            rd.Source = Uri(uri_str, UriKind.Absolute)
            win.Resources.MergedDictionaries.Add(rd)
        except Exception as e:
            print('DarkMode: Impossible de charger {}: {}'.format(name, e))
```

- [ ] **Étape 4 : Créer `UIResourceLoader.py`**

Cette version charge uniquement les ressources de thème partagées (Colors + Styles). Les contrôles spécifiques à chaque feature restent dans leur propre pushbutton.

```python
# 418.extension/lib/ui/helpers/UIResourceLoader.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from System import Uri, UriKind
    from System.Windows import ResourceDictionary
    _has_wpf = True
except Exception:
    _has_wpf = False

try:
    from core.AppPaths import AppPaths as _AppPaths
except Exception:
    _AppPaths = None


class UIResourceLoader(object):
    def __init__(self, window, dark=False):
        self._win = window
        self._dark = dark
        self._paths = _AppPaths() if _AppPaths is not None else None

    def merge_theme(self):
        if not _has_wpf:
            print('UIResourceLoader: WPF non disponible')
            return False
        if self._paths is None:
            print('UIResourceLoader: AppPaths non disponible')
            return False
        suffix = 'Dark' if self._dark else ''
        for name in ('Colors{}.xaml'.format(suffix), 'Styles{}.xaml'.format(suffix)):
            path = self._paths.resource_path(name)
            if not os.path.exists(path):
                print('UIResourceLoader: ressource introuvable: {}'.format(path))
                continue
            try:
                rd = ResourceDictionary()
                uri_str = 'file:///' + path.replace('\\', '/').replace(':', ':/')
                rd.Source = Uri(uri_str, UriKind.Absolute)
                self._win.Resources.MergedDictionaries.Add(rd)
            except Exception as e:
                print('UIResourceLoader: Erreur chargement {}: {}'.format(name, e))
        return True

    def merge_resource(self, xaml_path):
        if not _has_wpf or not os.path.exists(xaml_path):
            return False
        try:
            rd = ResourceDictionary()
            uri_str = 'file:///' + xaml_path.replace('\\', '/').replace(':', ':/')
            rd.Source = Uri(uri_str, UriKind.Absolute)
            self._win.Resources.MergedDictionaries.Add(rd)
            return True
        except Exception as e:
            print('UIResourceLoader: Erreur merge_resource {}: {}'.format(xaml_path, e))
            return False
```

- [ ] **Étape 5 : Créer `HoverOverlay.py`**

Version générique : ne suppose aucun nom d'élément XAML fixe — le nom est passé en paramètre.

```python
# 418.extension/lib/ui/helpers/HoverOverlay.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def _find(win, name):
    try:
        obj = getattr(win, name, None)
        if obj is not None:
            return obj
    except Exception:
        pass
    if hasattr(win, 'FindName'):
        try:
            return win.FindName(name)
        except Exception:
            pass
    return None


def set_hover_text(win, element_name, text):
    try:
        from System.Windows import Visibility
    except Exception:
        return False
    tb = _find(win, element_name)
    if tb is None:
        return False
    try:
        if text:
            tb.Text = text
            tb.Visibility = Visibility.Visible
        else:
            tb.Text = u''
            tb.Visibility = Visibility.Collapsed
        return True
    except Exception:
        return False


def clear_hover(win, element_name):
    set_hover_text(win, element_name, u'')
```

- [ ] **Étape 6 : Créer `GridRowToggle.py`**

```python
# 418.extension/lib/ui/helpers/GridRowToggle.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def unselect_row_on_preview_left_click(e):
    try:
        from System.Windows import DependencyObject
        from System.Windows.Media import VisualTreeHelper
        from System.Windows.Controls import DataGridRow
    except Exception:
        return
    try:
        src = getattr(e, 'OriginalSource', None)
        obj = src if isinstance(src, DependencyObject) else None
        row = None
        while obj is not None:
            if isinstance(obj, DataGridRow):
                row = obj
                break
            try:
                obj = VisualTreeHelper.GetParent(obj)
            except Exception:
                obj = None
        if row is not None and getattr(row, 'IsSelected', False):
            row.IsSelected = False
            e.Handled = True
    except Exception:
        pass
```

- [ ] **Étape 7 : Vérifier la syntaxe**

```bash
python -c "import ast
for f in ['RelayCommand','DarkMode','UIResourceLoader','HoverOverlay','GridRowToggle']:
    ast.parse(open('lib/ui/helpers/{}.py'.format(f)).read())
    print('OK ' + f)"
```

- [ ] **Étape 8 : Commit**

```bash
git add 418.extension/lib/ui/helpers/
git commit -m "feat(lib): ui/helpers — RelayCommand, DarkMode, UIResourceLoader, HoverOverlay, GridRowToggle"
```

---

## Task 4 : Migration des ressources XAML de thème

**Fichiers :**
- Créer : `418.extension/lib/ui/GUI/resources/Colors.xaml`
- Créer : `418.extension/lib/ui/GUI/resources/ColorsDark.xaml`
- Créer : `418.extension/lib/ui/GUI/resources/Styles.xaml`
- Créer : `418.extension/lib/ui/GUI/resources/StylesDark.xaml`

**Interfaces :**
- Consomme : fichiers sources dans `418.tab/Export.panel/BatchExport.pushbutton/GUI/resources/`
- Produit : même contenu dans `418.extension/lib/ui/GUI/resources/` — AppPaths pointe ici

- [ ] **Étape 1 : Copier les 4 fichiers XAML**

```bash
mkdir -p "418.extension/lib/ui/GUI/resources"
cp "418.tab/Export.panel/BatchExport.pushbutton/GUI/resources/Colors.xaml"      "418.extension/lib/ui/GUI/resources/Colors.xaml"
cp "418.tab/Export.panel/BatchExport.pushbutton/GUI/resources/ColorsDark.xaml"  "418.extension/lib/ui/GUI/resources/ColorsDark.xaml"
cp "418.tab/Export.panel/BatchExport.pushbutton/GUI/resources/Styles.xaml"      "418.extension/lib/ui/GUI/resources/Styles.xaml"
cp "418.tab/Export.panel/BatchExport.pushbutton/GUI/resources/StylesDark.xaml"  "418.extension/lib/ui/GUI/resources/StylesDark.xaml"
```

- [ ] **Étape 2 : Vérifier que les 4 fichiers sont bien copiés**

```bash
ls "418.extension/lib/ui/GUI/resources/"
```

Résultat attendu : `Colors.xaml  ColorsDark.xaml  Styles.xaml  StylesDark.xaml`

- [ ] **Étape 3 : Commit**

```bash
git add "418.extension/lib/ui/GUI/resources/"
git commit -m "feat(lib): migration ressources XAML thème vers lib partagée"
```

---

## Task 5 : Nettoyage + README

**Fichiers :**
- Supprimer : `418.tab/Beta.panel/` (git rm)
- Supprimer : `418.tab/lib/` (git rm)
- Modifier : `README.md`

- [ ] **Étape 1 : Supprimer `Beta.panel` et `418.tab/lib/`**

```bash
git rm -r "418.tab/Beta.panel/"
git rm -r "418.tab/lib/"
```

- [ ] **Étape 2 : Mettre à jour `README.md`**

Remplacer entièrement le contenu du README par :

```markdown
# 418.extension

Extension pyRevit pour l'automatisation et la gestion dans Revit.

## Fonctionnalités

| Feature | Panel | Description | Version | Statut |
|---------|-------|-------------|---------|--------|
| BatchExport | Export | Export en lot PDF/DWG depuis les jeux de feuilles | 0.3 | 🔨 En cours |
| Audit | Audit | Analyse et rapport sur la santé du modèle Revit | — | ⏳ Scaffold |
| ManageFiltre | Manage | Gestion avancée des filtres de vue | — | ⏳ Scaffold |
| ManageMatérial | Manage | Gestion et édition des matériaux | — | ⏳ Scaffold |
| ManageSheet | Manage | Gestion des feuilles (nommage, tri, duplication) | — | ⏳ Scaffold |
| ManageView | Manage | Gestion des vues (templates, organisation) | — | ⏳ Scaffold |
| ImageCrop | Tools | Recadrage automatique d'images/vues | — | 🔲 Placeholder |

## Installation

1. Installer [pyRevit](https://github.com/eirannejad/pyRevit)
2. Cloner ce dépôt dans le dossier extensions pyRevit
3. Recharger pyRevit (`pyRevit tab → Reload` ou `Ctrl+F5`)

## Architecture

### Bibliothèque partagée (`418.extension/lib/`)

pyRevit ajoute automatiquement `418.extension/lib/` au `sys.path`. Import direct depuis n'importe quel pushbutton :

```python
from core.UserConfig import UserConfig
from ui.base.BaseViewModel import BaseViewModel
from ui.helpers.RelayCommand import RelayCommand
```

Structure :
- `core/` — `AppPaths`, `UserConfig`, `sanitize`
- `ui/base/` — `BaseViewModel` (INotifyPropertyChanged), `BaseWindow` (chargement XAML)
- `ui/helpers/` — `RelayCommand`, `DarkMode`, `UIResourceLoader`, `HoverOverlay`, `GridRowToggle`
- `ui/GUI/resources/` — thème XAML unifié (Colors, Styles, variantes Dark)

### Pattern MVVM

Chaque pushbutton WPF suit :

```
<Feature>.pushbutton/
├── script.py                 ← instancie ViewModel + ouvre View
├── GUI/Views/MainWindow.xaml ← bindings sur ViewModel, zéro logique
└── lib/
    ├── models/               ← DTOs, wrappers Revit
    ├── viewmodels/           ← MainViewModel(BaseViewModel)
    ├── services/             ← logique métier + Revit API
    └── views/                ← MainWindowView (chargement fenêtre)
```

## Développement

Cycle : éditer → `pyRevit tab → Reload` → tester.

Pour tester un seul bouton sans recharger : clic droit → **Run script**.

Minimum Revit : 2026. Python 2/3 compatible.
```

- [ ] **Étape 3 : Commit**

```bash
git add README.md
git commit -m "chore: supprime Beta.panel et 418.tab/lib/, met à jour README"
```

---

## Task 6 : Branche `feat/Export`

`feat/Export` = branche de travail pour la migration de BatchExport vers la lib partagée et MVVM. Cette migration est un refactor complexe planifié séparément. Cette task crée la branche avec un marqueur TODO.

**Fichiers :**
- Modifier : `418.tab/Export.panel/BatchExport.pushbutton/script.py` (ajout commentaire de migration)

- [ ] **Étape 1 : Créer la branche depuis Developpement**

```bash
git checkout Developpement
git checkout -b feat/Export
```

- [ ] **Étape 2 : Ajouter un marqueur de migration dans `script.py`**

En haut de `418.tab/Export.panel/BatchExport.pushbutton/script.py`, après les docstrings existants, ajouter :

```python
# TODO(feat/Export): migrer les imports internes vers 418.extension/lib/
# Modules cibles : core.UserConfig, core.AppPaths, ui.helpers.RelayCommand,
#                  ui.helpers.DarkMode, ui.base.BaseWindow, ui.base.BaseViewModel
```

- [ ] **Étape 3 : Commit**

```bash
git add "418.tab/Export.panel/BatchExport.pushbutton/script.py"
git commit -m "feat(Export): branche créée — marqueur migration vers lib partagée"
```

---

## Task 7 : Branche `feat/Audit` — scaffold MVVM

**Fichiers créés :**
- `418.tab/Audit.panel/Audit.pushbutton/script.py`
- `418.tab/Audit.panel/Audit.pushbutton/GUI/Views/MainWindow.xaml`
- `418.tab/Audit.panel/Audit.pushbutton/lib/__init__.py`
- `418.tab/Audit.panel/Audit.pushbutton/lib/models/__init__.py`
- `418.tab/Audit.panel/Audit.pushbutton/lib/viewmodels/__init__.py`
- `418.tab/Audit.panel/Audit.pushbutton/lib/viewmodels/MainViewModel.py`
- `418.tab/Audit.panel/Audit.pushbutton/lib/services/__init__.py`
- `418.tab/Audit.panel/Audit.pushbutton/lib/views/__init__.py`
- `418.tab/Audit.panel/Audit.pushbutton/lib/views/MainWindowView.py`

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout Developpement
git checkout -b feat/Audit
```

- [ ] **Étape 2 : Créer les dossiers et `__init__.py`**

```bash
mkdir -p "418.tab/Audit.panel/Audit.pushbutton/GUI/Views"
mkdir -p "418.tab/Audit.panel/Audit.pushbutton/lib/models"
mkdir -p "418.tab/Audit.panel/Audit.pushbutton/lib/viewmodels"
mkdir -p "418.tab/Audit.panel/Audit.pushbutton/lib/services"
mkdir -p "418.tab/Audit.panel/Audit.pushbutton/lib/views"
```

Créer `lib/__init__.py`, `lib/models/__init__.py`, `lib/viewmodels/__init__.py`, `lib/services/__init__.py`, `lib/views/__init__.py` — tous identiques :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
```

- [ ] **Étape 3 : Créer `lib/viewmodels/MainViewModel.py`**

```python
# 418.tab/Audit.panel/Audit.pushbutton/lib/viewmodels/MainViewModel.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    RelayCommand = None


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._titre = u'Audit'
        self.fermer_cmd = RelayCommand(lambda p: None) if RelayCommand else None

    @property
    def Titre(self):
        return self._titre

    @Titre.setter
    def Titre(self, value):
        self._titre = value
        self.notify_property('Titre')
```

- [ ] **Étape 4 : Créer `lib/views/MainWindowView.py`**

```python
# 418.tab/Audit.panel/Audit.pushbutton/lib/views/MainWindowView.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = None

# Chemin : lib/views/ -> lib/ -> pushbutton/
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_XAML = os.path.join(_ROOT, 'GUI', 'Views', 'MainWindow.xaml')


class MainWindowView(object):
    def __init__(self, view_model):
        self._vm = view_model
        self._win = BaseWindow(_XAML, view_model) if BaseWindow is not None else None

    def show(self):
        if self._win is None:
            print('MainWindowView: BaseWindow non disponible')
            return
        self._win.show()
```

- [ ] **Étape 5 : Créer `GUI/Views/MainWindow.xaml`**

```xml
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="{Binding Titre}"
        Width="700" Height="500"
        WindowStartupLocation="CenterScreen"
        ResizeMode="CanResizeWithGrip">
    <Grid Margin="16">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <TextBlock Grid.Row="0"
                   Text="{Binding Titre}"
                   FontSize="20" FontWeight="Bold"
                   Margin="0,0,0,16"/>

        <Border Grid.Row="1"
                BorderBrush="#CCCCCC" BorderThickness="1"
                CornerRadius="4">
            <TextBlock Text="— Scaffold Audit — à implémenter —"
                       HorizontalAlignment="Center"
                       VerticalAlignment="Center"
                       FontSize="14" Foreground="Gray"/>
        </Border>
    </Grid>
</Window>
```

- [ ] **Étape 6 : Créer `script.py`**

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Audit"
__doc__ = "Analyse et rapport sur la santé du modèle Revit."
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

- [ ] **Étape 7 : Vérifier la syntaxe**

```bash
python -c "import ast
for f in ['script.py',
          'lib/viewmodels/MainViewModel.py',
          'lib/views/MainWindowView.py']:
    ast.parse(open('418.tab/Audit.panel/Audit.pushbutton/' + f).read())
    print('OK ' + f)"
```

- [ ] **Étape 8 : Commit**

```bash
git add "418.tab/Audit.panel/"
git commit -m "feat(Audit): scaffold MVVM complet"
```

---

## Task 8 : Branche `feat/ManageFiltre` — scaffold MVVM

Structure et code identiques à Task 7 — remplacer `Audit` par `ManageFiltre`, le panel est `Manage.panel`.

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout Developpement
git checkout -b feat/ManageFiltre
```

- [ ] **Étape 2 : Créer les dossiers**

```bash
mkdir -p "418.tab/Manage.panel/ManageFiltre.pushbutton/GUI/Views"
mkdir -p "418.tab/Manage.panel/ManageFiltre.pushbutton/lib/models"
mkdir -p "418.tab/Manage.panel/ManageFiltre.pushbutton/lib/viewmodels"
mkdir -p "418.tab/Manage.panel/ManageFiltre.pushbutton/lib/services"
mkdir -p "418.tab/Manage.panel/ManageFiltre.pushbutton/lib/views"
```

Créer les 5 fichiers `__init__.py` (contenu identique à Task 7, Étape 2).

- [ ] **Étape 3 : Créer `lib/viewmodels/MainViewModel.py`**

```python
# 418.tab/Manage.panel/ManageFiltre.pushbutton/lib/viewmodels/MainViewModel.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    RelayCommand = None


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._titre = u'Gestion des filtres'
        self.fermer_cmd = RelayCommand(lambda p: None) if RelayCommand else None

    @property
    def Titre(self):
        return self._titre

    @Titre.setter
    def Titre(self, value):
        self._titre = value
        self.notify_property('Titre')
```

- [ ] **Étape 4 : Créer `lib/views/MainWindowView.py`**

```python
# 418.tab/Manage.panel/ManageFiltre.pushbutton/lib/views/MainWindowView.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = None

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_XAML = os.path.join(_ROOT, 'GUI', 'Views', 'MainWindow.xaml')


class MainWindowView(object):
    def __init__(self, view_model):
        self._vm = view_model
        self._win = BaseWindow(_XAML, view_model) if BaseWindow is not None else None

    def show(self):
        if self._win is None:
            print('MainWindowView: BaseWindow non disponible')
            return
        self._win.show()
```

- [ ] **Étape 5 : Créer `GUI/Views/MainWindow.xaml`**

```xml
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="{Binding Titre}"
        Width="700" Height="500"
        WindowStartupLocation="CenterScreen"
        ResizeMode="CanResizeWithGrip">
    <Grid Margin="16">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <TextBlock Grid.Row="0"
                   Text="{Binding Titre}"
                   FontSize="20" FontWeight="Bold"
                   Margin="0,0,0,16"/>

        <Border Grid.Row="1"
                BorderBrush="#CCCCCC" BorderThickness="1"
                CornerRadius="4">
            <TextBlock Text="— Scaffold ManageFiltre — à implémenter —"
                       HorizontalAlignment="Center"
                       VerticalAlignment="Center"
                       FontSize="14" Foreground="Gray"/>
        </Border>
    </Grid>
</Window>
```

- [ ] **Étape 6 : Créer `script.py`**

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Filtres"
__doc__ = "Gestion avancée des filtres de vue."
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

- [ ] **Étape 7 : Vérifier la syntaxe**

```bash
python -c "import ast
for f in ['script.py','lib/viewmodels/MainViewModel.py','lib/views/MainWindowView.py']:
    ast.parse(open('418.tab/Manage.panel/ManageFiltre.pushbutton/' + f).read())
    print('OK ' + f)"
```

- [ ] **Étape 8 : Commit**

```bash
git add "418.tab/Manage.panel/ManageFiltre.pushbutton/"
git commit -m "feat(ManageFiltre): scaffold MVVM complet"
```

---

## Task 9 : Branche `feat/ManageMatérial` — scaffold MVVM

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout Developpement
git checkout -b "feat/ManageMatérial"
```

- [ ] **Étape 2 : Créer les dossiers**

```bash
mkdir -p "418.tab/Manage.panel/ManageMatérial.pushbutton/GUI/Views"
mkdir -p "418.tab/Manage.panel/ManageMatérial.pushbutton/lib/models"
mkdir -p "418.tab/Manage.panel/ManageMatérial.pushbutton/lib/viewmodels"
mkdir -p "418.tab/Manage.panel/ManageMatérial.pushbutton/lib/services"
mkdir -p "418.tab/Manage.panel/ManageMatérial.pushbutton/lib/views"
```

Créer les 5 fichiers `__init__.py` (même contenu que Task 7, Étape 2).

- [ ] **Étape 3 : Créer `lib/viewmodels/MainViewModel.py`**

```python
# 418.tab/Manage.panel/ManageMatérial.pushbutton/lib/viewmodels/MainViewModel.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    RelayCommand = None


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._titre = u'Gestion des matériaux'
        self.fermer_cmd = RelayCommand(lambda p: None) if RelayCommand else None

    @property
    def Titre(self):
        return self._titre

    @Titre.setter
    def Titre(self, value):
        self._titre = value
        self.notify_property('Titre')
```

- [ ] **Étape 4 : Créer `lib/views/MainWindowView.py`**

```python
# 418.tab/Manage.panel/ManageMatérial.pushbutton/lib/views/MainWindowView.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = None

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_XAML = os.path.join(_ROOT, 'GUI', 'Views', 'MainWindow.xaml')


class MainWindowView(object):
    def __init__(self, view_model):
        self._vm = view_model
        self._win = BaseWindow(_XAML, view_model) if BaseWindow is not None else None

    def show(self):
        if self._win is None:
            print('MainWindowView: BaseWindow non disponible')
            return
        self._win.show()
```

- [ ] **Étape 5 : Créer `GUI/Views/MainWindow.xaml`**

```xml
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="{Binding Titre}"
        Width="700" Height="500"
        WindowStartupLocation="CenterScreen"
        ResizeMode="CanResizeWithGrip">
    <Grid Margin="16">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <TextBlock Grid.Row="0"
                   Text="{Binding Titre}"
                   FontSize="20" FontWeight="Bold"
                   Margin="0,0,0,16"/>

        <Border Grid.Row="1"
                BorderBrush="#CCCCCC" BorderThickness="1"
                CornerRadius="4">
            <TextBlock Text="— Scaffold ManageMatérial — à implémenter —"
                       HorizontalAlignment="Center"
                       VerticalAlignment="Center"
                       FontSize="14" Foreground="Gray"/>
        </Border>
    </Grid>
</Window>
```

- [ ] **Étape 6 : Créer `script.py`**

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Matériaux"
__doc__ = "Gestion et édition des matériaux."
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

- [ ] **Étape 7 : Vérifier la syntaxe**

```bash
python -c "import ast
for f in ['script.py','lib/viewmodels/MainViewModel.py','lib/views/MainWindowView.py']:
    ast.parse(open('418.tab/Manage.panel/ManageMatérial.pushbutton/' + f).read())
    print('OK ' + f)"
```

- [ ] **Étape 8 : Commit**

```bash
git add "418.tab/Manage.panel/ManageMatérial.pushbutton/"
git commit -m "feat(ManageMatérial): scaffold MVVM complet"
```

---

## Task 10 : Branche `feat/ManageSheet` — scaffold MVVM

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout Developpement
git checkout -b feat/ManageSheet
```

- [ ] **Étape 2 : Créer les dossiers**

```bash
mkdir -p "418.tab/Manage.panel/ManageSheet.pushbutton/GUI/Views"
mkdir -p "418.tab/Manage.panel/ManageSheet.pushbutton/lib/models"
mkdir -p "418.tab/Manage.panel/ManageSheet.pushbutton/lib/viewmodels"
mkdir -p "418.tab/Manage.panel/ManageSheet.pushbutton/lib/services"
mkdir -p "418.tab/Manage.panel/ManageSheet.pushbutton/lib/views"
```

Créer les 5 fichiers `__init__.py` (même contenu que Task 7, Étape 2).

- [ ] **Étape 3 : Créer `lib/viewmodels/MainViewModel.py`**

```python
# 418.tab/Manage.panel/ManageSheet.pushbutton/lib/viewmodels/MainViewModel.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    RelayCommand = None


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._titre = u'Gestion des feuilles'
        self.fermer_cmd = RelayCommand(lambda p: None) if RelayCommand else None

    @property
    def Titre(self):
        return self._titre

    @Titre.setter
    def Titre(self, value):
        self._titre = value
        self.notify_property('Titre')
```

- [ ] **Étape 4 : Créer `lib/views/MainWindowView.py`**

```python
# 418.tab/Manage.panel/ManageSheet.pushbutton/lib/views/MainWindowView.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = None

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_XAML = os.path.join(_ROOT, 'GUI', 'Views', 'MainWindow.xaml')


class MainWindowView(object):
    def __init__(self, view_model):
        self._vm = view_model
        self._win = BaseWindow(_XAML, view_model) if BaseWindow is not None else None

    def show(self):
        if self._win is None:
            print('MainWindowView: BaseWindow non disponible')
            return
        self._win.show()
```

- [ ] **Étape 5 : Créer `GUI/Views/MainWindow.xaml`**

```xml
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="{Binding Titre}"
        Width="700" Height="500"
        WindowStartupLocation="CenterScreen"
        ResizeMode="CanResizeWithGrip">
    <Grid Margin="16">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <TextBlock Grid.Row="0"
                   Text="{Binding Titre}"
                   FontSize="20" FontWeight="Bold"
                   Margin="0,0,0,16"/>

        <Border Grid.Row="1"
                BorderBrush="#CCCCCC" BorderThickness="1"
                CornerRadius="4">
            <TextBlock Text="— Scaffold ManageSheet — à implémenter —"
                       HorizontalAlignment="Center"
                       VerticalAlignment="Center"
                       FontSize="14" Foreground="Gray"/>
        </Border>
    </Grid>
</Window>
```

- [ ] **Étape 6 : Créer `script.py`**

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Feuilles"
__doc__ = "Gestion des feuilles (nommage, tri, duplication)."
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

- [ ] **Étape 7 : Vérifier la syntaxe**

```bash
python -c "import ast
for f in ['script.py','lib/viewmodels/MainViewModel.py','lib/views/MainWindowView.py']:
    ast.parse(open('418.tab/Manage.panel/ManageSheet.pushbutton/' + f).read())
    print('OK ' + f)"
```

- [ ] **Étape 8 : Commit**

```bash
git add "418.tab/Manage.panel/ManageSheet.pushbutton/"
git commit -m "feat(ManageSheet): scaffold MVVM complet"
```

---

## Task 11 : Branche `feat/ManageView` — scaffold MVVM

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout Developpement
git checkout -b feat/ManageView
```

- [ ] **Étape 2 : Créer les dossiers**

```bash
mkdir -p "418.tab/Manage.panel/ManageView.pushbutton/GUI/Views"
mkdir -p "418.tab/Manage.panel/ManageView.pushbutton/lib/models"
mkdir -p "418.tab/Manage.panel/ManageView.pushbutton/lib/viewmodels"
mkdir -p "418.tab/Manage.panel/ManageView.pushbutton/lib/services"
mkdir -p "418.tab/Manage.panel/ManageView.pushbutton/lib/views"
```

Créer les 5 fichiers `__init__.py` (même contenu que Task 7, Étape 2).

- [ ] **Étape 3 : Créer `lib/viewmodels/MainViewModel.py`**

```python
# 418.tab/Manage.panel/ManageView.pushbutton/lib/viewmodels/MainViewModel.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    RelayCommand = None


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._titre = u'Gestion des vues'
        self.fermer_cmd = RelayCommand(lambda p: None) if RelayCommand else None

    @property
    def Titre(self):
        return self._titre

    @Titre.setter
    def Titre(self, value):
        self._titre = value
        self.notify_property('Titre')
```

- [ ] **Étape 4 : Créer `lib/views/MainWindowView.py`**

```python
# 418.tab/Manage.panel/ManageView.pushbutton/lib/views/MainWindowView.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = None

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_XAML = os.path.join(_ROOT, 'GUI', 'Views', 'MainWindow.xaml')


class MainWindowView(object):
    def __init__(self, view_model):
        self._vm = view_model
        self._win = BaseWindow(_XAML, view_model) if BaseWindow is not None else None

    def show(self):
        if self._win is None:
            print('MainWindowView: BaseWindow non disponible')
            return
        self._win.show()
```

- [ ] **Étape 5 : Créer `GUI/Views/MainWindow.xaml`**

```xml
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="{Binding Titre}"
        Width="700" Height="500"
        WindowStartupLocation="CenterScreen"
        ResizeMode="CanResizeWithGrip">
    <Grid Margin="16">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <TextBlock Grid.Row="0"
                   Text="{Binding Titre}"
                   FontSize="20" FontWeight="Bold"
                   Margin="0,0,0,16"/>

        <Border Grid.Row="1"
                BorderBrush="#CCCCCC" BorderThickness="1"
                CornerRadius="4">
            <TextBlock Text="— Scaffold ManageView — à implémenter —"
                       HorizontalAlignment="Center"
                       VerticalAlignment="Center"
                       FontSize="14" Foreground="Gray"/>
        </Border>
    </Grid>
</Window>
```

- [ ] **Étape 6 : Créer `script.py`**

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Vues"
__doc__ = "Gestion des vues (templates, organisation)."
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

- [ ] **Étape 7 : Vérifier la syntaxe**

```bash
python -c "import ast
for f in ['script.py','lib/viewmodels/MainViewModel.py','lib/views/MainWindowView.py']:
    ast.parse(open('418.tab/Manage.panel/ManageView.pushbutton/' + f).read())
    print('OK ' + f)"
```

- [ ] **Étape 8 : Commit**

```bash
git add "418.tab/Manage.panel/ManageView.pushbutton/"
git commit -m "feat(ManageView): scaffold MVVM complet"
```

---

## Task 12 : Branche `feat/ImageCrop` — placeholder

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout Developpement
git checkout -b feat/ImageCrop
```

- [ ] **Étape 2 : Créer le dossier et `script.py`**

```bash
mkdir -p "418.tab/Tools.panel/ImageCrop.pushbutton"
```

```python
# 418.tab/Tools.panel/ImageCrop.pushbutton/script.py
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "ImageCrop"
__doc__ = "Recadrage automatique d'images/vues — comportement à définir."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

# TODO(feat/ImageCrop): définir le comportement (sélection vues, paramètres de recadrage, export)
print(u'ImageCrop: non implémenté')
```

- [ ] **Étape 3 : Commit**

```bash
git add "418.tab/Tools.panel/ImageCrop.pushbutton/"
git commit -m "feat(ImageCrop): placeholder script.py"
```

---

## Récapitulatif des branches

| Branche | Base | Livrable |
|---------|------|----------|
| `Developpement` | — | lib partagée + README + nettoyage |
| `feat/Export` | Developpement | Marqueur migration BatchExport |
| `feat/Audit` | Developpement | Scaffold MVVM Audit.panel |
| `feat/ManageFiltre` | Developpement | Scaffold MVVM Manage.panel |
| `feat/ManageMatérial` | Developpement | Scaffold MVVM Manage.panel |
| `feat/ManageSheet` | Developpement | Scaffold MVVM Manage.panel |
| `feat/ManageView` | Developpement | Scaffold MVVM Manage.panel |
| `feat/ImageCrop` | Developpement | Placeholder Tools.panel |
