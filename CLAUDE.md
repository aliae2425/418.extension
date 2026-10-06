# CLAUDE.md

Guide de Claude Code (claude.ai/code) sur ce dépôt.

## Ce que c'est

Une extension [pyRevit](https://github.com/eirannejad/pyRevit) pour Revit, qui
outille la **production de documents** : export PDF/DWG en lot, duplication et
renommage de feuilles et de vues, alignement d'éléments en vue, gestion des
matériaux, recadrage d'images, import SVG, audit de modèle.

S'y greffe, **en bêta**, un harnais LLM (`lib/core/chat_*`, `lib/ui/OpenArchi*`,
`vendor/`) : la plomberie qui laisse un modèle travailler sur la maquette. Il
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

**Tests** : scripts `unittest` nus sous les `tests/` de chaque bouton, plus
`lib/core/tests/` et `lib/ui/tests/`. Ils amorcent leur `sys.path` eux-mêmes —
`python tests/test_x.py` suffit. Aucun runner, aucun framework, aucune fixture.
Les imports Revit sont sous `try/except` pour que la logique pure tourne hors
Revit ; un test ne doit jamais toucher le réseau, la maquette, ni lancer un CLI
(injecter un double, cf. `_ClientFactice`).

Tout passer en une fois :

```bash
for t in $(git ls-files '*/tests/test_*.py'); do python "$t" >/dev/null || echo "ECHEC $t"; done
```

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
`user_config.core.load_beta` à la main. C'est le cas du panneau ancrable
OpenArchi et du serveur MCP.

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

## Serveur MCP (`vendor/mcp-server-for-revit`)

Miroir git subtree de
[mcp-servers-for-revit/mcp-server-for-revit-python](https://github.com/mcp-servers-for-revit/mcp-server-for-revit-python)
(MIT). Moitié « dans Revit » : routes pyRevit sur
`http://127.0.0.1:48884/revit_mcp`, démarrées par le `startup.py` racine.
Moitié « hors Revit » : `vendor/.../main.py` (FastMCP, `uv run`).

- **Ne JAMAIS éditer sous `vendor/`.** Toute la surcouche 418 vit ailleurs et
  s'enregistre sur son propre `routes.API('418')` (`lib/core/api418.py`) —
  sinon le prochain `git subtree pull` part en conflit.
- Mise à jour :
  `git subtree pull --prefix=vendor/mcp-server-for-revit <url> master --squash`

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
├── core/   AppPaths, UserConfig, sanitize, transaction, selection, align,
│           bulk_edit, list_selection, text_filter, token_expander,
│           rename_service, et pour le harnais : chat_syntaxe, chat_cli,
│           chat_openai, chat_oauth, prompt, journal, api418, routes418,
│           revit_outils, markdown_simple, attente
└── ui/
    ├── base/     BaseViewModel, BaseWindow, RailWindow,
    │             SelectionPageVM, SelectionItemVM, SheetPreviewGroupVM
    ├── helpers/  UIResourceLoader, RelayCommand, DarkMode, wpf_runtime,
    │             FlowMarkdown
    ├── OpenArchiPanel · OpenArchiChatVM · OpenArchiConfig
    └── GUI/
        ├── resources/  Colors/Styles + variantes Dark (SEULE copie des thèmes)
        │                et Icons.xaml (SEULE copie du jeu d'icônes)
        └── pages/      SelectionPage.xaml, OpenArchiPanel.xaml
```

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
