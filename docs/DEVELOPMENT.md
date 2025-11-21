# Guide de développement - 418 Extension

Ce guide fournit toutes les informations nécessaires pour contribuer au développement de l'extension.

## Table des matières

1. [Environnement de développement](#environnement-de-développement)
2. [Structure du code](#structure-du-code)
3. [Standards de codage](#standards-de-codage)
4. [Workflow de développement](#workflow-de-développement)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Ajout de fonctionnalités](#ajout-de-fonctionnalités)
8. [FAQ Développeurs](#faq-développeurs)

---

## Environnement de développement

### Prérequis

**Logiciels obligatoires**:
- Autodesk Revit 2026 (ou supérieur)
- pyRevit 4.8+ ([Installation](https://github.com/eirannejad/pyRevit))
- VS Code ou IDE Python avec support IronPython
- Git pour le contrôle de version

**Extensions VS Code recommandées**:
- Python (Microsoft)
- pyRevit Extension (si disponible)
- XAML (pour édition des interfaces)
- GitLens (pour l'historique Git)

### Configuration initiale

1. **Cloner le dépôt**:
```powershell
cd "%APPDATA%\pyRevit-Master\extensions"
git clone https://github.com/aliae2425/418.extension.git
```

2. **Configurer pyRevit**:
```
- Ouvrir Revit
- Onglet pyRevit → Settings
- Vérifier que l'extension est chargée
```

3. **Configurer l'IDE**:
```json
// VS Code settings.json
{
    "python.autoComplete.extraPaths": [
        "C:\\Program Files\\Autodesk\\Revit 2026\\AddIns\\pyRevit",
        "%APPDATA%\\pyRevit-Master\\pyrevitlib"
    ],
    "python.linting.enabled": false,  // IronPython non compatible
    "files.encoding": "utf8bom"       // Important pour IronPython
}
```

### Structure des dossiers

```
418.extension/
├── .git/                    # Git repository
├── docs/                    # Documentation technique
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── DEVELOPMENT.md (ce fichier)
├── 418.tab/
│   └── [panels]/
│       └── [buttons]/
│           ├── script.py     # Point d'entrée (requis)
│           ├── icon.png      # Icône (optionnel)
│           ├── GUI/          # Interfaces XAML
│           └── lib/          # Code Python
└── README.md
```

---

## Structure du code

### Organisation modulaire

#### 1. Point d'entrée (`script.py`)

**Règles**:
- Toujours en UTF-8 avec BOM (`# -*- coding: utf-8 -*-`)
- Métadonnées obligatoires: `__title__`, `__doc__`, `__author__`
- Logique minimale: instancier et appeler le contrôleur

**Template**:
```python
# -*- coding: utf-8 -*-

__title__ = "Nom de l'outil"
__doc__ = """
    Version X.Y
    Auteur : Aliae
    _____________________________________________
    
    Description de l'outil
    _____________________________________________
"""
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from lib.ui.windows.MainWindowController import MainWindowController

if __name__ == "__main__":
    ctrl = MainWindowController()
    if not ctrl.show():
        print('[erreur] UI non affichée')
```

#### 2. Structure lib/

**Principes**:
- Chaque dossier = module Python avec `__init__.py`
- Pas de dépendances circulaires
- Imports relatifs depuis lib/

**Organisation**:
```
lib/
├── __init__.py
├── core/              # Configuration, chemins
├── data/              # Accès données, persistence
├── services/          # Logique métier
├── ui/                # Interface utilisateur
└── utils/             # Utilitaires réutilisables
```

#### 3. XAML et ressources

**Structure**:
```
GUI/
├── Views/             # Fenêtres principales
│   └── index.xaml
├── Controls/          # Composants réutilisables
│   ├── CollectionPreview.xaml
│   └── [autres].xaml
├── Modals/            # Fenêtres modales
│   └── SetupEditor.xaml
└── resources/         # Styles, templates, couleurs
    ├── Colors.xaml
    ├── Styles.xaml
    └── Templates.xaml
```

---

## Standards de codage

### Python (IronPython 2.7)

#### Encodage et compatibilité

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals  # Recommandé pour les chaînes
```

**Règles importantes**:
- UTF-8 avec BOM obligatoire
- Pas de f-strings (Python 3.6+)
- Utiliser `.format()` ou `%` pour formatage
- Pas de type hints (non supportés)

#### Style de code

**Nommage**:
```python
# Classes: PascalCase
class ExportOrchestrator:
    pass

# Fonctions/méthodes: snake_case
def export_pdf_sheet():
    pass

# Constantes: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3

# Privé: préfixe underscore
def _internal_method():
    pass
```

**Indentation**: 4 espaces (pas de tabs)

**Longueur de ligne**: 100-120 caractères max

**Docstrings**: Style Google (français accepté)
```python
def resolve_for_element(elem, rows, empty_fallback=True):
    """Résout un pattern de nommage pour un élément.
    
    Args:
        elem: Élément Revit (ViewSheet, etc.)
        rows: Liste de dicts avec Name/Prefix/Suffix
        empty_fallback: Utiliser fallback si valeur vide
        
    Returns:
        Chaîne résolue avec valeurs des paramètres
        
    Raises:
        Exception: Si document non disponible
    """
    pass
```

#### Gestion d'erreurs

**Principe**: Defensive programming avec try/except généreux

```python
# BON: Robuste face aux erreurs IronPython/Revit API
try:
    value = elem.get_Parameter(param_id).AsString()
except Exception:
    value = ''  # Fallback silencieux

# MAUVAIS: Trop spécifique (types d'exceptions limités en IronPython)
try:
    value = elem.get_Parameter(param_id).AsString()
except AttributeError:
    value = ''
```

**Zones critiques**:
1. Accès API Revit (toujours dans try/except)
2. Accès fichiers (vérifier existence)
3. Accès contrôles WPF (peuvent être None)
4. Parsing XAML (peut échouer)

#### Imports

**Ordre**:
1. Standard library
2. Imports Revit/pyRevit
3. Imports locaux (relatifs)

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys

try:
    from Autodesk.Revit import DB
    from pyrevit import forms
except Exception:
    DB = None
    forms = None

from ..core.UserConfig import UserConfig
from ..data.destination.DestinationStore import DestinationStore
```

### XAML

#### Structure de base

```xaml
<UserControl xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             x:Name="Root">
    
    <!-- Contenu -->
    
</UserControl>
```

#### Nommage des contrôles

```xaml
<!-- PascalCase avec suffixe type -->
<Button x:Name="ExportButton" Content="Exporter"/>
<ComboBox x:Name="PDFSetupCombo"/>
<TextBox x:Name="PathTextBox"/>
<CheckBox x:Name="CreateSubfoldersCheck"/>
```

#### Ressources et styles

**Utilisation**:
```xaml
<!-- Référence à un style global -->
<Button Style="{StaticResource PrimaryButton}"/>

<!-- Référence à une couleur -->
<Border Background="{StaticResource AccentBrush}"/>
```

**Définition** (dans `resources/Styles.xaml`):
```xaml
<ResourceDictionary xmlns="...">
    <Style x:Key="PrimaryButton" TargetType="Button">
        <Setter Property="Background" Value="{StaticResource AccentBrush}"/>
        <Setter Property="Padding" Value="15,8"/>
    </Style>
</ResourceDictionary>
```

---

## Workflow de développement

### 1. Branching strategy

**Branches principales**:
- `main`: Code stable en production
- `develop`: Intégration des fonctionnalités
- `feature/*`: Nouvelles fonctionnalités
- `bugfix/*`: Corrections de bugs
- `hotfix/*`: Corrections urgentes

**Workflow**:
```bash
# Créer une branche feature
git checkout develop
git pull origin develop
git checkout -b feature/export-revit-links

# Développer, commiter
git add .
git commit -m "feat: ajout export des liens Revit"

# Pusher et créer PR
git push origin feature/export-revit-links
```

### 2. Messages de commit

**Format**: Convention Conventional Commits

```
type(scope): description courte

Corps du message (optionnel)

Footer (optionnel)
```

**Types**:
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation
- `style`: Formatage (pas de changement de code)
- `refactor`: Refactoring
- `test`: Ajout/modification de tests
- `chore`: Maintenance (dépendances, config)

**Exemples**:
```bash
git commit -m "feat(export): support des liens Revit dans l'export DWG"
git commit -m "fix(naming): gestion des paramètres projet vides"
git commit -m "docs(api): documentation de NamingResolver"
```

### 3. Pull Requests

**Template de PR**:
```markdown
## Description
[Décrire les changements]

## Type de changement
- [ ] Bug fix
- [ ] Nouvelle fonctionnalité
- [ ] Breaking change
- [ ] Documentation

## Tests effectués
- [ ] Test manuel dans Revit 2026
- [ ] Test avec projet complexe
- [ ] Vérification des cas limites

## Checklist
- [ ] Code suit les standards
- [ ] Documentation mise à jour
- [ ] Pas de régression détectée
- [ ] CHANGELOG mis à jour
```

### 4. Cycle de développement

1. **Planification**:
   - Définir objectif de la fonctionnalité
   - Identifier les modules impactés
   - Créer issue GitHub

2. **Développement**:
   - Créer branche feature
   - Implémenter en commits atomiques
   - Tester au fur et à mesure

3. **Testing**:
   - Tests manuels dans Revit
   - Vérifier cas limites
   - Tester avec différents projets

4. **Documentation**:
   - Mettre à jour README si nécessaire
   - Documenter API ajoutée
   - Ajouter exemples d'usage

5. **Review**:
   - Créer PR avec description détaillée
   - Adresser commentaires
   - Merger après approbation

---

## Testing

### Stratégie de test

**Niveaux**:
1. **Tests manuels** (principal): Dans Revit avec projets réels
2. **Tests d'intégration**: Workflow complets
3. **Tests unitaires** (limités): Utilitaires et helpers uniquement

### Tests manuels

#### Checklist export

**Configuration de base**:
- [ ] Sélection de 3 paramètres différents
- [ ] Validation destination valide
- [ ] Sélection configuration PDF/DWG

**Modes d'export**:
- [ ] Export PDF seul
- [ ] Export DWG seul
- [ ] Export PDF + DWG
- [ ] Export par feuilles
- [ ] Export en carnet compilé
- [ ] Mix des deux dans un même run

**Options avancées**:
- [ ] Sous-dossiers par jeu de feuilles
- [ ] Dossiers séparés PDF/DWG
- [ ] Export séparé PDF
- [ ] Export séparé DWG

**Nommage**:
- [ ] Pattern avec paramètres feuille
- [ ] Pattern avec paramètres projet
- [ ] Préfixes et suffixes
- [ ] Paramètres vides (fallback)

**Cas limites**:
- [ ] Jeu vide (0 feuilles)
- [ ] Jeu avec 1 feuille
- [ ] Jeu avec 50+ feuilles
- [ ] Paramètres manquants sur certaines feuilles
- [ ] Caractères spéciaux dans noms
- [ ] Chemins très longs

**Performance**:
- [ ] Export de 100+ feuilles
- [ ] Projet de 500+ Mo
- [ ] UI reste responsive

#### Projets de test recommandés

**Projets types**:
1. **Petit projet**: 5-10 feuilles, simple
2. **Projet moyen**: 30-50 feuilles, jeux multiples
3. **Grand projet**: 100+ feuilles, complexe

**Créer un projet de test**:
```
1. Créer 3 jeux de feuilles minimum
2. Ajouter paramètres personnalisés:
   - Export (Oui/Non)
   - Carnet (Oui/Non)
   - Export DWG (Oui/Non)
3. Varier les configurations entre jeux
4. Tester avec noms spéciaux: "Plan/Coupe*A"
```

### Debugging

#### Outils disponibles

**1. Console pyRevit**:
```python
# Afficher dans la console
print('[debug] Valeur:', variable)

# Inspection d'objets
print(dir(object))  # Lister attributs/méthodes
```

**2. VS Code attach** (limité avec IronPython):
Non supporté nativement, utiliser logs extensifs.

**3. Logs dans fichiers**:
```python
import os

log_path = os.path.join(os.environ['TEMP'], 'batch_export_debug.log')
with open(log_path, 'a') as f:
    f.write('[{}] Message\n'.format(datetime.now()))
```

#### Techniques de debugging

**Assertions**:
```python
def export_sheet(sheet):
    assert sheet is not None, "Sheet cannot be None"
    assert hasattr(sheet, 'Id'), "Sheet must have Id"
    # ...
```

**Checkpoints progressifs**:
```python
print('[1/5] Collecte des jeux...')
collections = get_collections()
print('[2/5] Analyse des paramètres...')
params = analyze_params()
# ...
```

**Isolation de problèmes**:
```python
# Tester composant isolément
if __name__ == "__main__":
    # Code de test
    resolver = NamingResolver(doc)
    result = resolver.resolve_for_element(sheet, rows)
    print('Result:', result)
```

#### Erreurs courantes

**1. NoneType object has no attribute**:
```python
# PROBLÈME
value = control.SelectedItem.ToString()

# SOLUTION
ctrl = getattr(window, 'ControlName', None)
if ctrl and hasattr(ctrl, 'SelectedItem'):
    value = str(ctrl.SelectedItem)
```

**2. XAML non chargé**:
```python
# Vérifier chemins
print('XAML path:', xaml_path)
print('Exists:', os.path.exists(xaml_path))

# Vérifier merge
if not hasattr(window, 'ExpectedControl'):
    print('[warning] Template not loaded')
```

**3. Paramètres introuvables**:
```python
# Logger tous les paramètres disponibles
for p in elem.Parameters:
    print('Param:', p.Definition.Name)
```

---

## Ajout de fonctionnalités

### Ajouter un nouveau format d'export

**Exemple**: Export en DXF

**1. Créer le service**:
```python
# lib/services/formats/DxfExporterService.py
class DxfExporterService(object):
    def __init__(self):
        from ...core.UserConfig import UserConfig
        self._cfg = UserConfig('batch_export')
    
    def build_options(self, doc, setup_name=None):
        # Construire DXFExportOptions
        pass
    
    def list_setups(self, doc):
        # Lister configurations DXF disponibles
        pass
```

**2. Intégrer dans l'orchestrateur**:
```python
# lib/services/core/ExportOrchestrator.py
from ...services.formats.DxfExporterService import DxfExporterService

class ExportOrchestrator:
    def __init__(self):
        # ...
        self._dxf = DxfExporterService()
    
    def _export_dxf_sheet(self, doc, sheet, rows, base_folder, options):
        # Logique d'export DXF
        pass
```

**3. Ajouter UI**:
```xaml
<!-- GUI/Controls/ExportOptions.xaml -->
<Expander Header="Options DXF">
    <StackPanel>
        <ComboBox x:Name="DXFSetupCombo"/>
        <CheckBox x:Name="DXFSeparateCheck" Content="Export séparé"/>
    </StackPanel>
</Expander>
```

**4. Brancher dans composant**:
```python
# lib/ui/components/ExportOptionsComponent.py
def populate_dxf(self, window):
    combo = getattr(window, 'DXFSetupCombo', None)
    if combo:
        setups = self._dxf.list_setups(doc)
        for s in setups:
            combo.Items.Add(s)
```

### Ajouter un nouveau panel/bouton

**1. Créer structure**:
```
418.tab/
└── NouveauPanel.panel/
    └── NouvelOutil.pushbutton/
        ├── script.py
        ├── icon.png (optionnel)
        └── lib/ (si nécessaire)
```

**2. Créer script.py**:
```python
# -*- coding: utf-8 -*-
__title__ = "Nouvel Outil"
__doc__ = """Description"""
__author__ = 'Aliae'
__min_revit_ver__ = 2026

if __name__ == "__main__":
    print("Hello from Nouvel Outil!")
```

**3. Recharger pyRevit**:
- Cliquer sur le bouton "Reload" dans l'onglet pyRevit

### Ajouter une fenêtre modale

**1. Créer XAML**:
```xaml
<!-- GUI/Modals/MyModal.xaml -->
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Ma Fenêtre" Width="500" Height="300">
    <Grid>
        <!-- Contenu -->
        <Button x:Name="OkButton" Content="OK"/>
        <Button x:Name="CancelButton" Content="Annuler"/>
    </Grid>
</Window>
```

**2. Créer contrôleur**:
```python
# lib/ui/windows/MyModalWindow.py
from pyrevit import forms
from ...core.AppPaths import AppPaths

class MyModal(forms.WPFWindow):
    def __init__(self):
        paths = AppPaths()
        xaml_path = os.path.join(paths.modals_dir(), 'MyModal.xaml')
        forms.WPFWindow.__init__(self, xaml_path)
        
        # Brancher événements
        self.OkButton.Click += self._on_ok
        self.CancelButton.Click += self._on_cancel
    
    def _on_ok(self, sender, args):
        self.Close()
        self.DialogResult = True
    
    def _on_cancel(self, sender, args):
        self.Close()
        self.DialogResult = False

def open_modal():
    modal = MyModal()
    return modal.ShowDialog()  # Retourne True/False
```

**3. Utiliser**:
```python
from lib.ui.windows.MyModalWindow import open_modal

if open_modal():
    print("Utilisateur a cliqué OK")
```

---

## FAQ Développeurs

### Q: Pourquoi UTF-8 avec BOM?
**R**: IronPython 2.7 nécessite le BOM pour reconnaître l'encodage UTF-8. Sans BOM, les caractères accentués peuvent causer des erreurs.

### Q: Puis-je utiliser des packages PyPI?
**R**: Non, IronPython ne supporte pas pip. Utilisez uniquement:
- Modules Python standard compatibles 2.7
- Modules .NET (via `clr.AddReference`)
- pyRevit API

### Q: Comment débugger dans VS Code?
**R**: Le debugging attaché n'est pas supporté. Utilisez:
- `print()` extensif
- Logs dans fichiers temporaires
- Tests isolés dans script.py

### Q: Les type hints sont-ils supportés?
**R**: Non, IronPython 2.7 ne supporte pas les annotations de type Python 3.5+. Utilisez des commentaires ou docstrings.

### Q: Comment gérer les chemins Windows?
**R**: Utilisez `os.path.join()` et raw strings:
```python
# BON
path = os.path.join('C:', 'Exports', 'PDF')
path = r'C:\Exports\PDF'

# MAUVAIS (échappement)
path = 'C:\Exports\PDF'  # \E non reconnu
```

### Q: Comment accéder au document Revit actif?
**R**:
```python
try:
    doc = __revit__.ActiveUIDocument.Document
except Exception:
    doc = None
```

### Q: Comment créer une transaction Revit?
**R**:
```python
from Autodesk.Revit.DB import Transaction

trans = Transaction(doc, "Nom de la transaction")
try:
    trans.Start()
    # Modifications du document
    trans.Commit()
except Exception:
    trans.RollBack()
    raise
```

### Q: Puis-je utiliser async/await?
**R**: Non, IronPython 2.7 ne supporte pas asyncio. Les opérations sont séquentielles.

### Q: Comment optimiser les performances?
**R**:
- Minimiser les accès API Revit
- Cacher les résultats de requêtes répétées
- Éviter les transactions inutiles (lecture = pas de transaction)
- Filtrer les collections dès que possible

### Q: Comment gérer les versions de Revit?
**R**: Vérifier `__min_revit_ver__` et conditionner selon la version:
```python
import platform
revit_version = int(platform.python_version().split('.')[0])

if revit_version >= 2026:
    # Fonctionnalité récente
    pass
```

---

## Ressources

### Documentation officielle
- [pyRevit Docs](https://pyrevitlabs.notion.site/pyrevitlabs/pyRevit-bd907d6292ed4ce997c46e84b6ef67a0)
- [Revit API Docs](https://www.revitapidocs.com/)
- [IronPython 2.7](https://ironpython.net/documentation/)

### Outils recommandés
- [RevitLookup](https://github.com/jeremytammik/RevitLookup): Explorer API Revit
- [pyRevit CLI](https://github.com/eirannejad/pyRevit): Commandes ligne
- [XAML Power Toys](https://archive.codeplex.com/?p=xamlpowertoys): Génération XAML

### Communauté
- [pyRevit Forum](https://discourse.pyrevitlabs.io/)
- [Revit API Forum](https://forums.autodesk.com/t5/revit-api-forum/bd-p/160)

---

*Guide de développement - Version 0.4*
