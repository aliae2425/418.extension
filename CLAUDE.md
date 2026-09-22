# CLAUDE.md

Guide de Claude Code (claude.ai/code) sur ce dépôt.

## Ce que c'est

Un **harnais LLM pour l'architecture**, greffé sur Revit via
[pyRevit](https://github.com/eirannejad/pyRevit). L'objet du projet n'est pas
un modèle en particulier : c'est la plomberie qui permet à *n'importe quel*
LLM de travailler sur une maquette — le contexte qu'on lui donne, les outils
qu'on lui laisse appeler, et la surface par laquelle l'architecte lui parle.

Trois couches, dans cet ordre de dépendance :

1. **Les outils déterministes** (`418.tab/`) — export en lot PDF/DWG, audit de
   modèle, duplication et renommage de feuilles/vues. Ils marchent sans aucun
   LLM et restent utilisables à la main. Ce sont eux que le modèle devra
   appeler plutôt que de réinventer : un export doit être reproductible.
2. **Le socle** (`lib/core`, `lib/ui`) — logique métier pure et WPF partagés.
3. **Le harnais** (`lib/core/chat_*`, `lib/ui/OpenArchi*`, `vendor/`) — clients
   de modèle interchangeables, syntaxe du chat, panneau ancrable, et le pont
   MCP vers la maquette.

Tout le texte d'interface, les commentaires et les messages de commit sont en
**français**.

- **Revit minimum** : 2026
- **Python** : compatible 2/3 (`from __future__ import unicode_literals` en
  tête, en-tête `# -*- coding: utf-8 -*-`)

## Comportement d'agent

Toujours utiliser des équipes d'agents pour les tâches touchant plus d'un
fichier. Le lead travaille en mode délégation. Faire approuver le plan avant
d'écrire du code.

## Ligne de statut

Afficher le pourcentage de contexte, le coût de session, la branche git.

## Cycle de développement

Ni build, ni compilateur, ni linter :

1. Éditer les fichiers directement dans le dossier d'extensions pyRevit (ce dépôt).
2. Dans Revit : **onglet pyRevit → Reload** (ou `Ctrl+F5`).
3. Cliquer le bouton pour tester.

Pour tester un seul bouton sans tout recharger : clic droit sur le bouton →
**Run script**.

**Tests** : scripts `unittest` nus sous les `tests/` de chaque bouton, plus
`lib/core/tests/` et `lib/ui/tests/`. Ils amorcent leur `sys.path` eux-mêmes —
`python tests/test_x.py` suffit. Aucun runner, aucun framework, aucune fixture.
Les imports Revit sont sous `try/except` pour que la logique pure tourne hors
Revit ; un test ne doit jamais toucher le réseau ni lancer un CLI (injecter un
double, cf. `_ClientFactice`).

## Le harnais

**Agnostique du modèle.** Un fournisseur = un module de `lib/core/` qui honore
trois membres, rien de plus :

| membre | rôle |
|---|---|
| `pret()` | le client est utilisable ici et maintenant |
| `raison()` | ce qu'il manque quand `pret()` est faux, dit à l'utilisateur |
| `connecter()` | ouvre le flux navigateur, `None` s'il n'en a pas |
| `deconnecter()` | ferme la session, `None` s'il n'y en a pas |
| `modeles()` | noms disponibles, `()` si le client n'en expose pas |
| `attendre_connexion()` | *facultatif* — bloque jusqu'à la fin du flux navigateur |
| `repondre(messages, modele=None)` | `messages` = couples `(role, texte)` → texte |

Deux voies d'authentification, volontairement :

- `chat_cli.py` — passe par un CLI déjà connecté dans le navigateur
  (`codex login`), l'abonnement paie. **Aucun jeton n'est lu ni stocké par
  418** : le CLI garde son OAuth, on lui parle en sous-processus.
- `chat_openai.py` — clé API en variable d'environnement (`OPENAI_API_KEY`),
  `urllib` nu. Jamais de secret dans `data/`, qui finit poussé.

`lib/ui/OpenArchiConfig.py` est le catalogue, en arbre **fournisseur →
connexion → modèle**. **Un client à `None` suffit à griser l'entrée dans
`/connect`** — c'est le même champ qui décide de l'affichage et de
l'aiguillage, pas deux ; un fournisseur est grisé quand aucune de ses
connexions n'a de client. `/connect` déroule les trois étapes dans la liste en
place (Échap remonte d'un cran), `/model` ouvre directement la troisième.
Persisté en trois clés : `provider`, `connexion`, `modele`.

**`UserConfig` est un magasin de chaînes** : il sérialise `None` en `"None"`,
qui repasserait ensuite pour un nom de modèle valide. Écrire `''` pour « pas
de choix », jamais `None`.

Une entrée de la liste s'exécute au clic — elle ne remplit pas le champ de
saisie. Le jour où une commande prendra des arguments, il faudra rétablir le
remplissage pour celle-là.

**Le CLI codex n'expose aucun catalogue de modèles** — ni commande, ni config,
ni cache ; seul son `app-server` JSON-RPC expérimental le ferait. `modeles()`
y renvoie donc `()`, et `/model <nom>` permet d'en imposer un à la main. Ne pas
coder de liste en dur : elle vieillirait sans que rien ne le signale.

**Journal.** `lib/core/journal.py` écrit dans `data/418.log`. Un volet ancré
n'a aucune fenêtre de sortie pyRevit : un `print` s'y perd, et Revit avale les
exceptions de construction d'un volet. Tout ce qui doit se relire après coup
passe par `journal('<nom>')`. `/journal` en affiche la fin dans une bulle —
sélectionnable, donc collable dans un rapport de bug — et `/journal vider` le
remet à zéro. Un sous-processus lancé sans être attendu branche ses flux sur
`journal.flux()`, sinon son échec est muet.

**Surfaces.** Deux façons d'atteindre la maquette, à garder ouvertes toutes
les deux :

- *dans Revit* — panneau ancrable OpenArchi (`lib/ui/OpenArchiPanel.py`),
  enregistré par le `startup.py` racine. Syntaxe : `/commande` et
  `#{Référence}`, analysées par `lib/core/chat_syntaxe.py`.
- *hors Revit* — serveur MCP vendorisé, pour les clients déjà installés chez
  l'utilisateur (Claude Code, Codex, Claude Desktop…).

**Ce qui n'est pas encore branché** — à ne pas décrire comme acquis :

- les `#références` sont analysées mais ne résolvent aucun élément Revit ;
- le modèle ne peut appeler aucun des outils de `418.tab` (pas de boucle
  d'outils) ;
- pas de surcouche `routes.API('418')` : seules les routes vendorisées
  existent.

**Fil d'exécution.** L'appel au modèle part sur un `Thread` de fond et revient
par `Dispatcher.Invoke` — Revit reste rendu à la main, `EnAttente` pilote
l'animation d'attente. Hors .NET (tests), `_en_arriere_plan` exécute sur
place : le VM reste synchrone et se teste sans rien simuler. **Une commande
`/x` ne part JAMAIS en fond** : elle touche les listes et les réglages, donc
elle doit rester sur le fil d'interface.

## Arborescence

```
418.tab/
├── Export.panel/BatchExport.pushbutton/      ← export PDF/DWG en lot (principal)
├── Audit.panel/Audit.pushbutton/             ← audit de santé du modèle + tableau de bord
├── OpenArchi.panel/Chat.pushbutton/          ← ouvre le panneau de chat
├── Tools.panel/
│   ├── ImageCrop.pushbutton/
│   └── col1.stack/
│       ├── duplicate_sheets.pushbutton/
│       ├── views_duplicate.pushbutton/
│       └── Rename.pulldown/{FindReplace_Sheets, FindReplace - Views}.pushbutton/
└── 418.panel/Infos.pushbutton/               ← modale « À propos »
```

Chaque bouton est autonome : `script.py` en point d'entrée, `GUI/` pour le
XAML, `lib/` pour la logique découpée `services/` (métier) · `viewmodels/` ·
`views/` · `models/`.

## Socle partagé (`lib/` à la racine)

pyRevit le met sur `sys.path` : il s'importe en `core.X` / `ui.X` depuis
n'importe quel bouton.

```
lib/
├── core/   AppPaths, UserConfig, sanitize, transaction, selection,
│           bulk_edit, list_selection, text_filter, token_expander,
│           rename_service, chat_syntaxe, chat_openai, chat_cli
└── ui/
    ├── base/     BaseViewModel, BaseWindow, RailWindow,
    │             SelectionPageVM, SelectionItemVM
    ├── helpers/  UIResourceLoader, RelayCommand, DarkMode, wpf_runtime
    ├── OpenArchiPanel · OpenArchiChatVM · OpenArchiConfig
    ├── GUI/resources/  Colors/Styles + variantes Dark (SEULE copie des thèmes)
    └── GUI/pages/      SelectionPage.xaml, OpenArchiPanel.xaml
```

**La logique partagée va ici, pas dans un bouton.** Tout ce qui est dupliqué
entre deux outils appartient au socle.

## Serveur MCP (`vendor/mcp-server-for-revit`)

Miroir git subtree de
[mcp-servers-for-revit/mcp-server-for-revit-python](https://github.com/mcp-servers-for-revit/mcp-server-for-revit-python)
(MIT). Moitié « dans Revit » : routes pyRevit sur
`http://127.0.0.1:48884/revit_mcp`, démarrées par le `startup.py` racine.
Moitié « hors Revit » : `vendor/.../main.py` (FastMCP, `uv run`).

- **Ne JAMAIS éditer sous `vendor/`.** Toute la surcouche 418 vit ailleurs et
  s'enregistrera sur son propre `routes.API('418')` — sinon le prochain
  `git subtree pull` part en conflit.
- Mise à jour :
  `git subtree pull --prefix=vendor/mcp-server-for-revit <url> master --squash`

## Motifs importants

**MVVM** : `script.py` → `MainViewModel` → `MainWindowView` (hérite de
`BaseWindow`). Les services sont instanciés par le VM et **injectés** aux
couches basses — elles n'en créent jamais.

**UserConfig** : `lib/core/UserConfig.py`, unique implémentation. Persiste en
JSON dans `418.extension/data/<namespace>.json` (indépendant de
`pyrevit.userconfig`, qui ne persiste rien en mode admin). Clés insensibles à
la casse. BatchExport utilise le namespace `'batch_export'`, le chat
`'openarchi'`. Le VM crée UNE instance et l'injecte à tous les services.

**AppPaths** : ne jamais coder en dur un chemin vers un XAML ou une ressource.
`AppPaths().resources_dir()` / `.data_dir()`.

**Gardes d'import** : les imports inter-couches prennent la forme à deux
étages — `from core.X import Y` d'abord, `from lib.core.X import Y` en repli,
`None` en dernier. Ne JAMAIS utiliser d'import relatif profond
(`from ...core.X`) : selon la racine de package utilisée à l'import, il remonte
au-dessus de `lib` et retombe silencieusement sur `None`.

**Jamais de sous-dossier nommé `core/` ou `ui/` dans un bouton.** En import
relatif implicite (Python 2 / IronPython, pas d'`absolute_import` dans le
dépôt), un `core/` à côté d'un module fait résoudre ses `from core.X import Y`
vers `<package>/core/X` et masque le socle — le module meurt à l'import ou
retombe sur `None`. A déjà cassé BatchExport deux fois (`lib/core/`, puis
`lib/services/core/`). Garde-fou :
`tests/test_destination_service.py::TestPasDeMasquageDuSocle`.

**JSON sous IronPython** : toujours `json.dumps(..., ensure_ascii=False)` puis
encoder soi-même en UTF-8. Laisser json échapper les accents lève — invisible
en test CPython.

**Motifs de nommage** : `NamingService` résout les motifs à jetons
(`{numero}`, `{titre}`, `{param:NOM}`, `{param_projet:NOM}`) contre un élément
Revit. C'est la SEULE source de nommage — l'ancien système de `rows` et
`NamingResolver` ont été supprimés.

**Assainissement** : `lib/core/sanitize.py`, source unique. `sanitize()` pour
les noms de fichiers (max 180, retire `\/:*?"<>|` + espaces/points finaux,
`fallback` paramétrable) ; `sanitize_revit_name()` pour les noms d'éléments
Revit. `DestinationService.sanitize()` n'est qu'un passe-plat avec
`fallback='untitled'`.

**Destination** : `DestinationService` est la source unique (dossier, drapeaux
sous-dossiers/séparation formats, unicité). Utilisée par le VM ET par
`ExportOrchestrator`.

**Sélection de liste** : `SelectionPageVM` (socle, `lib/ui/base/`) — une seule
couche. Un outil appelle
`SelectionPageVM.depuis_descripteurs(descripteurs, ids, titre, est_identifiant=…)`
avec des triplets `(id, colonne_gauche, nom)`.

**Outils à rail** : les 4 outils de `Tools.panel` héritent de `RailWindow`
(socle) et ne déclarent que de la donnée — `ONGLETS`, `SUIVANTS`, `RUN`,
`RADIOS`. Contrat côté VM : `Mode` (chaîne) + `set_mode()` + un attribut par
onglet. La page Sélection est partagée
(`lib/ui/GUI/pages/SelectionPage.xaml`) ; un outil peut la surcharger en
déposant un `SelectionPage.xaml` dans son propre `GUI/Views/pages/`.

**Chargement WPF** : `UIResourceLoader` fusionne les dictionnaires de
ressources dans la fenêtre avant de charger le XAML. Toujours charger les
ressources avant une fenêtre qui les référence.
