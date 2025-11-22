# Documentation 418 Extension

Bienvenue dans la documentation technique de l'extension 418 pour pyRevit.

## 📚 Documentation disponible

### Pour les utilisateurs

- **[README.md](../README.md)** - Vue d'ensemble et guide d'utilisation
  - Installation
  - Fonctionnalités principales
  - Guide utilisateur de l'outil BatchExport
  - Configuration

### Pour les développeurs

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture technique détaillée
  - Principes architecturaux
  - Structure détaillée de tous les modules
  - Flux de données
  - Patterns de conception utilisés
  - Gestion d'erreurs et performance

- **[API.md](API.md)** - Documentation des API
  - Référence complète de toutes les classes et méthodes
  - Exemples d'utilisation
  - Structures de données
  - Callbacks et événements

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Guide de développement
  - Configuration de l'environnement
  - Standards de codage
  - Workflow de développement
  - Testing et debugging
  - Ajout de fonctionnalités
  - FAQ développeurs

### Historique et contributions

- **[CHANGELOG.md](../CHANGELOG.md)** - Historique des versions
  - Notes de version
  - Changements par version
  - Roadmap future
  - Problèmes connus

- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Guide de contribution
  - Code de conduite
  - Processus de contribution
  - Standards de développement
  - Template de Pull Request

## 🚀 Démarrage rapide

### Pour utiliser l'extension

1. Installez pyRevit
2. Clonez ce repo dans `%APPDATA%\pyRevit-Master\extensions\`
3. Rechargez pyRevit
4. Consultez le [README](../README.md) pour l'utilisation

### Pour développer

1. Lisez [DEVELOPMENT.md](DEVELOPMENT.md) pour configurer votre environnement
2. Parcourez [ARCHITECTURE.md](ARCHITECTURE.md) pour comprendre la structure
3. Référez-vous à [API.md](API.md) lors du développement
4. Suivez [CONTRIBUTING.md](../CONTRIBUTING.md) pour contribuer

## 📖 Navigation de la documentation

### Par cas d'usage

**"Je veux utiliser l'extension"**
→ [README.md](../README.md)

**"Je veux comprendre comment ça marche"**
→ [ARCHITECTURE.md](ARCHITECTURE.md)

**"Je veux développer une nouvelle fonctionnalité"**
→ [DEVELOPMENT.md](DEVELOPMENT.md) + [API.md](API.md)

**"Je veux contribuer"**
→ [CONTRIBUTING.md](../CONTRIBUTING.md)

**"Je veux voir l'historique des changements"**
→ [CHANGELOG.md](../CHANGELOG.md)

### Par module

**Core (Configuration)**
- Architecture: [Core Layer](ARCHITECTURE.md#core-libcore)
- API: [Core API](API.md#core-configuration)

**Data (Repositories)**
- Architecture: [Data Layer](ARCHITECTURE.md#data-layer-libdata)
- API: [Data API](API.md#data-repositories)

**Services (Logique métier)**
- Architecture: [Services Layer](ARCHITECTURE.md#services-layer-libservices)
- API: [Services API](API.md#services-logique-métier)

**UI (Interface)**
- Architecture: [UI Layer](ARCHITECTURE.md#ui-layer-libui)
- API: [UI API](API.md#ui-composants-interface)

**Utils (Utilitaires)**
- Architecture: [Utils](ARCHITECTURE.md#utils-libutils)
- API: [Utils API](API.md#utils-utilitaires)

## 🔍 Index des concepts clés

### Architecture

- **Pattern MVC adapté** → [ARCHITECTURE.md - Principes](ARCHITECTURE.md#principes-architecturaux)
- **Séparation en couches** → [ARCHITECTURE.md - Structure](ARCHITECTURE.md#structure-détaillée)
- **Flux de données** → [ARCHITECTURE.md - Flux](ARCHITECTURE.md#flux-de-données)
- **Patterns de conception** → [ARCHITECTURE.md - Patterns](ARCHITECTURE.md#patterns-de-conception-utilisés)

### Composants principaux

- **ExportOrchestrator** → [API.md - ExportOrchestrator](API.md#exportorchestrator)
- **NamingResolver** → [API.md - NamingResolver](API.md#namingresolver)
- **MainWindowController** → [API.md - MainWindowController](API.md#mainwindowcontroller)
- **UserConfig** → [API.md - UserConfig](API.md#userconfig)

### Développement

- **Environnement de dev** → [DEVELOPMENT.md - Environnement](DEVELOPMENT.md#environnement-de-développement)
- **Standards de code** → [DEVELOPMENT.md - Standards](DEVELOPMENT.md#standards-de-codage)
- **Workflow Git** → [DEVELOPMENT.md - Workflow](DEVELOPMENT.md#workflow-de-développement)
- **Testing** → [DEVELOPMENT.md - Testing](DEVELOPMENT.md#testing)
- **Debugging** → [DEVELOPMENT.md - Debugging](DEVELOPMENT.md#debugging)

### Guides pratiques

- **Ajouter un format d'export** → [DEVELOPMENT.md - Nouveau format](DEVELOPMENT.md#ajouter-un-nouveau-format-dexport)
- **Ajouter une fenêtre modale** → [DEVELOPMENT.md - Fenêtre modale](DEVELOPMENT.md#ajouter-une-fenêtre-modale)
- **Créer un composant UI** → [DEVELOPMENT.md - Composants](DEVELOPMENT.md#ajout-de-fonctionnalités)

## 📊 Diagrammes et schémas

### Architecture générale

```
┌─────────────────────────────────────┐
│         script.py (Entry)           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    MainWindowController (UI)        │
└──────────────┬──────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌────────┐ ┌─────────┐ ┌──────────┐
│ Config │ │ Data    │ │ Services │
│ (Core) │ │ Repos   │ │ Export   │
└────────┘ └─────────┘ └──────────┘
```

Voir [ARCHITECTURE.md - Flux](ARCHITECTURE.md#flux-de-données) pour détails.

### Flux d'export

```
UI Selection → Orchestrator.plan() → Export Plans
                    ↓
            Orchestrator.run()
                    ↓
        ┌───────────┴────────────┐
        ▼                        ▼
   PDF Export              DWG Export
        ↓                        ↓
   Naming Resolution ← Naming Resolver
        ↓                        ↓
   File Creation          File Creation
```

Voir [ARCHITECTURE.md - Export](ARCHITECTURE.md#3-exécution-de-lexport) pour détails.

## 🛠️ Outils et ressources

### Outils de développement
- [RevitLookup](https://github.com/jeremytammik/RevitLookup) - Explorer l'API Revit
- [pyRevit CLI](https://github.com/eirannejad/pyRevit) - Outils ligne de commande
- VS Code + Extensions Python/XAML

### Documentation externe
- [pyRevit Docs](https://pyrevitlabs.notion.site/)
- [Revit API Docs](https://www.revitapidocs.com/)
- [IronPython 2.7](https://ironpython.net/documentation/)

### Communauté
- [pyRevit Forum](https://discourse.pyrevitlabs.io/)
- [Revit API Forum](https://forums.autodesk.com/t5/revit-api-forum/bd-p/160)

## 📝 Notes de version

**Version actuelle**: 0.4.0

Voir [CHANGELOG.md](../CHANGELOG.md) pour l'historique complet.

**Prochaines versions**:
- 0.5.0: Multi-threading, export asynchrone
- 0.6.0: Outil de repérage, Color Splasher 2.0

## 🤝 Contribution

Pour contribuer à la documentation:

1. Documentation utilisateur → README.md
2. Documentation technique → docs/ARCHITECTURE.md, API.md
3. Guides pratiques → docs/DEVELOPMENT.md
4. Historique → CHANGELOG.md

Suivez le [guide de contribution](../CONTRIBUTING.md).

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/aliae2425/418.extension/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aliae2425/418.extension/discussions)
- **Contact**: [@aliae2425](https://github.com/aliae2425)

---

*Documentation générée pour la version 0.4.0*
