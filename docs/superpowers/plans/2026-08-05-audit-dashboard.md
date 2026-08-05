# Audit de maquette — Dashboard consultatif — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Doter `418.tab/Audit.panel/Audit.pushbutton/` d'un tableau de bord consultatif (lecture seule) qui audite la santé d'une maquette Revit 2027 sur 5 thèmes et présente les éléments conformes/problématiques (score, répartition, top critiques, détail dépliable, export HTML).

**Architecture:** MVVM en couches, calqué sur BatchExport. Un `*Check` isolé par thème (interface `run(doc) -> ThemeResult`), agrégé par `AuditRunner` en `AuditResult`, scoré par `ScoreService`. UI = coquille commune existante (`MainWindow.xaml`) peuplée par des ViewModels. Fenêtre **modale** (`BaseWindow.ShowDialog`) ; audit lancé **avant l'affichage** sous barre de progression pyRevit. Aucune écriture dans le modèle.

**Tech Stack:** Python 2/3 (IronPython dans Revit / CPython pour les tests), pyRevit, WPF chargé via `XamlReader`, `unittest` pour les tests standalone, API Revit `Autodesk.Revit.DB`.

## Global Constraints

- Cible **Revit 2027** ; `__min_revit_ver__ = 2026` conservé dans `script.py`.
- En-tête de chaque `.py` : `# -*- coding: utf-8 -*-` puis `from __future__ import unicode_literals`.
- Tout import inter-couches / Revit / WPF en `try/except` avec fallback `None`, vérifié avant usage. Import interne au bouton = **double forme gardée** : `try: from X import Y` puis `except: from lib.X import Y`.
- Textes UI, commentaires, messages de commit en **français**.
- `AppPaths` pour résoudre le XAML (jamais de chemin en dur) ; `UserConfig('audit')` pour toute persistance.
- Audit **strictement lecture seule** — aucune transaction, aucune modification du modèle.
- Chaque module doit s'importer/s'exécuter hors Revit sans lever (dégradation propre).
- Tests standalone : bootstrap `sys.path` vers `418.extension/lib` (4 niveaux au-dessus de `tests/`) **et** vers le dossier du bouton ; lancés par `python <chemin>/test_x.py`.
- **Ne jamais commiter sans l'accord explicite de l'utilisateur** (consigne projet). Les étapes « Commit » du plan sont préparées mais l'exécutant demande le feu vert avant chaque `git commit`.

---

## Prérequis de test — bootstrap commun

Chaque fichier de test commence par ce bloc (adapté du projet) :

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
# 418.extension/lib (tests -> pushbutton -> Audit.panel -> 418.tab -> 418.extension)
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
# Dossier du bouton (pour 'from lib.models...')
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)
```

---

## Task 1: Prérequis — rebaser feat/Audit sur Developpement

**Files:** aucun fichier créé ; opération git + vérification.

**Interfaces:**
- Produces: la bibliothèque partagée `lib/core/{selection,selection_list,text_filter}.py` disponible sur `feat/Audit`, base MVVM (`ui.base`, `ui.helpers`) et ressources de thème.

- [ ] **Step 1: Vérifier l'état propre et sauvegarder**

Run:
```bash
git status --short
git branch backup/Audit-avant-rebase feat/Audit
```
Expected: arbre propre (hormis modif `.gitignore` non liée, à stasher si présente : `git stash push .gitignore`).

- [ ] **Step 2: Rebaser sur Developpement**

Run:
```bash
git fetch origin
git checkout feat/Audit
git rebase origin/Developpement
```
Expected: un seul commit rejoué (`batch_export.json`), aucun ou très peu de conflit. En cas de conflit sur `batch_export.json`, garder la version de `feat/Audit`.

- [ ] **Step 3: Vérifier la présence de la lib partagée**

Run:
```bash
ls lib/core/selection.py lib/core/selection_list.py lib/core/text_filter.py
```
Expected: les 3 fichiers existent.

- [ ] **Step 4: Vérifier que les tests partagés passent (non-régression)**

Run:
```bash
python lib/core/tests/test_text_filter.py
python lib/core/tests/test_selection_list.py
```
Expected: `OK` pour chacun.

- [ ] **Step 5: (Après accord) pousser la branche rebasée**

Run:
```bash
git push --force-with-lease origin feat/Audit
```
Note : `--force-with-lease` car le rebase réécrit l'historique. Demander l'accord avant de pousser.

---

## Task 2: Modèles de données

**Files:**
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/models/Severity.py`
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/models/AuditIssue.py`
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/models/ThemeResult.py`
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/models/AuditResult.py`
- Modify: `418.tab/Audit.panel/Audit.pushbutton/lib/models/__init__.py` (existe, vide — laisser vide)
- Test: `418.tab/Audit.panel/Audit.pushbutton/tests/test_models.py`
- Create: `418.tab/Audit.panel/Audit.pushbutton/tests/__init__.py` (vide)

**Interfaces:**
- Produces:
  - `Severity`: constantes `OK=0`, `A_REVOIR=1`, `CRITIQUE=2` ; `libelle(niveau) -> unicode` ; `pire(iterable_de_niveaux) -> int`.
  - `AuditIssue(nom, gravite, element_id=None, emplacement=u'', type_=u'', message=u'')` — attributs publics `nom, gravite, element_id, emplacement, type, message`.
  - `ThemeResult(cle, libelle, issues=None, analyses=None, disponible=True, message=u'')` — props `compte -> int`, `pire_gravite -> int`.
  - `AuditResult(themes=None, score=100, top_critiques=None, meta=None)` — attributs `themes, score, top_critiques, meta`.

- [ ] **Step 1: Écrire le test qui échoue**

`tests/test_models.py` (après le bootstrap commun) :
```python
from lib.models.Severity import OK, A_REVOIR, CRITIQUE, libelle, pire
from lib.models.AuditIssue import AuditIssue
from lib.models.ThemeResult import ThemeResult
from lib.models.AuditResult import AuditResult


class TestSeverity(unittest.TestCase):
    def test_ordre(self):
        self.assertTrue(CRITIQUE > A_REVOIR > OK)

    def test_libelle(self):
        self.assertEqual(libelle(CRITIQUE), u'Critique')
        self.assertEqual(libelle(A_REVOIR), u'À revoir')
        self.assertEqual(libelle(OK), u'Conforme')

    def test_pire_vide_est_ok(self):
        self.assertEqual(pire([]), OK)

    def test_pire_prend_le_max(self):
        self.assertEqual(pire([OK, A_REVOIR, CRITIQUE, A_REVOIR]), CRITIQUE)


class TestThemeResult(unittest.TestCase):
    def test_compte_et_pire_gravite(self):
        issues = [AuditIssue(u'a', A_REVOIR), AuditIssue(u'b', CRITIQUE)]
        tr = ThemeResult(cle=u'cad', libelle=u'CAD', issues=issues, analyses=20)
        self.assertEqual(tr.compte, 2)
        self.assertEqual(tr.pire_gravite, CRITIQUE)

    def test_theme_vide(self):
        tr = ThemeResult(cle=u'nommage', libelle=u'Nommage')
        self.assertEqual(tr.compte, 0)
        self.assertEqual(tr.pire_gravite, OK)
        self.assertTrue(tr.disponible)


class TestAuditResult(unittest.TestCase):
    def test_defauts(self):
        ar = AuditResult()
        self.assertEqual(ar.score, 100)
        self.assertEqual(ar.themes, [])
        self.assertEqual(ar.top_critiques, [])
        self.assertEqual(ar.meta, {})


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Lancer le test — échoue**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_models.py`
Expected: FAIL (`ImportError: No module named ... Severity`).

- [ ] **Step 3: Implémenter les modèles**

`lib/models/Severity.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

OK = 0
A_REVOIR = 1
CRITIQUE = 2

_LIBELLES = {OK: u'Conforme', A_REVOIR: u'À revoir', CRITIQUE: u'Critique'}


def libelle(niveau):
    return _LIBELLES.get(niveau, u'Inconnu')


def pire(niveaux):
    p = OK
    for n in niveaux:
        if n > p:
            p = n
    return p
```

`lib/models/AuditIssue.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class AuditIssue(object):
    def __init__(self, nom, gravite, element_id=None,
                 emplacement=u'', type_=u'', message=u''):
        self.nom = nom
        self.gravite = gravite
        self.element_id = element_id
        self.emplacement = emplacement
        self.type = type_
        self.message = message
```

`lib/models/ThemeResult.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from models.Severity import OK, pire
except Exception:
    try:
        from lib.models.Severity import OK, pire
    except Exception:
        OK = 0
        def pire(niveaux):
            return max(list(niveaux) + [0])


class ThemeResult(object):
    def __init__(self, cle, libelle, issues=None, analyses=None,
                 disponible=True, message=u''):
        self.cle = cle
        self.libelle = libelle
        self.issues = list(issues) if issues else []
        self.analyses = analyses
        self.disponible = disponible
        self.message = message

    @property
    def compte(self):
        return len(self.issues)

    @property
    def pire_gravite(self):
        return pire([i.gravite for i in self.issues])
```

`lib/models/AuditResult.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class AuditResult(object):
    def __init__(self, themes=None, score=100, top_critiques=None, meta=None):
        self.themes = list(themes) if themes else []
        self.score = score
        self.top_critiques = list(top_critiques) if top_critiques else []
        self.meta = dict(meta) if meta else {}
```

- [ ] **Step 4: Lancer le test — passe**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_models.py`
Expected: `OK`.

- [ ] **Step 5: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/lib/models 418.tab/Audit.panel/Audit.pushbutton/tests/test_models.py 418.tab/Audit.panel/Audit.pushbutton/tests/__init__.py
git commit -m "feat(audit): modèles Severity/AuditIssue/ThemeResult/AuditResult"
```

---

## Task 3: ScoreService

**Files:**
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/services/ScoreService.py`
- Modify: `lib/services/__init__.py` (existe, vide)
- Test: `418.tab/Audit.panel/Audit.pushbutton/tests/test_score_service.py`

**Interfaces:**
- Consumes: `ThemeResult.pire_gravite`, `.compte`, `.cle`, `.disponible` (Task 2) ; `Severity.CRITIQUE/A_REVOIR` (Task 2).
- Produces: fonctions module `penalite_theme(theme) -> float` et `calculer(themes) -> int` (0..100) ; constantes réglables `POIDS_THEME`, `POINTS_CRITIQUE`, `POINTS_A_REVOIR`, `VOLUME_FACTEUR`, `VOLUME_MAX`.

- [ ] **Step 1: Écrire le test qui échoue**

`tests/test_score_service.py` (après bootstrap) :
```python
from lib.models.Severity import A_REVOIR, CRITIQUE
from lib.models.AuditIssue import AuditIssue
from lib.models.ThemeResult import ThemeResult
from lib.services import ScoreService


def _theme(cle, gravites):
    return ThemeResult(cle=cle, libelle=cle,
                       issues=[AuditIssue(u'x', g) for g in gravites])


class TestScore(unittest.TestCase):
    def test_aucun_theme_score_100(self):
        self.assertEqual(ScoreService.calculer([]), 100)

    def test_themes_sans_probleme_score_100(self):
        self.assertEqual(ScoreService.calculer([_theme(u'cad', [])]), 100)

    def test_un_critique_cad(self):
        # poids cad 1.0 * 10 + volume min(8, 0.05*1)=0.05 -> ~10.05 -> 90
        self.assertEqual(ScoreService.calculer([_theme(u'cad', [CRITIQUE])]), 90)

    def test_purge_pese_moins(self):
        # purge poids 0.6 * 4 (a_revoir) + volume 0.05 = 2.45 -> 98 (round(97.55))
        self.assertEqual(ScoreService.calculer([_theme(u'purge', [A_REVOIR])]), 98)

    def test_plancher_zero(self):
        gros = _theme(u'cad', [CRITIQUE] * 500)
        gros2 = _theme(u'warnings', [CRITIQUE] * 500)
        gros3 = _theme(u'vues_feuilles', [CRITIQUE] * 500)
        self.assertEqual(ScoreService.calculer([gros, gros2, gros3]), 82 - 82)  # >=0
        self.assertTrue(ScoreService.calculer([gros, gros2, gros3]) >= 0)

    def test_theme_indisponible_ignore(self):
        t = ThemeResult(cle=u'cad', libelle=u'CAD', disponible=False)
        self.assertEqual(ScoreService.calculer([t]), 100)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Lancer — échoue**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_score_service.py`
Expected: FAIL (`ImportError ScoreService`).

- [ ] **Step 3: Implémenter**

`lib/services/ScoreService.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from models.Severity import A_REVOIR, CRITIQUE
except Exception:
    try:
        from lib.models.Severity import A_REVOIR, CRITIQUE
    except Exception:
        A_REVOIR, CRITIQUE = 1, 2

# Constantes v1 — réglables.
POIDS_THEME = {
    u'warnings': 1.0, u'cad': 1.0, u'vues_feuilles': 1.0,
    u'purge': 0.6, u'nommage': 0.5,
}
POINTS_CRITIQUE = 10
POINTS_A_REVOIR = 4
VOLUME_FACTEUR = 0.05
VOLUME_MAX = 8


def _severite_base(theme):
    pg = theme.pire_gravite
    if pg == CRITIQUE:
        return POINTS_CRITIQUE
    if pg == A_REVOIR:
        return POINTS_A_REVOIR
    return 0


def penalite_theme(theme):
    poids = POIDS_THEME.get(theme.cle, 1.0)
    volume = min(VOLUME_MAX, VOLUME_FACTEUR * theme.compte)
    return poids * _severite_base(theme) + volume


def calculer(themes):
    total = 0.0
    for t in themes:
        if getattr(t, 'disponible', True):
            total += penalite_theme(t)
    return int(round(max(0, 100 - total)))
```

- [ ] **Step 4: Lancer — passe**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_score_service.py`
Expected: `OK`.

- [ ] **Step 5: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/lib/services/ScoreService.py 418.tab/Audit.panel/Audit.pushbutton/tests/test_score_service.py
git commit -m "feat(audit): ScoreService (pénalités pondérées, plancher 0)"
```

---

## Task 4: BaseCheck + AuditRunner

**Files:**
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/__init__.py` (vide)
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/BaseCheck.py`
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/services/AuditRunner.py`
- Test: `418.tab/Audit.panel/Audit.pushbutton/tests/test_audit_runner.py`

**Interfaces:**
- Consumes: `ThemeResult` (Task 2), `AuditResult` (Task 2), `ScoreService.calculer` (Task 3), `Severity` (Task 2).
- Produces:
  - `BaseCheck` : attributs de classe `cle`, `libelle` ; méthode `run(self, doc) -> ThemeResult` (à surcharger).
  - `AuditRunner(checks=None, score_module=None)` ; `run(self, doc) -> AuditResult`. Un check qui lève → `ThemeResult(disponible=False)`. `top_critiques` = jusqu'à 5 issues triées par gravité décroissante. `meta` rempli via `_meta(doc)` (robuste si `doc is None`).

- [ ] **Step 1: Écrire le test qui échoue**

`tests/test_audit_runner.py` (après bootstrap) :
```python
from lib.models.Severity import A_REVOIR, CRITIQUE
from lib.models.AuditIssue import AuditIssue
from lib.models.ThemeResult import ThemeResult
from lib.services.AuditRunner import AuditRunner


class _FakeCheck(object):
    def __init__(self, cle, issues):
        self.cle = cle
        self.libelle = cle
        self._issues = issues

    def run(self, doc):
        return ThemeResult(cle=self.cle, libelle=self.libelle, issues=self._issues)


class _CheckQuiLeve(object):
    cle = u'cad'
    libelle = u'CAD'

    def run(self, doc):
        raise ValueError(u'boom')


class TestAuditRunner(unittest.TestCase):
    def test_agrege_themes_et_score(self):
        checks = [_FakeCheck(u'cad', [AuditIssue(u'a', CRITIQUE)]),
                  _FakeCheck(u'purge', [AuditIssue(u'b', A_REVOIR)])]
        res = AuditRunner(checks=checks).run(doc=None)
        self.assertEqual(len(res.themes), 2)
        self.assertTrue(0 <= res.score <= 100)

    def test_top_critiques_trie_et_limite(self):
        issues = [AuditIssue(u'w%d' % i, A_REVOIR) for i in range(10)]
        issues.append(AuditIssue(u'grave', CRITIQUE))
        res = AuditRunner(checks=[_FakeCheck(u'warnings', issues)]).run(doc=None)
        self.assertEqual(len(res.top_critiques), 5)
        self.assertEqual(res.top_critiques[0].nom, u'grave')  # critique en tête

    def test_check_qui_leve_devient_indisponible(self):
        res = AuditRunner(checks=[_CheckQuiLeve()]).run(doc=None)
        self.assertEqual(len(res.themes), 1)
        self.assertFalse(res.themes[0].disponible)

    def test_meta_sans_doc(self):
        res = AuditRunner(checks=[_FakeCheck(u'cad', [])]).run(doc=None)
        self.assertIn('horodatage', res.meta)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Lancer — échoue**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_audit_runner.py`
Expected: FAIL (`ImportError AuditRunner`).

- [ ] **Step 3: Implémenter**

`lib/services/checks/BaseCheck.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class BaseCheck(object):
    cle = u'?'
    libelle = u'?'

    def run(self, doc):
        raise NotImplementedError
```

`lib/services/AuditRunner.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime

try:
    from models.ThemeResult import ThemeResult
    from models.AuditResult import AuditResult
except Exception:
    from lib.models.ThemeResult import ThemeResult
    from lib.models.AuditResult import AuditResult

try:
    from services import ScoreService as _score_default
except Exception:
    from lib.services import ScoreService as _score_default


def _default_checks():
    # Import tardif pour éviter les cycles ; chaque import gardé.
    checks = []
    for mod, cls in [
        (u'WarningsCheck', u'WarningsCheck'),
        (u'PurgeCheck', u'PurgeCheck'),
        (u'ViewsSheetsCheck', u'ViewsSheetsCheck'),
        (u'CadImportsCheck', u'CadImportsCheck'),
        (u'NamingCheck', u'NamingCheck'),
    ]:
        try:
            try:
                m = __import__(u'services.checks.' + mod, fromlist=[cls])
            except Exception:
                m = __import__(u'lib.services.checks.' + mod, fromlist=[cls])
            checks.append(getattr(m, cls)())
        except Exception:
            pass
    return checks


def _meta(doc):
    meta = {'horodatage': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
    try:
        if doc is not None:
            meta['fichier'] = doc.Title
    except Exception:
        pass
    return meta


def _top_critiques(themes, limite=5):
    toutes = []
    for t in themes:
        for i in t.issues:
            toutes.append(i)
    toutes.sort(key=lambda i: i.gravite, reverse=True)
    return toutes[:limite]


class AuditRunner(object):
    def __init__(self, checks=None, score_module=None):
        self._checks = checks if checks is not None else _default_checks()
        self._score = score_module or _score_default

    def run(self, doc):
        themes = []
        for chk in self._checks:
            try:
                themes.append(chk.run(doc))
            except Exception as e:
                themes.append(ThemeResult(
                    cle=getattr(chk, 'cle', u'?'),
                    libelle=getattr(chk, 'libelle', u'?'),
                    disponible=False,
                    message=u'Contrôle indisponible : {}'.format(e)))
        score = self._score.calculer(themes)
        return AuditResult(themes=themes, score=score,
                           top_critiques=_top_critiques(themes),
                           meta=_meta(doc))
```

- [ ] **Step 4: Lancer — passe**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_audit_runner.py`
Expected: `OK`.

- [ ] **Step 5: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/lib/services/checks 418.tab/Audit.panel/Audit.pushbutton/lib/services/AuditRunner.py 418.tab/Audit.panel/Audit.pushbutton/tests/test_audit_runner.py
git commit -m "feat(audit): BaseCheck + AuditRunner (agrégation, top critiques, isolation des checks)"
```

---

## Task 5: NamingCheck

**Files:**
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/NamingCheck.py`
- Test: `418.tab/Audit.panel/Audit.pushbutton/tests/test_naming_check.py`

**Interfaces:**
- Consumes: `BaseCheck` (Task 4), `ThemeResult`/`AuditIssue`/`Severity` (Task 2), `UserConfig` (`lib/core/UserConfig.py`, partagé).
- Produces:
  - `NamingCheck` (sous-classe `BaseCheck`, `cle=u'nommage'`), `run(doc) -> ThemeResult`.
  - Fonction pure module `est_conforme(nom, pattern) -> bool` (regex `re.match`, tolérante : renvoie `True` si pattern invalide).
  - Constantes `DEFAULT_VIEW_REGEX`, `DEFAULT_FAMILY_REGEX`.

- [ ] **Step 1: Écrire le test qui échoue** (logique pure uniquement)

`tests/test_naming_check.py` (après bootstrap) :
```python
from lib.services.checks.NamingCheck import (
    est_conforme, DEFAULT_VIEW_REGEX, DEFAULT_FAMILY_REGEX)


class TestNaming(unittest.TestCase):
    def test_vue_conforme(self):
        self.assertTrue(est_conforme(u'NIV_00_PLAN_RDC', DEFAULT_VIEW_REGEX))

    def test_vue_non_conforme(self):
        self.assertFalse(est_conforme(u'Sans titre 1', DEFAULT_VIEW_REGEX))

    def test_famille_conforme(self):
        self.assertTrue(est_conforme(u'MOB_Chaise', DEFAULT_FAMILY_REGEX))

    def test_famille_non_conforme(self):
        self.assertFalse(est_conforme(u'Famille2', DEFAULT_FAMILY_REGEX))

    def test_pattern_invalide_tolere(self):
        # un pattern cassé ne doit pas faire échouer l'audit
        self.assertTrue(est_conforme(u'X', u'([a-z'))

    def test_nom_none_non_conforme(self):
        self.assertFalse(est_conforme(None, DEFAULT_VIEW_REGEX))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Lancer — échoue**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_naming_check.py`
Expected: FAIL (`ImportError NamingCheck`).

- [ ] **Step 3: Implémenter**

`lib/services/checks/NamingCheck.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

try:
    from services.checks.BaseCheck import BaseCheck
except Exception:
    from lib.services.checks.BaseCheck import BaseCheck

try:
    from models.Severity import A_REVOIR
    from models.AuditIssue import AuditIssue
    from models.ThemeResult import ThemeResult
except Exception:
    from lib.models.Severity import A_REVOIR
    from lib.models.AuditIssue import AuditIssue
    from lib.models.ThemeResult import ThemeResult

try:
    from core.UserConfig import UserConfig
except Exception:
    try:
        from lib.core.UserConfig import UserConfig
    except Exception:
        UserConfig = None

try:
    from Autodesk.Revit.DB import (
        FilteredElementCollector, View, Family)
except Exception:
    FilteredElementCollector = View = Family = None

# Convention par défaut : préfixe majuscules + underscore.
DEFAULT_VIEW_REGEX = r'^[A-Z]{2,4}_\d{2}_.+'
DEFAULT_FAMILY_REGEX = r'^[A-Z]{2,4}_.+'


def est_conforme(nom, pattern):
    if nom is None:
        return False
    try:
        return re.match(pattern, nom) is not None
    except Exception:
        return True  # pattern cassé : on ne pénalise pas


class NamingCheck(BaseCheck):
    cle = u'nommage'
    libelle = u'Nommage'

    def _patterns(self):
        vue, fam = DEFAULT_VIEW_REGEX, DEFAULT_FAMILY_REGEX
        try:
            if UserConfig is not None:
                cfg = UserConfig('audit')
                vue = cfg.get('naming_view_regex', vue) or vue
                fam = cfg.get('naming_family_regex', fam) or fam
        except Exception:
            pass
        return vue, fam

    def run(self, doc):
        vue_re, fam_re = self._patterns()
        issues = []
        analyses = 0
        if doc is None or FilteredElementCollector is None:
            return ThemeResult(cle=self.cle, libelle=self.libelle,
                               issues=issues, analyses=0)
        # Vues (hors gabarits)
        try:
            for v in FilteredElementCollector(doc).OfClass(View):
                if getattr(v, 'IsTemplate', False):
                    continue
                analyses += 1
                nom = v.Name
                if not est_conforme(nom, vue_re):
                    issues.append(AuditIssue(
                        nom=nom, gravite=A_REVOIR, element_id=v.Id,
                        emplacement=u'Vue', type_=u'Vue',
                        message=u'Attendu : {}'.format(vue_re)))
        except Exception:
            pass
        # Familles
        try:
            for f in FilteredElementCollector(doc).OfClass(Family):
                analyses += 1
                nom = f.Name
                if not est_conforme(nom, fam_re):
                    issues.append(AuditIssue(
                        nom=nom, gravite=A_REVOIR, element_id=f.Id,
                        emplacement=u'Famille', type_=u'Famille',
                        message=u'Attendu : {}'.format(fam_re)))
        except Exception:
            pass
        return ThemeResult(cle=self.cle, libelle=self.libelle,
                           issues=issues, analyses=analyses)
```

- [ ] **Step 4: Lancer — passe**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_naming_check.py`
Expected: `OK`.

- [ ] **Step 5: Test manuel dans Revit** (déféré à l'intégration Task 13). Noter : à la Task 13, vérifier que le thème « Nommage » liste des vues/familles hors convention.

- [ ] **Step 6: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/NamingCheck.py 418.tab/Audit.panel/Audit.pushbutton/tests/test_naming_check.py
git commit -m "feat(audit): NamingCheck (regex de convention + surcharge UserConfig)"
```

---

## Task 6: WarningsCheck

**Files:**
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/WarningsCheck.py`
- Test: `418.tab/Audit.panel/Audit.pushbutton/tests/test_warnings_check.py`

**Interfaces:**
- Consumes: `BaseCheck`, `Severity`, `AuditIssue`, `ThemeResult`.
- Produces: `WarningsCheck` (`cle=u'warnings'`), `run(doc) -> ThemeResult` ; fonction pure `gravite_pour(description) -> int` (CRITIQUE si description évoque un doublon/même emplacement, sinon A_REVOIR).

- [ ] **Step 1: Écrire le test (logique pure)**

`tests/test_warnings_check.py` (après bootstrap) :
```python
from lib.models.Severity import A_REVOIR, CRITIQUE
from lib.services.checks.WarningsCheck import gravite_pour


class TestWarningsGravite(unittest.TestCase):
    def test_doublon_est_critique(self):
        self.assertEqual(
            gravite_pour(u'There are identical instances in the same place'),
            CRITIQUE)
        self.assertEqual(gravite_pour(u'Éléments dupliqués au même endroit'),
                         CRITIQUE)

    def test_autre_est_a_revoir(self):
        self.assertEqual(gravite_pour(u'Les murs se chevauchent'), A_REVOIR)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Lancer — échoue**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_warnings_check.py`
Expected: FAIL.

- [ ] **Step 3: Implémenter**

`lib/services/checks/WarningsCheck.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from services.checks.BaseCheck import BaseCheck
except Exception:
    from lib.services.checks.BaseCheck import BaseCheck
try:
    from models.Severity import A_REVOIR, CRITIQUE
    from models.AuditIssue import AuditIssue
    from models.ThemeResult import ThemeResult
except Exception:
    from lib.models.Severity import A_REVOIR, CRITIQUE
    from lib.models.AuditIssue import AuditIssue
    from lib.models.ThemeResult import ThemeResult

_MOTS_CRITIQUES = (u'dupliqu', u'identical', u'same place',
                   u'même endroit', u'meme endroit', u'même place')


def gravite_pour(description):
    d = (description or u'').lower()
    for mot in _MOTS_CRITIQUES:
        if mot in d:
            return CRITIQUE
    return A_REVOIR


class WarningsCheck(BaseCheck):
    cle = u'warnings'
    libelle = u'Avertissements'

    def run(self, doc):
        issues = []
        if doc is None:
            return ThemeResult(cle=self.cle, libelle=self.libelle, issues=issues)
        try:
            warnings = list(doc.GetWarnings())
        except Exception as e:
            return ThemeResult(cle=self.cle, libelle=self.libelle,
                               disponible=False,
                               message=u'GetWarnings indisponible : {}'.format(e))
        # Regrouper par description.
        groupes = {}
        for w in warnings:
            try:
                desc = w.GetDescriptionText()
            except Exception:
                desc = u'(avertissement)'
            groupes.setdefault(desc, 0)
            groupes[desc] += 1
        for desc, n in groupes.items():
            issues.append(AuditIssue(
                nom=desc, gravite=gravite_pour(desc),
                emplacement=u'Modèle', type_=u'Avertissement',
                message=u'{} occurrence(s)'.format(n)))
        return ThemeResult(cle=self.cle, libelle=self.libelle,
                           issues=issues, analyses=len(warnings))
```

- [ ] **Step 4: Lancer — passe**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_warnings_check.py`
Expected: `OK`.

- [ ] **Step 5: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/WarningsCheck.py 418.tab/Audit.panel/Audit.pushbutton/tests/test_warnings_check.py
git commit -m "feat(audit): WarningsCheck (regroupement par description, gravité doublons)"
```

---

## Task 7: PurgeCheck

**Files:**
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/PurgeCheck.py`

**Interfaces:**
- Consumes: `BaseCheck`, `Severity.A_REVOIR`, `AuditIssue`, `ThemeResult`, API `Document.GetUnusedElements`.
- Produces: `PurgeCheck` (`cle=u'purge'`), `run(doc) -> ThemeResult` (une issue par catégorie d'éléments purgeables, compte par catégorie).

- [ ] **Step 1: Implémenter** (pas de test standalone — API Revit pure ; test manuel Task 13)

`lib/services/checks/PurgeCheck.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from services.checks.BaseCheck import BaseCheck
except Exception:
    from lib.services.checks.BaseCheck import BaseCheck
try:
    from models.Severity import A_REVOIR
    from models.AuditIssue import AuditIssue
    from models.ThemeResult import ThemeResult
except Exception:
    from lib.models.Severity import A_REVOIR
    from lib.models.AuditIssue import AuditIssue
    from lib.models.ThemeResult import ThemeResult

try:
    from Autodesk.Revit.DB import ElementId, Category
except Exception:
    ElementId = Category = None

try:
    from System.Collections.Generic import HashSet
except Exception:
    HashSet = None


class PurgeCheck(BaseCheck):
    cle = u'purge'
    libelle = u'À purger'

    def run(self, doc):
        if doc is None or ElementId is None or HashSet is None:
            return ThemeResult(cle=self.cle, libelle=self.libelle, issues=[])
        try:
            ids = doc.GetUnusedElements(HashSet[ElementId]())
        except Exception as e:
            return ThemeResult(cle=self.cle, libelle=self.libelle,
                               disponible=False,
                               message=u'GetUnusedElements indisponible : {}'.format(e))
        # Regrouper par nom de catégorie.
        par_cat = {}
        total = 0
        for eid in ids:
            total += 1
            nom_cat = u'Autres'
            try:
                el = doc.GetElement(eid)
                if el is not None and el.Category is not None:
                    nom_cat = el.Category.Name
            except Exception:
                pass
            par_cat.setdefault(nom_cat, 0)
            par_cat[nom_cat] += 1
        issues = []
        for cat, n in sorted(par_cat.items(), key=lambda kv: kv[1], reverse=True):
            issues.append(AuditIssue(
                nom=cat, gravite=A_REVOIR,
                emplacement=u'Projet', type_=u'Non utilisé',
                message=u'{} élément(s) purgeable(s)'.format(n)))
        return ThemeResult(cle=self.cle, libelle=self.libelle,
                           issues=issues, analyses=total)
```

- [ ] **Step 2: Vérifier l'import standalone ne lève pas**

Run: `python -c "import sys; sys.path.insert(0, '418.tab/Audit.panel/Audit.pushbutton'); sys.path.insert(0, 'lib'); import lib.services.checks.PurgeCheck"`
Expected: aucune exception (les imports Revit dégradent en `None`).

- [ ] **Step 3: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/PurgeCheck.py
git commit -m "feat(audit): PurgeCheck (GetUnusedElements regroupé par catégorie)"
```

---

## Task 8: ViewsSheetsCheck

**Files:**
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/ViewsSheetsCheck.py`
- Test: `418.tab/Audit.panel/Audit.pushbutton/tests/test_views_sheets_check.py` (logique pure du nom par défaut)

**Interfaces:**
- Consumes: `BaseCheck`, `Severity`, `AuditIssue`, `ThemeResult`, API Revit (`FilteredElementCollector`, `View`, `ViewSheet`, `Viewport`, `ElementId`).
- Produces: `ViewsSheetsCheck` (`cle=u'vues_feuilles'`), `run(doc) -> ThemeResult` ; fonction pure `est_nom_par_defaut(nom) -> bool`.

- [ ] **Step 1: Écrire le test (logique pure)**

`tests/test_views_sheets_check.py` (après bootstrap) :
```python
from lib.services.checks.ViewsSheetsCheck import est_nom_par_defaut


class TestNomParDefaut(unittest.TestCase):
    def test_niveau_defaut(self):
        self.assertTrue(est_nom_par_defaut(u'Niveau 4'))
        self.assertTrue(est_nom_par_defaut(u'Level 2'))
        self.assertTrue(est_nom_par_defaut(u'Quadrillage 1'))

    def test_nom_personnalise(self):
        self.assertFalse(est_nom_par_defaut(u'RDC fini'))
        self.assertFalse(est_nom_par_defaut(u'A'))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Lancer — échoue**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_views_sheets_check.py`
Expected: FAIL.

- [ ] **Step 3: Implémenter**

`lib/services/checks/ViewsSheetsCheck.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

try:
    from services.checks.BaseCheck import BaseCheck
except Exception:
    from lib.services.checks.BaseCheck import BaseCheck
try:
    from models.Severity import A_REVOIR, CRITIQUE
    from models.AuditIssue import AuditIssue
    from models.ThemeResult import ThemeResult
except Exception:
    from lib.models.Severity import A_REVOIR, CRITIQUE
    from lib.models.AuditIssue import AuditIssue
    from lib.models.ThemeResult import ThemeResult

try:
    from Autodesk.Revit.DB import (
        FilteredElementCollector, View, ViewType, ElementId)
except Exception:
    FilteredElementCollector = View = ViewType = ElementId = None

_RE_DEFAUT = re.compile(r'^(Niveau|Level|Quadrillage|Grid)\s*\d+$')


def est_nom_par_defaut(nom):
    if not nom:
        return False
    return _RE_DEFAUT.match(nom) is not None


class ViewsSheetsCheck(BaseCheck):
    cle = u'vues_feuilles'
    libelle = u'Vues & Feuilles'

    def run(self, doc):
        if doc is None or FilteredElementCollector is None:
            return ThemeResult(cle=self.cle, libelle=self.libelle, issues=[])
        issues = []
        analyses = 0
        # Ids de vues placées sur une feuille (via Viewports).
        placees = set()
        try:
            from Autodesk.Revit.DB import Viewport
            for vp in FilteredElementCollector(doc).OfClass(Viewport):
                try:
                    placees.add(vp.ViewId.IntegerValue)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            for v in FilteredElementCollector(doc).OfClass(View):
                if getattr(v, 'IsTemplate', False):
                    continue
                # Ignorer feuilles et vues systèmes non plaçables.
                try:
                    if v.ViewType in (ViewType.DrawingSheet, ViewType.ProjectBrowser,
                                      ViewType.SystemBrowser, ViewType.Schedule):
                        continue
                except Exception:
                    pass
                analyses += 1
                non_placee = v.Id.IntegerValue not in placees
                try:
                    sans_gabarit = (v.ViewTemplateId == ElementId.InvalidElementId)
                except Exception:
                    sans_gabarit = False
                if non_placee and sans_gabarit:
                    issues.append(AuditIssue(
                        nom=v.Name, gravite=CRITIQUE, element_id=v.Id,
                        emplacement=u'Vue', type_=u'Non placée + sans gabarit',
                        message=u'Non placée sur feuille et sans gabarit'))
                elif non_placee:
                    issues.append(AuditIssue(
                        nom=v.Name, gravite=A_REVOIR, element_id=v.Id,
                        emplacement=u'Vue', type_=u'Non placée',
                        message=u'Non placée sur feuille'))
                elif sans_gabarit:
                    issues.append(AuditIssue(
                        nom=v.Name, gravite=A_REVOIR, element_id=v.Id,
                        emplacement=u'Vue', type_=u'Sans gabarit',
                        message=u'Aucun gabarit de vue appliqué'))
                if est_nom_par_defaut(v.Name):
                    issues.append(AuditIssue(
                        nom=v.Name, gravite=A_REVOIR, element_id=v.Id,
                        emplacement=u'Vue', type_=u'Nom par défaut',
                        message=u'Nom générique non renommé'))
        except Exception:
            pass
        return ThemeResult(cle=self.cle, libelle=self.libelle,
                           issues=issues, analyses=analyses)
```

- [ ] **Step 4: Lancer — passe**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_views_sheets_check.py`
Expected: `OK`.

- [ ] **Step 5: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/ViewsSheetsCheck.py 418.tab/Audit.panel/Audit.pushbutton/tests/test_views_sheets_check.py
git commit -m "feat(audit): ViewsSheetsCheck (non placée / sans gabarit / nom par défaut)"
```

---

## Task 9: CadImportsCheck

**Files:**
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/CadImportsCheck.py`

**Interfaces:**
- Consumes: `BaseCheck`, `Severity`, `AuditIssue`, `ThemeResult`, API Revit (`FilteredElementCollector`, `ImportInstance`, `CADLinkType`).
- Produces: `CadImportsCheck` (`cle=u'cad'`), `run(doc) -> ThemeResult` (import explosé/non lié = CRITIQUE, lien = A_REVOIR).

- [ ] **Step 1: Implémenter** (API Revit pure — test manuel Task 13)

`lib/services/checks/CadImportsCheck.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from services.checks.BaseCheck import BaseCheck
except Exception:
    from lib.services.checks.BaseCheck import BaseCheck
try:
    from models.Severity import A_REVOIR, CRITIQUE
    from models.AuditIssue import AuditIssue
    from models.ThemeResult import ThemeResult
except Exception:
    from lib.models.Severity import A_REVOIR, CRITIQUE
    from lib.models.AuditIssue import AuditIssue
    from lib.models.ThemeResult import ThemeResult

try:
    from Autodesk.Revit.DB import FilteredElementCollector, ImportInstance
except Exception:
    FilteredElementCollector = ImportInstance = None


class CadImportsCheck(BaseCheck):
    cle = u'cad'
    libelle = u'Imports / Liens CAD'

    def run(self, doc):
        if doc is None or FilteredElementCollector is None:
            return ThemeResult(cle=self.cle, libelle=self.libelle, issues=[])
        issues = []
        analyses = 0
        try:
            for inst in FilteredElementCollector(doc).OfClass(ImportInstance):
                analyses += 1
                try:
                    est_lie = bool(inst.IsLinked)
                except Exception:
                    est_lie = False
                try:
                    nom = inst.Category.Name if inst.Category else u'(CAD)'
                except Exception:
                    nom = u'(CAD)'
                # Emplacement : vue propriétaire si import spécifique à une vue.
                emplacement = u'Modèle'
                try:
                    owner = doc.GetElement(inst.OwnerViewId)
                    if owner is not None:
                        emplacement = u'Vue : {}'.format(owner.Name)
                except Exception:
                    pass
                if not est_lie:
                    issues.append(AuditIssue(
                        nom=nom, gravite=CRITIQUE, element_id=inst.Id,
                        emplacement=emplacement, type_=u'Import explosé',
                        message=u'Import CAD non lié (fragmente le modèle)'))
                else:
                    issues.append(AuditIssue(
                        nom=nom, gravite=A_REVOIR, element_id=inst.Id,
                        emplacement=emplacement, type_=u'Lien CAD',
                        message=u'Lien CAD présent'))
        except Exception as e:
            return ThemeResult(cle=self.cle, libelle=self.libelle,
                               disponible=False,
                               message=u'Collecte CAD indisponible : {}'.format(e))
        return ThemeResult(cle=self.cle, libelle=self.libelle,
                           issues=issues, analyses=analyses)
```

- [ ] **Step 2: Vérifier l'import standalone**

Run: `python -c "import sys; sys.path.insert(0,'418.tab/Audit.panel/Audit.pushbutton'); sys.path.insert(0,'lib'); import lib.services.checks.CadImportsCheck"`
Expected: aucune exception.

- [ ] **Step 3: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/lib/services/checks/CadImportsCheck.py
git commit -m "feat(audit): CadImportsCheck (imports explosés critiques, liens à revoir)"
```

---

## Task 10: ReportExporter (HTML autonome)

**Files:**
- Create: `418.tab/Audit.panel/Audit.pushbutton/lib/services/ReportExporter.py`
- Test: `418.tab/Audit.panel/Audit.pushbutton/tests/test_report_exporter.py`

**Interfaces:**
- Consumes: `AuditResult`, `ThemeResult`, `AuditIssue`, `Severity.libelle` ; `sanitize` (`lib/core/sanitize.py`, partagé — vérifier le nom exact de la fonction ; fallback interne si absente).
- Produces:
  - `construire_html(audit_result) -> unicode` (pur, testable).
  - `exporter(audit_result, dossier=None) -> chemin` (écrit le fichier ; nom `Audit_<fichier>_<date>.html`).

- [ ] **Step 1: Écrire le test (génération HTML pure)**

`tests/test_report_exporter.py` (après bootstrap) :
```python
from lib.models.Severity import CRITIQUE, A_REVOIR
from lib.models.AuditIssue import AuditIssue
from lib.models.ThemeResult import ThemeResult
from lib.models.AuditResult import AuditResult
from lib.services.ReportExporter import construire_html


class TestReportHtml(unittest.TestCase):
    def _result(self):
        t = ThemeResult(cle=u'cad', libelle=u'Imports / Liens CAD',
                        issues=[AuditIssue(u'plan.dwg', CRITIQUE,
                                           emplacement=u'Vue : Plan RDC',
                                           type_=u'Import explosé')],
                        analyses=20)
        return AuditResult(themes=[t], score=72,
                           top_critiques=[t.issues[0]],
                           meta={'fichier': u'Test.rvt',
                                 'horodatage': u'2026-08-05 10:00'})

    def test_contient_score_et_theme(self):
        html = construire_html(self._result())
        self.assertIn(u'72', html)
        self.assertIn(u'Imports / Liens CAD', html)
        self.assertIn(u'plan.dwg', html)
        self.assertTrue(html.strip().startswith(u'<!DOCTYPE html>'))

    def test_echappe_html(self):
        t = ThemeResult(cle=u'x', libelle=u'X',
                        issues=[AuditIssue(u'<script>', A_REVOIR)])
        html = construire_html(AuditResult(themes=[t], score=50))
        self.assertNotIn(u'<script>', html)
        self.assertIn(u'&lt;script&gt;', html)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Lancer — échoue**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_report_exporter.py`
Expected: FAIL.

- [ ] **Step 3: Implémenter**

`lib/services/ReportExporter.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import io
import datetime

try:
    from models.Severity import libelle as libelle_gravite
except Exception:
    from lib.models.Severity import libelle as libelle_gravite


def _esc(txt):
    s = u'' if txt is None else u'{}'.format(txt)
    return (s.replace(u'&', u'&amp;').replace(u'<', u'&lt;')
             .replace(u'>', u'&gt;').replace(u'"', u'&quot;'))


def construire_html(res):
    meta = res.meta or {}
    parts = [u'<!DOCTYPE html>', u'<html lang="fr"><head><meta charset="utf-8">',
             u'<title>Audit — {}</title>'.format(_esc(meta.get('fichier', u''))),
             u'<style>body{font-family:Segoe UI,Arial,sans-serif;margin:24px;'
             u'color:#1a1a1a}h1{font-size:22px}.score{font-size:40px;font-weight:700}'
             u'table{border-collapse:collapse;width:100%;margin:12px 0}'
             u'th,td{border:1px solid #e0e0e0;padding:8px;text-align:left;font-size:13px}'
             u'th{background:#f3f3f3}.crit{color:#d13438;font-weight:700}'
             u'.warn{color:#c77914;font-weight:700}</style></head><body>']
    parts.append(u'<h1>Audit de maquette — {}</h1>'.format(
        _esc(meta.get('fichier', u'(modèle)'))))
    parts.append(u'<p>Généré le {} · Score de santé : '
                 u'<span class="score">{}</span>/100</p>'.format(
                     _esc(meta.get('horodatage', u'')), res.score))
    for t in res.themes:
        parts.append(u'<h2>{} ({})</h2>'.format(_esc(t.libelle), t.compte))
        if not t.disponible:
            parts.append(u'<p><em>Contrôle indisponible : {}</em></p>'.format(
                _esc(t.message)))
            continue
        if not t.issues:
            parts.append(u'<p>Aucun problème détecté.</p>')
            continue
        parts.append(u'<table><tr><th>Élément</th><th>Emplacement</th>'
                     u'<th>Type</th><th>Gravité</th><th>Détail</th></tr>')
        for i in t.issues:
            cls = u'crit' if libelle_gravite(i.gravite) == u'Critique' else u'warn'
            parts.append(
                u'<tr><td>{}</td><td>{}</td><td>{}</td>'
                u'<td class="{}">{}</td><td>{}</td></tr>'.format(
                    _esc(i.nom), _esc(i.emplacement), _esc(i.type),
                    cls, _esc(libelle_gravite(i.gravite)), _esc(i.message)))
        parts.append(u'</table>')
    parts.append(u'</body></html>')
    return u'\n'.join(parts)


def _sanitize(nom):
    try:
        from core.sanitize import sanitize
    except Exception:
        try:
            from lib.core.sanitize import sanitize
        except Exception:
            sanitize = None
    if sanitize is not None:
        try:
            return sanitize(nom)
        except Exception:
            pass
    interdits = u'\\/:*?"<>|'
    return u''.join(c for c in (nom or u'audit') if c not in interdits)[:180]


def exporter(res, dossier=None):
    meta = res.meta or {}
    if dossier is None:
        dossier = os.path.expanduser(u'~/Documents')
    fichier = _sanitize(meta.get('fichier', u'modele'))
    date = datetime.datetime.now().strftime('%Y%m%d')
    chemin = os.path.join(dossier, u'Audit_{}_{}.html'.format(fichier, date))
    html = construire_html(res)
    with io.open(chemin, 'w', encoding='utf-8') as f:
        f.write(html)
    return chemin
```

> **Note d'implémentation :** à la Step 3, vérifier le nom réel exporté par `lib/core/sanitize.py` (fonction `sanitize` supposée). S'il diffère, ajuster l'import dans `_sanitize`. Le fallback interne garantit un fonctionnement même si l'API diffère.

- [ ] **Step 4: Lancer — passe**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_report_exporter.py`
Expected: `OK`.

- [ ] **Step 5: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/lib/services/ReportExporter.py 418.tab/Audit.panel/Audit.pushbutton/tests/test_report_exporter.py
git commit -m "feat(audit): ReportExporter (rapport HTML autonome, échappement)"
```

---

## Task 11: ViewModels

**Files:**
- Create: `lib/viewmodels/IssueRowVM.py`, `lib/viewmodels/ThemeCardVM.py`, `lib/viewmodels/ScoreVM.py`
- Modify: `418.tab/Audit.panel/Audit.pushbutton/lib/viewmodels/MainViewModel.py` (existe — scaffold à enrichir)
- Test: `418.tab/Audit.panel/Audit.pushbutton/tests/test_viewmodels.py`

**Interfaces:**
- Consumes: `BaseViewModel` (`ui.base`), `RelayCommand` (`ui.helpers`), `AuditResult`/`ThemeResult`/`AuditIssue` (Task 2), `AuditRunner` (Task 4), `Severity.libelle`.
- Produces:
  - `ScoreVM(audit_result)` : props `Score`, `Verdict`, `NbCritiques`.
  - `IssueRowVM(issue)` : props `Nom`, `Emplacement`, `Type`, `Gravite` (libellé), `ElementId` ; `selectionner_cmd` (câblé Task 13).
  - `ThemeCardVM(theme_result)` : props `Libelle`, `Compte`, `PireGravite` (libellé), `Disponible`, `Rows` (liste `IssueRowVM`), `EstDeplie` (bool notifiable).
  - `MainViewModel(doc=None)` : lance l'audit à l'init (Task 13 ajoute la barre de progression), expose `ScoreVM`, `Cartes` (liste `ThemeCardVM`), `TopCritiques` (liste `IssueRowVM`), `Meta`, commandes `relancer_cmd`, `exporter_cmd` (câblées Task 13).

- [ ] **Step 1: Écrire le test (état des VM depuis un AuditResult)**

`tests/test_viewmodels.py` (après bootstrap) :
```python
from lib.models.Severity import CRITIQUE, A_REVOIR
from lib.models.AuditIssue import AuditIssue
from lib.models.ThemeResult import ThemeResult
from lib.models.AuditResult import AuditResult
from lib.viewmodels.ScoreVM import ScoreVM
from lib.viewmodels.ThemeCardVM import ThemeCardVM
from lib.viewmodels.IssueRowVM import IssueRowVM


class TestVM(unittest.TestCase):
    def test_score_vm(self):
        vm = ScoreVM(AuditResult(score=72, top_critiques=[AuditIssue(u'a', CRITIQUE)]))
        self.assertEqual(vm.Score, 72)
        self.assertEqual(vm.NbCritiques, 1)
        self.assertTrue(len(vm.Verdict) > 0)

    def test_issue_row_vm(self):
        row = IssueRowVM(AuditIssue(u'plan.dwg', CRITIQUE,
                                    emplacement=u'Vue', type_=u'Import'))
        self.assertEqual(row.Nom, u'plan.dwg')
        self.assertEqual(row.Gravite, u'Critique')

    def test_theme_card_vm(self):
        t = ThemeResult(cle=u'cad', libelle=u'CAD',
                        issues=[AuditIssue(u'x', A_REVOIR)], analyses=10)
        card = ThemeCardVM(t)
        self.assertEqual(card.Libelle, u'CAD')
        self.assertEqual(card.Compte, 1)
        self.assertEqual(len(card.Rows), 1)
        self.assertFalse(card.EstDeplie)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Lancer — échoue**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_viewmodels.py`
Expected: FAIL.

- [ ] **Step 3: Implémenter les VM**

`lib/viewmodels/ScoreVM.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        BaseViewModel = object


def _verdict(score):
    if score >= 85:
        return u'Bon — modèle sain'
    if score >= 60:
        return u'Correct — à consolider'
    if score >= 35:
        return u'Fragile — points à traiter'
    return u'Critique — intervention requise'


class ScoreVM(BaseViewModel):
    def __init__(self, audit_result):
        try:
            super(ScoreVM, self).__init__()
        except Exception:
            pass
        self._r = audit_result

    @property
    def Score(self):
        return self._r.score

    @property
    def Verdict(self):
        return _verdict(self._r.score)

    @property
    def NbCritiques(self):
        return len(self._r.top_critiques)
```

`lib/viewmodels/IssueRowVM.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        BaseViewModel = object
try:
    from models.Severity import libelle as libelle_gravite
except Exception:
    from lib.models.Severity import libelle as libelle_gravite


class IssueRowVM(BaseViewModel):
    def __init__(self, issue, on_selectionner=None):
        try:
            super(IssueRowVM, self).__init__()
        except Exception:
            pass
        self._i = issue
        self.selectionner_cmd = None  # câblé en Task 13

    @property
    def Nom(self):
        return self._i.nom

    @property
    def Emplacement(self):
        return self._i.emplacement

    @property
    def Type(self):
        return self._i.type

    @property
    def Gravite(self):
        return libelle_gravite(self._i.gravite)

    @property
    def ElementId(self):
        return self._i.element_id
```

`lib/viewmodels/ThemeCardVM.py` :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        BaseViewModel = object
try:
    from models.Severity import libelle as libelle_gravite
except Exception:
    from lib.models.Severity import libelle as libelle_gravite
try:
    from viewmodels.IssueRowVM import IssueRowVM
except Exception:
    from lib.viewmodels.IssueRowVM import IssueRowVM


class ThemeCardVM(BaseViewModel):
    def __init__(self, theme_result, on_selectionner=None):
        try:
            super(ThemeCardVM, self).__init__()
        except Exception:
            pass
        self._t = theme_result
        self._deplie = False
        self.Rows = [IssueRowVM(i, on_selectionner) for i in theme_result.issues]

    @property
    def Libelle(self):
        return self._t.libelle

    @property
    def Compte(self):
        return self._t.compte

    @property
    def PireGravite(self):
        return libelle_gravite(self._t.pire_gravite)

    @property
    def Disponible(self):
        return self._t.disponible

    @property
    def EstDeplie(self):
        return self._deplie

    @EstDeplie.setter
    def EstDeplie(self, value):
        self._deplie = bool(value)
        try:
            self.notify_property('EstDeplie')
        except Exception:
            pass
```

`lib/viewmodels/MainViewModel.py` (remplacer le scaffold) :
```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        BaseViewModel = object
try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    try:
        from lib.ui.helpers.RelayCommand import RelayCommand
    except Exception:
        RelayCommand = None
try:
    from services.AuditRunner import AuditRunner
except Exception:
    from lib.services.AuditRunner import AuditRunner
try:
    from viewmodels.ScoreVM import ScoreVM
    from viewmodels.ThemeCardVM import ThemeCardVM
    from viewmodels.IssueRowVM import IssueRowVM
except Exception:
    from lib.viewmodels.ScoreVM import ScoreVM
    from lib.viewmodels.ThemeCardVM import ThemeCardVM
    from lib.viewmodels.IssueRowVM import IssueRowVM


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None, runner=None):
        try:
            super(MainViewModel, self).__init__()
        except Exception:
            pass
        self._doc = doc
        self._runner = runner or AuditRunner()
        self.Titre = u'Audit — Santé du modèle'
        self.ScoreVM = None
        self.Cartes = []
        self.TopCritiques = []
        self.Meta = {}
        self.relancer_cmd = RelayCommand(lambda p: self.lancer_audit()) if RelayCommand else None
        self.exporter_cmd = None  # câblé Task 13
        self.lancer_audit()

    def lancer_audit(self):
        res = self._runner.run(self._doc)
        self._appliquer(res)

    def _appliquer(self, res):
        self._resultat = res
        self.ScoreVM = ScoreVM(res)
        self.Cartes = [ThemeCardVM(t) for t in res.themes]
        self.TopCritiques = [IssueRowVM(i) for i in res.top_critiques]
        self.Meta = res.meta
        for prop in ('ScoreVM', 'Cartes', 'TopCritiques', 'Meta'):
            try:
                self.notify_property(prop)
            except Exception:
                pass
```

- [ ] **Step 4: Lancer — passe**

Run: `python 418.tab/Audit.panel/Audit.pushbutton/tests/test_viewmodels.py`
Expected: `OK`.

- [ ] **Step 5: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/lib/viewmodels 418.tab/Audit.panel/Audit.pushbutton/tests/test_viewmodels.py
git commit -m "feat(audit): ViewModels (Score/Theme/Issue/Main) alimentés par AuditResult"
```

---

## Task 12: Peuplement du XAML (MainWindow.xaml)

**Files:**
- Modify: `418.tab/Audit.panel/Audit.pushbutton/GUI/Views/MainWindow.xaml` (coquille existante — remplacer la zone « Contenu Audit à venir » et le footer)

**Interfaces:**
- Consumes (bindings) : `MainViewModel.Titre`, `.ScoreVM.Score/.Verdict/.NbCritiques`, `.TopCritiques` (ItemsSource : `Nom`, `Emplacement`, `Gravite`), `.Cartes` (ItemsSource : `Libelle`, `Compte`, `PireGravite`, `Disponible`, `Rows`, `EstDeplie`), commandes `.relancer_cmd`, `.exporter_cmd`.
- Produces : la surface de contenu peuplée conforme à la maquette validée.

Ce task est **non testable en standalone** (WPF/Revit). Suivre la maquette `scratchpad/audit-dashboard-mockup.html` et les ressources de thème partagées.

- [ ] **Step 1: Remplacer la zone de contenu (Grid.Row=0 de la surface)** par un `ScrollViewer` contenant, de haut en bas :
  1. Bandeau contexte : `TextBlock` liés à `Meta['fichier']` + horodatage.
  2. Récap : `UniformGrid`/`Grid` 3 colonnes dans l'ordre **Critiques · Répartition · Score**.
     - Carte critiques : `ItemsControl ItemsSource="{Binding TopCritiques}"` → `DataTemplate` (pastille gravité + `Nom` + `Emplacement`).
     - Carte répartition : `ItemsControl ItemsSource="{Binding Cartes}"` → ligne par thème (`Libelle`, barre proportionnelle simple, `Compte`).
     - Carte score : grand `TextBlock` `{Binding ScoreVM.Score}` + `{Binding ScoreVM.Verdict}` + mini-stats `{Binding ScoreVM.NbCritiques}`.
  3. Détail : `ItemsControl ItemsSource="{Binding Cartes}"` → `DataTemplate` = `Expander` (`Header` = `Libelle` + pastille `Compte` + `PireGravite` ; `IsExpanded="{Binding EstDeplie, Mode=TwoWay}"`) contenant un `DataGrid`/`ItemsControl` sur `Rows` (colonnes `Nom`, `Emplacement`, `Type`, `Gravite`).

  Utiliser exclusivement les brushes de thème via `DynamicResource` (`CardBackgroundBrush`, `TextPrimaryBrush`, `ErrorBrush`, etc.). Couleurs sémantiques bon/à revoir/critique : ajouter au besoin 2 brushes de thème (vert/orange) dans `Colors.xaml`/`ColorsDark.xaml` — sinon réutiliser `ErrorBrush` (rouge) + une ressource orange locale.

- [ ] **Step 2: Remplacer le footer** par deux boutons liés :
```xml
<Button Content="Exporter le rapport"
        Command="{Binding exporter_cmd}"
        Style="{DynamicResource SecondaryActionButtonStyle}" Margin="0,0,10,0"/>
<Button Content="Relancer l'audit"
        Command="{Binding relancer_cmd}"
        Style="{DynamicResource PrimaryActionButtonStyle}"/>
```

- [ ] **Step 3: Test manuel dans Revit**

1. pyRevit → Reload.
2. Ouvrir un projet Revit contenant quelques avertissements / imports CAD.
3. Cliquer le bouton **Audit**.
Expected : la fenêtre s'ouvre, montre score + 3 cartes (ordre Critiques/Répartition/Score) + accordéon des 5 thèmes. Vérifier thème clair ET sombre (basculer le thème pyRevit/OS).

- [ ] **Step 4: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/GUI/Views/MainWindow.xaml
git commit -m "feat(audit): peuplement du dashboard dans la coquille (récap + accordéon)"
```

---

## Task 13: Intégration finale (auto-lancement, progression, sélection, export)

**Files:**
- Modify: `lib/viewmodels/MainViewModel.py` (barre de progression + câblage `exporter_cmd` + `on_selectionner`)
- Modify: `lib/viewmodels/IssueRowVM.py` (câblage `selectionner_cmd`)
- Modify: `script.py` (déjà correct — vérifier)

**Interfaces:**
- Consumes: `AuditRunner.run` (Task 4), `ReportExporter.exporter` (Task 10), `core.selection` (partagé — vérifier l'API exacte de sélection/zoom), `pyrevit.forms` (barre de progression).
- Produces: fenêtre qui s'ouvre déjà remplie (audit sous progression) ; « Sélectionner & fermer » ; « Exporter le rapport ».

- [ ] **Step 1: Barre de progression pendant l'audit**

Dans `MainViewModel.lancer_audit`, entourer l'exécution d'une barre de progression pyRevit (import gardé) :
```python
def lancer_audit(self):
    res = None
    try:
        from pyrevit import forms
        with forms.ProgressBar(title=u'Audit en cours…', indeterminate=True):
            res = self._runner.run(self._doc)
    except Exception:
        res = self._runner.run(self._doc)  # hors Revit / pas de pyrevit
    self._appliquer(res)
```

- [ ] **Step 2: Câbler l'export**

Dans `MainViewModel.__init__`, après `lancer_audit()` :
```python
if RelayCommand:
    self.exporter_cmd = RelayCommand(lambda p: self._exporter())
```
Et la méthode :
```python
def _exporter(self):
    try:
        from services.ReportExporter import exporter
    except Exception:
        from lib.services.ReportExporter import exporter
    try:
        from core.UserConfig import UserConfig
        dossier = UserConfig('audit').get('report_dir', None)
    except Exception:
        dossier = None
    try:
        chemin = exporter(self._resultat, dossier)
        try:
            import os
            os.startfile(os.path.dirname(chemin))  # ouvre le dossier
        except Exception:
            pass
    except Exception:
        pass
```

- [ ] **Step 3: Câbler « Sélectionner & fermer »**

Vérifier d'abord l'API réelle de `lib/core/selection.py` (fonction de sélection par `ElementId` / zoom). Puis, dans `MainViewModel`, définir un callback passé aux cartes :
```python
def _selectionner_et_fermer(self, element_id):
    try:
        from core.selection import selectionner_elements  # vérifier le nom exact
    except Exception:
        try:
            from lib.core.selection import selectionner_elements
        except Exception:
            selectionner_elements = None
    try:
        if selectionner_elements is not None and element_id is not None:
            selectionner_elements(self._doc, [element_id])
    except Exception:
        pass
    if self.on_fermer:
        self.on_fermer()  # fourni par la View (fenêtre.Close)
```
> Si `core.selection` n'expose pas de helper direct, utiliser `__revit__.ActiveUIDocument.Selection.SetElementIds` + `ShowElements` dans un `try/except`. La View injecte `on_fermer = self._win.Close` après chargement.

Propager `on_selectionner=self._selectionner_et_fermer` à `ThemeCardVM`/`IssueRowVM`, et dans `IssueRowVM` :
```python
self.selectionner_cmd = RelayCommand(
    lambda p: on_selectionner(self.ElementId)) if (RelayCommand and on_selectionner) else None
```

- [ ] **Step 4: Exposer la fermeture depuis la View**

Dans `MainWindowView` (après `BaseWindow` chargé), injecter `view_model.on_fermer = self._win.Close` (attribut ajouté sur `MainViewModel`, défaut `None`). Ajouter au XAML une commande de sélection sur double-clic de ligne (`InputBinding MouseAction="LeftDoubleClick"` → `selectionner_cmd`) ou un bouton « Voir » par ligne.

- [ ] **Step 5: Test manuel complet dans Revit**

1. Reload pyRevit → ouvrir un projet réel.
2. Clic **Audit** → barre de progression puis fenêtre remplie.
3. Déplier chaque thème → listes cohérentes.
4. Double-clic (ou « Voir ») sur une ligne avec `ElementId` → l'élément est sélectionné dans Revit et la fenêtre se ferme.
5. Rouvrir → « Relancer l'audit » recalcule.
6. « Exporter le rapport » → un `.html` est créé et le dossier s'ouvre ; le rapport reflète le dashboard.
7. Vérifier thème clair + sombre.

- [ ] **Step 6: Vérifier la non-régression standalone**

Run (tous les tests du bouton) :
```bash
python 418.tab/Audit.panel/Audit.pushbutton/tests/test_models.py
python 418.tab/Audit.panel/Audit.pushbutton/tests/test_score_service.py
python 418.tab/Audit.panel/Audit.pushbutton/tests/test_audit_runner.py
python 418.tab/Audit.panel/Audit.pushbutton/tests/test_naming_check.py
python 418.tab/Audit.panel/Audit.pushbutton/tests/test_warnings_check.py
python 418.tab/Audit.panel/Audit.pushbutton/tests/test_views_sheets_check.py
python 418.tab/Audit.panel/Audit.pushbutton/tests/test_report_exporter.py
python 418.tab/Audit.panel/Audit.pushbutton/tests/test_viewmodels.py
```
Expected: `OK` partout.

- [ ] **Step 7: Commit** (après accord)

```bash
git add 418.tab/Audit.panel/Audit.pushbutton/lib 418.tab/Audit.panel/Audit.pushbutton/script.py
git commit -m "feat(audit): intégration finale (auto-lancement sous progression, sélection & fermeture, export)"
```

---

## Self-Review (couverture spec)

- §Périmètre 5 thèmes → Tasks 5-9 (un checker par thème). ✅
- §1 Rebase → Task 1. ✅
- §2 Mode fenêtre modal + auto-lancement sous progression → Tasks 11 (init lance l'audit) + 13 (barre de progression). ✅
- §2 « Sélectionner & fermer » → Task 13 Step 3-4. ✅
- §3 Arborescence MVVM → Tasks 2,4,5-11. ✅
- §4 Modèles → Task 2. ✅
- §5.1 Checkers (source de vérité nommage via UserConfig) → Task 5. ✅
- §5.2 AuditRunner → Task 4. ✅
- §5.3 Score (constantes chiffrées) → Task 3. ✅
- §5.4 ReportExporter HTML → Task 10. ✅
- §6 Peuplement UI (ordre Critiques/Répartition/Score) → Task 12. ✅
- §7 Flux de données → Tasks 11 + 13. ✅
- §8 Gestion erreurs (isolation checks, doc None) → Tasks 4,5-9. ✅
- §9 Tests standalone → Tasks 2,3,4,5,6,8,10,11 + récapitulatif Task 13 Step 6. ✅
- §13 Critères de réussite → couverts par les tests manuels Task 12/13. ✅

**Cohérence des types** : `cle` de thème identiques entre checkers, `ScoreService.POIDS_THEME` et modèles (`warnings/purge/vues_feuilles/cad/nommage`). `run(doc) -> ThemeResult` uniforme. `AuditResult.top_critiques` = liste d'`AuditIssue`, consommée en `IssueRowVM` (Task 11). Noms de fonctions export `construire_html`/`exporter` cohérents entre Task 10 et Task 13.

**Points à vérifier en cours d'implémentation (non bloquants, fallback prévu)** :
- Nom exact de la fonction `sanitize` dans `lib/core/sanitize.py` (Task 10).
- API réelle de `lib/core/selection.py` pour la sélection/zoom (Task 13).
- Nom exact de la méthode `notify_property` sur `BaseViewModel` (vérifier dans `lib/ui/base/BaseViewModel.py` ; ajuster si l'API diffère).
