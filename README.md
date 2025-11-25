# 418.extension

Une extension pyRevit conçue pour faciliter et automatiser l'exportation en lot de feuilles Revit vers les formats PDF et DWG.

## 🚀 Fonctionnalités

| Nom | Description | Version | Status |
|-----|-------------|---------|--------|
| Export Multi-Collections | Traitez plusieurs collections de feuilles en une seule opération | - | ✅ |
| Formats Supportés | Export simultané en **PDF** et **DWG** | - | ✅ |
| Nommage Intelligent | Configurez des modèles de nommage dynamiques utilisant n'importe quel paramètre de Projet, de Collection ou de Feuille avec prévisualisation en temps réel | - | ✅ |
| Options de Sortie Flexibles | Export par feuille individuelle ou combiné en carnets PDF, création automatique de sous-dossiers par collection, tri automatique par format | - | ✅ |
| Gestion des Fichiers | Détection automatique des fichiers existants avec choix d'écraser ou de renommer | - | ✅ |
| Interface Conviviale | Suivi de la progression et statut détaillé (succès/erreur) pour chaque fichier | - | ✅ |

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