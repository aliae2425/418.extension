# CLAUDE.md

Guide de Claude Code (claude.ai/code) sur ce dépôt.

## Ce que c'est

Une extension [pyRevit](https://github.com/eirannejad/pyRevit) pour Revit, qui
outille la **production de documents** : export PDF/DWG en lot, duplication et
renommage de feuilles et de vues, alignement d'éléments en vue, gestion des
matériaux, recadrage d'images, import SVG, audit de modèle.

S'y greffe, **en bêta**, un harnais LLM (`lib/web/`, `lib/harnais/`,
`lib/rvt/`) : la plomberie qui laisse un modèle travailler sur la maquette. Il
dépend des outils déterministes, jamais l'inverse — voir « Le harnais » plus
bas.

La ligne directrice : **ce qu'un architecte refait dix fois par semaine doit
tenir en un clic, et être reproductible**. Un export doit donner deux fois le
même résultat ; un renommage doit se relire avant d'être appliqué. D'où l'aperçu
systématique avant validation, et le refus des raccourcis qui marchent « la
plupart du temps ».

Tout le texte d'interface, les commentaires et les messages de commit sont en
**français**.

- **Revit minimum** : 2026
- **Python** : compatible 2/3 (`from __future__ import unicode_literals` en
  tête, en-tête `# -*- coding: utf-8 -*-`). Revit exécute du **IronPython 2.7** ;
  les tests tournent en CPython 3. Ce grand écart est la source de la moitié des
  pièges listés plus bas.

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

**Tests Python** : scripts `unittest` nus sous les `tests/` de chaque bouton,
plus `lib/core/tests/`, `lib/harnais/tests/`, `lib/rvt/tests/`, `lib/ui/tests/`.
Ils amorcent leur `sys.path` eux-mêmes — `python tests/test_x.py` suffit.
Aucun runner, aucun framework, aucune fixture. Les imports Revit sont sous
`try/except` pour que la logique pure tourne hors Revit ; un test ne doit
jamais toucher le réseau, la maquette, ni lancer un CLI (injecter un double).

**Tests JS** (`lib/web/`) : `node:test`, intégré depuis Node 18 — même
doctrine, aucun runner, aucune dépendance. Fichiers `*.test.js` à côté du
code qu'ils éprouvent.

Tout passer en une fois :

```bash
for t in $(git ls-files '*/tests/test_*.py'); do python "$t" >/dev/null || echo "ECHEC $t"; done
node --test "lib/web/**/tests/*.test.js"
```

**Le motif entre guillemets n'est pas une coquetterie** : passer un dossier à
`node --test` le fait charger comme un module et échouer en
`MODULE_NOT_FOUND`. C'est le glob qui déclenche la découverte.

`lib/web/package.json` ne déclare **que** `"type": "module"` — sans lui, Node
lit les `.js` en CommonJS et refuse les `import`. **Ce n'est pas un manifeste
de dépendances : rien ne s'installe ici, jamais.** Le navigateur l'ignore.

## Branches

- **`main`** — ce qui est livré. **Avance en fast-forward, jamais par merge** :

  ```bash
  git checkout main && git merge --ff-only Developpement
  git tag -a vX.Y.Z -m "…" && git push origin main --tags
  ```

  `--ff-only` n'est pas une coquetterie : il échoue bruyamment si `main` a
  pris un commit propre, ce qui est exactement ce qu'on veut interdire. Un
  seul commit sur `main` et les deux branches divergent pour toujours, chaque
  release ajoutant alors un commit de merge vide — l'échelle qu'on a mis neuf
  mois à produire et qu'on a remise à plat le 2026-10-06.

  Un correctif urgent se fait donc sur une branche issue du tag, puis remonte
  dans `Developpement` ; jamais directement sur `main`.
- **`Developpement`** — l'intégration, où vivent tous les outils, finis ou non.
- **`feat/*`** — le travail en cours. Fusionnée dans `Developpement` quand elle
  aboutit, **puis supprimée** (sinon elles s'accumulent : il y en a eu 33).

Ce qui n'est pas prêt n'est pas retiré de `main` — c'est **masqué par un drapeau
bêta** (voir ci-dessous). C'est la seule chose qui sépare un outil livré d'un
outil en chantier.

Trois familles de tags, à ne pas mélanger : `v*` pour les versions livrées,
`jalon/*` pour les repères historiques, `archive/*` pour ancrer une branche
supprimée ou un état d'avant réécriture.

**Les `v*` sont la seule trace des versions livrées.** Les états antérieurs à
la 2.9 ont été produits par l'ancien procédé (instantané de `Developpement`
amputé d'`Audit.panel`) : leurs tags `v2.5.0` à `v2.8.0` pointent donc hors du
tronc. C'est normal et ça ne se corrige pas — à partir de la prochaine release,
le tag est sur `main`.

**Lire l'historique.** Le graphe brut est large (jusqu'à 10 rails en
juillet 2026) parce qu'il porte neuf mois de branches de travail. Ne pas
chercher à l'aplatir : c'est la *vue* qu'il faut changer, pas la donnée.

```bash
git log --first-parent --graph --oneline    # le tronc seul : 188 entrees, une ligne droite
```

Deux alias locaux le font (`git config alias.*`, non versionnés, à reposer sur
un nouveau clone) :

| alias | ce qu'il montre |
|---|---|
| `git tronc` | le tronc seul — une entrée par intégration, zéro rail |
| `git releases` | les versions livrées, date et intitulé |

`--first-parent` ne cache rien : les commits des branches restent accessibles,
ils ne polluent simplement plus la lecture du tronc.

## Outils en chantier : le drapeau bêta

pyRevit ne **construit pas** un composant bêta tant que « Load Beta Tools » est
décoché dans ses réglages. Rien n'apparaît dans le ruban, le script n'est pas
chargé. Deux granularités :

| Portée | Où | Quoi |
|---|---|---|
| un panneau entier | `<Panneau>.panel/bundle.yaml` | `is_beta: true` |
| un bouton | `script.py` | `__beta__ = True` |

Aujourd'hui :

- **`Audit.panel`** — fonctionnel, pas stabilisé ;
- **`Manage.panel/Manage{Filtre,Sheet,View}`** — scaffolds (ossature MVVM
  seule, la fenêtre s'ouvre et ne fait rien) ;
- **`OpenArchi.panel`** — le harnais LLM ;
- **`Tools.panel/RampeParking.pushbutton`** — lecture des contraintes de rampe.

Sortir un outil de bêta = retirer la ligne. Ne jamais recréer une branche
amputée pour cacher quelque chose.

**Le drapeau ne couvre que le ruban.** `startup.py` est exécuté par pyRevit au
lancement, bêta ou non : tout ce qui n'est pas prêt y est gardé derrière
`user_config.load_beta` à la main — **la propriété, jamais
`user_config.core.load_beta`**. La seconde forme tombe sur
`configparser.__getattr__` et LÈVE quand la case n'a jamais été touchée : la
clé du fichier s'appelle `loadbeta`, sans underscore. La propriété, elle,
passe par `get_option(..., default_value=)` et rend `False`. L'erreur a coûté
les deux volets ancrables, en silence. C'est le cas du volet OpenArchi.

## Le harnais

**Le moteur tourne dans la page, pas dans Python.** Le volet OpenArchi héberge
un WebView2 qui sert `lib/web/` sur l'origine locale `https://418.local/`.
Toute la logique de conversation — boucle d'outils, permissions, protocole des
fournisseurs — est en JavaScript. Python n'est plus qu'un **hôte** : il monte
le contrôle, dit quel thème Revit affiche, et fait les trois choses qu'une
page ne peut pas faire.

```
lib/web/              servi au WebView2, UNE seule origine
├── vue/                l'interface : app · rendu · markdown · filet · css
└── harnais/            le moteur : protocole · permissions · boucle
    └── fournisseurs/   openai (clé) · chatgpt (abonnement)
lib/harnais/          le Python qui reste : outils · secrets · oauth
lib/rvt/              57 outils Revit + 3 routes
```

`vue/` ne dépend jamais de `harnais/`, et l'inverse non plus : ils se parlent
par **évènements**. C'est la règle de dépendance d'opencode, et elle se
vérifie à l'import.

**Ce que Python garde, et rien de plus :**

| | pourquoi |
|---|---|
| exécuter un outil | l'API Revit n'est joignable que depuis son fil — c'est le serveur de routes pyRevit qui marshale |
| tenir les secrets | clé et jetons dans `%LOCALAPPDATA%\418.extension\`, jamais dans `data/` qui finit poussé |
| écouter une socket | le navigateur revient sur `localhost:1455` après l'OAuth |
| sortir vers ChatGPT | `chatgpt.com/backend-api` ne renvoie aucun `Allow-Origin` — mesuré |

### Le protocole : des parts, pas des chaînes

La leçon d'opencode qu'on retient. **Un message n'est pas une chaîne** : il est
une suite de parts typées (`texte`, `raisonnement`, `outil`, `etape`, `erreur`)
et un évènement porte une part, pas un message. Sans ça, pas de rendu
incrémental — on ne peint pas au fil de l'eau ce qu'on ne reçoit qu'entier.

Trois évènements suffisent : `part.neuve`, `part.delta`, `part.maj`, plus
`tour.fini`. **Un delta porte le MORCEAU, jamais le cumul** — c'est la
différence entre un flux et un diaporama.

### Les permissions

Transcrites d'opencode (`core/src/policy.ts`, MIT, cf. `vendor/opencode-LICENSE`) :
des règles `{motif, effet}`, effet ∈ `autoriser` / `demander` / `refuser`, et
**la dernière qui correspond gagne**. Un défaut large en tête, chaque exception
poussée à la fin sans réordonner ce qui précède.

Réponses `une_fois` / `toujours` / `jamais`. `une_fois` ne retient **rien** :
c'est ce qui distingue « vas-y » de « vas-y et ne me redemande plus ». Toute
réponse inconnue vaut refus — le silence ne vaut pas accord.

**Le garde-fou est côté serveur, pas côté client.** `lib/rvt` exige un jeton de
session sur les 4 outils `irreversible` : le serveur de routes pyRevit écoute
sur `0.0.0.0` et n'authentifie rien, donc un garde-fou qu'on contourne en ne
passant pas par le client n'en est pas un.

### Ajouter un fournisseur

Un module de `lib/web/harnais/fournisseurs/` qui rend une fonction honorant :

```js
modele(messages, catalogue, { signal, surTexte, surRaisonnement })
    → { texte, appels: [{ id, nom, arguments }] }
```

La boucle ne sait pas à qui elle parle. **Le protocole appartient au
fournisseur** : `/v1/chat/completions` imbrique les outils sous `function`, le
backend Responses les pose à plat, et aucune abstraction ne rendra ces deux-là
identiques sans mentir.

**Les secrets n'entrent jamais dans la page.** Pour une clé API, `fetch` envoie
une sentinelle `Bearer 418-hote` que l'hôte remplace par `WebResourceRequested`
— pas un en-tête ajouté de rien, sinon le préflight CORS ne l'annoncerait pas.
Pour l'abonnement, l'égress entier passe par Python.

**Pas de catalogue de modèles en dur** : il vieillirait sans que rien ne le
signale. `/model <nom>` suffit, et un nom refusé revient en clair dans l'erreur
de l'API.

### Zone grise assumée

L'abonnement ChatGPT emprunte le `client_id` public du CLI Codex, comme
opencode. On ne se fait pas passer pour lui : `originator` dit `418`, là où
l'ancien code disait `codex_cli_rs`. OpenAI peut fermer ça sans préavis — le
repli est `/connect <clé>`. **Claude Pro/Max est exclu** : Anthropic l'interdit
explicitement, et opencode l'a retiré pour cette raison.

### Ce qui n'est pas branché — à ne pas décrire comme acquis

- `lib/rvt` compte **57 outils dont 56 n'ont jamais tourné dans Revit**
  (`lib/rvt/COUVERTURE.md`). C'est le risque n°1 du produit.
- pas de session persistée : un rechargement de la page perd la conversation ;
- pas de pièces jointes — l'ancien volet en avait, le nouveau pas encore ;
- les `#références` n'existent plus du tout.

### Journal

`lib/core/journal.py` écrit dans `data/418.log`. Un volet ancré n'a aucune
fenêtre de sortie pyRevit : un `print` s'y perd, et Revit avale les exceptions
de construction d'un volet. **Côté web, DevTools (F12) est bien plus utile** —
console, réseau, inspecteur.

### Le cycle de développement du volet

| tu modifies | il faut |
|---|---|
| `lib/web/**` | **F5 dans le volet** — les fichiers sont servis depuis le disque |
| un `import`/`export` JS | **Ctrl+Shift+R** — Chromium garde les modules en cache mémoire |
| `lib/harnais/*.py`, `lib/ui/OpenArchiPanel.py` | **redémarrer Revit** |

Le dernier point surprend : `register_dockable_panel` construit **une
instance** que Revit garde pour la session. Un Reload pyRevit rejoue
`startup.py`, qui répond « déjà enregistré » — l'objet vivant garde les
modules importés à sa construction.

## Arborescence

```
418.tab/
├── 418.panel/Infos.pushbutton/               ← modale « À propos »
├── Audit.panel/Audit.pushbutton/             ← santé du modèle (BÊTA)
├── Export.panel/BatchExport.pushbutton/      ← export PDF/DWG en lot (principal)
├── Manage.panel/
│   ├── Materiaux.pushbutton/                 ← voir, éditer, remplacer, renommer
│   └── Manage{Filtre,Sheet,View}.pushbutton/ ← scaffolds (BÊTA)
├── OpenArchi.panel/Chat.pushbutton/          ← ouvre le panneau de chat (BÊTA)
├── Tools.panel/
│   ├── ImageCrop.pushbutton/
│   ├── SvgImport.pushbutton/
│   ├── RampeParking.pushbutton/              ← contraintes NF P91-100 (BÊTA)
│   └── col1.stack/
│       ├── duplicate_sheets.pushbutton/
│       ├── views_duplicate.pushbutton/
│       └── Rename.pulldown/{FindReplace_Sheets, FindReplace - Views}.pushbutton/
└── Align.panel/col{1,2,3}.stack/             ← 8 boutons aligner/centrer/répartir
```

Chaque bouton est autonome : `script.py` en point d'entrée, `GUI/` pour le
XAML, `lib/` pour la logique découpée `services/` (métier) · `viewmodels/` ·
`views/` · `models/`.

L'ordre des panneaux dans le ruban est fixé par `418.tab/bundle.yaml` — **un
composant absent de `layout:` n'est pas construit** (`genericcomps.py:368`).

## Socle partagé (`lib/` à la racine)

pyRevit le met sur `sys.path` : il s'importe en `core.X` / `ui.X` depuis
n'importe quel bouton.

```
lib/
├── core/      le socle de TOUS les outils — AppPaths, UserConfig, sanitize,
│              transaction, selection, align, bulk_edit, list_selection,
│              text_filter, token_expander, rename_service, journal, routes418
│              ⚠ 15 boutons font `from core.X import Y`. Le renommer casse
│                BatchExport, Matériaux, Align. Intouchable.
├── harnais/   le Python du harnais — outils (pont vers lib/rvt), secrets, oauth
├── rvt/       les 57 outils Revit + les 3 routes `/418/`
├── web/       tout le JS, servi au WebView2 (voir « Le harnais »)
└── ui/        WPF seulement
    ├── base/     BaseViewModel, BaseWindow, RailWindow,
    │             SelectionPageVM, SelectionItemVM, SheetPreviewGroupVM
    ├── helpers/  UIResourceLoader, RelayCommand, DarkMode, wpf_runtime
    ├── OpenArchiPanel   l'hôte du WebView2, et rien d'autre
    └── GUI/
        ├── resources/  Colors/Styles + variantes Dark (SEULE copie des thèmes)
        │                et Icons.xaml (SEULE copie du jeu d'icônes)
        └── pages/      SelectionPage.xaml, OpenArchiPanel.xaml
```

**Une exception au « SEULE copie »**, et elle est isolée pour être générable :
`lib/web/vue/tokens.css` reprend les couleurs de `Colors.xaml` à la main, et
`lib/web/vue/logo*.png` recopie la théière d'Infos. Le CSS ne peut pas lire du
XAML, et le WebView2 ne sert que `lib/web/`. Marqué `ponytail:` sur place.

**La logique partagée va ici, pas dans un bouton.** Tout ce qui est dupliqué
entre deux outils appartient au socle.

## Motifs importants

**MVVM** : `script.py` → `MainViewModel` → `MainWindowView` (hérite de
`BaseWindow`). Les services sont instanciés par le VM et **injectés** aux
couches basses — elles n'en créent jamais.

**UserConfig** : `lib/core/UserConfig.py`, unique implémentation. Persiste en
JSON dans `418.extension/data/<namespace>.json` (indépendant de
`pyrevit.userconfig`, qui ne persiste rien en mode admin). Clés insensibles à
la casse. Namespaces en service : `'batch_export'`, `'audit'`, `'openarchi'`.
Le VM crée UNE instance et l'injecte à tous les services.

**`UserConfig` est un magasin de chaînes** : il sérialise `None` en `"None"`,
qui repasserait ensuite pour une valeur légitime. Écrire `''` pour « pas de
choix », jamais `None`.

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
encoder soi-même en UTF-8. Laisser json échapper les accents lève sous
IronPython 2.7 — et reste **invisible en test CPython**, donc aucun test ne
vous préviendra.

**Motifs de nommage** : `NamingService` résout les motifs à jetons
(`{numero}`, `{nom}`, `{titre}`, `{date}`, `{projet_*}`, `{param:NOM}`,
`{param_projet:NOM}`) contre un élément Revit. C'est la SEULE source de
nommage — l'ancien système de `rows` et `NamingResolver` ont été supprimés. Un
jeton vide ou introuvable disparaît du nom : jamais de `{...}` brut en sortie.

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

**Outils à rail** : les 4 outils de `Tools.panel` et Matériaux héritent de
`RailWindow` (socle) et ne déclarent que de la donnée — `ONGLETS`, `SUIVANTS`,
`RUN`, `RADIOS`. Contrat côté VM : `Mode` (chaîne) + `set_mode()` + un attribut
par onglet. La page Sélection est partagée
(`lib/ui/GUI/pages/SelectionPage.xaml`) ; un outil peut la surcharger en
déposant un `SelectionPage.xaml` dans son propre `GUI/Views/pages/`.

**Chargement WPF** : `UIResourceLoader` fusionne les dictionnaires de
ressources dans la fenêtre avant de charger le XAML. Toujours charger les
ressources avant une fenêtre qui les référence.

**Icônes** : toute icône de l'extension vient de
[Lucide](https://lucide.dev), et de Lucide seul — fenêtres comme ruban. Pas de
dessin maison, pas de second jeu. S'il n'existe pas de Lucide pour l'idée,
prendre un voisin : la cohérence prime sur l'exactitude.

`lib/ui/GUI/resources/Icons.xaml` est la SEULE copie du jeu, clés nommées par
le RÔLE et non par le nom Lucide — c'est ce qui donne le même dessin au même
onglet dans tous les outils. Les `icon.png` / `icon.dark.png` du ruban en sont
un **rendu jetable** :

```powershell
.\tools\icones.ps1 -Lister
.\tools\icones.ps1 -Cle IconAudit -Destination "418.tab\Audit.panel\Audit.pushbutton"
.\tools\icones.ps1 -Verifier
```

**Ne jamais dessiner une icône de ruban à la main** : ajouter sa géométrie à
`Icons.xaml`, puis régénérer. Ce n'est pas une étape de build — rien ne
l'appelle automatiquement.

`-Verifier` rend chaque clé et compare les empreintes aux `icon.png` du ruban :
il sort en erreur dès qu'une icône n'est reproductible par aucune clé. **Le
lancer après tout ajout d'icône** — c'est faute de ce contrôle que 18 boutons
avaient dérivé hors du pipeline.

Une seule exception, déclarée dans `tools/icones.ps1` : la **théière** d'Infos
est le logo du dépôt (HTTP 418, « I'm a teapot ») et n'existe pas chez Lucide.
Elle ne se régénère pas.

**Alignement** : `lib/core/align.py` sépare le calcul pur (`deltas_alignement`,
`deltas_distribution`, sur des scalaires projetés) de la glu Revit
(`executer()`). Les éléments **épinglés servent de référence** : ils ne bougent
pas, les autres s'y calent ; si tout est épinglé, l'outil le dit et ne touche à
rien.

## Vocabulaire

`CONTEXT.md` est le glossaire métier — uniquement des définitions, aucune
décision d'implémentation. S'y tenir dans le code comme dans l'interface.
Attention : il décrit le repérage des coupes, une fonctionnalité qui vit
aujourd'hui sur `test/reperage-coupes` et n'est pas encore dans cette branche.

## Hors de cette branche

Le repérage des coupes vit sur `test/reperage-coupes` : décrit dans
`CONTEXT.md`, absent du code ici. Ne pas s'appuyer dessus.
