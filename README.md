# 418.extension

Boîte à outils Revit pour la production de documents : **export PDF/DWG en lot**,
**duplication** et **renommage** de feuilles et de vues, **alignement** d'éléments
en vue, gestion des **matériaux**, **recadrage d'images** et **import SVG**.

Extension [pyRevit](https://github.com/eirannejad/pyRevit) — s'ajoute à Revit sous
la forme d'un onglet **418**.

Revit **2026** minimum.

---

## Installation

1. Installer [pyRevit](https://github.com/eirannejad/pyRevit) (si ce n'est pas déjà fait).
2. Cloner ce dépôt dans le dossier des extensions pyRevit :

   ```
   %APPDATA%\pyRevit\Extensions\418.extension
   ```

   ```bash
   git clone https://github.com/aliae2425/418.extension.git "%APPDATA%\pyRevit\Extensions\418.extension"
   ```

3. Dans Revit : onglet **pyRevit → Reload** (ou `Ctrl+F5`).

L'onglet **418** apparaît dans le ruban. Pour mettre à jour : `git pull`, puis
**Reload**.

---

## Les outils

| Onglet | Bouton | Ce que ça fait |
|---|---|---|
| Export | **Export** | Export PDF/DWG en lot, par jeu de feuilles ou feuille par feuille |
| Tools | **Dupliquer feuilles** | Duplique des feuilles avec leur contenu, en renommant à la volée |
| Tools | **Dupliquer vues** | Duplique des vues en N copies (avec/sans détails, dépendantes) |
| Tools | **Renommer feuilles** | Rechercher-remplacer / préfixe / suffixe sur numéro et nom |
| Tools | **Renommer vues** | Rechercher-remplacer / préfixe / suffixe sur les noms de vues |
| Tools | **ImageCrop** | Découpe une image importée selon des zones de pochage |
| Tools | **Importer SVG** | Importe un fichier SVG dans la vue active, via un DXF temporaire |
| Manage | **Matériaux** | Voir, éditer, remplacer et renommer les matériaux du modèle |
| Align | **8 boutons** | Aligner, centrer et répartir les éléments d'une vue |
| 418 | **À propos** | Version, dépôt, licence |

Tous les outils affichent un **aperçu avant validation** : rien n'est modifié dans
le modèle avant que vous cliquiez sur le bouton d'action.

Quelques outils sont encore en chantier et **n'apparaissent pas dans le ruban** par
défaut — voir [Outils en bêta](#outils-en-bêta) plus bas.

### Export — PDF / DWG en lot

Deux modes, au choix dans la barre latérale :

**Par jeu — préprogrammé.** L'outil lit les jeux de feuilles (*sheet collections*)
du modèle et exporte ceux qui portent le bon paramètre. Vous mappez une fois pour
toutes, dans **Paramètres → Mappage des paramètres**, trois paramètres Oui/Non de
vos jeux :

- **Export** — le jeu doit-il être exporté ?
- **Carnet** — les feuilles doivent-elles être reliées en un seul PDF ?
- **DWG** — faut-il aussi produire les DWG ?

Une fois mappé, l'export d'un carnet complet tient en un clic sur **Exporter**.

**Feuille par feuille — manuel.** La liste de toutes les feuilles, avec une case
PDF et une case DWG par ligne. Recherche, filtres par jeu, sélection multiple
(`Maj`/`Ctrl`), boutons **Tout PDF** / **Tout DWG**. Option **Combiné** pour
fusionner la sélection PDF en un seul fichier, avec son titre.

**Nommage des fichiers.** Le nom des fichiers produits suit un motif que vous
composez dans **Paramètres → Nommage des fichiers** (un motif pour les feuilles,
un pour les carnets). Un motif est du texte libre plus des jetons entre accolades :

```
{projet_numero}-{numero}_{nom}          →  2412-A101_Plan RDC.pdf
{date}_{titre}                          →  2026-08-25_Carnet DCE.pdf
{numero}_{param:Phase}                  →  A101_Phase 2.pdf
```

| Jeton | Valeur |
|---|---|
| `{numero}` | numéro de la feuille |
| `{nom}` | nom de la feuille (ou du jeu) — variantes `{nom_tiret}`, `{nom_underscore}` |
| `{titre}` | titre du jeu de feuilles (carnet) |
| `{date}` | date du jour `AAAA-MM-JJ` — aussi `{date_jour}`, `{date_mois}`, `{date_annee}` |
| `{projet_nom}` `{projet_numero}` `{projet_client}` `{projet_statut}` | infos du projet |
| `{param:NOM}` | n'importe quel paramètre de la feuille |
| `{param_projet:NOM}` | n'importe quel paramètre des informations du projet |

Un jeton dont la valeur est vide ou introuvable disparaît du nom : jamais de
`{...}` brut dans le nom de fichier. Les caractères interdits par Windows sont
retirés automatiquement.

**Organisation de l'export.** Dossier de destination, **sous-dossier par jeu**,
**séparation PDF / DWG** dans deux dossiers distincts. Les **setups d'impression**
PDF et DWG sont ceux définis dans Revit ; l'outil vous laisse choisir lesquels.

### Dupliquer feuilles

Sélection des feuilles → options → aperçu → validation. Vous choisissez ce qui
suit la copie (vues, légendes, nomenclatures, éléments de détail), le mode de
duplication des vues (simple, avec détails, dépendante), et le renommage appliqué
aux copies.

### Dupliquer vues

Même principe pour les vues, avec un nombre de copies par vue.

### Renommer feuilles / vues

Rechercher-remplacer, préfixe, suffixe. Pour les feuilles, numéro et nom sont
traités séparément. L'aperçu montre l'ancien et le nouveau nom avant validation.

### ImageCrop

Découpe une image importée en morceaux, sans logiciel externe.

1. Dessiner une ou plusieurs **régions remplies** (ou lignes de détail) par-dessus
   l'image, aux endroits à conserver.
2. Sélectionner l'image **et** ces zones.
3. Lancer **ImageCrop**.

Chaque zone produit un morceau d'image calé exactement dans son cadre. L'image
d'origine est conservée. Les zones traitées passent en contour vert sans fond
(simple habillage graphique de la vue, non destructif).

### Importer SVG

Importe un fichier SVG dans la vue active, en passant par un DXF temporaire.
L'outil prévient avant une décomposition vouée à échouer plutôt que de laisser
Revit produire un import vide.

### Matériaux

Liste les matériaux du modèle : consultation, édition, remplacement d'un matériau
par un autre, renommage en lot. L'éditeur montre un **aperçu fidèle** des motifs
de surface — taille réelle, densité, phase des tirets — plutôt qu'une vignette
approximative.

### Aligner, centrer, répartir

Huit boutons dans l'onglet **Align**, applicables à une sélection dans la vue
active : aligner à gauche / à droite / en haut / en bas, centrer horizontalement
ou verticalement, répartir horizontalement ou verticalement.

L'alignement se cale sur les extrêmes de la sélection, pas sur la vue. Les
**éléments épinglés servent de référence** : ils ne bougent pas, les autres
viennent s'y aligner. Si toute la sélection est épinglée, l'outil le signale et
ne touche à rien.

La répartition espace également les centres entre les deux éléments extrêmes.

---

## Outils en bêta

Certains outils sont présents dans le dépôt mais **pas encore finalisés**. Ils
portent le drapeau bêta de pyRevit : le bouton n'est tout simplement pas
construit, et rien n'apparaît dans le ruban.

Pour les afficher : **pyRevit → Settings → cocher « Load Beta Tools »**, puis
**Reload**.

| Onglet | Outil | État |
|---|---|---|
| Audit | **Audit** | Analyse de santé du modèle — fonctionnel, pas encore stabilisé |
| Manage | **Filtres**, **Feuilles**, **Vues** | Ossatures MVVM seules : la fenêtre s'ouvre, aucune logique métier n'est branchée |

Ne comptez pas dessus en production : ils peuvent changer ou disparaître sans
préavis.

---

## Réglages

Les réglages (mappage des paramètres, motifs de nommage, destination, setups) sont
**mémorisés** entre les sessions, dans `418.extension/data/`. Rien à reconfigurer
au prochain lancement.

Les réglages sont locaux à votre poste et ne sont pas versionnés.

---

## Problème ?

- **L'onglet 418 n'apparaît pas** : vérifier que le dossier s'appelle bien
  `418.extension` et qu'il est dans `%APPDATA%\pyRevit\Extensions`, puis **Reload**.
- **Un bouton reste grisé / affiche « indisponible »** : Revit 2026 minimum.
- **« Aucun jeu qualifié » à l'export** : le mappage des paramètres n'est pas fait,
  ou le paramètre Oui/Non n'est pas coché sur les jeux → **Paramètres → Mappage
  des paramètres**.
- **Autre** : [ouvrir une issue](https://github.com/aliae2425/418.extension/issues).

---

## Développement

Voir [CLAUDE.md](CLAUDE.md) pour l'architecture, les conventions et le cycle de
développement.

Licence [MIT](LICENSE) · © Aliae
