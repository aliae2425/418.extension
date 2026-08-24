# `audit_rules.json` — règles d'audit

Ce fichier définit les règles de l'audit de maquette. Il est **édité à la main** et
**versionnable**. Le plugin fonctionne **sans ce fichier** : s'il est absent (ou invalide),
l'audit retombe sur ses défauts internes.

**Aucun `audit_rules.json` n'est livré.** Les défauts internes
(`lib/config/AuditRules.py`, dict `DEFAULTS`) sont la référence : ils étaient auparavant
recopiés à l'identique dans un fichier livré, ce qui imposait de maintenir les mêmes
valeurs à deux endroits.

## Personnaliser les règles

Créer `audit_rules.json` à la racine du pushbutton (à côté de `script.py`) et n'y mettre
que les sections à surcharger — voir le schéma ci-dessous. Pour partager ses règles avec
une autre agence, il suffit de versionner ce fichier.

## Sémantique de chargement

**Remplacement strict par section.** Une section présente dans le fichier est utilisée telle
quelle ; une section absente retombe sur son défaut interne. Une clé absente à l'intérieur d'une
section présente retombe aussi sur son défaut (un oubli ne casse jamais une règle). Un JSON
malformé → tous les défauts, sans planter.

## Schéma

| Section | Clé | Type | Rôle |
|---|---|---|---|
| `score` | `poids_theme` | objet `{theme: nombre}` | Poids de chaque thème dans le score. Thèmes : `warnings`, `cad`, `vues_feuilles`, `purge`, `nommage`. |
| `score` | `points_critique` | entier | Pénalité de base d'un thème contenant au moins un problème **critique**. |
| `score` | `points_a_revoir` | entier | Pénalité de base d'un thème contenant au moins un problème **à revoir**. |
| `score` | `volume_facteur` | nombre | Pénalité additionnelle par problème (× nombre de problèmes du thème). |
| `score` | `volume_max` | nombre | Plafond de la pénalité de volume par thème. |
| `avertissements` | `mots_critiques` | liste de textes | Un avertissement Revit dont la description contient un de ces mots (insensible à la casse) est classé **critique** ; sinon **à revoir**. |
| `nommage` | `vue_regex` | regex | Une vue dont le nom ne correspond PAS est signalée. |
| `nommage` | `famille_regex` | regex | Une famille dont le nom ne correspond PAS est signalée. |
| `vues_feuilles` | `nom_defaut_regex` | regex | Un nom de vue qui correspond est signalé comme « nom par défaut ». |
| `cad` | `gravite_import_explose` | `critique`\|`a_revoir`\|`ok` | Gravité d'un import CAD explosé (non lié). |
| `cad` | `gravite_lien` | `critique`\|`a_revoir`\|`ok` | Gravité d'un lien CAD. |
| `purge` | `gravite` | `critique`\|`a_revoir`\|`ok` | Gravité des éléments purgeables. |

## Score — formule

```
base(theme)    = points_critique  si le thème a un problème critique
               = points_a_revoir  s'il a un problème à revoir (sans critique)
               = 0                 sinon
volume(theme)  = min(volume_max, volume_facteur × nombre_de_problèmes)
pénalité(theme)= poids_theme[theme] × base(theme) + volume(theme)
score          = arrondi( max(0, 100 − Σ pénalités des thèmes disponibles) )
```

## Notes

- Les regex utilisent la syntaxe Python. Dans le JSON, échappe les antislashs : `\\d`, `\\s`.
- Une gravité inconnue (texte hors `critique`/`a_revoir`/`ok`) retombe sur le défaut de la règle.
- Le fichier est chargé une fois par session (relance le bouton après édition).
