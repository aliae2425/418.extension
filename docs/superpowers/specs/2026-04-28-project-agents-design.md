# Design — Agents Projet 418.extension

**Date :** 2026-04-28  
**Auteur :** n.carmi@pda.archi  
**Statut :** Approuvé

---

## Contexte

Le projet 418.extension est une extension pyRevit Python qui expose trois domaines techniques bien séparés : l'interface WPF/XAML, la logique métier Revit (services et data stores), et la testabilité hors Revit (modules purs exploitables via `python script.py` grâce aux import guards `try/except`).

L'objectif est de définir trois agents Claude Code spécialisés (`.claude/agents/*.md`) pour que chaque conversation reste dans son domaine, avec les conventions du projet directement encodées dans les prompts.

---

## Architecture des agents

### Approche retenue

**Option A — Agents légers, prompts courts** : prompts ciblés avec les conventions critiques du projet, outils non restreints (Read/Edit/Write/Bash/Grep/Glob disponibles pour tous), règle de frontière pour les `*SectionController` explicitement encodée.

Pas de `model:` ni `tools:` spécifiés dans les frontmatters — héritage du contexte courant.

---

## Structure des fichiers

```
.claude/
├── settings.json          (existant)
└── agents/
    ├── 418-ui.md
    ├── 418-logic.md
    └── 418-testing.md
```

---

## Spécification de chaque agent

---

### `418-ui.md`

**Domaine** : tout ce qui concerne l'interface WPF/XAML du projet.

**Déclencheurs** : création ou modification de fichiers XAML, composants visuels, binding WPF, thème clair/sombre, fenêtres modales, section controllers (côté binding uniquement).

**Connaissances encodées dans le prompt** :
- Structure `GUI/` : `Views/` (fenêtres racines), `Controls/` (1 XAML par Component), `Modals/`, `resources/`
- Pattern de chargement : `UIResourceLoader` fusionne les ressources avant tout LoadXaml — toujours dans cet ordre
- `AppPaths` pour résoudre les chemins XAML — jamais de chemins hardcodés
- Thèmes : les styles light/dark sont des paires (`Colors.xaml` / `ColorsDark.xaml`, `Styles.xaml` / `StylesDark.xaml`) — modifier l'un implique vérifier l'autre
- Chaque classe `ui/components/` est le pendant exact d'un `Controls/*.xaml`
- Règle sections : responsabilité limitée au câblage XAML + bindings WPF (pas d'orchestration de services)

---

### `418-logic.md`

**Domaine** : logique métier, Revit API, services d'export, data stores, configuration utilisateur.

**Déclencheurs** : modifications dans `lib/core/`, `lib/data/`, `lib/services/`, appels Revit API, orchestration d'export, résolution de nommage, gestion de destination.

**Connaissances encodées dans le prompt** :
- Couches sans dépendance UI : `core/ → data/ → services/` — jamais d'import UI dans ces couches
- `UserConfig(namespace='batch_export')` pour toute persistance — clés en string plain (ex: `'PathDossier'`, `'create_subfolders'`)
- Pattern import guard obligatoire : `try/except` + fallback `None`, vérifier `if x is not None` avant tout usage
- `NamingResolver` : pattern = liste de dicts `{"Name", "Prefix", "Suffix"}`, résout contre élément Revit ou valeurs système (dates)
- `DestinationStore.sanitize()` : méthode canonique pour noms de fichiers Windows (max 180 chars, supprime `\/:*?"<>|`)
- Règle sections : responsabilité limitée à l'orchestration des appels services/data (pas de binding WPF)

---

### `418-testing.md`

**Domaine** : écriture de scripts Python standalone testables hors Revit.

**Déclencheurs** : demande de tests, couverture de logique pure, vérification de comportements de sanitization/nommage/sérialisation.

**Connaissances encodées dans le prompt** :
- Tous les modules dégradent proprement sans Revit grâce aux import guards `try/except` → exécutable avec `python script.py`
- Cibles prioritaires : `NamingResolver` (logique pure), `DestinationStore.sanitize()` et `unique_path()`, `NamingPatternStore` (sérialisation JSON)
- Structure des scripts : fichiers autonomes dans `tests/` à la racine du pushbutton concerné
- Pas de framework externe — stdlib uniquement (`unittest` ou scripts simples avec `assert`)
- Lancement : `python <script>` depuis `BatchExport.pushbutton/`

---

## Règle de frontière partagée

Les fichiers `ui/windows/sections/*SectionController.py` sont à cheval entre les deux domaines :

| Agent | Responsabilité dans les sections |
|---|---|
| `418-ui` | Structure XAML + data bindings WPF |
| `418-logic` | Orchestration des appels aux services et data stores |

Les deux agents peuvent modifier un même fichier de section selon le contexte.

---

## Critères de succès

- Les trois fichiers `.claude/agents/*.md` sont créés et reconnus par Claude Code
- Chaque agent, invoqué par `@418-ui`, `@418-logic` ou `@418-testing`, applique les conventions du projet sans avoir besoin de relire CLAUDE.md
- L'agent testing produit des scripts exécutables avec `python script.py` qui passent sans Revit installé
