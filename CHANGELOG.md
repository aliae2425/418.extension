# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Non publié]

### À venir
- Outil de repérage automatique des coupes et élévations
- Color Splasher 2.0 avec palettes prédéfinies
- Support des liens Revit dans l'export

## [0.4.0] - 2025-11-21

### Ajouté
- **Support des paramètres projet dans le nommage**: Les patterns de nommage peuvent maintenant utiliser des paramètres du projet (ex: Project Name, Project Number)
- **Cache des paramètres projet**: Optimisation des performances lors de la résolution de nommage
- **Mise à jour UI en temps réel**: La grille de prévisualisation se met à jour pendant l'export avec des indicateurs de statut
- **Statuts visuels détaillés**: Indicateurs de progression par collection et par feuille
- **Documentation technique complète**: README, Architecture, API, Guide de développement

### Modifié
- **Amélioration de la robustesse**: Gestion d'erreurs renforcée dans tous les modules
- **NamingResolver**: Recherche hiérarchique des paramètres (élément → projet)
- **ExportOrchestrator**: Ajout de callbacks pour mise à jour UI
- **CollectionPreviewComponent**: Support des statuts détaillés par format et feuille

### Corrigé
- **Résolution de nommage**: Gestion correcte des paramètres vides (pas de fallback sur le nom du paramètre)
- **Export DWG**: Nettoyage correct des fichiers temporaires
- **Validation de destination**: Vérification plus robuste des chemins Windows
- **Gestion des caractères spéciaux**: Sanitization améliorée pour les noms de fichiers

### Performance
- **Cache paramètres projet**: Évite les requêtes répétées à l'API Revit
- **Lazy loading**: Chargement progressif des composants UI
- **Optimisation des requêtes**: Filtrage des collections dès que possible

## [0.3.0] - 2025-10

### Ajouté
- **Interface WPF complète**: Nouvelle interface utilisateur moderne
- **Composants UI modulaires**: Architecture component-based pour l'UI
- **Gestion des configurations**: Sauvegarde et réutilisation des configurations d'export
- **Options avancées**: Sous-dossiers par jeu, séparation par format
- **Prévisualisation**: Grille de prévisualisation des exports

### Modifié
- **Architecture**: Refactoring complet vers une architecture en couches
- **Séparation des responsabilités**: Distinct entre UI, services, et data
- **Configuration**: Migration vers pyrevit.userconfig

### Technique
- **UIResourceLoader**: Système de chargement des ressources XAML
- **UITemplateBinder**: Binding automatique des templates
- **Pattern Repository**: Abstraction de l'accès aux données

## [0.2.0] - 2025-09

### Ajouté
- **Export DWG**: Support de l'export en format DWG
- **Nommage dynamique**: Configuration du pattern de nommage
- **Sélection de paramètres**: Interface pour choisir les paramètres de contrôle

### Modifié
- **Export PDF**: Amélioration de la robustesse
- **Gestion des chemins**: Génération de chemins uniques en cas de collision

## [0.1.0] - 2025-08

### Ajouté
- **Export PDF par lots**: Première version fonctionnelle
- **Export par jeu de feuilles**: Filtrage par paramètres
- **Mode carnet/feuilles séparées**: Choix du mode d'export
- **Configuration de base**: Sélection du dossier de destination

### Fonctionnalités initiales
- Export PDF uniquement
- Configuration basique
- Interface console simple

---

## Types de changements

- `Ajouté` pour les nouvelles fonctionnalités
- `Modifié` pour les changements dans les fonctionnalités existantes
- `Déprécié` pour les fonctionnalités qui seront bientôt supprimées
- `Supprimé` pour les fonctionnalités supprimées
- `Corrigé` pour les corrections de bugs
- `Sécurité` pour les vulnérabilités corrigées

## Notes de version

### Version 0.4.0 - Highlights

Cette version marque une étape importante dans la maturité du projet avec:

1. **Nommage avancé**: Support complet des paramètres projet, permettant des patterns plus flexibles et contextuels
2. **Feedback temps réel**: L'interface indique précisément l'état de chaque export en cours
3. **Documentation exhaustive**: Plus de 1000 lignes de documentation technique pour faciliter les contributions
4. **Robustesse**: Gestion d'erreurs renforcée dans tous les composants critiques
5. **Performance**: Optimisations significatives grâce au cache des paramètres

### Compatibilité

**Versions supportées**:
- Revit 2026+
- pyRevit 4.8+
- .NET Framework 4.8+

**Breaking changes**: Aucun depuis 0.3.0

### Migration depuis 0.3.x

Aucune action requise. La configuration existante est compatible.

### Problèmes connus

1. **Performance sur très grands projets**: Export de 500+ feuilles peut prendre plusieurs minutes
2. **Chemins longs**: Windows limite les chemins à 260 caractères (limitation système)
3. **UI bloquée pendant export**: L'interface ne répond pas pendant l'export (limitation IronPython)

### Roadmap

**Version 0.5.0** (Prévu Q1 2026):
- Support multi-threading pour export (via C# module)
- Export asynchrone avec UI responsive
- Support des vues 3D et schedules
- Templates de configuration exportables

**Version 0.6.0** (Prévu Q2 2026):
- Outil de repérage automatique
- Color Splasher 2.0
- Intégration avec BIM 360

---

## Contributeurs

- **Aliae** - Développeur principal - [aliae2425](https://github.com/aliae2425)

## Remerciements

- Communauté pyRevit pour le framework
- Équipe Revit API pour la documentation
- Tous les utilisateurs pour leurs retours et suggestions

---

*Pour signaler un bug ou suggérer une amélioration, ouvrez une issue sur GitHub.*

[Non publié]: https://github.com/aliae2425/418.extension/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/aliae2425/418.extension/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/aliae2425/418.extension/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/aliae2425/418.extension/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/aliae2425/418.extension/releases/tag/v0.1.0
