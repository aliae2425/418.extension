# 418.extension

Extension pyRevit pour l'automatisation et la gestion dans Revit.

## Fonctionnalités

| Feature | Panel | Description | Version | Statut |
|---------|-------|-------------|---------|--------|
| BatchExport | Export | Export en lot PDF/DWG depuis les jeux de feuilles | 0.3 | 🔨 En cours |
| ManageFiltre | Manage | Gestion avancée des filtres de vue | — | ⏳ Scaffold |
| ManageMatérial | Manage | Gestion et édition des matériaux | — | ⏳ Scaffold |
| ManageSheet | Manage | Gestion des feuilles (nommage, tri, duplication) | — | ⏳ Scaffold |
| ManageView | Manage | Gestion des vues (templates, organisation) | — | ⏳ Scaffold |
| ImageCrop | Tools | Recadrage automatique d'images/vues | — | 🔲 Placeholder |
| Infos | Aide | Fenêtre « À propos » (version, dépôt, licence) | 1.2.12 | ✅ Actif |

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
