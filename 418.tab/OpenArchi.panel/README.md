# OpenArchi

Un chat dans Revit, qui voit la maquette et peut y toucher.

Le bouton **Chat** ouvre un volet ancrable. On y parle en français, le modèle
répond, et il dispose des **57 outils** de `lib/rvt` pour lire le projet
ouvert — ou le modifier.

L'interface est une page web servie à un WebView2 ; le moteur de conversation
y tourne aussi. Côté Revit, Python n'est qu'un hôte. L'architecture est
décrite dans [CLAUDE.md](../../CLAUDE.md), section « Le harnais ».

---

## Prise en main

1. **pyRevit → onglet 418 → OpenArchi → Chat** ouvre le volet. Il s'ancre où
   vous le posez et y reste.
2. Tapez `/connect` — le navigateur s'ouvre, vous vous connectez à ChatGPT,
   et le volet reprend la main tout seul.
3. Posez une question : *« sur quelle vue je suis ? »*

Le pied du volet dit en permanence **qui répond** et **sur quels outils** —
par exemple `gpt-5.6-terra · abonnement · 57 outils Revit, dont 4 irréversibles`.

**Pour que les outils marchent** : « Routes » coché dans les réglages pyRevit,
et un projet ouvert. Sinon le pied affiche `maquette muette` et le modèle
répond sans rien voir.

---

## Les commandes

Tapez `/` : la liste s'ouvre et se filtre à la frappe. **Tab** complète.

| commande | effet |
|---|---|
| `/connect` | **ouvre le choix du fournisseur** — abonnement ChatGPT ou clé API |
| `/connect <clé>` | poser une clé OpenAI directement |
| `/model` | **ouvre la liste des modèles** que la connexion expose |
| `/model <nom>` | imposer un modèle à la main |
| `/logout` | fermer la session et effacer la clé |
| `/aide` | lister les commandes |

**Entrée** envoie · **Maj+Entrée** saute une ligne · **↑ ↓** rappellent ce qui
a déjà été envoyé · **Échap** ferme la liste.

`/connect` et `/model` ouvrent un **menu** au même endroit : ↑ ↓ pour choisir,
**Entrée** pour prendre, et la frappe le filtre.

Ce qu'on y voit vient de **[418.cloud](https://cloud.418.archi/api.json)**, le
catalogue des fournisseurs et modèles qu'on sait employer. Y ajouter une
entrée suffit à la voir apparaître ici ; l'en retirer suffit à la faire
disparaître — rien à redéployer côté volet.

Il est lu dans cet ordre : **cache local**, puis **instantané embarqué**
(`lib/web/catalogue.json`), puis le **service**, tiré en fond et jamais
attendu. D'où un `/connect` qui marche au premier lancement et sur un poste
sans Internet.

Sur une **clé**, `/model` demande la liste à l'API : elle sait ce que *cette*
clé peut appeler, là où le catalogue décrit ce qui existe. Sur l'**abonnement**,
le catalogue est la seule source — le backend Codex n'expose ni route, ni
config, ni cache.

Les deux connexions ne se valent pas : l'abonnement ne coûte rien au jeton, la
clé est facturée à l'usage. Si les deux existent, l'abonnement gagne.

**Ni la clé ni le jeton n'entrent dans la page.** Ils vivent dans
`%LOCALAPPDATA%\418.extension\auth.json`, hors du dépôt : une copie de
l'extension n'emporte pas votre session.

---

## Les outils

Le modèle les appelle seul quand il en a besoin. Chaque appel apparaît dans le
fil sous forme de carte — **repliée par défaut**, cliquez pour voir la sortie.

Trois familles, et la différence n'est pas cosmétique :

| famille | ce que ça veut dire |
|---|---|
| **lecture** | sans effet sur le projet |
| **écriture** | `Ctrl+Z` les défait |
| **irréversible** | aucun retour arrière — 4 outils |

Les irréversibles — `revit_executer_code`, `revit_synchroniser`,
`revit_enregistrer`, `revit_exporter` — **demandent votre accord dans le fil**,
avec *Refuser* / *Accorder* / *Toujours*. Refuser est le premier au clavier :
le geste sûr doit être le plus facile.

Pas de réponse = refus. Pas d'interface pour demander = refus aussi.
**Et le verrou est côté serveur** : les routes `/418/` exigent un jeton de
session, donc le contourner en n'utilisant pas le volet ne marche pas non plus.

La couverture outil par outil est dans
[`lib/rvt/COUVERTURE.md`](../../lib/rvt/COUVERTURE.md).

### Bornes

- **5 tours d'outils** par message, puis le modèle doit répondre en texte.
- Sortie d'outil **tronquée à 6 000 caractères** avant renvoi.

---

## Le volet

**Texte en flux** — la réponse arrive mot à mot. Pendant l'attente, une bulle
« réfléchit… » avec le temps écoulé en dessous ; le temps reste affiché une
fois la réponse là.

**Markdown rendu** — gras, listes, code, tableaux. Les tableaux défilent dans
leur coin quand le volet est étroit.

**Raisonnement replié** — ce que le modèle se dit à lui-même, quand il
l'expose, apparaît dans un bloc à dérouler.

**Stop** interrompt en cours de route, y compris pendant un appel d'outil.

---

## Quand ça ne va pas

- **F12** ouvre les DevTools : console, réseau, inspecteur. C'est le premier
  endroit à regarder pour tout ce qui est web.
- `data/418.log` porte le côté Python — montage du volet, appels d'outils,
  OAuth. Cherchez `openarchi.volet`, `openarchi.outils`, `openarchi.oauth`.
- **Port 1455 occupé** à la connexion : un `codex login` ou un opencode tourne
  déjà. Fermez-le et refaites `/connect`.

---

## Pas encore là

- **56 outils sur 57 n'ont jamais tourné dans Revit** — c'est le risque n°1,
  pas une formalité ;
- la conversation ne survit pas à un rechargement de la page ;
- pas de pièces jointes — l'ancien volet WPF en avait, celui-ci pas encore ;
- pas de coloration syntaxique dans les blocs de code.
