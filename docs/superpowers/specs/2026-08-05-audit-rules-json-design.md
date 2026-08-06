# Design — Règles d'audit externalisées dans un fichier JSON

**Date** : 2026-08-05
**Branche** : `feat/Audit`
**Statut** : Validé — prêt pour plan d'implémentation
**Contexte** : refactor de la fonction d'audit (voir `2026-08-05-audit-dashboard-design.md`)

## Objectif

Externaliser toutes les règles d'audit réglables (aujourd'hui codées en dur dans `ScoreService`
et les 5 checkers) dans un unique fichier `audit_rules.json` **facile à éditer, versionnable, ou
exclu** (gitignore) pour livrer le plugin à une autre agence. Le plugin doit fonctionner **sans le
fichier** grâce à des défauts en dur.

## Décisions validées

1. **Périmètre** : toutes les règles réglables (poids/points du score, mots-clés de gravité des
   avertissements, regex de nommage vues/familles, regex des noms par défaut, gravités CAD/purge).
2. **Emplacement** : `418.tab/Audit.panel/Audit.pushbutton/audit_rules.json`, **suivi git** par
   défaut (règles PDA). Livré **complet**.
3. **Sémantique de chargement** : **remplacement strict par section** —
   - fichier **absent** ou **JSON malformé** → défauts en dur (avec `print` d'avertissement si
     malformé) ;
   - fichier **présent & valide** → pour chaque section de premier niveau : présente = utilisée
     telle quelle, absente = défaut en dur de cette section.

## Architecture

### Nouveau module `lib/config/AuditRules.py`

- Constante `DEFAULTS` (dict) = toutes les règles actuelles (extraites verbatim des constantes en
  dur d'aujourd'hui). C'est le fallback ultime.
- Résolution du chemin : `audit_rules.json` à la racine du pushbutton (calculé depuis
  `__file__` : `lib/config/` → `lib/` → pushbutton), sans chemin en dur.
- Classe `AuditRules` :
  - `__init__(self, chemin=None, data=None)` — si `data` fourni, l'utilise directement (tests) ;
    sinon charge le JSON depuis `chemin` (ou le chemin par défaut) ; en cas d'absence/malformé,
    retombe sur `DEFAULTS`. Fusion **par section** avec `DEFAULTS`.
  - Accesseurs typés (jamais d'accès brut au dict par les consommateurs) :
    - `score_poids()` → dict `{cle_theme: float}`
    - `score_points()` → dict `{'critique': int, 'a_revoir': int}`
    - `score_volume()` → dict `{'facteur': float, 'max': float}`
    - `mots_critiques()` → liste de str (minuscules)
    - `vue_regex()` / `famille_regex()` → str
    - `nom_defaut_regex()` → str
    - `cad_gravite_import()` / `cad_gravite_lien()` → `Severity`
    - `purge_gravite()` → `Severity`
  - **Mapping gravité** : les valeurs `"critique"`/`"a_revoir"`/`"ok"` (str, insensibles casse)
    sont mappées vers `Severity.CRITIQUE`/`A_REVOIR`/`OK` par un helper interne ; une valeur
    inconnue retombe sur le défaut de la section (log discret).
- `AuditRules.charger()` (fonction module) → singleton mémoïsé pour l'usage runtime ; les tests
  instancient `AuditRules(data=...)` directement.

### Schéma `audit_rules.json` (livré complet)

```json
{
  "version": 1,
  "score": {
    "poids_theme": { "warnings": 1.0, "cad": 1.0, "vues_feuilles": 1.0, "purge": 0.6, "nommage": 0.5 },
    "points_critique": 10,
    "points_a_revoir": 4,
    "volume_facteur": 0.05,
    "volume_max": 8
  },
  "avertissements": {
    "mots_critiques": ["dupliqu", "identical", "same place", "même endroit", "meme endroit", "même place"]
  },
  "nommage": {
    "vue_regex": "^[A-Z]{2,4}_\\d{2}_.+",
    "famille_regex": "^[A-Z]{2,4}_.+"
  },
  "vues_feuilles": {
    "nom_defaut_regex": "^(Niveau|Level|Quadrillage|Grid)\\s*\\d+$"
  },
  "cad": {
    "gravite_import_explose": "critique",
    "gravite_lien": "a_revoir"
  },
  "purge": {
    "gravite": "a_revoir"
  }
}
```

Un commentaire d'en-tête de schéma est ajouté au README (JSON ne supporte pas les commentaires
inline).

## Refactor des consommateurs

Chaque consommateur reçoit une instance `AuditRules` par **injection** (défaut = singleton), pour
la testabilité. Aucune constante métier ne reste en dur dans ces fichiers (les valeurs déménagent
dans `AuditRules.DEFAULTS`).

- **`ScoreService`** : `calculer(themes, rules=None)` et `penalite_theme(theme, rules=None)` lisent
  `rules.score_poids()/score_points()/score_volume()`. `rules=None` → `AuditRules.charger()`.
- **`AuditRunner`** : crée `self._rules = rules or AuditRules.charger()` dans `__init__`, le passe
  à `_default_checks()` (chaque checker reçoit `rules`) et à `ScoreService.calculer(themes, self._rules)`.
- **`BaseCheck`** : `__init__(self, rules=None)` stocke `self._rules = rules or AuditRules.charger()`.
- **`WarningsCheck`** : `gravite_pour(description, rules=None)` lit `rules.mots_critiques()`.
- **`NamingCheck`** : `_patterns()` lit `rules.vue_regex()/famille_regex()` ; **supprime** la
  surcharge `UserConfig('audit')` (remplacée par le JSON — source unique).
- **`ViewsSheetsCheck`** : le regex des noms par défaut vient de `rules.nom_defaut_regex()`
  (compilé à l'usage) ; `est_nom_par_defaut(nom, rules=None)`.
- **`CadImportsCheck`** : gravités depuis `rules.cad_gravite_import()/cad_gravite_lien()`.
- **`PurgeCheck`** : gravité depuis `rules.purge_gravite()`.

`report_dir` **reste** dans `UserConfig('audit')` (chemin par-utilisateur, pas une règle d'agence).

## Gestion des erreurs

- Fichier absent / JSON invalide / clé de section absente → défaut de section, jamais de crash
  (tout gardé en `try/except`, cohérent avec les conventions du projet).
- Valeur de gravité inconnue → défaut de section.
- `AuditRules` doit s'importer/s'instancier **hors Revit** sans lever (aucune dépendance Revit ;
  seule `Severity` est importée, en double-forme gardée).

## Tests (standalone, hors Revit)

- `test_audit_rules.py` :
  - `AuditRules(data={})` → tous les défauts.
  - section partielle (ex. `score` seul customisé) → cette section prise, les autres en défaut.
  - mapping gravité `"critique"`→`CRITIQUE`, `"a_revoir"`→`A_REVOIR`, valeur inconnue → défaut.
  - chemin inexistant → défauts, pas d'exception.
  - JSON malformé (via `data` invalide ou fichier temporaire) → défauts.
- `test_score_service.py` (étendu) : `calculer(themes, rules=AuditRules(data={"score": {...}}))`
  avec des poids custom → score différent et calculable.
- `test_warnings_check.py` / `test_naming_check.py` / `test_views_sheets_check.py` (étendus) :
  passer des règles injectées avec mots-clés / regex custom et vérifier le comportement.
- Non-régression : la suite existante reste verte (les défauts injectés == constantes d'avant).

## Contraintes (conventions projet)

- En-têtes `# -*- coding: utf-8 -*-` + `from __future__ import unicode_literals`.
- Imports inter-couches en `try/except` + fallback `None`.
- Français partout ; exécutable hors Revit.
- Le fichier `audit_rules.json` livré = valeurs identiques aux `DEFAULTS` (donc comportement
  inchangé tant que l'utilisateur n'édite pas).

## Hors périmètre (YAGNI)

- UI de configuration des règles (l'engrenage du rail reste inerte pour l'instant).
- Rechargement à chaud du JSON (chargé une fois par session).
- Validation de schéma stricte / messages d'erreur détaillés par clé.
- Externaliser des seuils qui n'existent pas encore (ex. poids par catégorie de purge).

## Critères de réussite

1. Sans `audit_rules.json`, l'audit se comporte exactement comme avant (défauts).
2. Éditer une valeur du JSON (ex. `points_critique`, un regex de nommage, un mot-clé critique)
   change le comportement au prochain lancement, sans toucher au code.
3. Une section absente du fichier retombe sur son défaut ; un JSON malformé retombe sur tous les
   défauts sans crasher.
4. Ajouter `audit_rules.json` au `.gitignore` (ou le supprimer) laisse le plugin fonctionnel sur
   les défauts.
5. La suite de tests standalone (existante + nouvelle) passe.
