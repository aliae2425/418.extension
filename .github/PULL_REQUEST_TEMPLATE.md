# Template Pull Request

## Description

### Résumé des changements
<!-- Décrivez brièvement ce qui a été modifié -->

### Motivation et contexte
<!-- Pourquoi ces changements sont-ils nécessaires? Quel problème résout cette PR? -->
<!-- Si cela corrige un bug ouvert, veuillez ajouter: "Fixes #123" -->

## Type de changement

- [ ] 🐛 Bug fix (changement non-breaking qui corrige un problème)
- [ ] ✨ Nouvelle fonctionnalité (changement non-breaking qui ajoute une fonctionnalité)
- [ ] 💥 Breaking change (correction ou fonctionnalité qui casserait la compatibilité)
- [ ] 📝 Documentation (changements de documentation uniquement)
- [ ] 🎨 Refactoring (changement de code sans modification de comportement)
- [ ] ⚡ Performance (amélioration des performances)
- [ ] ✅ Tests (ajout ou modification de tests)

## Impact

### Modules affectés
<!-- Listez les modules/fichiers principaux modifiés -->
- [ ] Core (configuration, chemins)
- [ ] Data (repositories, stores)
- [ ] Services (orchestration, export)
- [ ] UI (composants, contrôleurs)
- [ ] Utils (utilitaires)
- [ ] Documentation

### Compatibilité
- [ ] Compatible avec Revit 2026
- [ ] Compatible avec pyRevit 4.8+
- [ ] Pas de breaking changes
- [ ] Migration nécessaire (détailler ci-dessous)

<!-- Si migration nécessaire, expliquez les étapes -->

## Tests effectués

### Tests manuels
- [ ] Test dans Revit 2026
- [ ] Test avec petit projet (< 20 feuilles)
- [ ] Test avec projet moyen (20-100 feuilles)
- [ ] Test avec grand projet (> 100 feuilles)

### Scénarios testés
<!-- Cochez et ajoutez des détails pour chaque scénario testé -->
- [ ] Export PDF seul
- [ ] Export DWG seul
- [ ] Export PDF + DWG combiné
- [ ] Export par feuilles individuelles
- [ ] Export en carnets compilés
- [ ] Nommage avec paramètres feuille
- [ ] Nommage avec paramètres projet
- [ ] Sous-dossiers par jeu
- [ ] Séparation par format

### Cas limites testés
- [ ] Jeux de feuilles vides
- [ ] Paramètres manquants
- [ ] Caractères spéciaux dans noms
- [ ] Chemins très longs
- [ ] Noms de fichiers en collision

### Résultats
<!-- Décrivez les résultats des tests -->
- ✅ Tous les tests passent
- ⚠️ Tests passent avec avertissements (détailler)
- ❌ Certains tests échouent (détailler et justifier)

## Checklist

### Code
- [ ] Le code suit les [standards de codage](docs/DEVELOPMENT.md#standards-de-codage)
- [ ] Encodage UTF-8 avec BOM sur tous les fichiers Python
- [ ] Pas de dépendances externes ajoutées
- [ ] Gestion d'erreurs robuste (try/except appropriés)
- [ ] Pas de régression détectée
- [ ] Code commenté dans les zones complexes

### Documentation
- [ ] README.md mis à jour (si nécessaire)
- [ ] CHANGELOG.md mis à jour
- [ ] Documentation API mise à jour (docs/API.md)
- [ ] Guide de développement mis à jour (si applicable)
- [ ] Docstrings ajoutées/mises à jour

### Git
- [ ] Les messages de commit suivent [Conventional Commits](https://www.conventionalcommits.org/)
- [ ] Pas de fichiers binaires/temporaires committé
- [ ] Pas de secrets ou chemins absolus dans le code
- [ ] Branch à jour avec develop/main

## Captures d'écran

<!-- Si changements UI, ajoutez des captures d'écran -->

### Avant
<!-- Image ou description de l'état avant -->

### Après
<!-- Image ou description de l'état après -->

## Notes additionnelles

### Considérations de performance
<!-- Y a-t-il des impacts sur les performances? -->

### Dépendances
<!-- Cette PR dépend-elle d'autres PRs ou changements? -->

### TODO restants
<!-- Y a-t-il des tâches à compléter dans une PR future? -->

## Checklist Reviewer

<!-- Pour le reviewer -->
- [ ] Code review effectué
- [ ] Tests manuels effectués
- [ ] Documentation vérifiée
- [ ] Pas de conflits de merge
- [ ] Approuvé pour merge

---

**Instructions pour le reviewer**: 
1. Vérifiez que tous les points de la checklist sont cochés
2. Testez manuellement dans Revit si possible
3. Validez la documentation
4. Approuvez ou demandez des changements
