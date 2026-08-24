# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
# Meme racine que pyRevit expose : <bouton>/lib.
_BUTTON_LIB = os.path.abspath(os.path.join(_HERE, '..', 'lib'))
if _BUTTON_LIB not in sys.path:
    sys.path.insert(0, _BUTTON_LIB)

from services.DuplicationSheetsService import DuplicationSheetsService
from services.DuplicationOptions import DuplicationOptions


class FakeDoc(object):
    """Registre partage des valeurs deja prises (noms + numeros de feuille).

    Simule la contrainte d'unicite de Revit : une valeur ne peut etre
    detenue que par une seule feuille a la fois."""

    def __init__(self):
        # cle -> id de la feuille detentrice
        self._names = {}
        self._numbers = {}


class _UniqueField(object):
    """Descripteur simulant un champ Revit contraint a l'unicite.

    Semantique du setter :
      - no-op si la valeur == valeur courante de CETTE feuille,
      - leve si la valeur est detenue par une AUTRE feuille du registre,
      - sinon deplace l'enregistrement (libere l'ancienne, prend la nouvelle).
    """

    def __init__(self, registry_attr):
        self._registry_attr = registry_attr
        self._value_attr = '_val_' + registry_attr

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self._value_attr)

    def __set__(self, obj, value):
        registry = getattr(obj._doc, self._registry_attr)
        current = getattr(obj, self._value_attr)
        if value == current:
            # no-op sur sa propre valeur
            return
        holder = registry.get(value)
        if holder is not None and holder != obj.Id:
            raise ValueError(u'valeur deja prise: %s' % value)
        # liberer l'ancienne cle detenue par cette feuille
        if current in registry and registry.get(current) == obj.Id:
            del registry[current]
        registry[value] = obj.Id
        setattr(obj, self._value_attr, value)


class FakeSheet(object):
    """Feuille factice avec .Name / .SheetNumber contraints a l'unicite via
    un FakeDoc partage, et un .Id."""

    Name = _UniqueField('_names')
    SheetNumber = _UniqueField('_numbers')

    def __init__(self, doc, id_, name, number):
        self._doc = doc
        self.Id = id_
        # initialisation directe (bypass des contraintes) + enregistrement
        self._val__names = name
        self._val__numbers = number
        doc._names[name] = id_
        doc._numbers[number] = id_


class FakeView(object):
    """Vue factice avec .Name contraint a l'unicite et un .Id."""

    Name = _UniqueField('_names')

    def __init__(self, doc, id_, name):
        self._doc = doc
        self.Id = id_
        self._val__names = name
        doc._names[name] = id_


class StrictSheet(object):
    """Feuille dont le setter de SheetNumber LEVE si on lui re-affecte sa
    valeur COURANTE (comme Revit qui refuse un doublon), mais ACCEPTE toute
    autre valeur.

    Sert a prouver que le garde-fou no-op (`target == valeur courante ->
    ne rien faire`) court-circuite AVANT toute tentative d'affectation :
      - garde-fou present  -> valeur inchangee ('PRE-A101'),
      - garde-fou absent    -> setter leve sur 'PRE-A101' -> boucle de
                               collision -> 'PRE-A101 (2)' accepte.
    """

    def __init__(self, number):
        self.Id = 99
        self._number = number

    @property
    def SheetNumber(self):
        return self._number

    @SheetNumber.setter
    def SheetNumber(self, value):
        if value == self._number:
            raise ValueError(u'doublon interdit (strict): %s' % value)
        self._number = value


class TestUpdateSheetNumber(unittest.TestCase):

    def test_regex_appliquee_a_execution(self):
        """(a) number_find regex '[0-9]+' -> substitution regex a l'execution.
        ECHOUE avec l'ancien str.replace (aucun substring litteral '[0-9]+')."""
        doc = FakeDoc()
        source = FakeSheet(doc, 1, u'Nom source', u'A101')
        new_sheet = FakeSheet(doc, 2, u'Nouveau', u'ZZZ999')
        opts = DuplicationOptions(number_find=u'[0-9]+', number_replace=u'X')
        svc = DuplicationSheetsService(doc)
        svc.update_sheet_number(source, new_sheet, opts)
        self.assertEqual(new_sheet.SheetNumber, u'AX')

    def test_token_resolu_a_execution(self):
        """(b) suffixe '_{n}' -> le token n'apparait PAS litteralement.
        Sans index, {n} vaut 1 (comme l'apercu). ECHOUE avec str.replace
        qui concatene '_{n}' litteralement."""
        doc = FakeDoc()
        source = FakeSheet(doc, 1, u'Nom source', u'A101')
        new_sheet = FakeSheet(doc, 2, u'Nouveau', u'ZZZ999')
        opts = DuplicationOptions(number_suffix=u'_{n}')
        svc = DuplicationSheetsService(doc)
        svc.update_sheet_number(source, new_sheet, opts)
        self.assertNotIn(u'{n}', new_sheet.SheetNumber)
        self.assertEqual(new_sheet.SheetNumber, u'A101_1')

    def test_prefixe_suffixe_litteraux(self):
        """(c) prefixe + suffixe litteraux sur le numero.
        (passe aussi avec l'ancien code — logique 'prefix + x + suffix'
        partagee ; valeur prouvee par mutation dans le rapport.)"""
        doc = FakeDoc()
        source = FakeSheet(doc, 1, u'Nom source', u'A101')
        new_sheet = FakeSheet(doc, 2, u'Nouveau', u'ZZZ999')
        opts = DuplicationOptions(number_prefix=u'PRE-', number_suffix=u'-SUF')
        svc = DuplicationSheetsService(doc)
        svc.update_sheet_number(source, new_sheet, opts)
        self.assertEqual(new_sheet.SheetNumber, u'PRE-A101-SUF')

    def test_collision_ajoute_suffixe_n(self):
        """(d) collision -> ' (2)' puis ' (3)', jamais '*'.
        ECHOUE avec l'ancien code qui ajoutait '*'."""
        doc = FakeDoc()
        source = FakeSheet(doc, 1, u'Nom source', u'A101')
        # deux feuilles occupent deja 'A101' (source) et 'A101 (2)'
        occupant2 = FakeSheet(doc, 3, u'Occ2', u'A101 (2)')
        new_sheet = FakeSheet(doc, 2, u'Nouveau', u'ZZZ999')
        opts = DuplicationOptions()  # aucune transformation -> target == 'A101'
        svc = DuplicationSheetsService(doc)
        svc.update_sheet_number(source, new_sheet, opts)
        # 'A101' pris (source), 'A101 (2)' pris (occupant2) -> 'A101 (3)'
        self.assertEqual(new_sheet.SheetNumber, u'A101 (3)')

    def test_noop_quand_cible_egale_valeur_courante(self):
        """(e) target == valeur courante du nouvel element -> ne rien faire.

        Le nouvel element est une StrictSheet dont le setter LEVE sur toute
        affectation. Le garde-fou no-op doit court-circuiter AVANT d'appeler
        le setter : la valeur reste inchangee. Assertion negative : le resultat
        ne doit PAS etre suffixe ' (2)' (ce qui arriverait si le garde-fou
        etait absent -> setter leve -> boucle de collision)."""
        doc = FakeDoc()
        # source de numero 'PRE-A101' sans prefixe -> target == 'PRE-A101',
        # exactement la valeur courante de la StrictSheet.
        source = FakeSheet(doc, 1, u'Nom source', u'PRE-A101')
        new_sheet = StrictSheet(u'PRE-A101')
        opts = DuplicationOptions()  # aucune transformation -> target == source
        svc = DuplicationSheetsService(doc)
        svc.update_sheet_number(source, new_sheet, opts)
        self.assertEqual(new_sheet.SheetNumber, u'PRE-A101')
        self.assertNotEqual(new_sheet.SheetNumber, u'PRE-A101 (2)')


class TestUpdateSheetName(unittest.TestCase):

    def test_prefixe_suffixe_litteraux_sur_nom(self):
        """(c) prefixe + suffixe litteraux sur le nom de feuille."""
        doc = FakeDoc()
        source = FakeSheet(doc, 1, u'Plan RDC', u'A101')
        new_sheet = FakeSheet(doc, 2, u'Nouveau nom', u'ZZZ999')
        opts = DuplicationOptions(name_prefix=u'DUP_', name_suffix=u'_v2')
        svc = DuplicationSheetsService(doc)
        svc.update_sheet_name(source, new_sheet, opts)
        self.assertEqual(new_sheet.Name, u'DUP_Plan RDC_v2')


class TestUpdateViewName(unittest.TestCase):

    def test_view_prefixe_et_regex(self):
        """(f) update_view_name applique prefixe + regex sur view.Name.
        ECHOUE avec str.replace (regex '\\d+' sans substring litteral)."""
        doc = FakeDoc()
        source = FakeView(doc, 1, u'Niveau 2')
        new_view = FakeView(doc, 2, u'Copie')
        opts = DuplicationOptions(view_prefix=u'V_', view_find=u'\\d+',
                                  view_replace=u'#')
        svc = DuplicationSheetsService(doc)
        svc.update_view_name(source, new_view, opts)
        self.assertEqual(new_view.Name, u'V_Niveau #')


if __name__ == '__main__':
    unittest.main()
