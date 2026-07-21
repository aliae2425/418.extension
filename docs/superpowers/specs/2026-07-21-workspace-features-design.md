# Design — Workspace complet 418.extension

**Date :** 2026-07-21
**Branche base :** `Developpement`
**Statut :** Approuvé

---

## Objectif

Créer une arborescence de branches feature isolées à partir de `Developpement`, avec une bibliothèque partagée au niveau de l'extension, une architecture MVVM pour les features WPF, et mettre à jour le README.

---

## 1. Bibliothèque partagée — `418.extension/lib/`

pyRevit ajoute automatiquement `<extension>/lib/` au `sys.path`. Tous les pushbuttons importent directement sans manipulation de `sys.path`.

```
418.extension/lib/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── AppPaths.py        ← résolution chemins XAML depuis extension root
│   ├── UserConfig.py      ← wrapper pyRevit config (namespace par feature)
│   └── sanitize.py        ← nettoyage noms Windows (max 180 chars, strip \/:*?"<>|)
└── ui/
    ├── __init__.py
    ├── helpers/
    │   ├── __init__.py
    │   ├── UIResourceLoader.py   ← merge ResourceDictionaries WPF
    │   ├── DarkMode.py           ← détection et application thème sombre
    │   ├── RelayCommand.py       ← ICommand bindable pour MVVM
    │   ├── HoverOverlay.py       ← effets hover génériques
    │   └── GridRowToggle.py      ← toggle visibilité lignes DataGrid
    ├── base/
    │   ├── __init__.py
    │   ├── BaseViewModel.py      ← INotifyPropertyChanged, notify_property()
    │   └── BaseWindow.py         ← chargement XAML + dark mode + resource loader
    └── GUI/
        └── resources/
            ├── Colors.xaml
            ├── ColorsDark.xaml
            ├── Styles.xaml
            └── StylesDark.xaml
```

**Imports dans un pushbutton :**
```python
from core.UserConfig import UserConfig
from ui.base.BaseViewModel import BaseViewModel
from ui.helpers.RelayCommand import RelayCommand
```

**`418.tab/lib/` supprimé** — les ressources XAML migrent dans `418.extension/lib/ui/GUI/resources/`.

---

## 2. Organisation des panels et pushbuttons

```
418.tab/
├── Export.panel/
│   └── BatchExport.pushbutton/       ← migré vers lib partagée (feat/Export)
├── Manage.panel/
│   ├── ManageFiltre.pushbutton/      ← WPF MVVM (feat/ManageFiltre)
│   ├── ManageMatérial.pushbutton/    ← WPF MVVM (feat/ManageMatérial)
│   ├── ManageSheet.pushbutton/       ← WPF MVVM (feat/ManageSheet)
│   └── ManageView.pushbutton/        ← WPF MVVM (feat/ManageView)
├── Audit.panel/
│   └── Audit.pushbutton/             ← WPF MVVM (feat/Audit)
└── Tools.panel/
    └── ImageCrop.pushbutton/         ← placeholder (feat/ImageCrop)
```

**`Beta.panel` supprimé.** Les pushbuttons `Keynotes` et `ColorSplasher` sont retirés de l'onglet.

---

## 3. Architecture MVVM par pushbutton WPF

Chaque pushbutton WPF (Audit, Manage*, BatchExport migré) suit ce pattern :

```
<Feature>.pushbutton/
├── script.py                    ← instancie ViewModel + charge View
├── icon.png
├── icon.dark.png
├── GUI/
│   └── Views/
│       └── MainWindow.xaml      ← bindings XAML sur ViewModel, zéro logique
└── lib/
    ├── __init__.py
    ├── models/                  ← objets domaine : DTOs, wrappers Revit
    │   └── __init__.py
    ├── viewmodels/              ← MainViewModel(BaseViewModel), ObservableCollection
    │   └── __init__.py
    ├── services/                ← logique métier + appels Revit API
    │   └── __init__.py
    └── views/                   ← chargement fenêtre, liaison View↔ViewModel
        └── __init__.py
```

**Règles MVVM :**
- Le ViewModel expose des propriétés notifiantes (`notify_property`) et des `RelayCommand`
- La View (XAML) se bind uniquement sur le ViewModel — pas de code-behind métier
- `script.py` est le seul point qui touche à Revit pour passer le document au ViewModel

**`script.py` type :**
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from lib.viewmodels.MainViewModel import MainViewModel
from lib.views.MainWindowView import MainWindowView

vm = MainViewModel(doc=__revit__.ActiveUIDocument.Document)
view = MainWindowView(vm)
view.show()
```

**Placeholder (`ImageCrop`) :**
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
# TODO: ImageCrop — comportement à définir
print("ImageCrop: non implémenté")
```

---

## 4. Stratégie des branches git

Toutes les branches partent de `Developpement`. Flux gitflow : `feat/XXX` → PR → merge `Developpement`.

| Branche | Contenu | Type |
|---------|---------|------|
| `feat/Export` | Migration BatchExport → lib partagée + MVVM | Refactor |
| `feat/Audit` | Scaffold MVVM complet | Scaffold WPF |
| `feat/ManageFiltre` | Scaffold MVVM complet | Scaffold WPF |
| `feat/ManageMatérial` | Scaffold MVVM complet | Scaffold WPF |
| `feat/ManageSheet` | Scaffold MVVM complet | Scaffold WPF |
| `feat/ManageView` | Scaffold MVVM complet | Scaffold WPF |
| `feat/ImageCrop` | `script.py` placeholder | Placeholder |

**Contenu de chaque branche :**
- Le pushbutton de la feature uniquement (pas les autres)
- `418.extension/lib/` complet
- `README.md` mis à jour
- Fichiers racine communs

---

## 5. README — Mise à jour

| Feature | Panel | Description | Version | Statut |
|---------|-------|-------------|---------|--------|
| BatchExport | Export | Export en lot PDF/DWG depuis les jeux de feuilles | 0.3 | 🔨 En cours |
| Audit | Audit | Analyse et rapport sur la santé du modèle Revit | — | ⏳ Scaffold |
| ManageFiltre | Manage | Gestion avancée des filtres de vue | — | ⏳ Scaffold |
| ManageMatérial | Manage | Gestion et édition des matériaux | — | ⏳ Scaffold |
| ManageSheet | Manage | Gestion des feuilles (nommage, tri, duplication) | — | ⏳ Scaffold |
| ManageView | Manage | Gestion des vues (templates, organisation) | — | ⏳ Scaffold |
| ImageCrop | Tools | Recadrage automatique d'images/vues | — | 🔲 Placeholder |

Section **Architecture** ajoutée au README : `418.extension/lib/`, pattern MVVM, couches.

---

## Décisions clés

| Décision | Choix | Raison |
|----------|-------|--------|
| Lib partagée | `418.extension/lib/` | pyRevit ajoute auto au sys.path |
| Architecture UI | MVVM | Séparation View/ViewModel, testabilité |
| Thème XAML | Migré dans lib partagée | Une seule source de vérité |
| `Beta.panel` | Supprimé | Hors scope du workspace |
| `418.tab/lib/` | Supprimé | Remplacé par `418.extension/lib/` |
| ImageCrop | Placeholder | Comportement non défini |
