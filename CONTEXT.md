# 418.extension

Glossaire du vocabulaire métier de l'extension. Uniquement des définitions —
aucune décision d'implémentation, aucune spécification.

## Repérage des coupes

**Plan de repérage** (PDR) :
Une vue en plan dont la raison d'être est de montrer où sont les coupes du
projet. C'est le plan qui porte le filtre, et l'unité que l'utilisateur édite.
_Éviter_ : plan de coupes, plan de situation.

**Repère** :
La marque graphique d'une coupe ou d'une élévation telle qu'elle apparaît sur
un PDR. C'est le repère qu'on masque, jamais la coupe elle-même.
_Éviter_ : symbole, marqueur, trait de coupe, callout.

**Coupe** :
Une vue de type `Section` ou `Elevation`, c'est-à-dire tout ce qui laisse un
repère sur un plan. Le mot couvre donc les élévations.
_Éviter_ : section, vue de coupe.

**Jeu** :
Un jeu de feuilles Revit (`SheetCollection`). Sert à désigner d'un coup toutes
les coupes ou tous les PDR d'un lot de feuilles — « les coupes du PC ».
_Éviter_ : lot, phase, collection, set.

**Feuille** :
La feuille Revit (`ViewSheet`) sur laquelle une vue est posée. Une coupe hors
feuille n'a pas de jeu.

**Règle** :
L'intention exprimée sur un PDR : quels repères y restent visibles. Elle se
règle plan par plan, jamais coupe par coupe.
_Éviter_ : filtre (le filtre est ce que Revit écrit, pas ce que l'on décide).

**Filtre** :
Le `ParameterFilterElement` que l'outil écrit dans le modèle pour appliquer une
règle. C'est un produit, pas une intention : il ne se relit pas.
_Éviter_ : règle, override.

**Appliquer** :
Traduire les règles en filtres et les poser sur les PDR. Le sens inverse
n'existe pas : un filtre posé ne redonne pas la règle qui l'a produit.
