# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

import lib.services.ViewsDuplicationService as vds_mod
from lib.services.ViewsDuplicationService import ViewsDuplicationService
from lib.services.ViewsDuplicationOptions import ViewsDuplicationOptions


class FakeId(object):
    """Faux ElementId : identité par valeur entiere."""

    _seq = 0

    def __init__(self):
        FakeId._seq += 1
        self.value = FakeId._seq

    def __eq__(self, other):
        return isinstance(other, FakeId) and other.value == self.value

    def __hash__(self):
        return hash(self.value)


class FakeDoc(object):
    """Faux Document : registre partagé des noms de vues + GetElement."""

    def __init__(self):
        self._by_id = {}
        self.names = set()   # registre partage des noms pris

    def register(self, view):
        self._by_id[view.Id] = view
        self.names.add(view._name)

    def GetElement(self, elem_id):
        return self._by_id.get(elem_id)


class FakeView(object):
    """Faux View : .Id, .ViewType (string), .Name (setter avec collision),
    .Duplicate(opt) qui cree une copie de nom Revit par defaut."""

    def __init__(self, doc, name, view_type=u'FloorPlan'):
        self._doc = doc
        self._name = name
        self.ViewType = view_type
        self.Id = FakeId()
        doc.register(self)

    @property
    def Name(self):
        return self._name

    @Name.setter
    def Name(self, value):
        if value == self._name:
            return  # no-op : renommage vers son propre nom
        if value in self._doc.names:
            raise Exception(u'Le nom "{0}" est deja utilise.'.format(value))
        self._doc.names.discard(self._name)
        self._name = value
        self._doc.names.add(value)

    def Duplicate(self, opt):
        copy = FakeView(self._doc, u'Copie de ' + self._name, self.ViewType)
        return copy.Id


class TestViewsDuplicationServiceRenommage(unittest.TestCase):

    def test_prefixe_applique(self):
        doc = FakeDoc()
        source = FakeView(doc, u'Plan1')
        opts = ViewsDuplicationOptions(count=1, prefixe=u'PFX_')
        svc = ViewsDuplicationService(doc)
        new_ids = svc.duplicate([source], opts)
        self.assertEqual(len(new_ids), 1)
        copie = doc.GetElement(new_ids[0])
        self.assertEqual(copie.Name, u'PFX_Plan1')

    def test_token_n_incremente_par_copie(self):
        doc = FakeDoc()
        source = FakeView(doc, u'Plan1')
        opts = ViewsDuplicationOptions(count=3, suffixe=u'_{n}')
        svc = ViewsDuplicationService(doc)
        new_ids = svc.duplicate([source], opts)
        noms = [doc.GetElement(i).Name for i in new_ids]
        self.assertEqual(noms, [u'Plan1_1', u'Plan1_2', u'Plan1_3'])

    def test_count_multiple_noms_uniques(self):
        doc = FakeDoc()
        source = FakeView(doc, u'Plan1')
        # Cible identique pour chaque copie (pas de {n}) → collision → suffixes.
        opts = ViewsDuplicationOptions(count=3, prefixe=u'PFX_')
        svc = ViewsDuplicationService(doc)
        new_ids = svc.duplicate([source], opts)
        noms = [doc.GetElement(i).Name for i in new_ids]
        self.assertEqual(noms, [u'PFX_Plan1', u'PFX_Plan1 (2)', u'PFX_Plan1 (3)'])
        self.assertEqual(len(set(noms)), 3)

    def test_collision_avec_vue_existante_suffixe_2(self):
        doc = FakeDoc()
        # Une vue existante occupe déjà le nom cible.
        FakeView(doc, u'PFX_Plan1')
        source = FakeView(doc, u'Plan1')
        opts = ViewsDuplicationOptions(count=1, prefixe=u'PFX_')
        svc = ViewsDuplicationService(doc)
        new_ids = svc.duplicate([source], opts)
        copie = doc.GetElement(new_ids[0])
        self.assertEqual(copie.Name, u'PFX_Plan1 (2)')

    def test_aucun_nommage_conserve_nom_revit(self):
        doc = FakeDoc()
        source = FakeView(doc, u'Plan1')
        opts = ViewsDuplicationOptions(count=1)  # aucun champ de nommage
        svc = ViewsDuplicationService(doc)
        new_ids = svc.duplicate([source], opts)
        copie = doc.GetElement(new_ids[0])
        # target == nom_source ('Plan1') → pas de renommage → nom Revit par défaut.
        self.assertEqual(copie.Name, u'Copie de Plan1')

    def test_plusieurs_vues_sources(self):
        doc = FakeDoc()
        v1 = FakeView(doc, u'Plan1')
        v2 = FakeView(doc, u'Plan2')
        opts = ViewsDuplicationOptions(count=2, prefixe=u'C_', suffixe=u'_{n}')
        svc = ViewsDuplicationService(doc)
        new_ids = svc.duplicate([v1, v2], opts)
        self.assertEqual(len(new_ids), 4)
        noms = [doc.GetElement(i).Name for i in new_ids]
        self.assertEqual(
            noms,
            [u'C_Plan1_1', u'C_Plan1_2', u'C_Plan2_1', u'C_Plan2_2'],
        )


class FakeSchedule(FakeView):
    """Faux ViewSchedule : sous-classe pour permettre isinstance()."""

    def __init__(self, doc, name):
        super(FakeSchedule, self).__init__(doc, name, view_type=u'Schedule')


class TestViewsDuplicationServiceBranches(unittest.TestCase):
    """Vérifie que schedules et legends sont renommés ET renvoyés
    (correction du bug de reselection : leurs ids étaient jetés)."""

    def setUp(self):
        # Sauvegarde et injecte des faux types Revit au niveau module.
        self._saved_schedule = vds_mod.ViewSchedule
        self._saved_viewtype = vds_mod.ViewType
        vds_mod.ViewSchedule = FakeSchedule

        class _FakeViewType(object):
            Legend = u'Legend'

        vds_mod.ViewType = _FakeViewType

    def tearDown(self):
        vds_mod.ViewSchedule = self._saved_schedule
        vds_mod.ViewType = self._saved_viewtype

    def test_schedule_id_renvoye_et_renomme(self):
        doc = FakeDoc()
        sched = FakeSchedule(doc, u'Nomenclature1')
        opts = ViewsDuplicationOptions(count=2, prefixe=u'S_', suffixe=u'_{n}')
        svc = ViewsDuplicationService(doc)
        new_ids = svc.duplicate([sched], opts)
        self.assertEqual(len(new_ids), 2)  # ids capturés, non jetés
        noms = [doc.GetElement(i).Name for i in new_ids]
        self.assertEqual(noms, [u'S_Nomenclature1_1', u'S_Nomenclature1_2'])

    def test_legend_id_renvoye_et_renomme(self):
        doc = FakeDoc()
        legend = FakeView(doc, u'Legende1', view_type=u'Legend')
        opts = ViewsDuplicationOptions(count=1, prefixe=u'L_')
        svc = ViewsDuplicationService(doc)
        new_ids = svc.duplicate([legend], opts)
        self.assertEqual(len(new_ids), 1)  # id capturé, non jeté
        copie = doc.GetElement(new_ids[0])
        self.assertEqual(copie.Name, u'L_Legende1')


if __name__ == '__main__':
    unittest.main()
