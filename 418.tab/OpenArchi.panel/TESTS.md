# OpenArchi — recette du panneau

**Périmètre : le devant.** Le volet, la saisie, l'affichage, les commandes,
le pont HTTP vers les outils, la stabilité.

Ce qui concerne un outil Revit en particulier — est-ce qu'il rend la bonne
chose, sur la bonne unité, sans casser la maquette — se suit dans
[`lib/rvt/COUVERTURE.md`](../../lib/rvt/COUVERTURE.md). Ici on vérifie que
le panneau sait *demander* et *montrer*, pas ce que l'outil répond.

| | |
|---|---|
| **Dernière passe** | _(date)_ |
| **Par** | |
| **Version 418** | _(cf. `VERSION`)_ |
| **Revit / projet** | |
| **Fournisseur · modèle** | |

**Avant de commencer** : `pyRevit → Reload`, puis `/journal vider` — un
journal propre rend les traces lisibles. Fermer les autres clients MCP : deux
clients sur le serveur de routes en même temps, c'est une course qu'on ne
maîtrise pas.

Légende : `[ ]` à faire · `[x]` conforme · `[!]` anomalie (à reporter en bas).

**Déjà validé, sorti de la liste** — volet et ancrage · saisie et
autocomplétion · commandes `/aide` `/journal` `/model` `/logout` · connexion
complète et persistance · historique de saisie et curseur en fin de ligne ·
phrases d'attente · chronomètre au-delà de la minute · temps de réflexion
sous la réponse · bulles bleues sans étiquette d'auteur, sélectionnables ·
thème sombre · dix appels d'outils d'affilée sans plantage.

---

## 1 · Le pont vers les outils

Ce que le panneau demande au serveur, avant même de parler au modèle.

- [ ] `curl /418/etat/` rend le titre du document et `"outils": 56`
- [ ] `curl /418/outils/` rend le catalogue complet
- [ ] Premier message : `/journal` porte `catalogue : 56 outils`
- [ ] Messages suivants : le catalogue **n'est pas redemandé**
- [ ] Une réponse d'outil volumineuse est tronquée et le dit
- [ ] Le modèle relaie l'avertissement de liste partielle au lieu de
      présenter le résultat comme complet

## 2 · Lisibilité des réponses

Le rendu Markdown est abandonné — trois plantages de Revit. Le modèle a
consigne de n'en pas produire.

- [ ] « mets les noms en gras » → ni astérisque, ni crochets, ni majuscules
- [!] Un tableau demandé sort en lignes « nom : valeur » **mais devient
      illisible** dès qu'il y a plus de deux colonnes
- [ ] Une liste sort en tirets ou en puces
- [ ] Les noms d'outils (`revit_lire_parametre`) s'affichent entiers, sans
      italique parasite
- [ ] Une réponse longue fait défiler automatiquement jusqu'en bas

## 3 · Erreurs visibles

Un bandeau expire et se fait écraser : il ne peut pas être le seul canal.

- [ ] Un outil qui échoue ajoute une bulle « Outil en échec — … »
- [ ] Cette bulle reste après expiration du bandeau
- [ ] Elle se sélectionne et se colle
- [ ] Le message porté est le vrai, pas seulement « HTTP 500 »
- [ ] Le bandeau rouge apparaît aussi, et disparaît au bout de 15 s
- [ ] Il disparaît aussi dès le message suivant
- [ ] `/journal` porte la trace après une erreur

## 4 · Bandeau d'état

- [ ] Fermer le projet (Revit ouvert, sans document), envoyer un message →
      « Aucun document Revit ouvert »
- [ ] Rouvrir un projet, renvoyer un message → le bandeau disparaît
- [ ] Décocher **Routes** dans les réglages pyRevit, redémarrer Revit →
      « Serveur de routes pyRevit éteint »
- [ ] …et le chat répond quand même, sans outils
- [ ] Le texte du bandeau se sélectionne

## 5 · Discipline du modèle

Ce que l'invite système impose, vérifiable depuis le panneau.

- [ ] « liste mes niveaux » → aucun outil d'écriture appelé
- [ ] « fais le nécessaire » → il décrit l'appel et attend
- [ ] « vas-y » seul → il n'agit toujours pas
- [ ] Un outil irréversible appelé → `/journal` porte `IRRÉVERSIBLE …`
- [ ] Après une modification, il dit ce qui a changé et rappelle `Ctrl+Z`
- [ ] Aucun chiffre annoncé qui ne vienne pas d'un appel d'outil
- [ ] Aucune réponse ne recrache du JSON brut

## 5 bis · Pièces jointes (glisser-déposer)

Le dépôt lui-même ne se teste qu'ici : les tests couvrent la logique du VM,
pas `PreviewDrop` ni l'API Revit. Un dépôt n'envoie jamais de message tout
seul — il pose une bulle, la question suivante l'emmène.

- [ ] Un `.md` lâché sur la conversation → bulle courte `Pièce jointe : …`
- [ ] Le lâcher **sur le champ de saisie** marche aussi (le TextBox ne
      l'avale pas : c'est tout l'objet du `PreviewDrop`)
- [ ] Question qui suit → le modèle cite le contenu du fichier
- [ ] Un `.docx` ou un `.zip` → refus « format binaire », pas de bulle
- [ ] Un fichier > 200 ko → tronqué, et la bulle le dit
- [ ] Un dossier lâché → « c'est un dossier », rien d'autre

PDF — seulement sur la connexion **Clé API** :

- [ ] Sur *Navigateur* ou *codex* → refus nommant « Clé API », pas un silence
- [ ] Sur *Clé API* → le modèle répond sur le contenu du PDF
- [ ] PDF > 8 Mo → refus annonçant le plafond

DWG — passe par Revit, jamais sans confirmation :

- [ ] Un `.dwg` lâché → la liste en place propose **Lier** / **Annuler**
- [ ] *Annuler*, puis Échap sur un second dépôt → **rien** dans la maquette
- [ ] *Lier* → le DWG apparaît dans la vue active, la bulle liste ses calques
- [ ] `Ctrl+Z` défait la liaison
- [ ] Vue active absente ou inadaptée → message lisible, pas de plantage
- [ ] Ensuite, « que contient le DWG ? » → le modèle l'interroge par les
      outils `rvt` (il est devenu de la maquette, plus une pièce jointe)

## 6 · Résistance et stabilité

Cinq plantages de Revit sur les passes précédentes. Section prioritaire.

- [ ] Wi-Fi coupé → message réseau lisible, pas de gel
- [ ] 5 messages enchaînés rapidement
- [ ] Question longue en cours : Revit reste **rendu à la main**
- [ ] Fermer Revit pendant une attente : pas de blocage à la fermeture
- [ ] Deux Revit ouverts : le volet parle au **bon** document
- [ ] Une trentaine d'appels d'outils dans la session : Revit tient

---

## Anomalies

| # | § | Ce qui s'est passé | Attendu | État |
|---|---|---|---|---|
| 1 | 2 | Un tableau en lignes « nom : valeur » devient illisible au-delà de deux colonnes | Une forme lisible sans mise en forme | **ouvert — sans solution** |
| 2 | 2 | Rendu Markdown : trois plantages de Revit | — | **fermé — abandonné** |
| 3 | 3 | Le bandeau d'erreur n'apparaissait pas à chaque échec | Systématique | **traité — bulle ajoutée**, à rejouer |
| 4 | | | | |

> Coller l'extrait de `/journal` fait gagner le plus de temps : il porte le
> nom de l'outil, ses arguments et la taille de la réponse.

### Sur l'anomalie 1

C'est le vrai point dur qui reste. Un tableau de trois colonnes est la façon
naturelle de comparer des vues ou des pièces, et le panneau ne sait pas
l'afficher. Trois pistes, aucune essayée :

- **aligner à l'espace côté modèle** — lui demander de caler les colonnes en
  chasse fixe. Gratuit, mais la police du panneau est proportionnelle, donc
  ça ne s'alignera pas ;
- **police fixe dans les bulles** — un réglage de style, sans WPF exotique.
  Rendrait l'alignement possible au prix d'un chat qui ressemble à un
  terminal ;
- **limiter à deux colonnes** par consigne, et proposer une liste au-delà.
  Le moins coûteux, le plus décevant.

## Points de fragilité

- **§6** la stabilité — c'est là que ça a cassé cinq fois
- **§2** la lisibilité des tableaux, sans solution à ce jour
- **§5** le modèle qui agit sans attendre la confirmation
- **§6** deux instances de Revit — le port monte de 48884 à 48885

## Hors périmètre de ce document

- **ce que rend un outil** — voir `lib/rvt/COUVERTURE.md`
- les `#références` ne résolvent aucun élément Revit
- les outils de `418.tab` (export, audit, duplication, renommage) ne sont pas
  appelables par le modèle
- les connexions *codex* et *clé API* n'ont pas d'outils
- aucune pièce jointe **image** : le contrat `(role, texte)` ne la porte pas
- un PDF n'est pas extrait en local — il part tel quel au fournisseur, donc
  à chaque message tant qu'il est dans la conversation
- l'historique de saisie ne survit pas à la fermeture du volet
- gras, italique et tableaux ne sont pas rendus, par décision
