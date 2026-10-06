# CLAUDE.md

Guide de Claude Code (claude.ai/code) sur ce dépôt.

## Ce que c'est

Une extension [pyRevit](https://github.com/eirannejad/pyRevit) pour Revit, qui
outille la **production de documents** : export PDF/DWG en lot, duplication et
renommage de feuilles et de vues, alignement d'éléments en vue, gestion des
matériaux, recadrage d'images, import SVG, audit de modèle.

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
Revit ; un test ne doit jamais toucher le réseau ni la maquette.

Tout passer en une fois :

```bash
for t in $(git ls-files '*/tests/test_*.py'); do python "$t" >/dev/null || echo "ECHEC $t"; done
```

## Branches

- **`main`** — ce qui est livré. Se rafraîchit par un `git merge Developpement`
  **ordinaire**, puis un tag `vX.Y.Z`. Son arbre est identique à celui de
  `Developpement` : il n'y a plus rien à retirer à la main.
- **`Developpement`** — l'intégration, où vivent tous les outils, finis ou non.
- **`feat/*`** — le travail en cours. Fusionnée dans `Developpement` quand elle
  aboutit, **puis supprimée** (sinon elles s'accumulent : il y en a eu 33).

Ce qui n'est pas prêt n'est pas retiré de `main` — c'est **masqué par un drapeau
bêta** (voir ci-dessous). C'est la seule chose qui sépare un outil livré d'un
outil en chantier.

Trois familles de tags, à ne pas mélanger : `v*` pour les versions livrées,
`jalon/*` pour les repères historiques, `archive/*` pour ancrer une branche
supprimée.

## Outils en chantier : le drapeau bêta

pyRevit ne **construit pas** un composant bêta tant que « Load Beta Tools » est
décoché dans ses réglages. Rien n'apparaît dans le ruban, le script n'est pas
chargé. Deux granularités :

| Portée | Où | Quoi |
|---|---|---|
| un panneau entier | `<Panneau>.panel/bundle.yaml` | `is_beta: true` |
| un bouton | `script.py` | `__beta__ = True` |

Aujourd'hui : **`Audit.panel`** (fonctionnel, pas stabilisé) et les trois
scaffolds **`Manage.panel/Manage{Filtre,Sheet,View}`** (ossature MVVM seule, la
fenêtre s'ouvre et ne fait rien).

Sortir un outil de bêta = retirer la ligne. Ne jamais recréer une branche
amputée pour cacher quelque chose.

## Arborescence

```
418.tab/
├── 418.panel/Infos.pushbutton/               ← modale « À propos »
├── Audit.panel/Audit.pushbutton/             ← santé du modèle (BÊTA)
├── Export.panel/BatchExport.pushbutton/      ← export PDF/DWG en lot (principal)
├── Manage.panel/
│   ├── Materiaux.pushbutton/                 ← voir, éditer, remplacer, renommer
│   └── Manage{Filtre,Sheet,View}.pushbutton/ ← scaffolds (BÊTA)
├── Tools.panel/
│   ├── ImageCrop.pushbutton/
│   ├── SvgImport.pushbutton/
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
│           rename_service
└── ui/
    ├── base/     BaseViewModel, BaseWindow, RailWindow,
    │             SelectionPageVM, SelectionItemVM, SheetPreviewGroupVM
    ├── helpers/  UIResourceLoader, RelayCommand, DarkMode, wpf_runtime
    └── GUI/
        ├── resources/  Colors/Styles + variantes Dark (SEULE copie des thèmes)
        │                et Icons.xaml (SEULE copie du jeu d'icônes)
        └── pages/      SelectionPage.xaml
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
la casse. Namespaces en service : `'batch_export'`, `'audit'`. Le VM crée UNE
instance et l'injecte à tous les services.

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
```

**Ne jamais dessiner une icône de ruban à la main** : ajouter sa géométrie à
`Icons.xaml`, puis régénérer. Ce n'est pas une étape de build — rien ne
l'appelle automatiquement.

Dette connue : **4 des 22 `icon.png` du ruban seulement sont rendues depuis
`Icons.xaml`** (Audit, et les 3 scaffolds de Manage). Les 18 autres sont du
Lucide elles aussi, mais exportées avant que `tools/icones.ps1` existe : aucune
clé ne les décrit, leur géométrie source est perdue. À rapatrier au fil de
l'eau — quand on touche à un bouton, ajouter sa clé et régénérer son PNG.

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

Un harnais LLM (clients de modèle interchangeables, panneau de chat ancrable,
pont MCP vers la maquette) est en cours sur `feat/mcp`. Rien n'en est fusionné
ici : ne pas le décrire comme acquis, ne pas s'appuyer dessus.
