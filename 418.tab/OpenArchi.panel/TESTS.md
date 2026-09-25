# OpenArchi — recette

Liste de passage à cocher avant de considérer une version bonne. À tenir à
jour : quand une fonctionnalité arrive, elle arrive avec sa ligne ici. Ce qui
est validé sort de la liste — seul le reste à faire doit rester visible.

| | |
|---|---|
| **Dernière passe** | _(date)_ |
| **Par** | |
| **Version 418** | _(cf. `VERSION`)_ |
| **Revit / projet** | |
| **Fournisseur · modèle** | |

**Avant de commencer** : `pyRevit → Reload`, puis `/journal vider` — un
journal propre rend les traces lisibles. Fermer les autres clients MCP
(rvt-mcp, Claude Code) : deux clients sur le serveur de routes en même temps,
c'est une course qu'on ne maîtrise pas.

Légende : `[ ]` à faire · `[x]` conforme · `[!]` anomalie (à reporter en bas).

**Déjà validé, sorti de la liste** — volet et ancrage · saisie et commandes ·
connexion complète · phrases d'attente et chronomètre · historique de saisie
(Haut/Bas, brouillon, rejeu de commande) · recherche de familles par
catégorie · annonce d'une liste tronquée · traces d'outils dans `/journal` ·
`color_splash` et son annulation au `Ctrl+Z` · `execute_code` sur demande
explicite. À rejouer seulement après un changement qui les touche.

---


## 0 section retour et amélioration user : 

- change la couleur de fond des bulle réponse pour un bleu un peu plus claire 
- Enleve openArchi au dessus de chaque bulle réponse. 
- Modifier la bulle de réponse pour gerer les format tableau, souligné, gras, italique 
      - gere le markdown de facon plus propre


## 1 · Corrections de la passe précédente

- [x] Rappel d'historique : le curseur se place **en fin de ligne**
      _(il restait au début — la notification partait avant que WPF ait
      écrit le texte, le déplacement passe maintenant après)_
- [x] Taper au milieu d'une phrase : le curseur **ne saute pas** à la fin
- [x] Une petite ligne sous chaque réponse indique le temps de réflexion
      (`réfléchi 42 s`)
- [x] Une commande locale (`/aide`) n'affiche **aucune** durée
- [x] Le message d'accueil n'affiche aucune durée

## 2 · Attente

- [ ] Au-delà d'une minute : `1 min 05 s` => donne moi un prompt de test. 


## 3 · Unités — **non résolu, demande du code**

L'invite système demande la conversion, le modèle ne la fait pas. Ces lignes
restent rouges tant que 418 ne convertit pas lui-même.

- [x] « combien de niveaux, et à quelles altitudes ? » → altitudes dans
      **l'unité du projet**, symbole affiché _(répond en pieds, sans unité)_
- [x] « quels paramètres sur les murs ? » → valeurs dans l'unité du projet
      _(données en ft)_
- [!] Placer une famille : les coordonnées données **dans l'unité du projet**
      arrivent au bon endroit _(interprétées en pieds)_
- [!] Changer l'unité du projet (m → mm) : les réponses suivent => NOP

## 4 · Outils de lecture

- [x] Aucun chiffre annoncé qui ne vienne pas d'un appel d'outil

## 5 · Écriture annulable

- [x] « enlève les couleurs sur les portes »
- [ ] `color_splash` depuis une **feuille** : erreur propre, pas de plantage
- [!] Une erreur d'outil est **expliquée dans la bulle**, pas avalée => la bulle apparait pas a chaque fois 
- [ ] Placer une famille sur un niveau nommé
- [x] **Ctrl+Z** retire l'instance placée

## 6 · Colorisation : filtre ou remplacement — **à construire**

Demande : proposer le choix, et **créer un filtre par défaut**. Le serveur
vendorisé ne sait faire que le remplacement graphique.

- [!] Colorer une catégorie crée un **filtre de vue** nommé => Erreur a chaque fois qu'on mentionne les filtres 
- [!] Le filtre apparaît dans les propriétés de la vue et se réutilise
- [x] Demander explicitement un remplacement graphique donne l'ancien
      comportement
- [ ] Le modèle demande lequel des deux quand la demande est ambiguë

## 7 · Outils irréversibles — **sur une copie du projet**

> Aucun `Ctrl+Z` ne rattrape cette section.

- [x] « vas-y » seul → il n'agit pas
- [ ] `use_transaction` vaut `true` sur un `execute_code` courant
- [ ] `/journal` contient `IRRÉVERSIBLE revit_execute_code {…}`
- [ ] `revit_save_document` — fichier jetable uniquement
- [ ] `revit_sync_with_central` — fichier jetable uniquement
- [ ] `revit_open_document` puis les outils ciblent le **nouveau** document
- [ ] `revit_close_document`

## 8 · Bandeau d'alerte

- [ ] Fermer le projet (Revit ouvert, sans document), envoyer un message →
      « Aucun document Revit ouvert »
- [ ] Rouvrir un projet, renvoyer un message → le bandeau **disparaît**
- [ ] Décocher **Routes** dans les réglages pyRevit, redémarrer Revit →
      « Serveur de routes pyRevit éteint »
- [ ] …et le chat répond quand même, sans outils
- [ ] Le texte du bandeau se sélectionne

## 9 · Affichage

- [!] Une réponse à listes et `**gras**` s'affiche sans astérisque ni backtick
- [!] Les puces apparaissent en `•`
- [ ] Les noms d'outils (`revit_list_views`) s'affichent **entiers**, sans
      italique parasite
- [ ] Une réponse longue fait défiler automatiquement jusqu'en bas
- [x] Thème sombre de Revit : le volet suit

## 10 · Résistance et stabilité

Quatre plantages de Revit sur les passes précédentes. Cette section est celle
qui compte le plus.

- [x] Une dizaine d'appels d'outils d'affilée : **Revit tient**
- [x] Une erreur d'outil (document fermé en cours de route) donne une bulle,
      pas un plantage
- [ ] Après une erreur, `/journal` porte bien la trace — rien ne disparaît en
      silence avec le process
- [ ] Wi-Fi coupé → message réseau lisible, pas de gel
- [ ] 5 messages enchaînés rapidement
- [ ] Question longue en cours : Revit reste **rendu à la main**
- [ ] Fermer Revit pendant une attente : pas de blocage à la fermeture
- [ ] Deux Revit ouverts en même temps : le volet parle au **bon** document

---

## Anomalies constatées

| # | § | Ce qui s'est passé | Attendu | Journal | État |
|---|---|---|---|---|---|
| 1 | 3 | Altitudes et paramètres annoncés en pieds, sans unité | Unité du projet, symbole affiché | | **ouvert — code à écrire** |
| 2 | 3 | `place_family` interprète les coordonnées en pieds | Unité du projet | | **ouvert — code à écrire** |
| 3 | 6 | `color_splash` ne fait qu'un remplacement graphique | Filtre de vue par défaut | | **ouvert — à construire** |
| 4 | | | | | |

> Coller l'extrait de `/journal` fait gagner le plus de temps : il porte le
> nom de l'outil, ses arguments et la taille de la réponse.

---

## Points de fragilité connus

- **§10** la stabilité — c'est là que ça a cassé quatre fois
- **§3** les unités : l'invite seule ne suffit pas, le modèle ne convertit pas
- **§5** `color_splash` depuis une feuille (vue sans remplacements possibles)
- **§7** le modèle qui agit sans attendre la confirmation
- **§10** deux instances de Revit — le port monte de 48884 à 48885

## Non couvert, et c'est normal

Ces points n'existent pas encore, inutile de les tester :

- les `#références` ne résolvent aucun élément Revit
- les outils de `418.tab` (export, audit, duplication, renommage) ne sont pas
  appelables par le modèle
- gras et italique sont **nettoyés, pas rendus** (le `RichTextBox` faisait
  tomber Revit)
- les connexions *codex* et *clé API* n'ont pas d'outils
- l'historique de saisie ne survit pas à la fermeture du volet
