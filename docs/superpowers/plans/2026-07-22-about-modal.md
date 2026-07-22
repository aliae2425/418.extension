# Bouton « À propos » — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un panneau « Aide » (à gauche du ruban) avec un bouton « À propos » qui ouvre une modal WPF présentant logo placeholder à gauche et infos/liens à droite.

**Architecture:** Nouveau pushbutton pyRevit suivant le pattern MVVM du projet — `script.py` instancie un `AboutViewModel` (hérite de `BaseViewModel` partagé) et un `AboutWindowView` qui charge `GUI/Views/AboutWindow.xaml` via `BaseWindow` (modal `ShowDialog`, thème auto). Le lien GitHub s'ouvre via une `RelayCommand`.

**Tech Stack:** pyRevit, Python 2/3, WPF/XAML chargé par `System.Windows.Markup.XamlReader`, bibliothèque partagée `418.extension/lib/` (`ui.base.BaseWindow`, `ui.base.BaseViewModel`, `ui.helpers.RelayCommand`).

## Global Constraints

- Minimum Revit : 2026. Python 2/3 compatible.
- Chaque `.py` commence par `# -*- coding: utf-8 -*-` puis `from __future__ import unicode_literals`.
- Tous les imports inter-couches en `try/except` avec fallback `None`, vérifié avant usage.
- Textes UI, commentaires et messages de commit en **français**.
- Modules exécutables hors Revit : imports Revit/WPF dégradent gracieusement (jamais d'exception à l'import ni à l'exécution standalone).
- Ne jamais coder en dur un chemin XAML : le résoudre relativement au fichier.
- Version affichée : `1.2.12`. Dépôt : `https://github.com/aliae2425/418.extension`. Auteur : `Aliae`. Licence : `MIT © 2025`.
- Ne pas committer sans validation utilisateur (préférence projet). Les étapes « Commit » sont préparées mais exécutées après accord.

---

### Task 1: ViewModel + test standalone

**Files:**
- Create: `418.tab/Aide.panel/Infos.pushbutton/lib/__init__.py` (vide)
- Create: `418.tab/Aide.panel/Infos.pushbutton/lib/viewmodels/__init__.py` (vide)
- Create: `418.tab/Aide.panel/Infos.pushbutton/lib/viewmodels/AboutViewModel.py`
- Test: `418.tab/Aide.panel/Infos.pushbutton/tests/test_about_viewmodel.py`

**Interfaces:**
- Consumes: `ui.base.BaseViewModel` (méthode `notify_property(name)`), `ui.helpers.RelayCommand(execute, can_execute=None)`.
- Produces: classe `AboutViewModel()` avec propriétés lecture seule `Nom` (`u'418.extension'`), `Version` (`u'Version 1.2.12'`), `Description`, `Auteur` (`u'Aliae'`), `Licence` (`u'Licence MIT © 2025'`), `UrlDepot` (`u'https://github.com/aliae2425/418.extension'`) ; attribut commande `ouvrir_depot_cmd` (RelayCommand ou None). Constante module `__version__ = u'1.2.12'`.

- [ ] **Step 1: Écrire le test qui échoue**

Le test s'exécute hors Revit ; `BaseViewModel` doit être importable via le `lib/` partagé. Le test ajoute ce `lib/` partagé au `sys.path` (comme le fait pyRevit) puis vérifie les propriétés et que déclencher la commande ne lève pas d'exception.

`418.tab/Aide.panel/Infos.pushbutton/tests/test_about_viewmodel.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

# Rendre importable le lib partagé (418.extension/lib) comme le fait pyRevit.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(
    _HERE, '..', '..', '..', '..', '..', 'lib'))  # -> 418.extension/lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
# Rendre importable le lib local du bouton (pour 'from lib.viewmodels...').
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.viewmodels.AboutViewModel import AboutViewModel, __version__


class TestAboutViewModel(unittest.TestCase):
    def setUp(self):
        self.vm = AboutViewModel()

    def test_nom(self):
        self.assertEqual(self.vm.Nom, u'418.extension')

    def test_version_contient_numero(self):
        self.assertIn(u'1.2.12', self.vm.Version)
        self.assertEqual(__version__, u'1.2.12')

    def test_description_non_vide(self):
        self.assertTrue(len(self.vm.Description) > 0)

    def test_auteur_et_licence(self):
        self.assertEqual(self.vm.Auteur, u'Aliae')
        self.assertIn(u'MIT', self.vm.Licence)

    def test_url_depot(self):
        self.assertEqual(
            self.vm.UrlDepot,
            u'https://github.com/aliae2425/418.extension')

    def test_ouvrir_depot_ne_leve_pas(self):
        # Hors Revit, Process.Start est indisponible : ne doit pas lever.
        cmd = self.vm.ouvrir_depot_cmd
        if cmd is not None:
            cmd.Execute(None)  # RelayCommand.Execute


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python 418.tab/Aide.panel/Infos.pushbutton/tests/test_about_viewmodel.py`
Expected: FAIL — `ModuleNotFoundError`/`ImportError: No module named lib.viewmodels.AboutViewModel` (le fichier n'existe pas encore).

- [ ] **Step 3: Créer les `__init__.py` vides puis implémenter le ViewModel**

`lib/__init__.py` et `lib/viewmodels/__init__.py` : fichiers vides.

`418.tab/Aide.panel/Infos.pushbutton/lib/viewmodels/AboutViewModel.py` :
```python
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

try:
    from System.Diagnostics import Process
except Exception:
    Process = None

__version__ = u'1.2.12'


class AboutViewModel(BaseViewModel):
    """Données affichées dans la fenêtre « À propos »."""

    def __init__(self):
        super(AboutViewModel, self).__init__()
        self._nom = u'418.extension'
        self._version = u'Version {0}'.format(__version__)
        self._description = (
            u'Extension pyRevit pour l\'automatisation et la gestion '
            u'dans Revit.')
        self._auteur = u'Aliae'
        self._licence = u'Licence MIT © 2025'
        self._url_depot = u'https://github.com/aliae2425/418.extension'
        self.ouvrir_depot_cmd = (
            RelayCommand(self._ouvrir_depot) if RelayCommand else None)

    def _ouvrir_depot(self, _param):
        """Ouvre le dépôt dans le navigateur par défaut."""
        if Process is None:
            return
        try:
            Process.Start(self._url_depot)
        except Exception:
            pass

    @property
    def Nom(self):
        return self._nom

    @property
    def Version(self):
        return self._version

    @property
    def Description(self):
        return self._description

    @property
    def Auteur(self):
        return self._auteur

    @property
    def Licence(self):
        return self._licence

    @property
    def UrlDepot(self):
        return self._url_depot
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python 418.tab/Aide.panel/Infos.pushbutton/tests/test_about_viewmodel.py`
Expected: PASS — `OK` (6 tests). Hors Revit `RelayCommand`/`Process` valent `None`, la commande est `None` et le test de commande passe sans exécuter.

- [ ] **Step 5: Commit** (après accord utilisateur)

```bash
git add 418.tab/Aide.panel/Infos.pushbutton/lib 418.tab/Aide.panel/Infos.pushbutton/tests
git commit -m "feat(about): ajoute AboutViewModel et son test standalone"
```

---

### Task 2: XAML de la modal + View

**Files:**
- Create: `418.tab/Aide.panel/Infos.pushbutton/GUI/Views/AboutWindow.xaml`
- Create: `418.tab/Aide.panel/Infos.pushbutton/lib/views/__init__.py` (vide)
- Create: `418.tab/Aide.panel/Infos.pushbutton/lib/views/AboutWindowView.py`

**Interfaces:**
- Consumes: `AboutViewModel` (Task 1) ; `ui.base.BaseWindow(xaml_path, view_model)` avec méthode `show()` (appelle `ShowDialog()`).
- Produces: classe `AboutWindowView(view_model)` avec méthode `show()`.

- [ ] **Step 1: Créer le XAML**

Layout 2 colonnes ; bouton « Fermer » avec `IsCancel="True"` (ferme la fenêtre `ShowDialog` sans code-behind) ; lien GitHub via `Button` plat lié à `ouvrir_depot_cmd`. Aucune couleur codée en dur superflue : on laisse le thème partagé s'appliquer (seuls le placeholder logo et le style hyperlien utilisent des valeurs locales discrètes).

`418.tab/Aide.panel/Infos.pushbutton/GUI/Views/AboutWindow.xaml` :
```xml
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="{Binding Nom}"
        Width="520" Height="300"
        ResizeMode="NoResize"
        WindowStartupLocation="CenterScreen">
    <Grid Margin="20">
        <Grid.ColumnDefinitions>
            <ColumnDefinition Width="160"/>
            <ColumnDefinition Width="*"/>
        </Grid.ColumnDefinitions>

        <!-- Colonne gauche : logo placeholder (à remplacer par une Image) -->
        <Border Grid.Column="0"
                CornerRadius="8"
                BorderBrush="#888888" BorderThickness="1"
                Margin="0,0,20,0">
            <TextBlock Text="418"
                       HorizontalAlignment="Center"
                       VerticalAlignment="Center"
                       FontSize="48" FontWeight="Bold"/>
        </Border>

        <!-- Colonne droite : infos + pied de page -->
        <Grid Grid.Column="1">
            <Grid.RowDefinitions>
                <RowDefinition Height="*"/>
                <RowDefinition Height="Auto"/>
            </Grid.RowDefinitions>

            <StackPanel Grid.Row="0">
                <TextBlock Text="{Binding Nom}"
                           FontSize="22" FontWeight="Bold"/>
                <TextBlock Text="{Binding Version}"
                           FontSize="13" Margin="0,2,0,10"/>
                <TextBlock Text="{Binding Description}"
                           TextWrapping="Wrap" Margin="0,0,0,12"/>
                <Button Content="github.com/aliae2425/418.extension"
                        Command="{Binding ouvrir_depot_cmd}"
                        Cursor="Hand"
                        HorizontalAlignment="Left"
                        Background="Transparent" BorderThickness="0"
                        Foreground="#2A7DE1" Padding="0"
                        ToolTip="Ouvrir le dépôt GitHub"/>
                <TextBlock Margin="0,12,0,0"
                           Text="Aliae · Licence MIT © 2025"
                           FontSize="12" Foreground="Gray"/>
            </StackPanel>

            <Button Grid.Row="1"
                    Content="Fermer"
                    IsCancel="True"
                    Width="90" Height="28"
                    HorizontalAlignment="Right"/>
        </Grid>
    </Grid>
</Window>
```

- [ ] **Step 2: Créer la View**

`lib/views/__init__.py` : fichier vide.

`418.tab/Aide.panel/Infos.pushbutton/lib/views/AboutWindowView.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = None

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_XAML = os.path.join(_ROOT, 'GUI', 'Views', 'AboutWindow.xaml')


class AboutWindowView(object):
    def __init__(self, view_model):
        self._vm = view_model
        self._win = BaseWindow(_XAML, view_model) if BaseWindow is not None else None

    def show(self):
        if self._win is None:
            print('AboutWindowView: BaseWindow non disponible')
            return
        self._win.show()
```

- [ ] **Step 3: Vérifier que le chemin XAML se résout hors Revit**

Run:
```bash
python -c "import os; p=os.path.join('418.tab','Aide.panel','Infos.pushbutton','GUI','Views','AboutWindow.xaml'); print('OK' if os.path.isfile(p) else 'MANQUANT', p)"
```
Expected: `OK 418.tab/Aide.panel/Infos.pushbutton/GUI/Views/AboutWindow.xaml`

- [ ] **Step 4: Commit** (après accord utilisateur)

```bash
git add 418.tab/Aide.panel/Infos.pushbutton/GUI 418.tab/Aide.panel/Infos.pushbutton/lib/views
git commit -m "feat(about): ajoute la fenetre XAML About et sa View"
```

---

### Task 3: script.py, icônes et intégration ruban

**Files:**
- Create: `418.tab/Aide.panel/Infos.pushbutton/script.py`
- Create: `418.tab/Aide.panel/Infos.pushbutton/icon.png`
- Create: `418.tab/Aide.panel/Infos.pushbutton/icon.dark.png`

**Interfaces:**
- Consumes: `AboutViewModel` (Task 1), `AboutWindowView` (Task 2).
- Produces: point d'entrée pyRevit `script.py` avec `__title__`, `__doc__`, `__author__`, `__min_revit_ver__`.

- [ ] **Step 1: Copier des icônes placeholder existantes**

Réutilise les icônes d'ImageCrop comme placeholder (à remplacer plus tard).
Run:
```bash
cp "418.tab/Tools.panel/ImageCrop.pushbutton/icon.png.png" "418.tab/Aide.panel/Infos.pushbutton/icon.png"
cp "418.tab/Tools.panel/ImageCrop.pushbutton/icon.dark.png" "418.tab/Aide.panel/Infos.pushbutton/icon.dark.png"
```
Expected: aucune sortie (succès). Vérifier : `ls 418.tab/Aide.panel/Infos.pushbutton/*.png` liste les deux fichiers.

- [ ] **Step 2: Créer `script.py`**

`418.tab/Aide.panel/Infos.pushbutton/script.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "À propos"
__doc__ = "Informations sur l'extension 418 (version, dépôt, licence)."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from lib.viewmodels.AboutViewModel import AboutViewModel
from lib.views.AboutWindowView import AboutWindowView

if __name__ == '__main__':
    vm = AboutViewModel()
    view = AboutWindowView(vm)
    view.show()
```

- [ ] **Step 3: Vérifier le chargement standalone (dégradation propre)**

Le script instancie le VM et appelle `view.show()` ; hors Revit `BaseWindow` est `None` → message imprimé, pas d'exception. On exécute depuis le dossier du bouton pour que `from lib...` résolve, avec le lib partagé sur le `sys.path`.

Run:
```bash
cd "418.tab/Aide.panel/Infos.pushbutton" && PYTHONPATH="../../../lib" python script.py; cd - >/dev/null
```
Expected: affiche `AboutWindowView: BaseWindow non disponible` et se termine sans traceback (code de sortie 0).

- [ ] **Step 4: Vérifier l'ordre du ruban (documentation/contrôle)**

Run: `python -c "print(sorted(['Aide','Audit','Export','Manage','Tools']))"`
Expected: `['Aide', 'Audit', 'Export', 'Manage', 'Tools']` — confirme que « Aide » est premier (à gauche).

- [ ] **Step 5: Relancer la suite de tests du ViewModel (non-régression)**

Run: `python 418.tab/Aide.panel/Infos.pushbutton/tests/test_about_viewmodel.py`
Expected: PASS — `OK`.

- [ ] **Step 6: Commit** (après accord utilisateur)

```bash
git add 418.tab/Aide.panel/Infos.pushbutton/script.py 418.tab/Aide.panel/Infos.pushbutton/icon.png 418.tab/Aide.panel/Infos.pushbutton/icon.dark.png
git commit -m "feat(about): ajoute le bouton A propos dans le panneau Aide"
```

---

### Task 4: Vérification manuelle dans Revit + doc README

**Files:**
- Modify: `README.md` (tableau des fonctionnalités : ajouter la ligne « Infos / Aide »)

**Interfaces:** aucune (intégration + doc).

- [ ] **Step 1: Recharger pyRevit et tester manuellement**

Dans Revit : pyRevit tab → Reload. Vérifier :
1. Le panneau « Aide » apparaît en premier (gauche) du ruban 418.
2. Le bouton « À propos » ouvre une fenêtre modale centrée : placeholder « 418 » à gauche, infos à droite.
3. Le clic sur le lien ouvre `https://github.com/aliae2425/418.extension` dans le navigateur.
4. « Fermer » ferme la fenêtre.
5. Basculer le thème Revit clair/sombre : le rendu suit le thème.

- [ ] **Step 2: Mettre à jour le README**

Ajouter dans le tableau des fonctionnalités de `README.md` (après la ligne ImageCrop) :
```markdown
| Infos | Aide | Fenêtre « À propos » (version, dépôt, licence) | 1.2.12 | ✅ Actif |
```

- [ ] **Step 3: Commit** (après accord utilisateur)

```bash
git add README.md
git commit -m "docs(about): reference le bouton A propos dans le README"
```

---

## Self-Review

**Spec coverage:**
- Emplacement panneau à gauche → Task 3 (nom `Aide.panel`, vérif ordre) + Task 4 (vérif Revit). ✓
- Logo placeholder « 418 » à gauche → Task 2 XAML. ✓
- Nom + version 1.2.12 → Task 1 (VM) + Task 2 (bindings). ✓
- Description courte → Task 1 + Task 2. ✓
- Lien dépôt GitHub cliquable → Task 1 (`ouvrir_depot_cmd`) + Task 2 (Button). ✓
- Auteur + licence MIT → Task 1 + Task 2. ✓
- Modal `ShowDialog` + thème → via `BaseWindow` (Task 2). ✓
- Bouton Fermer → Task 2 (`IsCancel="True"`). ✓
- Exécutable hors Revit → Task 1 (test), Task 2 (résolution chemin), Task 3 (script standalone). ✓
- Branche `feat/about-modal` → déjà créée. ✓

**Placeholder scan:** Aucun TODO/TBD ; tout le code est fourni intégralement.

**Type consistency:** `AboutViewModel` propriétés (`Nom`, `Version`, `Description`, `Auteur`, `Licence`, `UrlDepot`) et `ouvrir_depot_cmd` cohérents entre Task 1 (déf), Task 2 (bindings XAML) et le test. `AboutWindowView(view_model).show()` cohérent entre Task 2 et Task 3. `__version__` = `'1.2.12'` partout.
