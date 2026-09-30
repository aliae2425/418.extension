# Couverture et maintenance — `lib/rvt`

**Périmètre : le derrière.** Ce que chaque outil fait, ce qu'il rend, ce
qu'il casse, et ce qui manque encore par rapport à l'amont.

Le panneau lui-même — saisie, affichage, bandeau, stabilité — se suit dans
[`418.tab/OpenArchi.panel/TESTS.md`](../../418.tab/OpenArchi.panel/TESTS.md).
Ici on ne juge pas comment la réponse s'affiche, seulement si elle est juste.

Comparatif entre les **229 outils** de [rvt-mcp](https://github.com/bimwright/rvt-mcp)
(bimwright, Apache-2.0, C#) et les **56 outils** portés.

Inventaire amont relevé le 30/09/2026 depuis `src/shared/Handlers/*.cs`.

| colonne | sens |
|---|---|
| **rvt-mcp** | le ou les outils amont |
| **418** | notre équivalent, `—` si non porté |
| **Testé** | a tourné pour de vrai dans Revit, sur une maquette |

Le portage n'est pas un miroir : **41 outils amont se replient sur 4 des
nôtres** grâce au regroupement, et une trentaine ne nous concernent pas.
Cocher « testé » demande de l'avoir vu marcher, pas d'avoir lu le code.

## Anomalies d'outils

| # | outil | ce qui se passe | attendu | état |
|---|---|---|---|---|
| 1 | `revit_colorer` | échouait à chaque appel — le générateur de couleurs rendait des `DB.Color`, supposés être des tuples | filtres posés | **réécrit dans `lib/rvt`, à rejouer** |
| 2 | `revit_placer` | coordonnées interprétées au mauvais endroit | unité du projet | **conversion refaite en `base.point()`, à rejouer** |
| 3 | | | | |

## Ordre de vérification conseillé

Les familles ne se valent pas en risque. Par ordre décroissant :

1. **création · réseaux · annotation** — jamais exécutées, et ce sont les API
   dont les signatures changent le plus entre versions de Revit ;
2. **export** — irréversible, écrit sur disque, à ne tenter que sur un
   dossier jetable ;
3. **modification** — `transformer(action='supprimer')` supprime pour de vrai ;
4. **matériaux · géométrie** — lecture, mais beaucoup de géométrie absente
   selon les éléments ;
5. **requête · vues · feuilles · pièces · nomenclatures · audit** — lecture
   pure, le plus sûr pour commencer.

---

## Projet et état — 6 / 8

| rvt-mcp | 418 | Testé |
|---|---|---|
| `get_model_overview` | `revit_infos_maquette` | [ ] |
| `analyze_model_statistics` | `revit_statistiques` | [ ] |
| `get_model_warnings_summary` | `revit_avertissements` | [ ] |
| `show_message` · `send_code_to_revit` | `revit_executer_code` | [ ] |
| `get_selected_elements` | `revit_selection` | [ ] |
| — | `revit_etat` · `revit_unites` | [ ] |
| `set_project_info` | — | |
| `list_phases` · `set_element_phase` · `set_view_phase` | — | |
| `list_recent_models` · `open_model` · `purge_unused` | — | |

## Éléments — 7 / 14

| rvt-mcp | 418 | Testé |
|---|---|---|
| `get_element_details` · `get_element_parameters` · `get_type_parameters` | `revit_details` | [ ] |
| `ai_element_filter` | `revit_elements` | [ ] |
| `get_element_bounding_box` · `get_element_centroid` | `revit_emprise` | [ ] |
| `measure_distance_between_elements` | `revit_distance` | [ ] |
| `set_element_parameter_values` · `set_type_parameter_values` · `set_parameter_value_by_guid` | `revit_definir_parametre` | [ ] |
| `operate_element` · `delete_element` | `revit_transformer` | [ ] |
| `create_point_based_element` | `revit_placer` | [ ] |
| — | `revit_categories` · `revit_lire_parametre` · `revit_parametres_de_categorie` | [ ] |
| `get_element_relationships` · `get_element_geometry` | — | |
| `change_element_type` · `replace_family_type` | — | |
| `select_elements` · `show_element_in_view` | — | |
| `save_selection` · `load_selection` · `list_saved_selections` · `delete_saved_selection` | — | |
| `raycast_from_point` · `project_point_onto_face` · `find_elements_in_volume` | — | |
| `get_assembly_members` · `list_assemblies` | — | |

## Vues et feuilles — 8 / 22

| rvt-mcp | 418 | Testé |
|---|---|---|
| `get_current_view` | `revit_vue_active` | [ ] |
| `activate_view` | `revit_activer_vue` | [ ] |
| `list_sheets` | `revit_feuilles` | [ ] |
| `list_view_templates` · `apply_view_template` | `revit_gabarits` · `revit_appliquer_gabarit` | [ ] |
| — | `revit_vues` · `revit_elements_de_la_vue` · `revit_vues_hors_feuille` | [ ] |
| `create_view` · `create_callout_view` · `create_sheet` · `create_placeholder_sheet` | — | |
| `duplicate_sheet` · `duplicate_view_template` · `renumber_sheets` | — | |
| `place_view_on_sheet` · `place_schedule_on_sheet` · `create_view_sheet_set` | — | |
| `set_view_crop` · `set_view_scale` · `get_view_visibility` · `set_category_visibility` | — | |
| `list_titleblocks` · `get_titleblock_parameters` · `set_titleblock_parameters` | — | |
| `analyze_sheet_layout` · `analyze_view_naming_patterns` · `suggest_view_name_corrections` | — | |
| `capture_view_image` | voir *Export* | |

## Familles — 3 / 12

| rvt-mcp | 418 | Testé |
|---|---|---|
| `list_loaded_families` · `get_family_types` · `get_family_instances` | `revit_familles` | [ ] |
| `audit_families` | `revit_familles_inutilisees` | [ ] |
| `create_point_based_element` | `revit_placer` | [ ] |
| `load_family_from_path` · `unload_family` · `export_family_to_path` | — | |
| `duplicate_family_type` · `rename_family_type` · `list_family_types_in_family` | — | |

## Pièces et surfaces — 3 / 12

| rvt-mcp | 418 | Testé |
|---|---|---|
| `list_rooms` | `revit_pieces` | [ ] |
| — | `revit_surfaces_par_niveau` · `revit_pieces_sans_nom` | [ ] |
| `create_room` · `create_room_separator` · `auto_create_rooms_from_walls` | — | |
| `get_room_boundaries` · `get_room_openings` · `compute_room_finishes` | — | |
| `create_space` · `create_area` · `list_areas` | — | |
| `export_room_data` · `workflow_room_documentation` | — | |

## Nomenclatures — 2 / 12

| rvt-mcp | 418 | Testé |
|---|---|---|
| `list_schedules` | `revit_nomenclatures` | [ ] |
| `get_schedule_data` | `revit_lire_nomenclature` | [ ] |
| `create_schedule` · `add_schedule_field` · `update_schedule_field` | — | |
| `apply_schedule_filter_sort` · `get_schedule_definition` · `get_schedule_formulas` | — | |
| `get_schedulable_fields` · `find_schedule_elements` · `export_schedule_csv` | — | |
| `get_panel_schedule` | — | |

## Matériaux — 3 / 11

| rvt-mcp | 418 | Testé |
|---|---|---|
| `list_materials` | `revit_materiaux` | [ ] |
| `get_material_quantities` · `get_material_takeoff` | `revit_metres` | [ ] |
| `get_material_properties` | `revit_materiaux_de` | [ ] |
| `create_material` · `duplicate_material` · `assign_material_to_element` | — | |
| `set_material_appearance` · `set_material_identity` · `set_material_structural_asset` · `set_material_thermal_asset` | — | |

## Graphismes — 2 / 9

| rvt-mcp | 418 | Testé |
|---|---|---|
| `color_elements` · `create_view_filter` · `apply_filter_to_view` · `set_filter_overrides` · `override_element_graphics` | `revit_colorer` | [ ] |
| `clear_element_overrides` · `remove_filter_from_view` | `revit_effacer_couleurs` | [ ] |
| `list_view_filters` | — | |
| `create_filled_region` | — | |

## Annotation — 3 / 12

| rvt-mcp | 418 | Testé |
|---|---|---|
| `tag_elements` · `tag_all_by_category` · `tag_all_rooms` · `tag_all_walls` · `tag_all_areas` · `tag_structural_framing` | `revit_etiqueter` | [ ] |
| `create_text_note` | `revit_noter` | [ ] |
| `find_untagged_elements` | `revit_non_etiquetes` | [ ] |
| — | `revit_etiquettes` | [ ] |
| `create_dimensions` · `find_undimensioned_elements` | — | |
| `wipe_empty_tags` · `list_keynotes` · `apply_keynote_to_element` | — | |
| `create_detail_line` | — | |

## Création — 6 / 14

| rvt-mcp | 418 | Testé |
|---|---|---|
| `create_level` | `revit_creer_niveau` | [ ] |
| `create_grid` | `revit_creer_quadrillage` | [ ] |
| `create_line_based_element` · `create_structural_wall` | `revit_creer_mur` | [ ] |
| `create_surface_based_element` | `revit_creer_sol` | [ ] |
| `create_structural_column` · `create_structural_beam` | `revit_creer_porteur` | [ ] |
| `create_group_from_elements` · `get_group_members` · `list_groups` | `revit_groupes` (lecture seule) | [ ] |
| `create_foundation_isolated` · `create_foundation_wall` | — | |
| `create_rebar_set` · `create_rebar_stirrup` · `list_rebar` | — | |
| `analyze_structural_connections` · `get_structural_loads` · `set_structural_load` | — | |

## MEP — 1 / 12

| rvt-mcp | 418 | Testé |
|---|---|---|
| `create_duct` · `create_pipe` · `create_cable_tray` · `create_conduit` | `revit_creer_reseau` | [ ] |
| `create_air_terminal` · `create_lighting_fixture` · `create_mep_fitting` | — | |
| `connect_mep_elements` · `find_mep_disconnects` · `analyze_mep_network` | — | |
| `list_mep_systems` · `get_mep_element_connectors` · `get_system_inventory` | — | |
| `detect_system_elements` · `set_system_classification` | — | |

## Géométrie — 2 / 6

| rvt-mcp | 418 | Testé |
|---|---|---|
| `clash_detection` · `find_overlapping_elements` | `revit_collisions` ⚠ | [ ] |
| `compute_element_area` · `compute_element_volume` | `revit_metres` | [ ] |
| `analyze_geometry_complexity` | — | |

⚠ `revit_collisions` compare des **boîtes englobantes**. C'est une
pré-détection : elle signale des candidats à vérifier, jamais des collisions
certaines. `clash_detection` amont fait une vraie intersection de solides.

## Organisation et liens — 3 / 14

| rvt-mcp | 418 | Testé |
|---|---|---|
| `list_worksets` | `revit_sous_projets` | [ ] |
| `list_linked_models` | `revit_liens` | [ ] |
| `list_groups` · `get_group_members` | `revit_groupes` | [ ] |
| `assign_elements_to_workset` | — | |
| `link_revit_model` · `reload_link` · `unload_link` · `get_link_elements` | — | |
| `acquire_coordinates_from_link` · `publish_coordinates_to_link` · `get_link_coordinate_system` | — | |
| `get_project_coordinate_system` · `set_project_base_point` | — | |
| `import_cad_to_view` · `list_linked_cad` | — | |
| `create_revision` · `list_revisions` · `assign_revision_to_sheet` | — | |

## Paramètres partagés et projet — 0 / 7

| rvt-mcp | 418 | Testé |
|---|---|---|
| `create_shared_parameter` · `bind_shared_parameter` · `list_shared_parameters` | — | |
| `create_project_parameter` · `list_project_parameters` · `list_project_parameter_bindings` · `remove_parameter_binding` | — | |
| `export_shared_parameter_file` | — | |

## Export — 1 / 14

| rvt-mcp | 418 | Testé |
|---|---|---|
| `export_pdf` · `export_dwg` · `export_ifc` · `export_nwc` · `export_image` | `revit_exporter` | [ ] |
| `export_dgn` · `export_dwf` · `export_fbx` · `export_gbxml` | — | |
| `export_elements_data` · `export_room_data` · `export_schedule_csv` | — | |
| `batch_export_sheets` | voir **BatchExport**, bouton 418 | |
| `list_export_settings` · `get_print_settings` | — | |

## Audit et document — 4 / 6

| rvt-mcp | 418 | Testé |
|---|---|---|
| `find_untagged_elements` | `revit_non_etiquetes` | [ ] |
| `audit_families` | `revit_familles_inutilisees` | [ ] |
| — | `revit_vues_inutilisees` | [ ] |
| `workflow_model_audit` | `revit_statistiques` | [ ] |
| — | `revit_enregistrer` · `revit_synchroniser` | [ ] |

## Volontairement non porté — 37 outils

| famille | outils | pourquoi |
|---|---|---|
| ToolBaker | `list_baked_tools` · `run_baked_tool` · `create_bake_issue_draft` · `accept_bake_suggestion` · `apply_bake_suggestion` · `dismiss_bake_suggestion` · `list_bake_suggestions` | outillage propre à rvt-mcp |
| Multi-instance | `list_available_targets` · `switch_target` · `batch_execute` | un seul Revit, un seul serveur de routes |
| Workflows | `workflow_clash_review` · `workflow_takeoff_report` · `workflow_sheet_set` · `workflow_view_cleanup` · `workflow_naming_normalization` · `workflow_data_roundtrip` | enchaînements que le modèle compose lui-même à partir des outils simples |
| KEI, profil | `detect_firm_profile` · `query_kei_database` · `import_project_equipment` | métier d'un autre bureau |
| Image | `capture_view_image` | la boucle d'outils du chat ne transporte pas d'image ; `revit_exporter(format='image')` écrit un fichier |

---

## Où on en est

**56 outils sur 229**, soit **24 %** du nombre — mais la comparaison par le
nombre trompe. Le regroupement replie 41 outils amont sur 4 des nôtres, et
37 autres ne nous concernent pas. Sur les **151 outils restants**, on en
couvre **56**, soit **37 %**.

Ce qui manque et qui se sentira le plus vite, par ordre :

1. **créer des vues et des feuilles** — placer une vue sur une feuille,
   dupliquer, renuméroter ;
2. **les nomenclatures en écriture** — créer, ajouter un champ, filtrer ;
3. **les pièces** — créer, séparer, calculer les finitions ;
4. **les paramètres de projet et partagés** — en créer, les lier ;
5. **la visibilité** — masquer une catégorie, régler le cadrage et l'échelle.

Aucune case n'est cochée : **rien n'a encore tourné dans Revit.** Le premier
passage compte plus que le reste du tableau.

---

## Maintenance

### Ajouter un outil

Une famille = un fichier dans `rvt/outils/`, déclaré dans `charger_outils()`.
Dans le fichier :

```python
@outil('feuilles', 'Ce que le modèle lit pour décider de l\'appeler.',
       proprietes={'contient': {'type': 'string', 'description': '…'}},
       requis=(), ecrit=False, irreversible=False, besoins=('doc',))
def feuilles(doc, donnees=None):
    return {'count': …, 'feuilles': […]}
```

La déclaration sert au routage, au catalogue et aux garde-fous. Il n'y a rien
d'autre à mettre à jour — c'est tout l'intérêt du registre.

### Règles qui ont toutes été payées

**Déclaration hors du corps.** `@outil(...)` s'exécute à l'import même quand
`DB` est `None` : c'est ce qui rend le catalogue testable hors Revit.

**`ErreurOutil` pour ce que l'appelant peut corriger** — catégorie inconnue,
paramètre absent, aucune vue active. Elle sort en HTTP 400 avec son message,
et le modèle peut réessayer autrement. Tout le reste part en 500, avec sa
trace dans le journal.

**Un outil d'écriture qui ne modifie rien doit lever.** Rendre « 0 modifié »
laisse le modèle annoncer une modification qui n'a pas eu lieu.

**Les mesures se convertissent aux frontières**, jamais au milieu :
`base.point()` en entrée, `base.vers_projet()` et `base.mesure()` en sortie.
Et **une aire ne se convertit pas avec le facteur d'une longueur** — un pied
carré vaut 0,0929 m², pas 0,3048.

**Toute liste porte `total` et `partielle`.** Sans ça le modèle croit avoir
tout vu et l'annonce.

**Une famille qui ne s'importe pas ne doit pas emporter les autres** —
`charger_outils()` attrape par famille. Une famille en moins vaut mieux qu'un
chat sans outils.

### Pièges d'API rencontrés

- `element.Name` **lève** sur certains types sous IronPython — c'est
  l'`AttributeError: Name` des journaux. Passer par `base.nom_element()` ;
- `ElementId.Value` en 2024+, `IntegerValue` avant — `base.id_valeur()` ;
- `ParameterFilterRuleFactory.CreateEqualsRule` a perdu son argument
  `caseSensitive` en 2022 : les deux signatures sont tentées ;
- `IndependentTag.GetTaggedLocalElementIds()` n'existe qu'à partir de 2022,
  `TaggedLocalElementId` avant ;
- l'export NWC exige le greffon Navisworks Exporter, absent chez beaucoup —
  l'outil le dit plutôt que de laisser une trace incompréhensible.

### Ce qu'on ne fait pas ici

**Aucune socket, aucun fil, aucun WPF.** Enregistrer une route pose une
fonction dans le routeur global de pyRevit, rien de plus. 418 ne démarre
aucun serveur : l'essai a coûté deux plantages de Revit. Le chat se branche
sur celui de pyRevit, port découvert dans `core/routes418.py`.

**Une seule requête en vol à la fois.** Le serveur de routes partage un
handler et un `ExternalEvent` entre toutes ses requêtes ; deux appels
simultanés se marchent dessus dans le contexte d'API. Le verrou de
`core/revit_outils.py` ne protège que de nous — un client MCP externe qui
tape le même serveur rouvre la course.
