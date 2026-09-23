# -*- coding: utf-8 -*-
"""Tests du markdown minimal des bulles de chat."""
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core import markdown_simple as md


class TestMorceaux(unittest.TestCase):
    def test_texte_nu_reste_dun_seul_tenant(self):
        self.assertEqual(md.morceaux('bonjour'), [(md.BRUT, 'bonjour')])

    def test_gras(self):
        self.assertEqual(md.morceaux('le **gras** ici'),
                         [(md.BRUT, 'le '), (md.GRAS, 'gras'),
                          (md.BRUT, ' ici')])

    def test_le_gras_gagne_sur_l_italique(self):
        # Avec les alternatives dans le mauvais ordre, « **x** » se lit comme
        # un italique vide suivi d'une étoile.
        self.assertEqual(md.morceaux('**x**'), [(md.GRAS, 'x')])

    def test_italique_etoile_et_souligne(self):
        self.assertEqual(md.morceaux('*a* _b_'),
                         [(md.ITAL, 'a'), (md.BRUT, ' '), (md.ITAL, 'b')])

    def test_code_en_ligne(self):
        self.assertEqual(md.morceaux('appelle `revit_status` vite'),
                         [(md.BRUT, 'appelle '), (md.CODE, 'revit_status'),
                          (md.BRUT, ' vite')])

    def test_les_marques_du_code_ne_sont_pas_relues(self):
        # Dans du code, « * » est du texte : le styliser massacrerait un
        # extrait Python.
        self.assertEqual(md.morceaux('`a * b`'), [(md.CODE, 'a * b')])

    def test_une_etoile_isolee_reste_du_texte(self):
        self.assertEqual(md.morceaux('3 * 4 = 12'), [(md.BRUT, '3 * 4 = 12')])

    def test_un_souligne_dans_un_identifiant_ne_passe_pas_en_italique(self):
        self.assertEqual(md.morceaux('revit_list_views et revit_status'),
                         [(md.BRUT, 'revit_list_views et revit_status')])


class TestBlocs(unittest.TestCase):
    def genres(self, texte):
        return [genre for genre, _n, _m in md.blocs(texte)]

    def test_paragraphe_simple(self):
        self.assertEqual(self.genres('bonjour'), [md.PARAGRAPHE])

    def test_lignes_vides_ignorees(self):
        self.assertEqual(self.genres('a\n\n\nb'),
                         [md.PARAGRAPHE, md.PARAGRAPHE])

    def test_puces_des_trois_marqueurs(self):
        self.assertEqual(self.genres('- a\n* b\n+ c'), [md.PUCE] * 3)

    def test_puce_indentee(self):
        self.assertEqual(self.genres('  - a'), [md.PUCE])

    def test_le_contenu_de_la_puce_perd_son_tiret(self):
        _genre, _n, parts = md.blocs('- **porte**')[0]
        self.assertEqual(parts, [(md.GRAS, 'porte')])

    def test_liste_numerotee_garde_son_numero(self):
        genre, _n, parts = md.blocs('2. deuxième')[0]
        self.assertEqual(genre, md.NUMERO)
        self.assertEqual(parts[0], (md.BRUT, '2. '))

    def test_titres_et_niveaux(self):
        niveaux = [n for _g, n, _m in md.blocs('# un\n### trois')]
        self.assertEqual(niveaux, [1, 3])

    def test_le_diese_sans_espace_n_est_pas_un_titre(self):
        # « #{Référence} » est la syntaxe des références du chat.
        self.assertEqual(self.genres('#{Porte 01}'), [md.PARAGRAPHE])

    def test_bloc_de_code_cloture(self):
        genres = self.genres('avant\n```python\nx = 1\n```\naprès')
        self.assertEqual(genres, [md.PARAGRAPHE, md.BLOC_CODE,
                                  md.PARAGRAPHE])

    def test_les_marques_du_bloc_de_code_ne_s_affichent_pas(self):
        for _g, _n, parts in md.blocs('```\nx\n```'):
            self.assertNotIn('```', parts[0][1])

    def test_le_markdown_est_inerte_dans_un_bloc_de_code(self):
        _genre, _n, parts = md.blocs('```\n- a **b**\n```')[0]
        self.assertEqual(parts, [(md.CODE, '- a **b**')])

    def test_bloc_de_code_jamais_referme(self):
        # Une réponse tronquée ne doit pas faire perdre le reste.
        self.assertEqual(self.genres('```\nx\ny'),
                         [md.BLOC_CODE, md.BLOC_CODE])

    def test_texte_vide_ne_leve_pas(self):
        self.assertEqual(md.blocs(''), [])
        self.assertEqual(md.blocs(None), [])


class TestTexteNu(unittest.TestCase):
    def test_les_marques_disparaissent(self):
        self.assertEqual(md.texte_nu('**a** et `b`'), 'a et b')

    def test_les_puces_gardent_un_reperage(self):
        self.assertEqual(md.texte_nu('- a\n- b'), '• a\n• b')


if __name__ == '__main__':
    unittest.main()
