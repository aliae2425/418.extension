# -*- coding: utf-8 -*-
"""Le volet ne s'importe pas hors Revit — on lit donc sa source.

`from pyrevit import forms` en tête : aucun test ne peut charger ce module.
Il n'était éprouvé par rien, et deux fautes muettes y sont passées le même
jour :

- `for signature in signature.SIGNATURES` — la variable de boucle masque le
  module, et la ligne d'après cherche un attribut sur un dictionnaire ;
- un nom ajouté à l'import principal et oublié dans le repli, qui ne lève
  que sur les postes où le premier import échoue.

Les deux se voient dans l'arbre syntaxique, sans rien exécuter.
"""
from __future__ import unicode_literals
import ast
import io
import os
import sys
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(os.path.dirname(ICI), 'OpenArchiPanel.py')


def _arbre():
    with io.open(SOURCE, encoding='utf-8') as ouvert:
        return ast.parse(ouvert.read())


def _importes(arbre):
    """Les noms liés par un import, et la liste de CHAQUE `from … import`."""
    noms = set()
    listes = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.ImportFrom):
            lus = [a.asname or a.name for a in noeud.names]
            # Les imports locaux à une fonction (`Microsoft.Web…`) ne sont pas
            # le sujet : on ne compare que ceux de nos propres paquets.
            if (noeud.module or '').split('.')[-1] in ('harnais',):
                listes.append(sorted(lus))
            noms.update(lus)
        elif isinstance(noeud, ast.Import):
            noms.update(a.asname or a.name.split('.')[0] for a in noeud.names)
    return noms, listes


def _affectes(arbre):
    """Tout nom auquel on ÉCRIT : affectation, boucle, with, except, def."""
    ecrits = set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Name) and isinstance(noeud.ctx, ast.Store):
            ecrits.add(noeud.id)
        elif isinstance(noeud, (ast.FunctionDef, ast.ClassDef)):
            ecrits.add(noeud.name)
    return ecrits


class TestSourceDuVolet(unittest.TestCase):

    def test_la_source_est_analysable(self):
        self.assertIsInstance(_arbre(), ast.Module)

    def test_aucun_module_importe_n_est_masque(self):
        arbre = _arbre()
        noms, _ = _importes(arbre)
        # Seuls nos modules : `json`, `os` ne risquent rien, mais les lister
        # ne coûte rien non plus.
        surveilles = noms & set(['signature', 'secrets', 'oauth', 'outils',
                                 'json', 'os', 'forms'])
        masques = sorted(surveilles & _affectes(arbre))
        self.assertEqual([], masques,
                         'ces imports sont réaffectés quelque part : %s'
                         % masques)

    def test_l_import_de_repli_liste_les_MEMES_noms(self):
        # `try: from harnais … except: from lib.harnais …`. Un nom ajouté
        # d'un côté seulement ne lève que là où le premier import échoue —
        # donc jamais sur la machine où on l'a écrit.
        _, listes = _importes(_arbre())
        self.assertEqual(2, len(listes),
                         'on attend les deux formes de l’import harnais')
        self.assertEqual(listes[0], listes[1])

    def test_tout_module_nomme_en_prefixe_est_importe(self):
        arbre = _arbre()
        noms, _ = _importes(arbre)
        connus = noms | _affectes(arbre) | set(['self', 'cls'])
        manquants = set()
        for noeud in ast.walk(arbre):
            # `signature.SIGNATURES` : la base est un Name lu.
            if (isinstance(noeud, ast.Attribute)
                    and isinstance(noeud.value, ast.Name)
                    and isinstance(noeud.value.ctx, ast.Load)
                    and noeud.value.id not in connus
                    and not hasattr(__builtins__, noeud.value.id)):
                manquants.add(noeud.value.id)
        # Les noms venus des paramètres de fonction sont dans `_affectes`
        # (ast.arg n'existe pas en py2, mais les tests tournent en py3).
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.arguments):
                for a in list(noeud.args) + list(getattr(noeud, 'kwonlyargs', [])):
                    manquants.discard(getattr(a, 'arg', None))
        self.assertEqual(set(), manquants,
                         'employés en préfixe sans être importés : %s'
                         % sorted(manquants))


if __name__ == '__main__':
    unittest.main()
