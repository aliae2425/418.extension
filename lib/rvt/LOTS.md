# Portage rvt-mcp → `lib/rvt`

Le serveur vendorisé (`mcp-server-for-revit-python`, 18 routes) est supprimé.
La surface fonctionnelle de **rvt-mcp** (bimwright, Apache-2.0, 227 outils en
C#) est portée en Python sur `routes.API('418')`.

**56 outils, 18 familles.** Le portage est terminé.

## Ce qui l'a rendu tenable

rvt-mcp fait 111 000 lignes de C# pour 235 handlers. On n'en a pas porté la
moitié, pour trois raisons :

**48 % du dépôt ne nous concerne pas.** Transport, add-in par année de Revit,
serveur MCP stdio, localisation, ToolBaker, sécurité : pyRevit nous le donne,
ou on n'en a pas l'usage.

**Une route, pas deux cent trente.** `POST /418/outil/<nom>` dispatche sur un
registre. Chaque outil se déclare une fois, avec son schéma, et cette
déclaration sert au routage, au catalogue (`GET /418/outils/`) et aux
garde-fous (`ecrit`, `irreversible`). Le catalogue écrit à la main a divergé
deux fois — il n'existe plus.

**On a regroupé** partout où des variantes d'un même geste partageaient leur
code :

| rvt-mcp | ici |
|---|---|
| `export_pdf` · `export_dwg` · `export_ifc` · `export_nwc` · image | `revit_exporter(format=…)` |
| `move` · `copy` · `rotate` · `delete` | `revit_transformer(action=…)` |
| `create_duct` · `create_pipe` · `create_cable_tray` | `revit_creer_reseau(type=…)` |
| `create_structural_column` · `create_beam` | `revit_creer_porteur(type=…)` |

## Les 56 outils

### Lecture — 37

**Projet** `etat` · `infos_maquette` · `unites` · `niveaux` · `statistiques`

**Éléments** `categories` · `elements` · `details` · `selection` · `emprise` ·
`distance` · `collisions`

**Vues et feuilles** `vue_active` · `vues` · `elements_de_la_vue` ·
`feuilles` · `vues_hors_feuille` · `gabarits` · `etiquettes`

**Familles** `familles` · `parametres_de_categorie` · `lire_parametre`

**Pièces** `pieces` · `surfaces_par_niveau` · `pieces_sans_nom`

**Nomenclatures** `nomenclatures` · `lire_nomenclature`

**Matériaux** `materiaux` · `materiaux_de` · `metres`

**Organisation** `sous_projets` · `groupes` · `liens`

**Audit** `avertissements` · `non_etiquetes` · `vues_inutilisees` ·
`familles_inutilisees`

### Écriture annulable au Ctrl+Z — 15

`placer` · `transformer` · `definir_parametre` · `colorer` ·
`effacer_couleurs` · `activer_vue` · `appliquer_gabarit` · `etiqueter` ·
`noter` · `creer_niveau` · `creer_quadrillage` · `creer_mur` · `creer_sol` ·
`creer_reseau` · `creer_porteur`

### Irréversible — 4

`enregistrer` · `synchroniser` · `exporter` · `executer_code`

Aucun ne pose de transaction. Le routeur les journalise en WARNING avec leurs
arguments, et l'invite système impose une demande explicite de l'architecte
dans son dernier message.

## Ce que le portage corrige

- **les unités** — toute mesure sort dans l'unité du projet, avec son
  symbole, en regardant le *type de donnée* et pas le nom du champ. Les aires
  ne se convertissent pas avec le facteur des longueurs : un pied carré vaut
  0,0929 m², pas 0,3048 ;
- **les familles par catégorie** — `list_families` ne savait filtrer que sur
  le nom, et ne trouvait donc pas « les portes » ;
- **les feuilles** — leur propre outil, avec numéro et vues placées. Elles
  étaient noyées dans un seau « other », dernier du JSON, donc tronqué ;
- **les paramètres** — lire une valeur, écrire une valeur. Impossible avant ;
- **la troncature annoncée** — chaque liste porte `total` et `partielle`.

## Règles à tenir

**Toute déclaration hors du corps.** `@outil(...)` s'exécute à l'import même
quand `DB` est `None` : c'est ce qui rend le catalogue testable hors Revit.

**Une famille = un fichier**, ajouté à `charger_outils()`. Un import qui
échoue ne doit pas emporter les autres : une famille en moins vaut mieux
qu'un chat sans outils.

**`ErreurOutil` pour ce que l'appelant peut corriger** — catégorie inconnue,
paramètre absent, aucune vue active. Elle sort en HTTP 400 avec son message,
et le modèle peut réessayer autrement. Tout le reste part en 500 avec sa
trace dans le journal.

**Les mesures se convertissent aux frontières**, jamais au milieu :
`base.point()` en entrée, `base.vers_projet()` et `base.mesure()` en sortie.

**Un outil d'écriture qui ne modifie rien doit lever.** Rendre « 0 modifié »
laisse le modèle annoncer une modification qui n'a pas eu lieu.

## Non porté, et pourquoi

- **ToolBaker, lint avancé, mémoire de session, localisation** — de
  l'outillage propre à rvt-mcp, sans objet ici ;
- **armatures, réseaux MEP analytiques, coordonnées partagées** — métiers
  qu'aucune demande n'a encore touchés. À porter quand ils serviront, pas
  avant ;
- **`capture_view_image`** — rend une image en base64, que la boucle d'outils
  du chat ne transporte pas. `revit_exporter(format='image')` écrit un
  fichier, ce qui répond au même besoin autrement.
