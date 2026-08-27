# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import contextlib
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.services import MaterialService as module
from lib.services.MaterialService import MaterialService


# ----------------------------------------------------------------------
# Doublures : le service ne voit de Revit que ce qu'il appelle réellement.
# ----------------------------------------------------------------------

class FauxHostObjAttributes(object):
    """Tient la place de `Autodesk.Revit.DB.HostObjAttributes` : la classe
    des TYPES porteurs d'une structure composée (WallType, FloorType…)."""


class FausseStructure(object):
    """`CompoundStructure` : des couches, chacune avec un id matériau."""

    def __init__(self, ids_couches):
        self._couches = list(ids_couches)

    @property
    def LayerCount(self):
        return len(self._couches)

    def GetMaterialId(self, index):
        return self._couches[index]

    def SetMaterialId(self, index, id_materiau):
        self._couches[index] = id_materiau


class FauxType(FauxHostObjAttributes):
    """Un `WallType` : le matériau vit dans ses couches, et `GetMaterialIds`
    ne le voit PAS — un ElementType n'a pas de géométrie. C'est tout le
    piège que ce fichier verrouille."""

    def __init__(self, nom, ids_couches):
        self.Name = nom
        self.Id = nom
        self.Category = type('C', (), {'Name': u'Murs'})()
        self.Parameters = []
        self._structure = FausseStructure(ids_couches)
        self.structure_reaffectee = False

    def GetMaterialIds(self, peints):
        return []

    def GetCompoundStructure(self):
        return self._structure

    def SetCompoundStructure(self, structure):
        self.structure_reaffectee = True
        self._structure = structure

    def ids_couches(self):
        return list(self._structure._couches)


class FausseInstance(object):
    """Un `Wall` : remonte les matériaux des couches de son type, mais n'a
    aucune structure ni paramètre à lui. Détecté, jamais modifiable."""

    def __init__(self, nom, ids_materiaux):
        self.Name = nom
        self.Id = nom
        self.Category = type('C', (), {'Name': u'Murs'})()
        self.Parameters = []
        self._ids = list(ids_materiaux)

    def GetMaterialIds(self, peints):
        return [] if peints else list(self._ids)


class FauxCollecteur(object):
    """`FilteredElementCollector` : rend les types puis les instances selon
    le `WhereElementIs...` demandé."""

    def __init__(self, doc):
        self._doc = doc
        self._elements = []

    def WhereElementIsElementType(self):
        self._elements = self._doc.types
        return self

    def WhereElementIsNotElementType(self):
        self._elements = self._doc.instances
        return self

    def WherePasses(self, filtre):
        return self

    def ToElements(self):
        return list(self._elements)


class FauxDoc(object):

    def __init__(self, types=None, instances=None):
        self.types = list(types or [])
        self.instances = list(instances or [])


@contextlib.contextmanager
def _fausse_transaction(doc, nom):
    yield type('T', (), {'GetStatus': staticmethod(lambda: u'Committed')})()


class BaseService(unittest.TestCase):
    """Substitue les symboles Revit du module, et les restaure après coup."""

    def setUp(self):
        self._origines = {}
        for nom, valeur in (
                ('HostObjAttributes', FauxHostObjAttributes),
                ('FilteredElementCollector', FauxCollecteur),
                ('ElementMulticategoryFilter', None),
                ('StorageType', None),
                ('revit_transaction', _fausse_transaction)):
            self._origines[nom] = getattr(module, nom)
            setattr(module, nom, valeur)

    def tearDown(self):
        for nom, valeur in self._origines.items():
            setattr(module, nom, valeur)


class TestDetectionDesTypes(BaseService):
    """Régression : un type dont le matériau n'est QUE dans ses couches doit
    être détecté. `GetMaterialIds` ne renvoie rien sur un ElementType, donc
    s'appuyer sur lui seul rendait le remplacement muet — 3 porteurs
    trouvés, 0 modifié."""

    def test_type_detecte_par_ses_couches(self):
        mur = FauxType(u'Ext. Brique 22', [u'877', u'873'])
        service = MaterialService(FauxDoc(types=[mur]))
        rapport = service.analyser([u'877'])
        self.assertEqual(rapport.Total, 1)

    def test_type_hors_sources_ignore(self):
        mur = FauxType(u'Ext. Voile BA 20', [u'999'])
        service = MaterialService(FauxDoc(types=[mur]))
        self.assertTrue(service.analyser([u'877']).EstVide)

    def test_instance_detectee_par_get_material_ids(self):
        service = MaterialService(
            FauxDoc(instances=[FausseInstance(u'Mur 1', [u'877'])]))
        self.assertEqual(service.analyser([u'877']).Total, 1)


class TestRemplacementDesCouches(BaseService):

    def test_couche_reaffectee_a_la_cible(self):
        mur = FauxType(u'Ext. Brique 22', [u'877', u'873'])
        service = MaterialService(FauxDoc(types=[mur]))
        rapport = service.remplacer([u'877'], u'258872')
        self.assertEqual(mur.ids_couches(), [u'258872', u'873'])
        self.assertTrue(mur.structure_reaffectee)
        self.assertEqual(rapport.Total, 1)

    def test_plusieurs_sources_fusionnees_sur_la_cible(self):
        mur = FauxType(u'Composé', [u'877', u'872', u'873'])
        service = MaterialService(FauxDoc(types=[mur]))
        service.remplacer([u'877', u'872'], u'258872')
        self.assertEqual(mur.ids_couches(), [u'258872', u'258872', u'873'])

    def test_instance_seule_ne_compte_pas_comme_modifiee(self):
        """Une instance porte le matériau mais rien d'inscriptible : elle ne
        doit pas gonfler le rapport de modifications."""
        service = MaterialService(
            FauxDoc(instances=[FausseInstance(u'Mur 1', [u'877'])]))
        self.assertTrue(service.remplacer([u'877'], u'258872').EstVide)

    def test_cible_ecartee_des_sources(self):
        mur = FauxType(u'Ext. Brique 22', [u'877'])
        service = MaterialService(FauxDoc(types=[mur]))
        self.assertTrue(service.remplacer([u'877'], u'877').EstVide)
        self.assertEqual(mur.ids_couches(), [u'877'])

    def test_sans_cible_ne_touche_rien(self):
        mur = FauxType(u'Ext. Brique 22', [u'877'])
        service = MaterialService(FauxDoc(types=[mur]))
        self.assertTrue(service.remplacer([u'877'], None).EstVide)
        self.assertEqual(mur.ids_couches(), [u'877'])


class TestComptageDesUsages(BaseService):
    """Le chiffre affiché sur les cards doit voir la même chose qu'Analyser :
    couches de structure composée comprises, sinon un matériau utilisé par un
    WallType s'affiche « Non utilisé » alors que le remplacement le trouve."""

    def test_types_et_instances_comptes_separement(self):
        service = MaterialService(FauxDoc(
            types=[FauxType(u'Ext. Brique 22', [u'877', u'873']),
                   FauxType(u'Int. Brique', [u'877'])],
            instances=[FausseInstance(u'Mur 1', [u'877']),
                       FausseInstance(u'Mur 2', [u'877'])]))
        lignes = service.compter_utilisations([u'877', u'873'])
        self.assertEqual((lignes[u'877'].Types, lignes[u'877'].Instances),
                         (2, 2))
        self.assertEqual(lignes[u'877'].Total, 4)
        self.assertEqual(lignes[u'877'].Detail, u'2 types · 2 instances')
        self.assertEqual((lignes[u'873'].Types, lignes[u'873'].Instances),
                         (1, 0))
        self.assertEqual(lignes[u'873'].Detail, u'1 type')

    def test_materiau_inutilise_a_sa_ligne_a_zero(self):
        service = MaterialService(FauxDoc(types=[FauxType(u'M', [u'877'])]))
        lignes = service.compter_utilisations([u'877', u'999'])
        self.assertEqual(lignes[u'999'].Total, 0)
        self.assertEqual(lignes[u'999'].Detail, u'')

    def test_une_couche_repetee_ne_compte_l_element_qu_une_fois(self):
        """`_ids_materiaux` rend un set : un mur à trois couches du même
        matériau reste UN porteur, pas trois."""
        service = MaterialService(
            FauxDoc(types=[FauxType(u'Triple', [u'877', u'877', u'877'])]))
        self.assertEqual(
            service.compter_utilisations([u'877'])[u'877'].Total, 1)

    def test_sans_id_aucun_parcours(self):
        service = MaterialService(FauxDoc(types=[FauxType(u'M', [u'877'])]))
        self.assertEqual(service.compter_utilisations([]), {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
