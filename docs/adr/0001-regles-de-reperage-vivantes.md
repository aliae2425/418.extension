# Les règles de repérage sont vivantes

Le repérage des coupes s'exprime sur la **place** d'une coupe — le numéro de
feuille et le jeu de feuilles de la vue, tels que Revit les expose comme
paramètres filtrables sur `OST_Sections` — et non sur son nom. Le filtre posé
dit « masque tout repère dont la feuille n'est pas A01 », jamais « masque tout
sauf Coupe AA et Coupe BB ». Revit réévalue donc la règle seul : une coupe
ajoutée, retirée ou déplacée met les plans à jour sans repasser par l'outil.

## Considered Options

L'implémentation évidente — celle du premier jet de cet outil — résout la règle
en Python et gèle le résultat en une liste de `NotEquals` sur
`BuiltInParameter.VIEW_NAME`. Elle a été retirée : rien ne se met à jour, et
renommer une coupe fait disparaître son repère de tous les plans, sans erreur,
des semaines plus tard.

Un paramètre partagé stable écrit sur chaque repère (`418_PDR_visible`)
immuniserait tout contre le renommage. Écarté : l'outil cesserait d'écrire des
filtres pour se mettre à tatouer des éléments, avec un paramètre partagé à
déployer sur tous les projets.

## Consequences

Le mode « Coupes choisies » — désigner une coupe précise où qu'elle soit — ne
peut pas être vivant : le seul identifiant filtrable d'une coupe est son nom.
C'est la seule règle **gelée** de l'outil, et elle casse au renommage. Le
compromis est assumé : la dérive est détectée à l'ouverture et se répare en
réappliquant.

L'outil n'a donc pas besoin de connaître les coupes du modèle, sauf pour ce
mode. Aucun aperçu chiffré n'est affiché : un compte serait un instantané d'une
règle qui change toute seule. Les règles se lisent en toutes lettres.

Le paramètre « Jeu de feuilles » est résolu à l'exécution en parcourant
`ParameterFilterUtilities.GetFilterableParametersInCommon` et en comparant les
libellés — son `BuiltInParameter` n'est pas supposé connu, ce qui survit au
changement de nom interne et à la langue de l'installation.
