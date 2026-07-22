# Design — Bouton « À propos » (modal WPF d'informations)

**Date** : 2026-07-22
**Branche** : `feat/about-modal` (depuis `Developpement`)
**Statut** : Validé — prêt pour plan d'implémentation

## Objectif

Ajouter un bouton dans le ruban 418 qui ouvre une petite fenêtre modale WPF présentant les
informations de l'extension : logo à gauche, métadonnées et liens à droite (version, description,
dépôt GitHub, auteur, licence).

## Emplacement dans le ruban

- Nouveau panneau `418.tab/Aide.panel/`.
- Tri alphabétique de pyRevit → « Aide » précède « Audit » (2ᵉ caractère `i` < `u`), donc le panneau
  apparaît **en premier / à gauche** du ruban sans fichier `_layout`.
- Bouton `Infos.pushbutton/` avec `icon.png` + `icon.dark.png` (placeholder adapté d'une icône
  existante).

## Structure des fichiers (pattern MVVM du projet)

```
418.tab/Aide.panel/Infos.pushbutton/
├── script.py                      # __title__="À propos", instancie VM + View, view.show()
├── icon.png
├── icon.dark.png
├── GUI/Views/AboutWindow.xaml     # layout 2 colonnes, bindings sur le VM, zéro logique
└── lib/
    ├── __init__.py
    ├── viewmodels/
    │   ├── __init__.py
    │   └── AboutViewModel.py       # expose les propriétés + commande OuvrirDepot
    └── views/
        ├── __init__.py
        └── AboutWindowView.py      # charge le XAML via BaseWindow (modal)
```

Réutilise la bibliothèque partagée `418.extension/lib/` :
- `ui.base.BaseWindow` — chargement XAML + thème + `ShowDialog()` (modal).
- `ui.base.BaseViewModel` — `INotifyPropertyChanged`.
- `ui.helpers.RelayCommand` — commande du lien GitHub.

## AboutViewModel

Hérite de `BaseViewModel`. Propriétés en lecture seule (bindings one-way) :

| Propriété     | Valeur                                                        |
|---------------|---------------------------------------------------------------|
| `Nom`         | `418.extension`                                               |
| `Version`     | `Version 1.2.12` (constante module `__version__ = "1.2.12"`)  |
| `Description` | Ligne courte issue du README (« Extension pyRevit pour l'automatisation et la gestion dans Revit. ») |
| `Auteur`      | `Aliae`                                                       |
| `Licence`     | `Licence MIT © 2025`                                          |
| `UrlDepot`    | `https://github.com/aliae2425/418.extension`                 |

Commande :
- `OuvrirDepot` (`RelayCommand`) → ouvre `UrlDepot` dans le navigateur via
  `System.Diagnostics.Process.Start(url)`, dans un `try/except` (échec silencieux hors Revit).

## Layout de la modal (`AboutWindow.xaml`)

- `Window` : `Width=520`, `Height=300`, `ResizeMode=NoResize`,
  `WindowStartupLocation=CenterScreen`, `Title="{Binding Nom}"`.
- `Grid` racine, marge 20, 2 colonnes : `[0]=160` (fixe), `[1]=*`.
- **Colonne gauche (logo placeholder)** : `Border` arrondi (`CornerRadius`), texte « 418 »
  centré en grande typo. Emplacement conçu pour être remplacé plus tard par un `<Image>`.
- **Colonne droite** : `Grid` 2 lignes (`*` contenu, `Auto` pied de page).
  - `StackPanel` (contenu) :
    - `TextBlock` « 418.extension » (titre, gras, ~20px) — `{Binding Nom}`
    - `TextBlock` « Version 1.2.12 » — `{Binding Version}`
    - `TextBlock` description, `TextWrapping=Wrap` — `{Binding Description}`
    - Lien dépôt : `TextBlock` cliquable (style hyperlien ou `Button` plat) déclenchant
      `OuvrirDepot` — texte « github.com/aliae2425/418.extension »
    - `TextBlock` « Aliae · Licence MIT © 2025 » — auteur + licence
  - Pied de page : `Button` « Fermer » aligné à droite. Ferme la fenêtre
    (`Click` géré simplement, ou binding vers une commande de fermeture).

Le thème clair/sombre est appliqué automatiquement par `BaseWindow` via `UIResourceLoader` ;
les couleurs proviennent des ressources partagées, pas de valeurs codées en dur là où un style
partagé existe.

## Comportement du bouton Fermer

`BaseWindow` n'expose pas de handle direct de la fenêtre au VM. Approche retenue : bouton
« Fermer » avec un handler minimal côté XAML/code-behind non disponible en WPF pur chargé par
`XamlReader`. → Le VM ne peut pas fermer la fenêtre proprement. **Décision** : le bouton Fermer
utilisera l'attribut `IsCancel="True"` sur le `Button`, qui ferme une fenêtre ouverte en
`ShowDialog()` sans code. C'est le mécanisme WPF natif adapté au chargement par `XamlReader`.

## Contraintes techniques (conventions du projet)

- En-tête `# -*- coding: utf-8 -*-` + `from __future__ import unicode_literals` sur chaque `.py`.
- Tous les imports inter-couches en `try/except` avec fallback `None`, vérifié avant usage.
- Textes UI, commentaires et messages en **français**.
- Exécutable hors Revit (imports Revit/WPF dégradent gracieusement).

## Hors périmètre (YAGNI)

- Liste des dépendances / crédits tiers.
- Changelog ou notes de version.
- Vérification de mise à jour en ligne.
- Multi-langue.
- Chargement d'un vrai fichier logo (placeholder texte pour l'instant, emplacement prévu).

## Critères de réussite

1. Le panneau « Aide » avec le bouton « À propos » apparaît à gauche du ruban après Reload pyRevit.
2. Un clic ouvre une fenêtre modale centrée montrant logo placeholder + infos.
3. Le clic sur le lien GitHub ouvre le dépôt dans le navigateur.
4. « Fermer » ferme la fenêtre.
5. Le rendu respecte le thème clair et sombre.
6. `python script.py` hors Revit ne lève pas d'exception (dégradation propre).
