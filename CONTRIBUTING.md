# Contributing to 418 Extension

Merci de votre intérêt pour contribuer à l'extension 418! Ce document fournit les lignes directrices pour les contributions.

## Table des matières

1. [Code de conduite](#code-de-conduite)
2. [Comment contribuer](#comment-contribuer)
3. [Standards de développement](#standards-de-développement)
4. [Processus de Pull Request](#processus-de-pull-request)
5. [Signalement de bugs](#signalement-de-bugs)
6. [Suggestions de fonctionnalités](#suggestions-de-fonctionnalités)

## Code de conduite

### Notre engagement

Dans l'intérêt de favoriser un environnement ouvert et accueillant, nous nous engageons à faire de la participation à notre projet une expérience exempte de harcèlement pour tous.

### Standards

**Comportements encouragés**:
- Utiliser un langage accueillant et inclusif
- Respecter les points de vue et expériences différents
- Accepter gracieusement les critiques constructives
- Se concentrer sur ce qui est meilleur pour la communauté
- Faire preuve d'empathie envers les autres membres

**Comportements inacceptables**:
- Langage ou imagerie à connotation sexuelle
- Commentaires insultants/dérogatoires
- Harcèlement public ou privé
- Publication d'informations privées sans permission
- Autre conduite inappropriée professionnellement

## Comment contribuer

### Environnement de développement

Consultez le [Guide de développement](docs/DEVELOPMENT.md) pour configurer votre environnement.

### Types de contributions

**Nous acceptons**:
- 🐛 Corrections de bugs
- ✨ Nouvelles fonctionnalités
- 📝 Améliorations de documentation
- 🎨 Améliorations UI/UX
- ⚡ Optimisations de performance
- ✅ Ajout de tests

**Avant de commencer**:
1. Vérifiez les issues existantes
2. Créez une issue pour discuter des changements majeurs
3. Attendez l'approbation du mainteneur pour les grandes fonctionnalités

## Standards de développement

### Style de code

**Python** (IronPython 2.7):
- Suivre PEP 8 (adapté pour IronPython)
- UTF-8 avec BOM obligatoire
- Pas de f-strings (utiliser `.format()`)
- Gestion d'erreurs robuste avec try/except
- Docstrings pour toutes les fonctions publiques

**XAML**:
- Indentation 4 espaces
- Nommage PascalCase avec suffixe de type
- Utiliser ressources globales pour styles/couleurs

### Documentation

**Obligatoire pour**:
- Nouvelles fonctionnalités (API.md)
- Changements d'architecture (ARCHITECTURE.md)
- Nouveaux patterns (DEVELOPMENT.md)
- Changements utilisateur (README.md)

**Format**:
- Markdown avec formatage cohérent
- Exemples de code commentés
- Captures d'écran pour changements UI

### Tests

**Requis**:
- Tests manuels dans Revit 2026
- Tests avec différents types de projets
- Tests des cas limites
- Vérification de non-régression

**Checklist de tests**: Voir [template PR](.github/PULL_REQUEST_TEMPLATE.md)

## Processus de Pull Request

### 1. Fork et branche

```bash
# Fork le repo sur GitHub
git clone https://github.com/VOTRE-USERNAME/418.extension.git
cd 418.extension

# Créer une branche
git checkout -b feature/ma-fonctionnalite
```

### 2. Développement

```bash
# Faire vos changements
# Committer régulièrement
git add .
git commit -m "feat(module): description du changement"

# Pusher vers votre fork
git push origin feature/ma-fonctionnalite
```

### 3. Pull Request

1. Allez sur GitHub et créez une PR
2. Remplissez le template complètement
3. Liez les issues associées
4. Attendez la review

### 4. Review et merge

**Le reviewer va**:
- Vérifier le code
- Tester manuellement
- Demander des changements si nécessaire
- Approuver et merger

**Après merge**:
- Votre branche sera supprimée
- Les crédits seront ajoutés au CHANGELOG

## Signalement de bugs

### Avant de signaler

1. ✅ Vérifiez les [issues existantes](https://github.com/aliae2425/418.extension/issues)
2. ✅ Assurez-vous d'utiliser la dernière version
3. ✅ Vérifiez que c'est bien un bug (pas un feature request)

### Template de bug

```markdown
**Description du bug**
Description claire et concise du bug.

**Étapes pour reproduire**
1. Ouvrir Revit
2. Cliquer sur '...'
3. Faire '...'
4. Voir l'erreur

**Comportement attendu**
Ce qui devrait se passer normalement.

**Comportement actuel**
Ce qui se passe actuellement.

**Captures d'écran**
Si applicable, ajoutez des captures.

**Environnement**
- OS: [e.g. Windows 11]
- Revit: [e.g. 2026]
- pyRevit: [e.g. 4.8.12]
- Extension: [e.g. 0.4.0]

**Contexte additionnel**
Toute autre information pertinente.

**Logs**
```
Coller les logs de la console pyRevit
```
```

## Suggestions de fonctionnalités

### Avant de suggérer

1. ✅ Vérifiez la roadmap dans le CHANGELOG
2. ✅ Cherchez les suggestions existantes
3. ✅ Assurez-vous que c'est dans le scope du projet

### Template de suggestion

```markdown
**Problème à résoudre**
Quel problème cette fonctionnalité résoudrait-elle?

**Solution proposée**
Décrivez la solution que vous envisagez.

**Alternatives considérées**
Autres solutions que vous avez envisagées.

**Contexte d'utilisation**
Comment utiliseriez-vous cette fonctionnalité?

**Impact**
- Utilisateurs concernés: [tous/avancés/spécifique]
- Fréquence d'utilisation: [quotidienne/hebdomadaire/rare]
- Priorité suggérée: [haute/moyenne/basse]

**Mockups/Exemples**
Si applicable, ajoutez des mockups ou exemples.
```

## Convention de commits

Nous utilisons [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[corps optionnel]

[footer optionnel]
```

**Types**:
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation
- `style`: Formatage
- `refactor`: Refactoring
- `perf`: Performance
- `test`: Tests
- `chore`: Maintenance

**Scopes** (exemples):
- `export`: Module d'export
- `naming`: Système de nommage
- `ui`: Interface utilisateur
- `config`: Configuration
- `docs`: Documentation

**Exemples**:
```bash
feat(export): ajout support format DXF
fix(naming): gestion paramètres projet vides
docs(api): documentation de NamingResolver
refactor(ui): extraction composant DestinationPicker
```

## Versioning

Nous suivons [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: Nouvelles fonctionnalités (rétrocompatibles)
- **PATCH**: Corrections de bugs

**Exemple**: `0.4.2`
- `0` = Version majeure (pre-release)
- `4` = Fonctionnalités ajoutées
- `2` = Bugs corrigés

## Questions?

- 📖 Consultez la [documentation](docs/)
- 💬 Ouvrez une [discussion](https://github.com/aliae2425/418.extension/discussions)
- 📧 Contactez [@aliae2425](https://github.com/aliae2425)

## Licence et droits

En contribuant, vous acceptez que vos contributions soient sous la même licence que le projet.

---

**Merci de contribuer à améliorer l'extension 418!** 🎉
