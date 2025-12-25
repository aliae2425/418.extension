# 418.extension

Une extension pyRevit conçue pour faciliter et automatiser l'exportation en lot de feuilles Revit vers les formats PDF et DWG.

## 🚀 Fonctionnalités

| Nom | Description | Version | Status |
|-----|-------------|---------|--------|
|BatchExport| Option d'export à partir des jeux de feuilles.|0.3|🖋️|
|Repérage| Crée des filtres en fonction de la sélection ou du jeu de feuilles|-|⏳|
|Edit material| Gestion des matériaux un peu plus sympa|-|⏳|
|KeyNotes editor| Gestion des matériaux un peu plus sympa|-|⏳|
|CadastreImporter| Importe automatiquement le cadastre en fonction de la géolocalisation|-|⏳|


## 📦 Installation

1.  Assurez-vous que [pyRevit](https://github.com/eirannejad/pyRevit) est installé sur votre machine.
2.  Installez cette extension via le gestionnaire d'extensions pyRevit ou en clonant ce dépôt dans votre dossier d'extensions.
3.  Rechargez pyRevit.

## 🛠️ Utilisation

1.  Allez dans l'onglet **418** du ruban Revit.
2.  Cliquez sur le bouton **Batch Export** dans le panneau Export.
3.  **Configuration** :
    *   Sélectionnez les paramètres Revit qui pilotent l'export (ex: "A Exporter", "Est un Carnet").
    *   Choisissez vos configurations d'export (Setups) PDF et DWG définies dans Revit.
    *   Définissez le dossier de destination.
4.  **Nommage** : Cliquez sur les icônes de configuration pour définir les règles de nommage des feuilles et des carnets.
5.  **Lancement** : Vérifiez le résumé dans la grille de prévisualisation et cliquez sur **Exporter**.