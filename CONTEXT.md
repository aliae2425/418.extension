# 418.extension

Glossaire du vocabulaire métier de l'extension. Uniquement des définitions —
aucune décision d'implémentation, aucune spécification.

## Repérage des coupes

**Plan de repérage** (PDR) :
Une vue en plan dont la raison d'être est de montrer où sont les coupes du
projet. C'est le plan qui porte le filtre, et l'unité que l'utilisateur édite.
_Éviter_ : plan de coupes, plan de situation.

**Repère** :
La marque graphique d'une coupe telle qu'elle apparaît sur un PDR. C'est le
repère qu'on masque, jamais la coupe elle-même.
_Éviter_ : symbole, marqueur, trait de coupe, callout.

**Coupe** :
Une vue de type `Section`. Les élévations sont hors du repérage : leur repère
est un marqueur d'annotation, qui ne porte pas les propriétés sur lesquelles
une règle s'exprime.
_Éviter_ : section, vue de coupe.

**Jeu** :
Un jeu de feuilles Revit (`SheetCollection`). Sert à désigner d'un coup toutes
les coupes d'un lot de feuilles — « les coupes du PC ».
_Éviter_ : lot, phase, collection, set.

**Feuille** :
La feuille Revit (`ViewSheet`) sur laquelle une vue est posée. Une coupe hors
feuille n'a pas de jeu.

**Règle** :
L'intention exprimée sur un PDR : quels repères y restent visibles. Elle se
règle plan par plan, jamais coupe par coupe.
_Éviter_ : filtre (le filtre est ce que Revit écrit, pas ce que l'on décide).

**Règle vivante** :
Une règle que Revit réévalue seul, parce qu'elle désigne les coupes par leur
place (feuille, jeu) et non par leur identité. Ajouter une coupe met les plans
à jour sans repasser par l'outil.
_Éviter_ : dynamique, automatique.

**Règle gelée** :
Une règle qui nomme les coupes une par une. Elle ne suit rien et se casse si
une coupe est renommée. C'est le prix du choix « cette coupe précise, où
qu'elle soit ».
_Éviter_ : statique, figée.

**Plan géré** :
Un PDR dont le repérage est confié à l'outil. Un plan non géré ne porte aucun
filtre de l'outil et garde l'affichage natif de Revit.

**Filtre** :
Le `ParameterFilterElement` que l'outil écrit dans le modèle pour appliquer une
règle. C'est un produit, pas une intention : il ne se relit pas.
_Éviter_ : règle, override.

**Appliquer** :
Traduire les règles en filtres et les poser sur les plans gérés. Le sens
inverse n'existe pas : un filtre posé ne redonne pas la règle qui l'a produit.

**Dérive** :
L'écart entre une règle et le filtre posé, quand le modèle a bougé sous lui —
une feuille renumérotée, un PDR déplacé, une coupe renommée. Se détecte à
l'ouverture, se répare en réappliquant.
