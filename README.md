# 418.extension

Tous les outils présentés dans cette extension ont été développés pour simplifier mon utilisation personnelle de Revit. Ils répondent à des besoins spécifiques rencontrés au quotidien. Cependant, je reste ouvert à toute suggestion ou idée d'amélioration pour enrichir ces fonctionnalités.
Une intégration de certains outils directement dans pyRevit pourra être envisagée ultérieurement selon leur utilité et les retours des utilisateurs.

**Outils clés**:
- BatchExport
- Keynote manager

## Installation

### Prérequis
- [pyRevit](https://github.com/eirannejad/pyRevit) doit être installé sur votre machine (compatible Revit 2018+).

### Méthode recommandée
1. Téléchargez ou clonez ce dépôt dans le dossier d’extensions pyRevit :
	- Généralement : `C:\Users\<utilisateur>\AppData\Roaming\pyRevit\Extensions\`
3. Vérifiez que le dossier s’appelle bien `418.extension` (et non `418.extension-main` ou autre).
4. Recharger pyrevit
5. L’onglet **418** doit apparaître dans le ruban Revit.

### Mise à jour
Pour mettre à jour, remplacez simplement le dossier par la nouvelle version et rechargez pyRevit.
## Fonctionnalités

| Fonctionnalité                | Description                                                                                   | Statut      | Remarques                                  |
|-------------------------------|----------------------------------------------------------------------------------------------|-------------|---------------------------------------------|
| **BatchExport**               | Export en masse basé sur les jeux de feuilles (PDF/DWG), profils, nommage, prévisualisation   | Actif       | Outil principal                             |
| **Keynotes Editor**           | Refonte de l’éditeur de keynotes pyRevit pour une utilisation plus fluide                    | En cours    |                                            |
| **Edit Material**             | Permet de remplacer facilement toutes les instances d’un matériau par un autre               | En cours    |                                            |
| **Repérage**                  | Génère des filtres pour repérer les coupes selon la sélection de feuilles                    | En cours    |                                            |
| **Nommage automatique des vues** | Script activable qui maintient les noms des vues à jour selon un pattern défini par l’utilisateur | À venir     | Peut être activé/désactivé                  |
| **CadastreImporter**          | (Abandonné) Devait importer le cadastre selon la géolocalisation                             | Abandonné   | Limite Python 3.2, à tester en C#           |


## Roadmap

- Améliorations continues de BatchExport (ergonomie, profils, stabilité)
- Keynotes Editor : nouvelle interface plus fluide et rapide (à venir)
- Nommage automatique des vues : script activable pour garder les noms à jour selon un pattern
- Finalisation de Repérage et Edit Material
- Tests d’intégration pour Revit 2026+


## Contribution

Les contributions sont bienvenues !

- Pour signaler un bug ou suggérer une amélioration, ouvrez une **issue** sur le dépôt (merci de détailler le contexte et la version de Revit/pyRevit).
- Pour proposer du code : fork, créez une branche claire (`fix/…` ou `feature/…`), faites un PR avec une description concise.
- Respectez le style du projet (Python 2/3 compatible, docstrings, commentaires en français ou anglais).