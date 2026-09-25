# -*- coding: utf-8 -*-
"""Tests de l'invite système. C'est le seul endroit où se règle le modèle :
ce qui se perd ici se perd dans toutes les conversations à la fois."""
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core import prompt
from core import revit_outils


class TestSansOutils(unittest.TestCase):
    """Le cas de chat_cli et chat_openai : pas de boucle d'outils."""

    def setUp(self):
        self.texte = prompt.systeme(False)

    def test_ne_promet_aucun_outil(self):
        # Promettre des yeux à un client qui n'en a pas fait répondre
        # « je regarde » à un modèle qui ne regardera rien.
        for interdit in ('revit_', 'outil', 'Ctrl+Z', 'IRRÉVERSIBLE'):
            self.assertNotIn(interdit, self.texte, interdit)

    def test_pose_quand_meme_le_role_et_la_langue(self):
        self.assertIn('architecte', self.texte)
        self.assertIn('français', self.texte)


class TestPasDeMarkdown(unittest.TestCase):
    """Le panneau affiche du texte brut : le rendre est ce qui a fait tomber
    Revit trois fois. On demande donc au modèle de n'en pas produire — c'est
    trois lignes d'invite au lieu d'un FlowDocument."""

    def test_la_consigne_vaut_avec_ET_sans_outils(self):
        # Le volet est le même dans les deux cas, la règle aussi.
        for avec in (False, True):
            texte = prompt.systeme(avec)
            self.assertIn('TEXTE BRUT', texte)
            self.assertIn('tableaux', texte)

    def test_elle_dit_quoi_faire_a_la_place(self):
        # Interdire sans proposer laisse le modèle inventer sa propre forme.
        texte = prompt.systeme(True)
        self.assertIn('tiret', texte)
        self.assertIn('nom : valeur', texte)


class TestAvecOutils(unittest.TestCase):
    def setUp(self):
        self.texte = prompt.systeme(True)

    def test_contient_tout_ce_que_contient_la_version_sans_outils(self):
        # Ajouter les outils ne doit rien retirer : c'est un empilement.
        for bloc in (prompt.IDENTITE, prompt.REPONSE, prompt.REFERENCES):
            self.assertIn(bloc, self.texte)

    def test_la_regle_des_unites_est_la(self):
        # Le modèle répondait en pieds ; lui demander de convertir n'a rien
        # donné, deux passes de suite. 418 convertit donc lui-même, et
        # l'invite doit dire au modèle de NE PAS reconvertir par-dessus.
        self.assertIn('unite_de_longueur', self.texte)
        self.assertIn('reconvertis', self.texte)

    def test_on_ne_parle_plus_de_pieds_au_modele(self):
        # S'il croit recevoir des pieds, il multiplie une valeur déjà
        # convertie et se trompe d'un facteur 3,28.
        self.assertNotIn('PIEDS', self.texte)

    def test_la_colorisation_par_filtre_est_preferee(self):
        self.assertIn('revit_filtre_couleur', self.texte)
        self.assertIn('revit_color_splash', self.texte)

    def test_la_regle_de_troncature_est_la(self):
        # Sans elle, il rappelle le même outil pour le même résultat coupé.
        self.assertIn('partielle', self.texte)

    def test_la_regle_de_recherche_en_francais_est_la(self):
        # « liste les familles de portes » ne trouvait rien : les noms du
        # projet sont français, et un filtre vide n'est pas une absence.
        self.assertIn('français', self.texte)
        self.assertIn('catégories', self.texte)

    def test_les_outils_irreversibles_sont_tous_nommes(self):
        # Un outil destructeur absent de l'invite n'a plus que sa
        # description pour garde-fou.
        for nom in revit_outils.IRREVERSIBLES:
            self.assertIn(nom, self.texte, nom)

    def test_une_demande_vague_ne_vaut_pas_accord(self):
        self.assertIn('vas-y', self.texte)
        self.assertIn('explicitement', self.texte)


class TestAssemblage(unittest.TestCase):
    def test_les_sections_sont_separees_par_une_ligne_vide(self):
        self.assertIn('\n\n', prompt.systeme(True))

    def test_aucune_section_vide(self):
        for bloc in prompt._AVEC_OUTILS:
            self.assertTrue(bloc.strip(), 'section vide dans l\'assemblage')

    def test_pas_d_espace_en_trop_aux_extremites(self):
        for avec in (False, True):
            texte = prompt.systeme(avec)
            self.assertEqual(texte, texte.strip())


class TestSourceUnique(unittest.TestCase):
    def test_chat_syntaxe_ne_porte_plus_d_invite(self):
        # Deux sources, ce sont deux comportements qui s'éloignent au
        # premier ajustement.
        from core import chat_syntaxe
        for parti in ('SYSTEME', 'OUTILLE'):
            self.assertFalse(hasattr(chat_syntaxe, parti), parti)

    def test_les_trois_clients_passent_par_ici(self):
        from core import chat_cli, chat_oauth, chat_openai
        for client in (chat_cli, chat_oauth, chat_openai):
            self.assertIs(client.systeme, prompt.systeme,
                          client.__name__)


if __name__ == '__main__':
    unittest.main()
