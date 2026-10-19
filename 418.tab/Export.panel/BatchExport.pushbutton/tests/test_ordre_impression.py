# -*- coding: utf-8 -*-
# Ordre d'impression des feuilles : les deux fonctions pures, le ViewModel de
# la modale, et la persistance côté MainViewModel.
from __future__ import unicode_literals
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in os.sys.path:
    os.sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in os.sys.path:
    os.sys.path.insert(0, _BUTTON)

import tempfile as _tf
os.environ['PY418_CONFIG_DIR'] = _tf.mkdtemp(prefix='418test_')

from lib.services.ordre import ordonner, reposer
from lib.viewmodels.OrdreImpressionViewModel import OrdreImpressionViewModel
from lib.viewmodels.MainViewModel import MainViewModel


class _Feuille(object):
    """Substitut de SheetItemVM / ManualSheetVM : seul `.Numero` compte."""

    def __init__(self, numero):
        self.Numero = numero
        self.Nom = u'plan ' + numero

    def __repr__(self):
        return str('<{}>'.format(self.Numero))


class _Config(object):
    """Faux magasin UserConfig : même contrat get/set, en mémoire."""

    def __init__(self, valeurs=None):
        self.valeurs = dict(valeurs or {})

    def get(self, cle, defaut=u''):
        return self.valeurs.get(cle, defaut)

    def set(self, cle, valeur):
        self.valeurs[cle] = valeur


class _SheetService(object):
    """Faux SheetCollectionService : un jeu unique, des feuilles données."""

    def __init__(self, numeros):
        self._numeros = list(numeros)

    def list_collections(self):
        return [{'Titre': u'Détails', 'Id': 1, 'Elem': None}]

    def list_sheets(self, collection_id=None):
        return [{'Numero': n, 'Nom': u'plan ' + n, 'CollectionId': 1,
                 'Elem': None} for n in self._numeros]

    def list_all_sheets(self):
        return self.list_sheets()

    def list_view_sheet_sets(self):
        return []


def _numeros(items):
    return [f.Numero for f in items]


class TestOrdonner(unittest.TestCase):

    def test_sans_reference_tri_naturel(self):
        """Le défaut de l'outil : A9 avant A10, pas l'inverse."""
        feuilles = [_Feuille(u'A10'), _Feuille(u'A9'), _Feuille(u'A2')]
        trie = ordonner(feuilles, None, cle=lambda f: f.Numero)
        self.assertEqual(_numeros(trie), [u'A2', u'A9', u'A10'])

    def test_reference_vide_equivaut_a_sans_reference(self):
        feuilles = [_Feuille(u'100'), _Feuille(u'20')]
        self.assertEqual(
            _numeros(ordonner(feuilles, [], cle=lambda f: f.Numero)),
            [u'20', u'100'])

    def test_reference_impose_son_ordre(self):
        feuilles = [_Feuille(u'A1'), _Feuille(u'A2'), _Feuille(u'A3')]
        trie = ordonner(feuilles, [u'A3', u'A1', u'A2'],
                        cle=lambda f: f.Numero)
        self.assertEqual(_numeros(trie), [u'A3', u'A1', u'A2'])

    def test_feuille_absente_de_la_reference_passe_a_la_fin(self):
        """Une feuille créée après la réorganisation : à la fin, jamais
        insérée au milieu d'un ordre validé par l'utilisateur."""
        feuilles = [_Feuille(u'A1'), _Feuille(u'A9'), _Feuille(u'A2'),
                    _Feuille(u'A10')]
        trie = ordonner(feuilles, [u'A2', u'A1'], cle=lambda f: f.Numero)
        self.assertEqual(_numeros(trie), [u'A2', u'A1', u'A9', u'A10'])

    def test_reference_citant_une_feuille_disparue(self):
        feuilles = [_Feuille(u'A2'), _Feuille(u'A1')]
        trie = ordonner(feuilles, [u'A1', u'DISPARUE', u'A2'],
                        cle=lambda f: f.Numero)
        self.assertEqual(_numeros(trie), [u'A1', u'A2'])

    def test_numero_vide_ne_leve_pas(self):
        feuilles = [_Feuille(u'A1'), _Feuille(u'')]
        trie = ordonner(feuilles, None, cle=lambda f: f.Numero)
        self.assertEqual(len(trie), 2)


class TestReposer(unittest.TestCase):

    def test_sous_ensemble_repose_sur_ses_places(self):
        """Les feuilles masquées (B1) ne bougent pas : seules les places
        qu'occupait le sous-ensemble sont redistribuées."""
        a1, b1, a2, a3 = (_Feuille(u'A1'), _Feuille(u'B1'),
                          _Feuille(u'A2'), _Feuille(u'A3'))
        complet = [a1, b1, a2, a3]
        resultat = reposer(complet, [a3, a2, a1], cle=lambda f: f.Numero)
        self.assertEqual(_numeros(resultat), [u'A3', u'B1', u'A2', u'A1'])

    def test_sous_ensemble_vide_ne_change_rien(self):
        complet = [_Feuille(u'A1'), _Feuille(u'A2')]
        self.assertEqual(_numeros(reposer(complet, [], cle=lambda f: f.Numero)),
                         [u'A1', u'A2'])

    def test_longueur_conservee(self):
        complet = [_Feuille(str(i)) for i in range(5)]
        resultat = reposer(complet, list(reversed(complet)),
                           cle=lambda f: f.Numero)
        self.assertEqual(len(resultat), 5)


class TestOrdreImpressionViewModel(unittest.TestCase):

    def setUp(self):
        self.vm = OrdreImpressionViewModel(
            [_Feuille(u'A10'), _Feuille(u'A9'), _Feuille(u'A1')],
            sous_titre=u'Détails')

    def test_part_de_la_liste_recue_sans_la_retrier(self):
        self.assertEqual(self.vm.Numeros, [u'A10', u'A9', u'A1'])
        self.assertEqual(self.vm.SousTitre, u'Détails')
        self.assertEqual(self.vm.NbFeuilles, 3)

    def test_trier_par_numero_rend_lordre_naturel(self):
        self.vm.trier_numero()
        self.assertEqual(self.vm.Numeros, [u'A1', u'A9', u'A10'])

    def test_monter_deplace_et_garde_la_selection(self):
        self.vm.SelectedIndex = 2
        self.vm.monter()
        self.assertEqual(self.vm.Numeros, [u'A10', u'A1', u'A9'])
        self.assertEqual(self.vm.SelectedIndex, 1)

    def test_descendre_deplace_et_garde_la_selection(self):
        self.vm.SelectedIndex = 0
        self.vm.descendre()
        self.assertEqual(self.vm.Numeros, [u'A9', u'A10', u'A1'])
        self.assertEqual(self.vm.SelectedIndex, 1)

    def test_glisser_vers_le_bas(self):
        """Le glissé prend la place de la ligne visée : A10 lâché sur A1
        devient la 3e ligne, les autres remontent d'un rang."""
        self.vm.deplacer_vers(0, 2)
        self.assertEqual(self.vm.Numeros, [u'A9', u'A1', u'A10'])
        self.assertEqual(self.vm.SelectedIndex, 2)

    def test_glisser_vers_le_haut(self):
        self.vm.deplacer_vers(2, 0)
        self.assertEqual(self.vm.Numeros, [u'A1', u'A10', u'A9'])
        self.assertEqual(self.vm.SelectedIndex, 0)

    def test_tout_mouvement_rend_une_NOUVELLE_liste(self):
        """`ItemsSource` est une propriété de dépendance : `SetValue`
        court-circuite quand la référence ne change pas. Muter la liste en
        place laissait la ListBox figée, PropertyChanged ou pas."""
        for geste in (lambda: self.vm.deplacer_vers(0, 2),
                      lambda: self.vm.monter(),
                      lambda: self.vm.descendre(),
                      lambda: self.vm.trier_numero()):
            self.vm.SelectedIndex = 1
            avant = self.vm.Feuilles
            geste()
            self.assertIsNot(self.vm.Feuilles, avant)

    def test_glisser_sur_soi_meme_sans_effet(self):
        self.vm.deplacer_vers(1, 1)
        self.assertEqual(self.vm.Numeros, [u'A10', u'A9', u'A1'])

    def test_glisser_hors_bornes_sans_effet(self):
        """Le dépôt peut viser n'importe où — y compris le vide sous la
        dernière ligne, qui résout un rang calculé, pas cliqué."""
        for depart, arrivee in ((0, 3), (0, -1), (5, 0), (-1, 0)):
            self.vm.deplacer_vers(depart, arrivee)
        self.assertEqual(self.vm.Numeros, [u'A10', u'A9', u'A1'])

    def test_glisser_rang_non_entier_sans_effet(self):
        self.vm.deplacer_vers(None, 1)
        self.vm.deplacer_vers(0, u'pas un rang')
        self.assertEqual(self.vm.Numeros, [u'A10', u'A9', u'A1'])

    def test_hors_bornes_sans_effet(self):
        self.vm.SelectedIndex = 0
        self.vm.monter()
        self.vm.SelectedIndex = 2
        self.vm.descendre()
        self.assertEqual(self.vm.Numeros, [u'A10', u'A9', u'A1'])

    def test_peut_monter_descendre_suivent_la_selection(self):
        self.vm.SelectedIndex = 0
        self.assertFalse(self.vm.PeutMonter)
        self.assertTrue(self.vm.PeutDescendre)
        self.vm.SelectedIndex = 2
        self.assertTrue(self.vm.PeutMonter)
        self.assertFalse(self.vm.PeutDescendre)

    def test_valide_seulement_apres_valider(self):
        self.assertFalse(self.vm.Valide)
        self.vm.valider()
        self.assertTrue(self.vm.Valide)

    def test_rend_les_objets_recus_pas_des_copies(self):
        """`appliquer_ordre_manuel` passe `Feuilles` à `reposer`, qui doit
        reconnaître les ManualSheetVM d'origine."""
        feuilles = [_Feuille(u'A1'), _Feuille(u'A2')]
        vm = OrdreImpressionViewModel(feuilles)
        self.assertIs(vm.Feuilles[0], feuilles[0])


class TestMainViewModelOrdre(unittest.TestCase):

    def _vm(self, numeros, config=None):
        return MainViewModel(doc=None,
                             sheet_service=_SheetService(numeros),
                             config=config or _Config())

    def test_carte_de_jeu_en_ordre_naturel_par_defaut(self):
        vm = self._vm([u'A10', u'A9', u'A2'])
        vm.refresh_par_jeu()
        self.assertEqual(_numeros(vm.Collections[0].Sheets),
                         [u'A2', u'A9', u'A10'])

    def test_liste_manuelle_en_ordre_naturel_par_defaut(self):
        vm = self._vm([u'A10', u'A9', u'A2'])
        vm.refresh_manuel()
        self.assertEqual(_numeros(vm.SheetsManuel), [u'A2', u'A9', u'A10'])

    def test_ordre_de_jeu_persiste_et_se_relit(self):
        cfg = _Config()
        vm = self._vm([u'A1', u'A2', u'A3'], config=cfg)
        vm.appliquer_ordre_jeu(u'Détails', [u'A3', u'A1', u'A2'])
        self.assertEqual(_numeros(vm.Collections[0].Sheets),
                         [u'A3', u'A1', u'A2'])

        # Même config, nouvelle instance : l'ordre revient.
        autre = self._vm([u'A1', u'A2', u'A3'], config=cfg)
        autre.refresh_par_jeu()
        self.assertEqual(_numeros(autre.Collections[0].Sheets),
                         [u'A3', u'A1', u'A2'])

    def test_titre_accentue_persiste(self):
        """IronPython lève sur `json.dumps` d'un accent sans
        `ensure_ascii=False` — invisible ici, mais la clé doit rester lisible."""
        cfg = _Config()
        vm = self._vm([u'A1', u'A2'], config=cfg)
        vm.appliquer_ordre_jeu(u'1.06_Détails', [u'A2', u'A1'])
        self.assertIn(u'Détails', cfg.get('jeux_ordre'))

    def test_ordre_naturel_nest_pas_stocke(self):
        """« Trier par numéro » rend son défaut au jeu : rien n'est mémorisé,
        sinon une feuille créée ensuite atterrirait en fin de carnet."""
        cfg = _Config()
        vm = self._vm([u'A1', u'A2'], config=cfg)
        vm.appliquer_ordre_jeu(u'Détails', [u'A2', u'A1'])
        self.assertIn(u'A2', cfg.get('jeux_ordre'))
        vm.appliquer_ordre_jeu(u'Détails', [u'A1', u'A2'])
        self.assertEqual(vm._ordre_jeux, {})

    def test_ordre_transmis_a_lexport(self):
        """`lancer_export` doit passer les ordres à l'orchestrateur : sans
        ça, la modale ne changerait que l'affichage."""
        vus = {}

        class _Orch(object):
            def run(self, doc, flags, **kwargs):
                vus.update(kwargs)
                return True

        vm = self._vm([u'A1', u'A2'])
        vm._doc = object()
        vm.appliquer_ordre_jeu(u'Détails', [u'A2', u'A1'])
        vm._creer_orchestrateur = lambda: _Orch()
        vm.lancer_export()
        self.assertEqual(vus.get('ordres'), {u'Détails': [u'A2', u'A1']})

    def test_ordre_manuel_ne_perd_pas_les_cases_cochees(self):
        """`appliquer_ordre_manuel` ne doit PAS passer par refresh_manuel(),
        qui remet ExportPdf à False (sélection éphémère)."""
        vm = self._vm([u'A1', u'A2', u'A3'])
        vm.refresh_manuel()
        for s in vm.SheetsManuel:
            s.ExportPdf = True
        inverse = list(reversed(vm.SheetsManuelFiltrees))
        vm.appliquer_ordre_manuel(inverse)
        self.assertEqual(_numeros(vm.SheetsManuel), [u'A3', u'A2', u'A1'])
        self.assertTrue(all(s.ExportPdf for s in vm.SheetsManuel))

    def test_ordre_manuel_persiste_et_se_relit(self):
        cfg = _Config()
        vm = self._vm([u'A1', u'A2', u'A3'], config=cfg)
        vm.refresh_manuel()
        vm.appliquer_ordre_manuel(list(reversed(vm.SheetsManuelFiltrees)))

        autre = self._vm([u'A1', u'A2', u'A3'], config=cfg)
        autre.refresh_manuel()
        self.assertEqual(_numeros(autre.SheetsManuel), [u'A3', u'A2', u'A1'])

    def test_config_corrompue_revient_au_tri_naturel(self):
        cfg = _Config({'jeux_ordre': u'{pas du json',
                       'manuel_ordre': u'[[['})
        vm = self._vm([u'A10', u'A2'], config=cfg)
        vm.refresh_par_jeu()
        vm.refresh_manuel()
        self.assertEqual(_numeros(vm.Collections[0].Sheets), [u'A2', u'A10'])
        self.assertEqual(_numeros(vm.SheetsManuel), [u'A2', u'A10'])


if __name__ == '__main__':
    unittest.main()
