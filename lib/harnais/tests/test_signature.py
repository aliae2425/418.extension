# -*- coding: utf-8 -*-
"""La substitution de la sentinelle, éprouvée hors Revit.

Ce chemin décide si la clé atteint l'API. Il tourne sur le fil d'interface
de Revit, où une exception fait tomber l'hôte, et il ne se rejoue pas à la
main : d'où ces doubles, qui imitent `CoreWebView2HttpRequestHeaders` —
`GetHeader` compris, qui LÈVE sur un en-tête absent.
"""
from __future__ import unicode_literals
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from harnais.signature import signer, SIGNATURES                # noqa: E402


class Entetes(object):
    """Le double. `GetHeader` lève sur un absent — comme le vrai."""

    def __init__(self, **poses):
        self.poses = dict(poses)

    def Contains(self, nom):
        return nom in self.poses

    def GetHeader(self, nom):
        if nom not in self.poses:
            raise KeyError(nom)            # c'est ce que fait WebView2
        return self.poses[nom]

    def SetHeader(self, nom, valeur):
        self.poses[nom] = valeur


def cles(**table):
    return lambda nom: table.get(nom, '')


class TestSignature(unittest.TestCase):

    def test_openai_recoit_son_bearer(self):
        e = Entetes(Authorization='Bearer 418-hote')
        self.assertEqual('openai', signer(e, cles(openai='sk-zzz')))
        self.assertEqual('Bearer sk-zzz', e.poses['Authorization'])

    def test_anthropic_recoit_sa_cle_NUE(self):
        # Pas de « Bearer » : chez Anthropic c'est `x-api-key`, valeur nue.
        e = Entetes(**{'x-api-key': '418-hote'})
        self.assertEqual('anthropic', signer(e, cles(anthropic='sk-ant-zzz')))
        self.assertEqual('sk-ant-zzz', e.poses['x-api-key'])

    def test_une_requete_anthropic_n_a_PAS_d_Authorization(self):
        # LE défaut vécu : `GetHeader('Authorization')` levait sur la
        # première signature et emportait toute la boucle, donc la clé
        # Anthropic n'était jamais posée — 401 muet.
        e = Entetes(**{'x-api-key': '418-hote'})
        self.assertFalse(e.Contains('Authorization'))
        self.assertEqual('anthropic', signer(e, cles(anthropic='sk-ant-zzz')))

    def test_un_entete_sans_sentinelle_n_est_PAS_signe(self):
        # Un appel anonyme signé par hasard serait pire qu'un 401 franc.
        e = Entetes(Authorization='Bearer autre-chose')
        self.assertEqual('', signer(e, cles(openai='sk-zzz')))
        self.assertEqual('Bearer autre-chose', e.poses['Authorization'])

    def test_sans_cle_rien_n_est_pose(self):
        e = Entetes(Authorization='Bearer 418-hote')
        self.assertEqual('', signer(e, cles()))
        # La sentinelle part telle quelle : l'API dira 401, ce qui est juste.
        self.assertEqual('Bearer 418-hote', e.poses['Authorization'])

    def test_un_fournisseur_qui_leve_n_emporte_pas_les_autres(self):
        class Mechant(Entetes):
            def Contains(self, nom):
                if nom == 'Authorization':
                    raise RuntimeError('COM a hoqueté')
                return Entetes.Contains(self, nom)

        e = Mechant(**{'x-api-key': '418-hote'})
        self.assertEqual('anthropic', signer(e, cles(anthropic='sk-ant-zzz')))

    def test_chaque_signature_a_son_entete_et_sa_sentinelle(self):
        # Deux fournisseurs qui partageraient un en-tête se voleraient leur
        # signature — la première trouvée gagnerait.
        entetes = [s['entete'] for s in SIGNATURES]
        self.assertEqual(len(entetes), len(set(entetes)))
        for s in SIGNATURES:
            self.assertTrue(s['sentinelle'])
            self.assertTrue(s['filtre'].startswith('https://'))


if __name__ == '__main__':
    unittest.main()
