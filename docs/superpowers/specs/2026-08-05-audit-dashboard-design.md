# Design — Audit de maquette (dashboard consultatif)

**Date** : 2026-08-05
**Branche** : `feat/Audit` (à rebaser sur `Developpement` — voir §1)
**Statut** : Validé — prêt pour plan d'implémentation
**Maquette visuelle** : `scratchpad/audit-dashboard-mockup.html` (artifact validé)

## Objectif

Doter le panneau `Audit.panel/Audit.pushbutton/` d'un tableau de bord **consultatif** (lecture
seule) qui analyse la santé de la maquette Revit et présente, en un coup d'œil, les éléments
conformes et problématiques. Aucune modification du modèle n'est effectuée par l'outil.

Cible Revit **2027** (`__min_revit_ver__ = 2026` conservé, l'outil vise 2027).

## Périmètre v1 — 5 thèmes de contrôle

| Thème | Source API Revit | Gravité attribuée |
|---|---|---|
| **Avertissements** | `doc.GetWarnings()` groupés par description | Doublons au même endroit = Critique ; reste = À revoir |
| **À purger** | `Document.GetUnusedElements()` (API native ≥ 2024) : familles, matériaux, motifs, gabarits de vue non utilisés | À revoir |
| **Vues & Feuilles** | Vues hors feuille, gabarit manquant, niveaux/quadrillages au nom par défaut, noms de vues dupliqués | Non placée **et** gabarit manquant = Critique ; reste = À revoir |
| **Imports / Liens CAD** | `ImportInstance` explosés (import et non lien), liens CAD rompus, motifs de lignes importés | Import explosé = Critique ; lien rompu / motif importé = À revoir |
| **Nommage** | Noms de vues et de familles confrontés à des regex de convention | Non conforme = À revoir |

## 1. Prérequis de branche

`feat/Audit` est en retard de la bibliothèque partagée (elle n'a que
`core.AppPaths / UserConfig / sanitize`). **Rebaser `feat/Audit` sur `Developpement`** pour
récupérer :

- `core.selection` — sélection/navigation vers un élément dans Revit (« Sélectionner & fermer »).
- `core.selection_list` + `core.text_filter` — listes « Tout afficher » filtrables.
- Base MVVM déjà présente (`ui.base.BaseWindow/BaseViewModel`, helpers, ressources de thème).

`feat/Audit` n'a qu'un seul commit unique (`batch_export.json`) → rebase quasi sans conflit.
**`core.transaction` n'est PAS requis** (audit strictement lecture seule).

## 2. Mode fenêtre & contexte API Revit (décision structurante)

`BaseWindow.show()` fait `ShowDialog()` → **fenêtre modale**. BatchExport appelle l'API Revit
directement dans ses handlers de bouton (valide, car on reste sur le thread API de la commande
pyRevit). La v1 de l'audit **suit ce pattern modal** :

- **Auto-lancement à l'ouverture** = l'audit s'exécute **avant** `ShowDialog()`, pendant l'`__init__`
  du `MainViewModel`, sous la **barre de progression pyRevit** (`pyrevit.forms.ProgressBar` ou
  équivalent). La fenêtre s'affiche déjà remplie. Aucun `Dispatcher.BeginInvoke`, aucun spinner
  qui resterait figé (le thread UI est bloqué en modal).
- **« Relancer l'audit »** ré-exécute `AuditRunner.run(doc)` dans le handler (thread API OK) puis
  rafraîchit les VMs.
- **Action sur une ligne = « Sélectionner & fermer »** : `core.selection` positionne la sélection
  Revit (`uidoc.Selection.SetElementIds` + `ShowElements`) **puis** ferme la fenêtre, pour que
  l'utilisateur atterrisse sur l'élément. La sélection « live » (garder le dashboard ouvert pendant
  qu'on navigue dans Revit) impose un modèle **modeless + `ExternalEvent`** que `BaseWindow` ne
  gère pas → **hors périmètre v1** (voir Évolutions futures).

## 3. Structure des fichiers (pattern MVVM du projet)

```
418.tab/Audit.panel/Audit.pushbutton/
├── script.py                         # existe — instancie VM + View, view.show()
├── icon.png / icon.dark.png          # existent
├── GUI/Views/MainWindow.xaml         # coquille commune existante → à peupler (§6)
└── lib/
    ├── __init__.py
    ├── models/
    │   ├── __init__.py
    │   ├── Severity.py               # OK / A_REVOIR / CRITIQUE (+ ordre de gravité)
    │   ├── AuditIssue.py             # element_id, nom, emplacement, type, gravité, message
    │   ├── ThemeResult.py            # clé, libellé, analysés, issues[], pire_gravité, compte
    │   └── AuditResult.py            # themes[], score, top_critiques[], méta_modèle
    ├── services/
    │   ├── __init__.py
    │   ├── checks/
    │   │   ├── __init__.py
    │   │   ├── BaseCheck.py          # interface run(doc) -> ThemeResult
    │   │   ├── WarningsCheck.py
    │   │   ├── PurgeCheck.py
    │   │   ├── ViewsSheetsCheck.py
    │   │   ├── CadImportsCheck.py
    │   │   └── NamingCheck.py
    │   ├── AuditRunner.py            # orchestre les 5 checks, agrège en AuditResult
    │   ├── ScoreService.py           # score 0-100 (pur, testable)
    │   └── ReportExporter.py         # rapport HTML autonome
    ├── viewmodels/
    │   ├── __init__.py
    │   ├── MainViewModel.py          # état global, commandes Lancer/Exporter, liste des ThemeCardVM
    │   ├── ScoreVM.py
    │   ├── ThemeCardVM.py            # une carte détail dépliable
    │   └── IssueRowVM.py             # une ligne de tableau (+ commande Sélectionner&fermer)
    └── views/
        ├── __init__.py
        └── MainWindowView.py         # existe — charge le XAML via BaseWindow (modal)
└── tests/
    ├── test_score_service.py
    ├── test_audit_runner.py          # checkers mockés
    └── test_naming_check.py          # logique regex (pure)
```

## 4. Modèles de données

- **`Severity`** : trois niveaux `OK`, `A_REVOIR`, `CRITIQUE`, avec un rang comparable
  (`CRITIQUE > A_REVOIR > OK`) pour calculer la « pire gravité » d'un thème.
- **`AuditIssue`** : `element_id` (int/`ElementId`, ou `None` pour un agrégat), `nom` (str),
  `emplacement` (str, ex. « Vue : Plan RDC »), `type` (str, ex. « Import explosé »),
  `gravite` (`Severity`), `message` (str court).
- **`ThemeResult`** : `cle` (str, ex. `"cad"`), `libelle` (str), `analyses` (int — total examiné,
  peut être `None` si non pertinent comme pour les warnings), `issues` (`list[AuditIssue]`),
  propriétés dérivées `compte` (len issues), `pire_gravite`.
- **`AuditResult`** : `themes` (`list[ThemeResult]`), `score` (int 0-100), `top_critiques`
  (`list[AuditIssue]`, ~5 items les plus graves toutes catégories), `meta` (nom fichier, version
  Revit, horodatage, nb éléments analysés). Objets purs Python, sans dépendance Revit → testables.

## 5. Services

### 5.1 Checkers (`checks/`)

`BaseCheck` définit `run(doc) -> ThemeResult`. Chaque checker :

- encapsule **tous** ses appels Revit dans `try/except` ; en cas d'échec, renvoie un `ThemeResult`
  marqué « indisponible » (compte `None`, message d'erreur) plutôt que de lever.
- est **indépendant** des autres (aucun état partagé).

Détails par checker :

- **WarningsCheck** : `doc.GetWarnings()` → regroupe par `GetDescriptionText()`. Heuristique de
  gravité : la description contenant « dupliqu » / « same location » ⇒ `CRITIQUE`, sinon
  `A_REVOIR`. Chaque groupe = un `AuditIssue` avec le nombre d'occurrences dans `message`.
- **PurgeCheck** : `Document.GetUnusedElements(HashSet[ElementId]())` (API 2024+). Regroupe les
  ids par catégorie (familles, matériaux, motifs, gabarits de vue). Un `AuditIssue` par catégorie
  avec le compte. **Pas d'estimation de taille disque** (non fournie par l'API).
- **ViewsSheetsCheck** : parcourt les vues (hors gabarits) → non placée sur feuille
  (`Viewport` absents), gabarit manquant (`ViewTemplateId == InvalidElementId`), noms de vues
  dupliqués ; niveaux/quadrillages au nom par défaut (regex `^(Niveau|Level|Quadrillage|Grid)\s*\d+$`).
  Non placée **et** sans gabarit ⇒ `CRITIQUE`.
- **CadImportsCheck** : `ImportInstance` — distingue import (explosé, `IsLinked == False`) de lien.
  Import non lié dans une vue ⇒ `CRITIQUE`. Liens CAD dont le chemin est introuvable ⇒ `A_REVOIR`.
  Motifs de lignes importés (préfixe `IMPORT`) ⇒ `A_REVOIR`.
- **NamingCheck** : confronte noms de vues et de familles à des **regex de convention**.
  - **Source de vérité** : constantes par défaut dans `NamingCheck` (`DEFAULT_VIEW_REGEX`,
    `DEFAULT_FAMILY_REGEX`), **surchargeables** via `UserConfig('audit')` aux clés
    `naming_view_regex` / `naming_family_regex`. Pas d'UI de configuration en v1 (édition via le
    fichier de config pyRevit). Regex par défaut volontairement permissives (documentées, à affiner).

### 5.2 AuditRunner

`run(doc) -> AuditResult` : instancie les 5 checkers, appelle `run(doc)` sur chacun (chacun isolé),
assemble les `ThemeResult`, calcule `top_critiques` (tri par gravité puis compte), délègue le score
à `ScoreService`, remplit `meta`. Testable en injectant des checkers mockés.

### 5.3 ScoreService — formule (constantes v1, ajustables)

Score = pénalités pondérées par thème, plancher 0 :

```
severite_base(theme) = 10 si le thème contient au moins un CRITIQUE
                     =  4 si au moins un A_REVOIR (et aucun CRITIQUE)
                     =  0 sinon
poids_theme          = { warnings: 1.0, cad: 1.0, vues_feuilles: 1.0,
                         purge: 0.6, nommage: 0.5 }
volume(theme)        = min(8, 0.05 * nombre_issues_du_theme)   # nudge volumétrique borné
penalite(theme)      = poids_theme * severite_base(theme) + volume(theme)

score = round( max(0, 100 - somme(penalite(theme) pour les 5 thèmes)) )
```

Rationale : la présence d'un critique domine ; le volume ne fait que moduler (borné à 8 pts/thème) ;
purge et nommage pèsent moins (moins graves pour la « santé »). Les constantes sont regroupées en
tête de `ScoreService` pour un réglage facile. Le score « 72 » de la maquette est **illustratif** ;
la valeur réelle dépend du modèle.

### 5.4 ReportExporter

`export_html(audit_result, chemin) -> chemin_ecrit` : génère un **fichier HTML autonome** (CSS
inline) reproduisant le dashboard (récap + score + tableaux par thème). Nom de fichier via la
`sanitize` partagée (`Audit_<nom-modele>_<date>.html`). Ouvre le dossier en fin d'export (comme le
modal « Export terminé » de BatchExport). Emplacement par défaut : dossier configurable via
`UserConfig('audit')` clé `report_dir`, défaut = `Documents`.

## 6. UI — peuplement de la coquille commune

`MainWindow.xaml` existe déjà (coquille borderless Fluent : barre de titre, rail 64px, surface
flottante, footer). À peupler dans la surface de contenu, conformément à la maquette validée :

- **Bandeau contexte** : nom du modèle + méta (Revit 2027, horodatage, nb éléments analysés).
- **Récap (3 cartes, ordre : Critiques · Répartition · Score)** :
  - *Principaux problèmes critiques* : liste priorisée (`top_critiques`), puce de gravité.
  - *Répartition par thème* : barres empilées conforme/à revoir/critique + compteur `problèmes/total`.
  - *Score* : jauge (arc `stroke-dasharray`), verdict, mini-stats.
- **Détail par thème** : 5 cartes **dépliables** (une par `ThemeCardVM`) ; en-tête bandeau de
  gravité + badge + pastille de compteur ; corps = tableau des `IssueRowVM` (élément, id,
  emplacement, type, gravité). Bouton « Tout afficher » → liste filtrable
  (`selection_list` + `text_filter`).
- **Footer** (coquille) : « Exporter le rapport » (secondaire) + « Relancer l'audit » (primaire) ;
  mention « Audit consultatif · lecture seule ».

Rail de navigation : items « Vue d'ensemble » / « Détails » + engrenage Paramètres en bas (déjà
prévus par la coquille). Thème clair/sombre appliqué automatiquement par `BaseWindow` /
`UIResourceLoader` (pas de bascule utilisateur en v1 — la bascule de la maquette est un artifice de
démo). Toutes les couleurs via ressources de thème partagées ; sémantique bon/à revoir/critique =
vert / orange / rouge (distincte de l'accent Fluent).

## 7. Flux de données

`script.py` → `MainViewModel(doc)` → (dans l'`__init__`) `AuditRunner.run(doc)` sous barre de
progression → `AuditResult` peuple `ScoreVM` + 5 `ThemeCardVM` → `MainWindowView.show()`
(`ShowDialog`, fenêtre déjà remplie) → l'utilisateur déplie une carte → « Tout afficher » ouvre la
liste filtrable → « Sélectionner & fermer » sur une ligne → `core.selection` sélectionne/zoome puis
ferme → « Relancer l'audit » ré-exécute et rafraîchit → « Exporter le rapport » écrit le HTML et
ouvre le dossier.

## 8. Gestion des erreurs

- Chaque checker isolé (`try/except`) : un thème en échec devient une carte « indisponible », les
  autres restent affichés.
- Tous les imports inter-couches en `try/except` + fallback `None`, vérifiés avant usage (convention
  projet), pour rester exécutable hors Revit.
- `AuditRunner` protège l'ensemble : si `doc is None` (hors Revit), renvoie un `AuditResult` vide
  cohérent (score 100, thèmes « non analysés ») pour permettre le rendu et les tests.

## 9. Tests (standalone, hors Revit)

- `test_score_service.py` : formule de score (cas 0 issue, critiques, plafonnement, plancher 0).
- `test_audit_runner.py` : agrégation avec checkers mockés (`top_critiques`, robustesse d'un checker
  qui lève).
- `test_naming_check.py` : logique regex (conforme / non conforme) sans dépendance Revit.

Les checkers dépendants de l'API Revit (Warnings, Purge, Vues, CAD) sont testés **manuellement dans
Revit** (Reload pyRevit → clic bouton).

## 10. Contraintes techniques (conventions du projet)

- En-tête `# -*- coding: utf-8 -*-` + `from __future__ import unicode_literals` sur chaque `.py`.
- Imports inter-couches en `try/except` avec fallback `None`.
- Textes UI, commentaires et messages de commit en **français**.
- `AppPaths` pour résoudre le XAML (jamais de chemin en dur).
- `UserConfig('audit')` pour toute persistance (regex de nommage, dossier de rapport).

## 11. Hors périmètre (YAGNI v1)

- Toute **action corrective** (purge, renommage, suppression) — l'outil est consultatif.
- Fenêtre **modeless + ExternalEvent** pour sélection « live » sans fermer (évolution future).
- Export **CSV** ou **PDF natif** (HTML seulement ; PDF via impression navigateur).
- Contrôles supplémentaires (worksets, groupes, familles in-place, poids détaillé, révisions).
- UI de configuration des conventions de nommage (édition via config pour l'instant).
- Historisation / comparaison de scores dans le temps.
- Multi-langue.

## 12. Évolutions futures (notées, non v1)

- Passage modeless + `ExternalEvent` pour navigation Revit sans fermer le dashboard.
- Actions correctives one-clic (purger, renommer) réutilisant `core.transaction`.
- Contrôles additionnels et pondérations de score par profil d'agence.
- Export CSV/PDF, historique de santé.

## 13. Critères de réussite

1. Après rebase sur `Developpement` + Reload pyRevit, le bouton **Audit** ouvre une fenêtre déjà
   remplie (audit exécuté à l'ouverture, barre de progression pendant la collecte).
2. Le récap montre score, répartition par thème (barres bon/problème) et top problèmes critiques,
   dans l'ordre Critiques · Répartition · Score.
3. Les 5 cartes détail se déplient et listent des éléments réels du modèle avec leur gravité.
4. « Sélectionner & fermer » sur une ligne sélectionne l'élément dans Revit et ferme la fenêtre.
5. « Relancer l'audit » recalcule et rafraîchit l'affichage.
6. « Exporter le rapport » produit un HTML autonome fidèle au dashboard et ouvre le dossier.
7. Le rendu respecte le thème clair et sombre.
8. `python script.py` hors Revit ne lève pas d'exception (dégradation propre), et les tests
   standalone passent.
