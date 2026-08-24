# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core import bulk_edit


# ---------------------------------------------------------------------------
# Faux objet générique — propriétés posées dynamiquement via setattr/getattr
# ---------------------------------------------------------------------------

class _Item(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# get_selected
# ---------------------------------------------------------------------------

class TestGetSelected(unittest.TestCase):

    def setUp(self):
        self.svc = bulk_edit

    def test_liste_vide_retourne_vide(self):
        self.assertEqual(self.svc.get_selected([]), [])

    def test_none_retourne_vide(self):
        self.assertEqual(self.svc.get_selected(None), [])

    def test_un_item_selectionne_retourne_cet_item(self):
        item = _Item(Selected=True)
        self.assertEqual(self.svc.get_selected([item]), [item])

    def test_un_item_non_selectionne_retourne_vide(self):
        item = _Item(Selected=False)
        self.assertEqual(self.svc.get_selected([item]), [])

    def test_plusieurs_items_filtre_correctement(self):
        a = _Item(Selected=True)
        b = _Item(Selected=False)
        c = _Item(Selected=True)
        result = self.svc.get_selected([a, b, c])
        self.assertEqual(result, [a, c])

    def test_prop_absente_traite_comme_falsy(self):
        # L'item n'a pas l'attribut Selected → getattr retourne False.
        item = _Item()
        self.assertEqual(self.svc.get_selected([item]), [])

    def test_prop_custom(self):
        a = _Item(Visible=True)
        b = _Item(Visible=False)
        result = self.svc.get_selected([a, b], prop=u'Visible')
        self.assertEqual(result, [a])

    def test_valeur_truthy_non_booleenne_retenue(self):
        # Une valeur comme 1 ou 'oui' est truthy → l'item doit être retenu.
        item = _Item(Selected=1)
        self.assertEqual(self.svc.get_selected([item]), [item])

    def test_valeur_falsy_non_booleenne_exclue(self):
        item = _Item(Selected=0)
        self.assertEqual(self.svc.get_selected([item]), [])


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

class TestApply(unittest.TestCase):

    def setUp(self):
        self.svc = bulk_edit

    def test_liste_vide_ne_leve_pas(self):
        self.svc.apply([], u'Selected', True)  # doit passer silencieusement

    def test_none_ne_leve_pas(self):
        self.svc.apply(None, u'Selected', True)

    def test_un_item_fixe_la_valeur(self):
        item = _Item(Selected=False)
        self.svc.apply([item], u'Selected', True)
        self.assertTrue(item.Selected)

    def test_plusieurs_items_tous_mis_a_jour(self):
        items = [_Item(Selected=True), _Item(Selected=True), _Item(Selected=True)]
        self.svc.apply(items, u'Selected', False)
        for it in items:
            self.assertFalse(it.Selected)

    def test_prop_inexistante_cree_lattribut_silencieusement(self):
        # setattr crée l'attribut s'il n'existait pas, sans lever.
        item = _Item()
        self.svc.apply([item], u'NouvellePropr', 42)
        self.assertEqual(item.NouvellePropr, 42)

    def test_objet_avec_setattr_bloquant_est_ignore_silencieusement(self):
        # Un objet qui refuse tous les setattr ne doit pas faire planter apply.
        class _Immuable(object):
            __slots__ = ()
        item = _Immuable()
        # Ne doit pas lever
        self.svc.apply([item], u'Selected', True)


# ---------------------------------------------------------------------------
# toggle
# ---------------------------------------------------------------------------

class TestToggle(unittest.TestCase):

    def setUp(self):
        self.svc = bulk_edit

    def test_liste_vide_ne_leve_pas(self):
        self.svc.toggle([], u'Selected')

    def test_none_ne_leve_pas(self):
        self.svc.toggle(None, u'Selected')

    def test_tous_true_bascule_vers_false(self):
        items = [_Item(Selected=True), _Item(Selected=True), _Item(Selected=True)]
        self.svc.toggle(items, u'Selected')
        for it in items:
            self.assertFalse(it.Selected)

    def test_tous_false_bascule_vers_true(self):
        items = [_Item(Selected=False), _Item(Selected=False)]
        self.svc.toggle(items, u'Selected')
        for it in items:
            self.assertTrue(it.Selected)

    def test_partiel_true_bascule_tous_vers_true(self):
        # Au moins un False → règle « sinon tout à True ».
        a = _Item(Selected=True)
        b = _Item(Selected=False)
        self.svc.toggle([a, b], u'Selected')
        self.assertTrue(a.Selected)
        self.assertTrue(b.Selected)

    def test_un_seul_item_true_bascule_vers_false(self):
        item = _Item(Selected=True)
        self.svc.toggle([item], u'Selected')
        self.assertFalse(item.Selected)

    def test_un_seul_item_false_bascule_vers_true(self):
        item = _Item(Selected=False)
        self.svc.toggle([item], u'Selected')
        self.assertTrue(item.Selected)

    def test_prop_custom(self):
        items = [_Item(Actif=True), _Item(Actif=True)]
        self.svc.toggle(items, u'Actif')
        for it in items:
            self.assertFalse(it.Actif)

    def test_prop_absente_traitee_comme_false_donc_bascule_vers_true(self):
        # getattr retourne False (défaut) → not all_on = True.
        items = [_Item(), _Item()]
        self.svc.toggle(items, u'Selected')
        for it in items:
            self.assertTrue(it.Selected)

    def test_double_toggle_retourne_a_letat_initial(self):
        items = [_Item(Selected=True), _Item(Selected=False)]
        # état initial : partiel → tous True
        self.svc.toggle(items, u'Selected')
        self.assertTrue(all(it.Selected for it in items))
        # deuxième toggle : tous True → tous False
        self.svc.toggle(items, u'Selected')
        self.assertFalse(any(it.Selected for it in items))


# ---------------------------------------------------------------------------
# select_all
# ---------------------------------------------------------------------------

class TestSelectAll(unittest.TestCase):

    def setUp(self):
        self.svc = bulk_edit

    def test_liste_vide_ne_leve_pas(self):
        self.svc.select_all([])

    def test_tous_mis_a_true(self):
        items = [_Item(Selected=False), _Item(Selected=False), _Item(Selected=True)]
        self.svc.select_all(items)
        for it in items:
            self.assertTrue(it.Selected)

    def test_un_seul_item_mis_a_true(self):
        item = _Item(Selected=False)
        self.svc.select_all([item])
        self.assertTrue(item.Selected)

    def test_deja_tous_true_reste_stable(self):
        items = [_Item(Selected=True), _Item(Selected=True)]
        self.svc.select_all(items)
        for it in items:
            self.assertTrue(it.Selected)

    def test_prop_custom(self):
        items = [_Item(Visible=False), _Item(Visible=False)]
        self.svc.select_all(items, prop=u'Visible')
        for it in items:
            self.assertTrue(it.Visible)


# ---------------------------------------------------------------------------
# deselect_all
# ---------------------------------------------------------------------------

class TestDeselectAll(unittest.TestCase):

    def setUp(self):
        self.svc = bulk_edit

    def test_liste_vide_ne_leve_pas(self):
        self.svc.deselect_all([])

    def test_tous_mis_a_false(self):
        items = [_Item(Selected=True), _Item(Selected=True), _Item(Selected=False)]
        self.svc.deselect_all(items)
        for it in items:
            self.assertFalse(it.Selected)

    def test_un_seul_item_mis_a_false(self):
        item = _Item(Selected=True)
        self.svc.deselect_all([item])
        self.assertFalse(item.Selected)

    def test_deja_tous_false_reste_stable(self):
        items = [_Item(Selected=False), _Item(Selected=False)]
        self.svc.deselect_all(items)
        for it in items:
            self.assertFalse(it.Selected)

    def test_prop_custom(self):
        items = [_Item(Visible=True), _Item(Visible=True)]
        self.svc.deselect_all(items, prop=u'Visible')
        for it in items:
            self.assertFalse(it.Visible)


# ---------------------------------------------------------------------------
# Cas d'intégration légers (enchaînements réalistes)
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):
    """Enchaînements cohérents entre les méthodes — simule un usage réel."""

    def setUp(self):
        self.svc = bulk_edit

    def test_select_all_puis_get_selected_retourne_tout(self):
        items = [_Item(Selected=False), _Item(Selected=False), _Item(Selected=False)]
        self.svc.select_all(items)
        self.assertEqual(self.svc.get_selected(items), items)

    def test_deselect_all_puis_get_selected_retourne_rien(self):
        items = [_Item(Selected=True), _Item(Selected=True)]
        self.svc.deselect_all(items)
        self.assertEqual(self.svc.get_selected(items), [])

    def test_toggle_sur_selection_partielle_puis_get_selected_retourne_tout(self):
        a = _Item(Selected=True)
        b = _Item(Selected=False)
        self.svc.toggle([a, b], u'Selected')
        # Les deux doivent être True après le toggle partiel → True.
        self.assertEqual(self.svc.get_selected([a, b]), [a, b])

    def test_apply_valeur_arbitraire_puis_get_selected(self):
        # apply avec une valeur truthy quelconque → get_selected doit trouver l'item.
        item = _Item(Selected=False)
        self.svc.apply([item], u'Selected', u'oui')
        self.assertEqual(self.svc.get_selected([item]), [item])


if __name__ == '__main__':
    unittest.main()
