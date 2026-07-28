# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.list_selection import ListSelectionService


class _Item(object):
    """Item minimal exposant la propriété de sélection par défaut (IsSelected)."""

    def __init__(self, selected=False):
        self.IsSelected = selected


def _states(items):
    return [it.IsSelected for it in items]


def _make(n):
    return [_Item() for _ in range(n)]


# ---------------------------------------------------------------------------
# Clic simple (sans modificateur)
# ---------------------------------------------------------------------------

class TestClicSimple(unittest.TestCase):

    def setUp(self):
        self.svc = ListSelectionService()

    def test_selectionne_uniquement_lindex_clique(self):
        items = _make(4)
        self.svc.handle_click(items, 2)
        self.assertEqual(_states(items), [False, False, True, False])

    def test_efface_la_selection_precedente(self):
        items = _make(4)
        self.svc.handle_click(items, 1)
        self.svc.handle_click(items, 3)
        self.assertEqual(_states(items), [False, False, False, True])

    def test_liste_vide_ne_leve_pas(self):
        self.svc.handle_click([], 0)

    def test_none_ne_leve_pas(self):
        self.svc.handle_click(None, 0)

    def test_index_hors_bornes_ignore(self):
        items = _make(3)
        self.svc.handle_click(items, 5)
        self.assertEqual(_states(items), [False, False, False])

    def test_index_negatif_ignore(self):
        items = _make(3)
        self.svc.handle_click(items, -1)
        self.assertEqual(_states(items), [False, False, False])


# ---------------------------------------------------------------------------
# Ctrl-clic (bascule ponctuelle)
# ---------------------------------------------------------------------------

class TestCtrlClic(unittest.TestCase):

    def setUp(self):
        self.svc = ListSelectionService()

    def test_ctrl_ajoute_sans_effacer(self):
        items = _make(4)
        self.svc.handle_click(items, 0)
        self.svc.handle_click(items, 2, ctrl=True)
        self.assertEqual(_states(items), [True, False, True, False])

    def test_ctrl_rebascule_deselectionne(self):
        items = _make(3)
        self.svc.handle_click(items, 1, ctrl=True)
        self.assertEqual(_states(items), [False, True, False])
        self.svc.handle_click(items, 1, ctrl=True)
        self.assertEqual(_states(items), [False, False, False])

    def test_ctrl_deplace_lancre(self):
        items = _make(5)
        self.svc.handle_click(items, 0)
        self.svc.handle_click(items, 3, ctrl=True)      # ancre → 3
        self.svc.handle_click(items, 1, shift=True)     # plage [1, 3] (réécrit tout)
        self.assertEqual(_states(items), [False, True, True, True, False])


# ---------------------------------------------------------------------------
# Shift-clic (plage inclusive)
# ---------------------------------------------------------------------------

class TestShiftClic(unittest.TestCase):

    def setUp(self):
        self.svc = ListSelectionService()

    def test_shift_selectionne_la_plage_inclusive(self):
        items = _make(5)
        self.svc.handle_click(items, 1)             # ancre → 1
        self.svc.handle_click(items, 3, shift=True)
        self.assertEqual(_states(items), [False, True, True, True, False])

    def test_shift_fonctionne_en_ordre_inverse(self):
        items = _make(5)
        self.svc.handle_click(items, 3)             # ancre → 3
        self.svc.handle_click(items, 1, shift=True)
        self.assertEqual(_states(items), [False, True, True, True, False])

    def test_shift_sans_ancre_se_comporte_comme_clic_simple(self):
        # Ancre à -1 (aucun clic préalable) → branche « sans modificateur ».
        items = _make(4)
        self.svc.handle_click(items, 2, shift=True)
        self.assertEqual(_states(items), [False, False, True, False])

    def test_shifts_consecutifs_gardent_la_meme_ancre(self):
        items = _make(6)
        self.svc.handle_click(items, 2)             # ancre → 2
        self.svc.handle_click(items, 4, shift=True) # plage [2, 4]
        self.assertEqual(_states(items), [False, False, True, True, True, False])
        self.svc.handle_click(items, 0, shift=True) # plage [0, 2], ancre inchangée
        self.assertEqual(_states(items), [True, True, True, False, False, False])

    def test_reset_efface_lancre(self):
        items = _make(4)
        self.svc.handle_click(items, 1)             # ancre → 1
        self.svc.reset()
        self.svc.handle_click(items, 3, shift=True) # ancre perdue → clic simple
        self.assertEqual(_states(items), [False, False, False, True])


# ---------------------------------------------------------------------------
# Propriété personnalisée
# ---------------------------------------------------------------------------

class TestPropPersonnalisee(unittest.TestCase):

    def test_prop_custom_est_utilisee(self):
        class _Row(object):
            def __init__(self):
                self.Checked = False

        svc = ListSelectionService(prop=u'Checked')
        rows = [_Row(), _Row(), _Row()]
        svc.handle_click(rows, 1)
        self.assertEqual([r.Checked for r in rows], [False, True, False])

    def test_prop_absente_ne_leve_pas(self):
        class _Bare(object):
            __slots__ = ()

        svc = ListSelectionService()
        # setattr échoue silencieusement sur __slots__ vide → ne doit pas lever.
        svc.handle_click([_Bare(), _Bare()], 0)


if __name__ == '__main__':
    unittest.main()
