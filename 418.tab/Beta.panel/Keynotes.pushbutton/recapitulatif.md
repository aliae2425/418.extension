# Récapitulatif de la logique et des fonctionnalités du bouton Keynotes (Beta.panel)

## 1. Fonctionnalités principales
- **Affichage d'une fenêtre WPF personnalisée** pour éditer les fichiers Keynotes.
- **Chargement et parsing de fichiers Keynotes** (format texte, tabulé, hiérarchique).
- **Affichage de l'arborescence des keynotes** (arbre, sélection, détails).
- **Comptage du nombre d'utilisations de chaque keynote** dans le projet Revit courant.
- **Mode sombre/clair** (toggle dans le menu burger, chargement dynamique des ressources XAML).
- **Navigation par menu burger** (ouverture/fermeture, sélection de fichier, affichage du chemin courant).
- **Affichage des détails d'une keynote sélectionnée** (placeholder, à compléter).
- **Sauvegarde et rechargement des keynotes** dans le projet Revit.

## 2. Structure technique
- **script.py** : point d'entrée, lanceur de la fenêtre principale via `MainWindowController`.
- **lib/core/AppPaths.py** : gestion des chemins vers les ressources et fichiers XAML.
- **lib/data/KeynoteParser.py** : parsing du fichier keynotes, construction de la hiérarchie.
- **lib/data/KeynoteItem.py** : objet keynote (clé, description, parent, enfants, compteur).
- **lib/services/KeynoteUsageService.py** : comptage des utilisations des keynotes dans le modèle Revit.
- **lib/ui/windows/MainWindowController.py** : logique principale de la fenêtre, gestion des événements, intégration des composants UI.
- **lib/ui/components/** :
  - `BurgerMenuComponent.py` : gestion du menu burger (toggle, dark mode, chargement fichier).
  - `KeynoteTreeComponent.py` : gestion de l'arbre des keynotes (sélection, binding).
  - `KeynoteDetailsComponent.py` : affichage des détails (à compléter).
- **lib/ui/helpers/** : chargement des ressources XAML, binding des templates.
- **GUI/** : fichiers XAML pour la fenêtre principale, les contrôles, les styles, etc.

## 3. Logique générale
- **Initialisation** :
  - Ouverture de la fenêtre principale.
  - Chargement des ressources (styles, couleurs, templates).
  - Initialisation des composants (menu, arbre, détails).
  - Détection du thème Revit (clair/sombre).
  - Chargement automatique du fichier keynotes courant du projet si disponible.
- **Interaction utilisateur** :
  - Sélection d'un fichier keynotes via le menu burger.
  - Affichage de l'arborescence et des détails.
  - Possibilité de basculer en mode sombre/clair.
  - Sauvegarde/rechargement des keynotes dans le projet.

## 4. Points perfectibles / à fiabiliser
- Gestion des erreurs lors du parsing ou du chargement de fichiers.
- Affichage des détails d'une keynote (fonctionnalité à compléter).
- Meilleure gestion des cas où le fichier keynotes n'est pas trouvé ou mal formaté.
- Optimisation du comptage des usages (performances sur gros modèles).
- UI/UX : feedback utilisateur, messages d'erreur, confirmations.

---

Ce fichier sert de base pour planifier la mise à jour et fiabilisation du bouton Keynotes.
