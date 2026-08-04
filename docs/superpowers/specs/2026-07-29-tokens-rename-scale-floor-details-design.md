# Design — Nouveaux tokens de nommage `{i}` `{scale}` `{floor}` `{details}` + tooltip d'aide

Date : 2026-07-29
Statut : validé (design), en attente de plan d'implémentation

## Contexte

Le projet possède deux familles d'outils partageant le même moteur de nommage
(`RenameService` + `TokenExpander`) :

1. **Outils de duplication** — `views_duplicate.pushbutton`, `duplicate_sheets.pushbutton`.
2. **Outils FindReplace / Rename** — `Rename.pulldown/FindReplace - Views.pushbutton`,
   `Rename.pulldown/FindReplace_Sheets.pushbutton`.

Les tokens actuels résolus par `TokenExpander.expand(template, index=1, context=None)` :
`{date}`, `{annee}`, `{mois}`, `{jour}`, `{n}` (intégrés) + tout `{clé}` fourni via
`context` (ex. `{type}` dans `views_duplicate`).

On veut ajouter quatre tokens et documenter les tokens disponibles dans un tooltip
accessible via une icône « ⓘ » au-dessus du champ **Remplacer**.

## Objectif

- `{i}` : compteur global **indépendant**, continu sur tout le run (1, 2, 3…),
  ajouté aux **4 outils**. `{n}` est **conservé** partout (pas de suppression).
- `{scale}` : échelle de la vue au format `"1." + dénominateur` (ex. vue 1:100 → `1.100`).
- `{floor}` : niveau associé à la vue.
- `{details}` : numéro de détail (viewport) de la vue.
- Tokens vue (`{scale}`, `{floor}`, `{details}`) : **outils vues uniquement**.
- Tooltip d'aide « ⓘ » sur le champ Remplacer : **ajout** dans les 2 outils de
  duplication, **mise à jour** dans les 2 outils FindReplace (qui l'ont déjà).

## Sémantique des tokens

| Token | Valeur | Chaîne vide si |
|-------|--------|----------------|
| `{i}` | Compteur global continu, incrémenté une fois par **élément produit** sur tout le run | jamais |
| `{scale}` | `"1." + str(view.Scale)` (Revit donne le dénominateur) | `view.Scale <= 0` ou non applicable |
| `{floor}` | `view.GenLevel.Name` (niveau associé) | vue sans niveau (coupe, 3D, légende, nomenclature, drafting…) |
| `{details}` | N° de détail du viewport de la vue source (`BuiltInParameter.VIEWPORT_DETAIL_NUMBER`) | vue non posée sur une feuille / paramètre vide |

Règle générale : **toute valeur indisponible se résout en chaîne vide** (`""`),
jamais une exception ni un token littéral résiduel.

`{n}` et `{i}` peuvent différer :
- `views_duplicate` : `{n}` = index de la copie **dans une vue source** (1..count) ;
  `{i}` = compteur continu, toutes vues sources et copies confondues.
- `duplicate_sheets` : `{n}` reste tel quel (vaut `1`, aucun index n'est passé aujourd'hui) ;
  `{i}` = ordinal de la feuille produite (compteur continu).
- FindReplace (Views / Sheets) : `{i}` = position dans la sélection (identique à `{n}`,
  qui vaut déjà `enumerate(start=1)`).

## Répartition par outil

| Outil | Cible(s) de nommage | `{i}` | `{scale}` `{floor}` `{details}` |
|-------|---------------------|:---:|:---:|
| `views_duplicate` | Nom de vue | ✅ | ✅ |
| `FindReplace - Views` | Nom de vue | ✅ | ✅ |
| `duplicate_sheets` | Nom vue / N° feuille / Nom feuille | ✅ | ❌ |
| `FindReplace_Sheets` | N° feuille / Nom feuille | ✅ | ❌ |

### Décision : ligne « Nom vue » de `duplicate_sheets`

`duplicate_sheets` renomme aussi les vues placées (`update_view_name`), mais **son aperçu
ne montre que le n° et le nom de feuille** — pas les vues. Ajouter `{scale}/{floor}/{details}`
à la ligne « Nom vue » les rendrait *exécutés sans être prévisualisés*, brisant le principe
aperçu = exécution.

**Décidé** : la ligne « Nom vue » de `duplicate_sheets` reçoit seulement `{i}` (comme le reste
de l'outil). `{scale}/{floor}/{details}` n'y sont **pas** ajoutés dans cette itération.
Extension possible ultérieurement si un aperçu des noms de vues est ajouté.

## Architecture — garantir aperçu = exécution

Le VM d'aperçu (`OptionsPageVM` / `NamingPageVM`) **n'a pas accès aux objets Revit** ; il ne
reçoit que des tuples descripteurs. Pour que `{scale}/{floor}/{details}` s'affichent
identiquement en aperçu et à l'exécution :

1. **Helper partagé** `view_naming_context(view, doc)` → `dict`
   `{'type': ..., 'scale': ..., 'floor': ..., 'details': ...}`.
   - Imports Revit gardés (`try/except`), renvoie des chaînes vides quand une propriété est
     indisponible. Testable hors Revit avec une fausse vue / faux doc.
   - Emplacement : un module par outil vue (ex. `lib/services/RevitViewContext.py`), suivant la
     convention du projet (chaque pushbutton est autonome, la duplication de code est tolérée —
     cf. `TokenExpander.py` dupliqué). Réutilisé par `script.py` **et** par le service.
2. **Aperçu** : `script.py` (qui possède les objets Revit) appelle `view_naming_context` par vue
   et **enrichit les descripteurs** ; `MainViewModel` propage ces métadonnées jusqu'au VM ;
   `_recompute_preview` les injecte dans le `context` passé à `apply()`.
3. **Exécution** : le service appelle **le même** `view_naming_context` sur la vue source, et
   passe le même `context` à `RenameService.apply()`.
4. **`{i}`** : compteur maintenu explicitement — dans le VM pour l'aperçu, dans le service pour
   l'exécution — incrémenté par élément produit, dans le même ordre.

### `TokenExpander` — changement minimal

La résolution générique `for key, value in context.items(): result.replace('{'+key+'}', str(value))`
gère **déjà** n'importe quelle clé. Donc :
- Aucune nouvelle logique de résolution.
- Mettre à jour `_AVAILABLE_TOKENS` et la docstring pour inclure `{i}`, `{scale}`, `{floor}`,
  `{details}` (documentation ; `available_tokens()` reste cohérent).
- `{i}`, `{scale}`, `{floor}`, `{details}` sont tous fournis via `context`.

## Fichiers touchés (≈ 5 par outil)

Pour chaque outil concerné :
- `lib/services/TokenExpander.py` — `_AVAILABLE_TOKENS` + docstring (les 4 copies).
- `script.py` — extraction `view_naming_context` + descripteurs enrichis (outils vues).
- VM d'aperçu (`OptionsPageVM` / `NamingPageVM`) — threader `context` + compteur `{i}`.
- Service (`ViewsDuplicationService` / `DuplicationSheetsService` /
  `RenameViewsService` / `RenameSheetsService`) — construire `context` (+ helper vue) + `{i}`.
- XAML de la page de nommage — icône ⓘ + tooltip :
  - **Ajout** : `views_duplicate/GUI/Views/pages/OptionsPage.xaml`,
    `duplicate_sheets/GUI/Views/pages/OptionsPage.xaml`.
  - **Mise à jour** : `FindReplace - Views/.../NamingPage.xaml`,
    `FindReplace_Sheets/.../NamingPage.xaml`.
- Nouveau module `lib/services/RevitViewContext.py` (outils vues) — `view_naming_context`.

## Tooltip d'aide

Réutilise le bloc `<ToolTip>` existant des FindReplace (icône glyphe `&#9432;` « ⓘ »,
`ToolTipService.InitialShowDelay="150"`, `ShowDuration="30000"`, `MaxWidth="340"`).
Chaque outil liste **exactement** ses tokens :

- **Outils vues** (`views_duplicate`, `FindReplace - Views`) :
  `{date}`, `{annee}`, `{mois}`, `{jour}`, `{n}`, `{i}`, `{type}`, `{scale}`, `{floor}`, `{details}`.
- **Outils feuilles** (`duplicate_sheets`, `FindReplace_Sheets`) :
  `{date}`, `{annee}`, `{mois}`, `{jour}`, `{n}`, `{i}`.

Chaque ligne : `{token}  —  description`. Note de bas : « Utilisables dans Préfixe,
Remplacer et Suffixe. »

## Plan de tests (standalone, TDD)

Tous les tests s'exécutent hors Revit via `python -m unittest discover -s tests -p "test_*.py"`.

1. **`TokenExpander`** (les 4 copies, ou test représentatif) :
   - `{i}/{scale}/{floor}/{details}` résolus depuis `context`.
   - `available_tokens()` inclut les nouveaux tokens.
   - Token de context vide → remplacement par `""`.
2. **`view_naming_context`** (outils vues) : fausse vue / faux doc →
   - `scale` : `Scale=100` → `1.100` ; `Scale=0` → `""`.
   - `floor` : `GenLevel.Name='N01'` → `N01` ; pas de niveau → `""`.
   - `details` : viewport avec n° `3` → `3` ; vue non posée → `""`.
3. **VM d'aperçu** : items enrichis → l'aperçu montre les tokens résolus ; `{i}` continu
   sur plusieurs vues/copies.
4. **Services** :
   - `{i}` incrémente correctement (continu, dans l'ordre de production).
   - `views_duplicate` : `{scale}/{floor}/{details}` appliqués au nom réel des copies.
   - `duplicate_sheets` / FindReplace : `{i}` appliqué ; regex/tokens existants intacts.
   - Les tests existants restent verts (61 views_duplicate, 20 duplicate_sheets ; FindReplace
     n'a pas de tests aujourd'hui — en ajouter pour les parties touchées).

## Hors périmètre

- Pas de `{scale}/{floor}/{details}` sur la ligne « Nom vue » de `duplicate_sheets` (voir décision).
- Pas de refactor de la duplication de `TokenExpander`/`RenameService` entre les 4 outils.
- Pas de tooltip piloté par `available_tokens()` (le XAML reste écrit à la main).

## Points décidés (récapitulatif)

- `{scale}` = `"1." + dénominateur` (format `1.100`).
- `{i}` = compteur global continu, ajouté aux 4 outils, `{n}` conservé partout.
- `{details}` = n° de détail du viewport, **outils vues uniquement**, `""` si non posée/vide.
- Ligne « Nom vue » de `duplicate_sheets` → `{i}` seulement.
