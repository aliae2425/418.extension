<<<<<<< HEAD
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="418.tab/418.panel/Infos.pushbutton/icon.dark.png">
    <img src="418.tab/418.panel/Infos.pushbutton/icon.png" width="90" height="90" alt="418.extension">
  </picture>
</p>

<h1 align="center">418.extension</h1>

<p align="center">
  <em>I'm a teapot.</em>
</p>

<p align="center">
  <img alt="Revit 2026+" src="https://img.shields.io/badge/Revit-2026%2B-0696D7?style=for-the-badge&logo=autodesk&logoColor=white">
  <img alt="Extension pyRevit" src="https://img.shields.io/badge/pyRevit-extension-F7941E?style=for-the-badge">
  <img alt="IronPython 2.7" src="https://img.shields.io/badge/IronPython-2.7-3776AB?style=for-the-badge&logo=python&logoColor=white">
</p>

<p align="center">
  <a href="https://github.com/aliae2425/418.extension/tags"><img alt="Version" src="https://img.shields.io/github/v/tag/aliae2425/418.extension?style=for-the-badge&label=version&color=4c1&filter=v*"></a>
  <a href="LICENSE"><img alt="Licence MIT" src="https://img.shields.io/badge/licence-MIT-4c1?style=for-the-badge"></a>
  <a href="https://forthebadge.com"><img alt="Built with love" src="https://forthebadge.com/images/badges/built-with-love.svg"></a>
</p>
=======
<p align="center"><picture>
<source media="(prefers-color-scheme: dark)" srcset="418.tab/418.panel/Infos.pushbutton/icon.dark.png">
<img src="418.tab/418.panel/Infos.pushbutton/icon.png" alt="" width="90" height="90"></picture></p>
>>>>>>> Developpement

<h1 align="center">418.extension</h1>

<p align="center"><strong>I'm a teapot.</strong><br>
Les dix gestes qu'un architecte refait chaque semaine, derrière un bouton, et reproductibles.</p>

<p align="center"><a href="https://github.com/aliae2425/418.extension/tags"><img alt="Version" src="https://img.shields.io/github/v/tag/aliae2425/418.extension?label=version&filter=v*"></a>
<img alt="Revit 2026+" src="https://img.shields.io/badge/Revit-2026%2B-0696D7">
<a href="https://github.com/eirannejad/pyRevit"><img alt="Extension pyRevit" src="https://img.shields.io/badge/pyRevit-extension-F7941E"></a>
<a href="LICENSE"><img alt="Licence MIT" src="https://img.shields.io/badge/licence-MIT-blue"></a></p>

<p align="center"><a href="https://forthebadge.com"><img alt="Built with love" src="https://forthebadge.com/images/badges/built-with-love.svg"></a></p>

Sortir un carnet PDF, dupliquer une série de feuilles, renommer trente vues,
caler des éléments dans une vue. Revit rend tout ça possible et rien de tout ça
rapide. 418 met ces gestes derrière un bouton — et derrière un **aperçu** : rien
n'est modifié dans le modèle tant que vous n'avez pas validé. Un export donne
deux fois le même résultat ; un renommage se relit avant de s'appliquer.

## Installation

```bash
git clone https://github.com/aliae2425/418.extension.git "%APPDATA%\pyRevit\Extensions\418.extension"
```

[pyRevit][pyrevit] d'abord, puis **pyRevit → Reload** dans Revit (`Ctrl+F5`).
L'onglet **418** apparaît dans le ruban. Mise à jour : `git pull`, puis Reload.

Revit **2026** minimum.

## Les outils

| Onglet | Bouton | Ce que ça fait |
|---|---|---|
| Export | **Export** | PDF/DWG en lot, par jeu de feuilles ou feuille par feuille |
| Tools | **Dupliquer feuilles** | Duplique des feuilles avec leur contenu, en renommant à la volée |
| Tools | **Dupliquer vues** | Duplique des vues en N copies (avec/sans détails, dépendantes) |
| Tools | **Renommer feuilles** | Rechercher-remplacer, préfixe, suffixe — numéro et nom séparément |
| Tools | **Renommer vues** | Idem sur les noms de vues |
| Tools | **ImageCrop** | Découpe une image importée selon des zones de pochage |
| Tools | **Importer SVG** | Importe un SVG dans la vue active, via un DXF temporaire |
| Manage | **Matériaux** | Voir, éditer, remplacer, renommer les matériaux du modèle |
| Align | **8 boutons** | Aligner, centrer, répartir les éléments d'une vue |
| 418 | **À propos** | Version, dépôt, licence |

## Export

**Par jeu — préprogrammé.** L'outil lit les jeux de feuilles du modèle et exporte
ceux qui portent le bon paramètre. Vous mappez une fois pour toutes, dans
**Paramètres → Mappage des paramètres**, trois paramètres Oui/Non de vos jeux :
**Export** (le jeu part-il ?), **Carnet** (relié en un seul PDF ?) et **DWG**.
Ensuite, un carnet complet tient en un clic.

**Feuille par feuille — manuel.** Toutes les feuilles, une case PDF et une case
DWG par ligne. Recherche, filtres par jeu, sélection multiple (`Maj`/`Ctrl`),
**Tout PDF** / **Tout DWG**. **Combiné** fusionne la sélection en un seul PDF.

**Organisation.** Dossier de destination, sous-dossier par jeu, séparation
PDF/DWG. Les setups d'impression sont ceux de Revit ; l'outil vous laisse choisir.

## Nommage

Le nom des fichiers suit un motif que vous composez dans **Paramètres → Nommage
des fichiers** — du texte libre, plus des jetons entre accolades :

```
{projet_numero}-{numero}_{nom}          →  2412-A101_Plan RDC.pdf
{date}_{titre}                          →  2026-08-25_Carnet DCE.pdf
{numero}_{param:Phase}                  →  A101_Phase 2.pdf
```

| Jeton | Valeur |
|---|---|
| `{numero}` | numéro de la feuille |
| `{nom}` | nom de la feuille ou du jeu — variantes `{nom_tiret}`, `{nom_underscore}` |
| `{titre}` | titre du jeu de feuilles (carnet) |
| `{date}` | `AAAA-MM-JJ` — aussi `{date_jour}`, `{date_mois}`, `{date_annee}` |
| `{projet_nom}` `{projet_numero}` `{projet_client}` `{projet_statut}` | infos du projet |
| `{param:NOM}` | n'importe quel paramètre de la feuille |
| `{param_projet:NOM}` | n'importe quel paramètre des informations du projet |

Un jeton vide ou introuvable **disparaît** du nom : jamais de `{...}` brut en
sortie. Les caractères interdits par Windows sont retirés automatiquement.

## Les autres outils, en bref

**Dupliquer feuilles / vues.** Sélection → options → aperçu → validation. Vous
choisissez ce qui suit la copie (vues, légendes, nomenclatures, détails), le mode
de duplication, et le renommage appliqué aux copies.

**ImageCrop.** Dessinez des régions remplies par-dessus une image importée,
sélectionnez l'image *et* ces zones, lancez l'outil : chaque zone produit un
morceau calé dans son cadre. L'original est conservé, rien n'est détruit.

**Importer SVG.** Passe par un DXF temporaire, et prévient avant une
décomposition vouée à échouer plutôt que de laisser Revit produire un import vide.

**Matériaux.** L'éditeur montre un aperçu *fidèle* des motifs de surface — taille
réelle, densité, phase des tirets — pas une vignette approximative.

**Align.** L'alignement se cale sur les extrêmes de la sélection, pas sur la vue.
Les **éléments épinglés servent de référence** : ils ne bougent pas, les autres
viennent s'y aligner. Si toute la sélection est épinglée, l'outil le dit et ne
touche à rien. La répartition espace également les centres.

## Ce que ce n'est pas

- **Pas un modeleur.** 418 déplace, nomme, exporte et recadre. Il ne dessine rien.
- **Pas un gestionnaire de projet.** Aucune nomenclature, aucun suivi, aucun rendu.
- **Pas un garde-fou.** L'aperçu vous protège de la faute de frappe, pas de la
  mauvaise décision. Relisez-le.

## Outils en bêta

Certains outils sont au dépôt mais pas finalisés. Ils portent le drapeau bêta de
pyRevit : le bouton n'est pas construit, rien n'apparaît dans le ruban. Pour les
afficher : **pyRevit → Settings → « Load Beta Tools »**, puis Reload.

| Onglet | Outil | État |
|---|---|---|
| Audit | **Audit** | Analyse de santé du modèle — fonctionnel, pas stabilisé |
| Manage | **Filtres**, **Feuilles**, **Vues** | Ossatures MVVM seules : la fenêtre s'ouvre, rien n'est branché |
| OpenArchi | **Chat** | Harnais LLM : panneau de chat ancré, pont MCP vers la maquette |
| Tools | **Rampe parking** | Lit les contraintes d'une rampe pour le calculateur NF P91-100 |

Ne comptez pas dessus en production : ça peut changer ou disparaître sans préavis.

## Réglages

Mappage des paramètres, motifs de nommage, destination, setups : tout est
mémorisé entre les sessions dans `418.extension/data/`. Rien à reconfigurer au
prochain lancement. Ces réglages sont locaux à votre poste et non versionnés.

## Problème ?

- **L'onglet 418 n'apparaît pas** — vérifier que le dossier s'appelle bien
  `418.extension` et qu'il est dans `%APPDATA%\pyRevit\Extensions`, puis Reload.
- **Un bouton reste grisé** — Revit 2026 minimum.
- **« Aucun jeu qualifié » à l'export** — le mappage n'est pas fait, ou le
  paramètre Oui/Non n'est coché sur aucun jeu.
- **Autre** — [ouvrir une issue][issues].

## Développement

[CLAUDE.md](CLAUDE.md) pour l'architecture, les conventions et le cycle de
développement. [CONTEXT.md](CONTEXT.md) pour le vocabulaire métier.

## Licence

MIT. Voir [LICENSE](LICENSE). © Aliae

[pyrevit]: https://github.com/eirannejad/pyRevit
[issues]: https://github.com/aliae2425/418.extension/issues
