# 418 Extension pour pyRevit

Extension pyRevit personnalisée développée par Aliae pour automatiser et optimiser les workflows Revit.

## 📋 Vue d'ensemble

Cette extension pyRevit fournit un ensemble d'outils spécialisés pour améliorer la productivité dans Autodesk Revit, avec un accent particulier sur l'exportation par lots de plans et feuilles.

### Version
- **Version actuelle**: 0.4
- **Auteur**: Aliae
- **Revit minimum requis**: 2026

## 🚀 Fonctionnalités principales

### 1. Exportation par lots (BatchExport) ✅
Outil complet d'exportation automatisée de feuilles par jeux de feuilles.

**Caractéristiques principales:**
- ✅ Export PDF et DWG en masse
- ✅ Configuration par jeu de feuilles via paramètres personnalisés
- ✅ Nommage dynamique basé sur les paramètres Revit et du projet
- ✅ Export par feuilles individuelles ou carnets compilés
- ✅ Organisation automatique des dossiers de destination
- ✅ Interface utilisateur WPF moderne avec prévisualisation en temps réel
- ✅ Suivi de progression avec indicateurs visuels
- ✅ Configurations d'export réutilisables

**Paramètres contrôlables:**
- `Export` : Activer/désactiver l'export pour un jeu de feuilles
- `Carnet` : Mode compilation (carnet unique vs feuilles séparées)
- `Export DWG` : Activer l'export DWG en plus du PDF

### 2. Repérage (En développement) 🚧
Outil de repérage automatique des coupes et élévations sur les feuilles sélectionnées.

**Statut**: Fonctionnalité à venir

### 3. Color Splasher 2.0 (En développement) 🚧
Nouvelle version améliorée de l'outil de gestion des couleurs.

**Fonctionnalités prévues:**
- Choix prédéfinis de palettes de couleurs
- Interface utilisateur retravaillée
- Sauvegarde des paramètres entre sessions

**Statut**: Fonctionnalité à venir

## 📦 Installation

1. Clonez ou téléchargez ce dépôt dans votre dossier d'extensions pyRevit:
   ```
   %APPDATA%\pyRevit-Master\extensions\
   ```

2. Rechargez pyRevit (ou redémarrez Revit)

3. L'onglet "418" apparaîtra dans le ruban Revit

## 🏗️ Structure du projet

```
418.extension/
├── 418.tab/                          # Onglet principal du ruban
│   ├── Export.panel/                 # Panneau d'exportation
│   │   └── BatchExport.pushbutton/   # Outil d'exportation par lots
│   │       ├── script.py             # Point d'entrée
│   │       ├── GUI/                  # Interfaces XAML
│   │       └── lib/                  # Bibliothèques Python
│   │           ├── core/             # Configuration et chemins
│   │           ├── data/             # Gestion des données
│   │           ├── services/         # Services d'export
│   │           ├── ui/               # Contrôleurs UI
│   │           └── utils/            # Utilitaires
│   ├── layout.panel/                 # Panneau de mise en page
│   │   ├── Reperage.pushbutton/      # Outil de repérage
│   │   └── ReplaceMaterial.pushbutton/ # Remplacement de matériaux
│   └── Beta.panel/                   # Fonctionnalités en développement
│       └── ColorSplasher.pushbutton/ # Gestion des couleurs
└── README.md                         # Cette documentation
```

## 💻 Utilisation

### Exportation par lots

1. **Préparation**:
   - Créez des jeux de feuilles dans Revit
   - Ajoutez les paramètres personnalisés requis aux jeux de feuilles
   - Configurez les valeurs des paramètres pour chaque jeu

2. **Configuration de l'export**:
   - Cliquez sur le bouton "Exportation" dans le panneau Export
   - Sélectionnez les paramètres correspondants dans les listes déroulantes
   - Définissez le dossier de destination
   - Configurez les options PDF/DWG

3. **Nommage des fichiers**:
   - Cliquez sur "Nommage des feuilles" ou "Nommage des carnets"
   - Définissez le pattern de nommage avec préfixes/suffixes
   - Utilisez les paramètres Revit et projet comme variables

4. **Lancement**:
   - Vérifiez la prévisualisation dans la grille
   - Cliquez sur "Exporter"
   - Suivez la progression dans l'interface

### Options avancées

- **Sous-dossiers par jeu**: Crée un dossier pour chaque jeu de feuilles
- **Dossiers séparés par format**: Sépare PDF et DWG dans des dossiers distincts
- **Export séparé**: Configure le comportement d'export séparé pour PDF/DWG
- **Configurations d'export**: Créez et sauvegardez des configurations réutilisables

## 🔧 Configuration technique

### Dépendances
- pyRevit (framework requis)
- Autodesk Revit 2026+
- .NET Framework 4.8+
- IronPython 2.7

### Paramètres utilisateur
Les configurations sont sauvegardées via `pyrevit.userconfig` dans la section `batch_export`:
- Paramètres sélectionnés pour l'export
- Chemin de destination
- Options de dossiers
- Configurations PDF/DWG
- Patterns de nommage

## 📚 Documentation technique

Pour plus de détails techniques, consultez:
- [ARCHITECTURE.md](./docs/ARCHITECTURE.md) - Architecture détaillée du système
- [API.md](./docs/API.md) - Documentation des API et modules
- [DEVELOPMENT.md](./docs/DEVELOPMENT.md) - Guide de développement
- [CHANGELOG.md](./CHANGELOG.md) - Historique des versions

## 🤝 Contribution

### Standards de code
- Encodage UTF-8 avec BOM pour tous les fichiers Python
- Style PEP 8 avec adaptations IronPython
- Documentation en français dans les docstrings
- Gestion d'erreurs robuste avec try/except

### Workflow de développement
1. Créez une branche pour votre fonctionnalité
2. Développez et testez localement
3. Documentez vos changements
4. Soumettez une Pull Request avec description détaillée

## 📝 License

© Aliae - Tous droits réservés

## 🐛 Signalement de bugs

Pour signaler un bug ou suggérer une amélioration:
1. Vérifiez que le bug n'a pas déjà été signalé
2. Incluez la version de Revit et de pyRevit
3. Fournissez les étapes pour reproduire le problème
4. Ajoutez des captures d'écran si pertinent

## 📧 Contact

**Auteur**: Aliae  
**Repository**: aliae2425/418.extension

---

*Documentation générée pour la version 0.4*
