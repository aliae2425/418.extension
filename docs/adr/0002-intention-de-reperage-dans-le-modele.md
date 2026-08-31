# L'intention de repérage vit dans le modèle, pas dans UserConfig

Les règles de repérage sont persistées par **Extensible Storage** sur un
`DataStorage` du document, et non dans `UserConfig` comme tout le reste de
l'extension. Le repérage est une décision de projet, pas une préférence
personnelle : dans un `UserConfig` — un fichier JSON par utilisateur, sur son
poste — deux architectes d'un même projet central ont deux jeux de règles
divergents et invisibles l'un de l'autre, et le dernier qui applique écrase le
travail de l'autre sans un mot.

## Considered Options

Un paramètre de projet texte sur `ProjectInformation` contenant le même JSON
serait plus simple à écrire, et le dépôt sait déjà lire `ProjectInformation`.
Écarté : la valeur est visible et éditable à la main dans les propriétés du
projet, sur une donnée que l'outil ne sait pas reconstruire — un filtre posé ne
redonne pas la règle qui l'a produit. C'est une perte silencieuse programmée.

Un fichier à côté du `.rvt` ne demande aucune API mais casse dès que le fichier
bouge, et rien ne le lie au modèle.

Encoder l'intention dans le nom du filtre pour la rendre relisible a été
écarté : quelqu'un renomme un filtre à la main et l'intention est perdue.

## Consequences

Le GUID du schéma est éternel : le faire évoluer demande une migration écrite à
la main. Le schéma doit donc porter un numéro de version dès le premier jour.

Toute sauvegarde est désormais une transaction Revit. Il n'y a plus de
persistance au vol à chaque clic : les règles sont écrites au moment
d'« Appliquer », intention et filtres dans la même transaction. Un état « réglé
mais pas appliqué » ferait diverger l'intention stockée et le modèle, ce que
cette décision existe précisément pour empêcher — d'où un avertissement à la
fermeture si des changements n'ont pas été appliqués.
