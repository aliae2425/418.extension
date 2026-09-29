# Portage rvt-mcp → `lib/rvt` — journal des lots

Le serveur vendorisé (`mcp-server-for-revit-python`, 18 routes) est supprimé.
On reprend la surface fonctionnelle de **rvt-mcp** (bimwright, Apache-2.0,
227 outils en C#) en Python, sur `routes.API('418')`.

## Ce qui rend le portage tenable

rvt-mcp fait 111 000 lignes de C# pour 235 handlers. On n'en porte pas la
moitié, et pour trois raisons :

**48 % du dépôt ne nous concerne pas.** Transport, add-in par année de Revit,
serveur MCP stdio, localisation, ToolBaker, sécurité : pyRevit nous le donne,
ou on n'en a pas l'usage. Reste les handlers.

**Une route, pas deux cent trente.** `POST /418/outil/<nom>` dispatche sur un
registre. Chaque outil se déclare une fois, avec son schéma, et sert à la
fois au routage, au catalogue (`GET /418/outils/`) et à la doctrine
(`ecrit`, `irreversible`). Le catalogue écrit à la main a divergé deux fois —
il n'existe plus.

**On regroupe.** Les variantes d'un même geste deviennent un outil
paramétré : les quatre `export_*` en un `exporter(format=…)`, les trois
`create_duct/pipe/conduit` en un `creer_reseau(type=…)`.

## État

| lot | famille | outils | état |
|---|---|---|---|
| 1 | socle, requête, vues, feuilles, paramètres, familles, graphismes, document | **25** | **fait** |
| 2 | pièces, nomenclatures, audit | **9** | **fait** |
| 3 | annotation, cotes, étiquettes | ~12 | à faire |
| 4 | matériaux, géométrie, clash | ~10 | à faire |
| 5 | création : niveaux, quadrillages, murs, sols | ~12 | à faire |
| 6 | MEP : gaines, canalisations, réseaux | ~8 | à faire |
| 7 | structure : poteaux, poutres, armatures | ~8 | à faire |
| 8 | export PDF/DWG/IFC/NWC | ~2 | à faire |
| 9 | liens, coordonnées partagées | ~6 | à faire |
| 10 | organisation : gabarits, worksets, groupes | ~8 | à faire |
| 11 | lint et audit : non étiquetés, doublons | ~6 | à faire |

## Lot 2 — livré

**Pièces** — `revit_pieces` (surfaces dans l'unité du projet, non placées
comptées à part parce qu'elles fausseraient tout total) ·
`revit_surfaces_par_niveau` · `revit_pieces_sans_nom`

**Nomenclatures** — `revit_nomenclatures` · `revit_lire_nomenclature`. Lire
une nomenclature vaut mieux que recompter à côté : elle porte les champs, les
filtres et les groupements que l'architecte a choisis, donc on répond avec
SES chiffres.

**Audit** — `revit_non_etiquetes` · `revit_vues_inutilisees` ·
`revit_familles_inutilisees` · `revit_statistiques`

Piège écarté en passant : les **aires ne se convertissent pas avec le facteur
des longueurs**. Un pied carré vaut 0,0929 m², pas 0,3048 — l'erreur est
tentante et silencieuse. D'où `base.mesure(doc, valeur, SpecTypeId)`, qui
prend la spécification plutôt que de supposer.

## Lot 1 — livré

**Parité avec l'ancien serveur**, et ce qu'il ne savait pas faire.

`revit_etat` · `revit_infos_maquette` · `revit_unites` · `revit_niveaux` ·
`revit_selection` · `revit_categories` · `revit_elements` · `revit_details` ·
`revit_avertissements` · `revit_vue_active` · `revit_vues` ·
`revit_elements_de_la_vue` · `revit_feuilles` · `revit_vues_hors_feuille` ·
`revit_parametres_de_categorie` · `revit_lire_parametre` · `revit_familles`

Écriture annulable : `revit_activer_vue` · `revit_colorer` ·
`revit_effacer_couleurs` · `revit_definir_parametre` · `revit_placer`

Irréversible : `revit_enregistrer` · `revit_synchroniser` ·
`revit_executer_code`

### Ce que le lot 1 corrige

- **les unités** — toute longueur sort convertie dans l'unité du projet, avec
  son symbole, et les valeurs de paramètres aussi : on regarde le type de
  donnée, pas le nom du champ. Le vendor rendait des pieds nus ;
- **les familles par catégorie** — `revit_familles` filtre sur la catégorie
  autant que sur le nom. `list_families` ne savait que le nom, et ne trouvait
  donc pas « les portes » ;
- **les feuilles** — leur propre outil, avec numéro et vues placées. Elles
  étaient noyées dans un seau « other », dernier du JSON, donc tronqué ;
- **les paramètres** — lire une valeur, écrire une valeur. Impossible avant ;
- **la troncature annoncée** — chaque liste porte `total` et `partielle`, au
  lieu de laisser le modèle croire qu'il a tout vu.

## Règles du portage

**Toute déclaration hors du corps.** `@outil(...)` s'exécute à l'import même
quand `DB` est `None` : c'est ce qui rend le catalogue testable hors Revit.

**Rien de neuf dans `base.py` sans usage.** Les helpers y arrivent quand un
deuxième outil en a besoin, pas avant.

**Une famille = un fichier**, ajouté à `charger_outils()`. Un import qui
échoue ne doit pas emporter les autres : une famille en moins vaut mieux
qu'un chat sans outils.

**`ErreurOutil` pour ce que l'appelant peut corriger** — catégorie inconnue,
paramètre absent, aucune vue active. Elle sort en HTTP 400 avec son message.
Tout le reste part en 500 avec sa trace dans le journal.

**Les longueurs se convertissent aux frontières**, jamais au milieu :
`base.point()` en entrée, `base.vers_projet()` en sortie.
