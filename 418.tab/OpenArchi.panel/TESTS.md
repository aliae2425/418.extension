# OpenArchi — recette du panneau

**Périmètre : le devant.** Le volet, la saisie, l'affichage, les commandes,
le pont vers les outils, la stabilité.

Ce qui concerne un outil Revit en particulier — est-ce qu'il rend la bonne
chose, sur la bonne unité, sans casser la maquette — se suit dans
[`lib/rvt/COUVERTURE.md`](../../lib/rvt/COUVERTURE.md). Ici on vérifie que le
volet sait *demander* et *montrer*, pas ce que l'outil répond.

| | |
|---|---|
| **Dernière passe** | _(date)_ |
| **Par** | |
| **Version 418** | _(cf. `VERSION`)_ |
| **Revit / projet** | |
| **Fournisseur · modèle** | |

**Avant de commencer** : redémarrer Revit — pas un Reload. `register_dockable_panel`
construit une instance que Revit garde pour la session, donc tout changement
Python du volet exige un redémarrage. Puis vider `data/418.log`, et fermer les
autres clients qui taperaient sur le serveur de routes : deux clients à la
fois, c'est une course qu'on ne maîtrise pas.

**Les 149 tests automatiques tournent d'abord** — ils couvrent la boucle, les
permissions, les protocoles et l'historique. Cette recette ne reprend QUE ce
qu'ils ne peuvent pas atteindre : le DOM, le WebView2, et Revit.

```bash
for t in $(git ls-files '*/tests/test_*.py'); do python "$t" >/dev/null || echo "ECHEC $t"; done
node --test "lib/web/**/tests/*.test.js"
```

Légende : `[ ]` à faire · `[x]` conforme · `[!]` anomalie (à reporter en bas).

---

## 1 · Le volet vit

- [ ] Le volet s'ouvre, l'accueil montre la théière et pose sa question
- [ ] **Ancrer, désancrer, faire flotter, ré-ancrer** : la page survit aux
      quatre, rien ne devient blanc
- [ ] Thème Revit **clair** → fond clair, logo sombre ; **sombre** → l'inverse
- [ ] Le volet s'ouvre sur un Revit **sans projet** sans rien casser
- [ ] Fermer et rouvrir le volet : il repart, sans doubler le WebView2

## 2 · La saisie

- [ ] Le champ **grandit** jusqu'à 5 lignes, puis une barre fine apparaît
- [ ] Aucune barre tant qu'il grandit encore
- [ ] **Entrée** envoie · **Maj+Entrée** saute une ligne
- [ ] **↑ ↓** rappellent les messages envoyés ; le brouillon en cours revient
      quand on redescend
- [ ] Dans un texte multiligne, **↑ ↓** déplacent le curseur au lieu de
      rappeler — sauf en haut et en bas du texte

## 3 · Les commandes

- [ ] Taper `/` ouvre la liste ; `/co` ne laisse que `connect`
- [ ] **Tab** complète · **↑ ↓** choisissent · **Échap** ferme
- [ ] Cliquer une entrée **remplit** le champ, ne l'exécute pas
- [ ] `/aide` liste les quatre commandes
- [ ] `/model gpt-4o` puis `/model` : le nom est retenu, le pied l'affiche

## 4 · Se connecter

- [ ] `/connect` ouvre le navigateur ; après connexion, le volet reprend la
      main seul et le pied dit `· abonnement`
- [ ] `/connect sk-…` : le pied dit `· clé`, sans redémarrer Revit
- [ ] `/logout` : le pied repasse à `non connecté`
- [ ] Reconnexion après `/logout` sans redémarrer
- [ ] **Port 1455 occupé** (lancer `codex login` d'abord) : le message nomme
      la cause au lieu d'un code brut

## 5 · Parler

- [ ] Le texte arrive **mot à mot**, pas d'un bloc
- [ ] Bulle « réfléchit… » avec le temps en dessous ; à la fin la bulle part
      et `12 s de réflexion` reste
- [ ] **Markdown** : gras, listes, code, tableau — le tableau défile dans son
      coin quand le volet est étroit
- [ ] **Stop** interrompt ; le fil dit « interrompu », pas « erreur »
- [ ] Une réponse longue défile et suit le bas toute seule
- [ ] Le texte des bulles se **sélectionne et se copie**

## 6 · Les outils

- [ ] « sur quelle vue je suis ? » → carte d'outil, **repliée**, état `fait`
- [ ] Cliquer la carte montre la sortie ; recliquer la referme
- [ ] Un outil en **échec** s'ouvre tout seul
- [ ] Routes pyRevit **décochées** → le pied dit `maquette muette`, le volet
      marche quand même
- [ ] Projet **fermé** → même chose, et le modèle le dit au lieu d'inventer

## 7 · L'accord sur un irréversible

C'est le point qu'on ne livre pas sans l'avoir vu marcher.

- [ ] Demander une synchronisation → la carte naît en **attente d'accord**,
      ouverte, avec les trois boutons
- [ ] Elle **ne se referme pas** tant qu'on n'a pas répondu
- [ ] **Refuser** → rien ne part, le modèle le dit
- [ ] **Accorder** → l'outil part une fois ; redemander redemande l'accord
- [ ] **Toujours** → l'outil part, et ne redemande plus de la session
- [ ] **Stop** pendant l'attente d'accord → le tour s'arrête proprement
- [ ] Hors du volet : `curl -X POST .../418/outil/revit_executer_code`
      répond **403**, sans exécuter

## 8 · Ce qui ne doit jamais arriver

- [ ] Revit ne tombe pas, quoi qu'il se passe dans le volet
- [ ] Revit reste **rendu à la main** pendant un appel d'outil et pendant
      l'attente du navigateur à la connexion
- [ ] Fermer Revit pendant un tour en cours ne le retient pas
- [ ] **F12 → Console** : aucune erreur rouge sur un parcours nominal
- [ ] Aucune clé, aucun jeton dans `data/418.log` ni dans la console

---

## Anomalies

| # | où | ce qui se passe | attendu | état |
|---|---|---|---|---|
| 1 | | | | |
