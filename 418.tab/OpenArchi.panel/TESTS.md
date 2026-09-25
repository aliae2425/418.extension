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
et curseur en fin de ligne · temps de réflexion sous la réponse · recherche
de familles par catégorie · annonce d'une liste tronquée · altitudes et
paramètres dans l'unité du projet · `color_splash` et son `Ctrl+Z` ·
`execute_code` sur demande explicite · dix appels d'affilée sans plantage ·
thème sombre.

---

## 0 · Confort de lecture

Le rendu Markdown est **abandonné** : trois tentatives, trois plantages de
Revit. À la place, le modèle a consigne de n'en pas produire.

- [ ] Fond des bulles de réponse en bleu clair, distinct des bulles
      utilisateur
- [ ] L'étiquette « OpenArchi » au-dessus de chaque réponse a disparu
- [ ] Le texte d'une bulle reste **sélectionnable et copiable**
- [ ] Demander « fais-moi un tableau des trois premières vues » → il répond
      en lignes « nom : valeur », **pas** en barres verticales
- [ ] Demander « mets les noms en gras » → il n'écrit aucun astérisque
- [ ] Une liste sort en tirets simples
- [ ] Aucun backtick autour des noms d'outils

## 1 · Filtres de couleur — **correctif à vérifier**

`generate_distinct_colors` rend des `DB.Color`, pas des tuples : tout appel
échouait. Corrigé, non rejoué.

- [ ] « colore les portes par leur paramètre Mark » → ça n'échoue plus
- [ ] Des filtres nommés `418 · Portes · Mark = …` apparaissent dans les
      propriétés de la vue
- [ ] Ils se réutilisent sur une autre vue
- [ ] Relancer le même appel **met à jour** au lieu d'empiler un doublon
- [ ] Un seul `Ctrl+Z` retire tout
- [ ] Depuis une **feuille** : erreur propre, pas de plantage
- [ ] Le modèle demande filtre ou remplacement quand la demande est ambiguë

## 2 · Unités — reste à faire

- [!] Placer une famille : les coordonnées données **dans l'unité du projet**
      arrivent au bon endroit
- [ ] Ouvrir un autre projet en cours de session : les altitudes suivent
      **sa** unité, pas celle du précédent

> **Tranché** : l'unité est fixée à la création du projet, elle est donc lue
> une seule fois et gardée pour la session. La relire à chaque message
> coûterait une requête de plus — le genre de requête en trop qui a fini par
> faire tomber Revit. Seul un changement de document l'invalide
> (`revit_open_document`, `revit_close_document`).

## 3 · Erreurs visibles

- [!] Une erreur d'outil apparaît **à chaque fois** en bandeau rouge
      _(elle n'apparaît pas systématiquement)_
- [ ] Le bandeau porte le message réel, pas seulement « HTTP 500 »
- [ ] Il disparaît au bout de 15 s
- [ ] Il disparaît aussi dès le message suivant
- [ ] Après une erreur, `/journal` porte la trace

## 4 · Attente

- [ ] Au-delà d'une minute : `1 min 05 s`

> Prompt de test : **« liste toutes les vues du projet, puis pour chacune des
> trois premières donne son type, son échelle et sa discipline, puis résume
> la maquette et compte les niveaux »** — cinq appels d'outils enchaînés,
> largement au-delà de la minute.

## 5 · Écriture annulable

- [ ] Placer une famille sur un niveau nommé

## 6 · Outils irréversibles — **sur une copie du projet**

> Aucun `Ctrl+Z` ne rattrape cette section.

- [ ] `use_transaction` vaut `true` sur un `execute_code` courant
- [ ] `/journal` contient `IRRÉVERSIBLE revit_execute_code {…}`
- [ ] `revit_save_document` — fichier jetable uniquement
- [ ] `revit_sync_with_central` — fichier jetable uniquement
- [ ] `revit_open_document` puis les outils ciblent le **nouveau** document
- [ ] `revit_close_document`

## 7 · Sélection — **nouveau, jamais testé**

- [ ] Sélectionner trois éléments dans Revit, puis « qu'est-ce que j'ai
      sélectionné ? » → il les liste
- [ ] « colore ça par leur type » → il part de la sélection
- [ ] Sans rien de sélectionné, il le dit au lieu d'inventer

## 8 · Bandeau d'alerte

- [ ] Fermer le projet (Revit ouvert, sans document), envoyer un message →
      « Aucun document Revit ouvert »
- [ ] Rouvrir un projet, renvoyer un message → le bandeau **disparaît**
- [ ] Décocher **Routes** dans les réglages pyRevit, redémarrer Revit →
      « Serveur de routes pyRevit éteint »
- [ ] …et le chat répond quand même, sans outils
- [ ] Le texte du bandeau se sélectionne

## 9 · Affichage — reste à faire

- [ ] Les noms d'outils (`revit_list_views`) s'affichent **entiers**, sans
      italique parasite
- [ ] Une réponse longue fait défiler automatiquement jusqu'en bas

## 10 · Résistance et stabilité

Cinq plantages de Revit sur les passes précédentes.

- [ ] Wi-Fi coupé → message réseau lisible, pas de gel
- [ ] 5 messages enchaînés rapidement
- [ ] Question longue en cours : Revit reste **rendu à la main**
- [ ] Fermer Revit pendant une attente : pas de blocage à la fermeture
- [ ] Deux Revit ouverts en même temps : le volet parle au **bon** document

---

## Anomalies constatées

| # | § | Ce qui s'est passé | Attendu | État |
|---|---|---|---|---|
| 1 | 1 | `revit_filtre_couleur` échoue à chaque appel — `couleurs()` supposait des tuples, le vendor rend des `DB.Color` | Filtres posés | **corrigé, à rejouer** |
| 2 | 2 | `place_family` : coordonnées au mauvais endroit | Unité du projet | ouvert |
| 3 | 2 | Changer l'unité du projet ne change rien | — | **fermé — comportement voulu**, l'unité appartient au projet |
| 4 | 3 | Le bandeau d'erreur n'apparaît pas à chaque échec | Systématique | ouvert |
| 5 | 0 | Rendu Markdown : trois plantages de Revit | — | **fermé — abandonné**, le modèle n'en produit plus |
| 6 | | | | |

> Coller l'extrait de `/journal` fait gagner le plus de temps : il porte le
> nom de l'outil, ses arguments et la taille de la réponse.

---

## Points de fragilité connus

- **§10** la stabilité — c'est là que ça a cassé quatre fois
- **§1** `filtre_couleur` depuis une feuille (vue sans remplacements)
- **§6** le modèle qui agit sans attendre la confirmation
- **§10** deux instances de Revit — le port monte de 48884 à 48885

## Non couvert, et c'est normal

- les `#références` ne résolvent aucun élément Revit
- les outils de `418.tab` (export, audit, duplication, renommage) ne sont pas
  appelables par le modèle
- les connexions *codex* et *clé API* n'ont pas d'outils
- l'historique de saisie ne survit pas à la fermeture du volet
- **gras, italique et tableaux ne sont pas rendus** : le modèle a
  consigne de n'en pas produire, c'est la seule parade qui tienne
- les **valeurs de paramètres** restent en pieds : il faudrait le type
  d'unité de chaque paramètre, qu'aucune route n'expose
