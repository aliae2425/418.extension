# OpenArchi

Un chat dans Revit, qui voit la maquette et peut y toucher.

Le bouton **Chat** ouvre un volet ancrable. On y parle en français, le modèle
répond, et il dispose de 17 outils pour lire le projet ouvert — ou le
modifier.

Tout est dans l'extension : aucun CLI à installer, aucun `uv`, aucun serveur
externe. La connexion au modèle passe par votre abonnement ChatGPT, dans le
navigateur, ou par une clé API si vous préférez.

La recette à passer avant de valider une version est dans
[TESTS.md](TESTS.md).

---

## Prise en main

1. **pyRevit → onglet 418 → OpenArchi → Chat** ouvre le volet. Il s'ancre où
   vous le posez et y reste.
2. Tapez `/connect` — la liste s'ouvre au-dessus du champ de saisie.
3. Choisissez **OpenAI → Navigateur** : le navigateur s'ouvre, vous vous
   connectez à ChatGPT, le volet enchaîne tout seul sur le choix du modèle.
4. Posez une question : *« sur quelle vue je suis ? »*

Le pied du volet affiche en permanence `fournisseur · connexion · modèle`.

---

## La syntaxe

| forme | rôle |
|---|---|
| `texte libre` | va au modèle, avec l'historique de la conversation |
| `/commande` | traitée sur place, ne part pas au modèle |
| `#{Nom}` ou `#Nom` | cite un élément — **analysé mais pas encore résolu** |

**Entrée** envoie · **Tab** complète sur la première proposition ·
**Échap** remonte d'une étape dans `/connect`, ou referme la liste.

Les entrées de la liste s'**exécutent** au clic, elles ne remplissent pas le
champ.

---

## Les commandes

| commande | effet |
|---|---|
| `/connect` | choisir fournisseur → connexion → modèle, en trois étapes |
| `/model` | changer de modèle sur la connexion en cours |
| `/model <nom>` | imposer un modèle à la main, sans passer par la liste |
| `/logout` | fermer la session du fournisseur courant |
| `/journal` | afficher la fin de `data/418.log`, texte sélectionnable |
| `/journal vider` | remettre le journal à zéro |
| `/aide` | lister les commandes |

`/model <nom>` existe parce que le backend ChatGPT n'expose aucun catalogue
de modèles. Il n'y a pas de liste en dur : elle vieillirait en silence.

---

## Les fournisseurs

| fournisseur | connexion | ce qu'il faut |
|---|---|---|
| OpenAI | **Navigateur** | un abonnement ChatGPT. 418 déroule OAuth lui-même, rien à installer. **Le seul qui a les outils.** |
| OpenAI | Navigateur (codex) | le CLI `codex` déjà connecté. Pas d'outils. |
| OpenAI | Clé API | `OPENAI_API_KEY` en variable d'environnement. Pas d'outils. |
| Anthropic · Ollama | — | listés, grisés, pas encore branchés |

Le jeton OAuth vit dans `%LOCALAPPDATA%\418.extension\auth.json`, hors du
dépôt : une copie de l'extension n'emporte pas votre session.

---

## Les outils

Le modèle les appelle seul quand il en a besoin. Chaque appel laisse une
ligne dans `/journal`.

### Lecture — sans effet sur le projet

| outil | ce qu'il rend |
|---|---|
| `revit_status` | document ouvert, état du lien |
| `revit_model_info` | niveaux, nombre de pièces, avertissements |
| `revit_current_view_info` | vue active : nom, type, échelle, discipline |
| `revit_list_views` | vues exportables, par type |
| `revit_list_levels` | niveaux et altitudes |
| `revit_list_family_categories` | catégories chargées et leur nombre de types |
| `revit_list_families` | familles et types — filtre `contains`, `limit` |
| `revit_list_category_parameters` | paramètres d'une catégorie |
| `revit_current_view_elements` | éléments visibles dans la vue active |

### Écriture annulable — `Ctrl+Z` les défait

| outil | ce qu'il fait |
|---|---|
| `revit_place_family` | place une instance. Coordonnées en **pieds** |
| `revit_color_splash` | colore une catégorie selon un paramètre |
| `revit_clear_colors` | retire les remplacements de couleur |

### Irréversible — aucun retour arrière

| outil | ce qu'il fait |
|---|---|
| `revit_execute_code` | exécute du IronPython dans Revit |
| `revit_save_document` | enregistre, écrase la version sur disque |
| `revit_sync_with_central` | synchronise — **visible par toute l'équipe** |
| `revit_open_document` | ouvre un autre projet, change la cible de tout |
| `revit_close_document` | ferme le projet courant |

Ces cinq-là ne posent aucune transaction : `Ctrl+Z` n'y peut rien. La consigne
système interdit au modèle de les appeler sans demande explicite dans votre
dernier message — un « vas-y » ne suffit pas, il doit décrire l'appel et
attendre. **C'est une consigne, pas un verrou.** Chaque appel est journalisé
en `IRRÉVERSIBLE` avec ses arguments.

### Bornes

- **5 tours d'outils** par message, puis le modèle doit répondre en texte.
- Sortie d'outil **tronquée à 6 000 caractères** avant renvoi.
- `revit_list_views` n'a pas de filtre : sur un gros projet, le modèle n'en
  voit qu'une partie.

---

## Le volet

**Bandeau d'alerte** en tête quand le lien avec la maquette est rompu :

- *« Serveur de routes pyRevit éteint »* — cocher **Routes** dans les
  réglages pyRevit, puis redémarrer Revit ;
- *« Aucun document Revit ouvert »* — les outils resteront muets.

Il se remplit après le premier échange, pas à l'ouverture du volet.

**Animation d'attente** : une phrase qui change toutes les 5 secondes, suivie
du temps écoulé (`je cherche le nord…  ·  12 s`). Le chronomètre repart de
zéro à chaque message. Avec deux ou trois appels d'outils, comptez 20 à 60 s.

**Bulles sélectionnables** : le texte se copie, marques Markdown retirées à
l'affichage. Le gras et l'italique ne sont pas encore *rendus*, seulement
nettoyés.

---

## Sous le capot

Le volet parle aux routes pyRevit du serveur MCP vendorisé, sur
`127.0.0.1:<port>/revit_mcp`. Le port est **découvert**, jamais supposé : il
part de 48884 et monte d'un cran par Revit ouvert.

418 ne démarre aucun serveur — il utilise celui de pyRevit. D'où le bandeau
si la case **Routes** n'est pas cochée.

Pas de MCP côté chat : le protocole existe pour les clients qui sont
*dehors* (Claude Code, Codex, Claude Desktop, qui eux passent par
`vendor/mcp-server-for-revit`). Le volet est *dedans*, un GET local suffit.

L'appel au modèle part sur un fil de fond et revient par le dispatcher :
Revit reste rendu à la main pendant que ça réfléchit.

**Journal** : `data/418.log`, lisible par `/journal`. Un volet ancré n'a pas
de fenêtre de sortie pyRevit — un `print` s'y perd.

---

## Pas encore branché

- les `#références` sont analysées mais ne résolvent aucun élément ;
- le modèle ne peut appeler aucun outil de `418.tab` (export, audit,
  duplication, renommage) ;
- gras et italique nettoyés, pas rendus ;
- outils absents sur les connexions *codex* et *clé API*.
