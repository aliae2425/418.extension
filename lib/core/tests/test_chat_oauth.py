# -*- coding: utf-8 -*-
"""Tests du client OAuth ChatGPT embarqué. Aucun réseau, aucun disque utilisateur."""
from __future__ import unicode_literals
import base64
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core import chat_oauth

try:                                   # CPython 3
    from urllib.parse import urlparse, parse_qs
except ImportError:                    # IronPython 2.7
    from urlparse import urlparse, parse_qs


def _jeton_identite(claims):
    """Fabrique un id_token : en-tête et signature bidons, payload réel."""
    def part(donnees):
        brut = json.dumps(donnees).encode('utf-8')
        return base64.urlsafe_b64encode(brut).decode('ascii').rstrip('=')
    return '{0}.{1}.signature'.format(part({'alg': 'none'}), part(claims))


class TestPKCE(unittest.TestCase):
    def test_defi_est_le_sha256_base64url_sans_remplissage(self):
        verifier = 'abc123'
        attendu = base64.urlsafe_b64encode(
            hashlib.sha256(b'abc123').digest()).decode('ascii').rstrip('=')
        self.assertEqual(chat_oauth.defi(verifier), attendu)
        self.assertNotIn('=', chat_oauth.defi(verifier))

    def test_url_porte_les_parametres_attendus(self):
        url = chat_oauth.url_autorisation('monverifier', 'monetat')
        self.assertTrue(url.startswith(chat_oauth.URL_AUTORISATION + '?'))
        params = parse_qs(urlparse(url).query)
        self.assertEqual(params['client_id'], [chat_oauth.CLIENT])
        self.assertEqual(params['response_type'], ['code'])
        self.assertEqual(params['redirect_uri'], [chat_oauth.REDIRECTION])
        self.assertEqual(params['code_challenge_method'], ['S256'])
        self.assertEqual(params['code_challenge'],
                         [chat_oauth.defi('monverifier')])
        self.assertEqual(params['state'], ['monetat'])
        self.assertEqual(params['originator'], [chat_oauth.ORIGINATEUR])
        # Les deux extras propres au flux Codex : sans eux, l'écran de
        # consentement change et le jeton ne porte pas l'organisation.
        self.assertEqual(params['id_token_add_organizations'], ['true'])
        self.assertEqual(params['codex_cli_simplified_flow'], ['true'])
        self.assertIn('offline_access', params['scope'][0])

    def test_la_redirection_utilise_le_port_impose(self):
        self.assertEqual(chat_oauth.REDIRECTION,
                         'http://localhost:1455/auth/callback')


class TestCompte(unittest.TestCase):
    def test_extrait_le_compte_du_jeton_identite(self):
        jeton = _jeton_identite({
            'https://api.openai.com/auth': {'chatgpt_account_id': 'acct-42'}})
        self.assertEqual(chat_oauth.compte(jeton), 'acct-42')

    def test_supporte_un_payload_sans_remplissage_base64(self):
        # Le cas qui casse en vrai : OpenAI émet du base64url non rembourré,
        # et b64decode lève si on ne rajoute pas les « = ».
        for taille in range(1, 40):
            jeton = _jeton_identite({
                'https://api.openai.com/auth': {
                    'chatgpt_account_id': 'a' * taille}})
            reste = len(jeton.split('.')[1]) % 4
            self.assertNotEqual(reste, 1)     # base64 impossible, jamais émis
            self.assertEqual(chat_oauth.compte(jeton), 'a' * taille)

    def test_jeton_illisible_rend_une_chaine_vide(self):
        for mauvais in ('', 'pas-un-jeton', 'a.b.c',
                        _jeton_identite({'autre': 1})):
            self.assertEqual(chat_oauth.compte(mauvais), '')


class TestExtraireSSE(unittest.TestCase):
    def _flux(self, evenements):
        lignes = []
        for evenement in evenements:
            lignes.append('event: {0}'.format(evenement.get('type', '')))
            lignes.append('data: {0}'.format(json.dumps(evenement)))
            lignes.append('')
        lignes.append('data: [DONE]')
        return '\n'.join(lignes)

    def test_retient_le_texte_de_response_completed(self):
        brut = self._flux([
            {'type': 'response.created'},
            {'type': 'response.output_text.delta', 'delta': 'bon'},
            {'type': 'response.output_text.delta', 'delta': 'jour'},
            {'type': 'response.completed', 'response': {'output': [
                {'content': [{'type': 'output_text', 'text': 'bonjour'}]}]}},
        ])
        # Les delta répètent le texte final : les accumuler le doublerait.
        self.assertEqual(chat_oauth.extraire(brut), 'bonjour')

    def test_ignore_done_et_les_lignes_illisibles(self):
        brut = 'data: [DONE]\ndata: pas du json\nbruit\n'
        self.assertEqual(chat_oauth.extraire(brut), '')

    def test_recolle_les_blocs_sans_separateur(self):
        # Ce sont des fragments d'un même message, pas des paragraphes : les
        # delta se recollent forcément bout à bout, le reste doit suivre.
        brut = self._flux([{'type': 'response.completed', 'response': {
            'output': [
                {'content': [{'type': 'output_text', 'text': 'une '}]},
                {'content': [{'type': 'output_text', 'text': 'phrase'},
                             {'type': 'reasoning', 'text': 'ignoré'}]},
            ]}}])
        self.assertEqual(chat_oauth.extraire(brut), 'une phrase')

    def test_sans_completed_les_items_termines_suffisent(self):
        # Le cas qui a rendu la bulle vide en vrai : le modèle n'émet pas
        # d'instantané final, seulement ses items un à un.
        brut = self._flux([
            {'type': 'response.output_item.done',
             'item': {'type': 'reasoning', 'summary': ['je réfléchis']}},
            {'type': 'response.output_item.done', 'item': {
                'type': 'message',
                'content': [{'type': 'output_text', 'text': 'bonjour'}]}},
        ])
        self.assertEqual(chat_oauth.extraire(brut), 'bonjour')

    def test_a_defaut_les_deltas_sont_recolles(self):
        brut = self._flux([
            {'type': 'response.output_text.delta', 'delta': 'bon'},
            {'type': 'response.output_text.delta', 'delta': 'jour'},
        ])
        self.assertEqual(chat_oauth.extraire(brut), 'bonjour')

    def test_les_trois_sources_ne_se_cumulent_jamais(self):
        # Elles portent le même texte : les concaténer le triplerait.
        brut = self._flux([
            {'type': 'response.output_text.delta', 'delta': 'bonjour'},
            {'type': 'response.output_item.done', 'item': {
                'content': [{'type': 'output_text', 'text': 'bonjour'}]}},
            {'type': 'response.completed', 'response': {'output': [
                {'content': [{'type': 'output_text', 'text': 'bonjour'}]}]}},
        ])
        self.assertEqual(chat_oauth.extraire(brut), 'bonjour')

    def test_texte_agrege_pose_directement_sur_la_reponse(self):
        brut = self._flux([{'type': 'response.completed',
                            'response': {'output_text': 'bonjour'}}])
        self.assertEqual(chat_oauth.extraire(brut), 'bonjour')

    def test_garde_les_accents(self):
        brut = self._flux([{'type': 'response.completed', 'response': {
            'output': [{'content': [
                {'type': 'output_text', 'text': 'éléments à côté'}]}]}}])
        self.assertEqual(chat_oauth.extraire(brut), 'éléments à côté')


class TestErreurDuFlux(unittest.TestCase):
    """Un refus peut arriver en HTTP 200, caché dans le flux."""

    def _flux(self, evenements):
        return '\n'.join('data: {0}'.format(json.dumps(e)) for e in evenements)

    def test_evenement_error_remonte_son_message(self):
        brut = self._flux([{'type': 'error',
                            'error': {'message': 'quota épuisé'}}])
        self.assertEqual(chat_oauth.erreur_du_flux(brut), 'quota épuisé')

    def test_response_failed_remonte_son_message(self):
        brut = self._flux([{'type': 'response.failed', 'response': {
            'error': {'message': 'modèle indisponible'}}}])
        self.assertEqual(chat_oauth.erreur_du_flux(brut),
                         'modèle indisponible')

    def test_un_flux_sain_ne_signale_rien(self):
        brut = self._flux([{'type': 'response.completed', 'response': {
            'output': [{'content': [{'type': 'output_text', 'text': 'ok'}]}]}}])
        self.assertEqual(chat_oauth.erreur_du_flux(brut), '')


class TestCharge(unittest.TestCase):
    def test_store_faux_et_types_de_contenu_par_role(self):
        corps = chat_oauth.charge([('user', 'salut'), ('assistant', 'ok')])
        self.assertFalse(corps['store'])
        self.assertEqual(corps['instructions'], chat_oauth.SYSTEME)
        self.assertEqual(corps['input'][0]['content'][0]['type'], 'input_text')
        # L'assistant en input_text fait répondre un 400 au corps entier.
        self.assertEqual(corps['input'][1]['content'][0]['type'], 'output_text')

    def test_le_modele_demande_prime_sur_le_defaut(self):
        self.assertEqual(chat_oauth.charge([], 'gpt-X')['model'], 'gpt-X')
        self.assertEqual(chat_oauth.charge([])['model'],
                         chat_oauth.MODELE_DEFAUT)

    def test_le_defaut_nest_pas_un_slug_refuse_par_les_comptes_chatgpt(self):
        # Les suffixes « -codex » et « -pro » se prennent un HTTP 400 : c'est
        # exactement l'erreur qui a cassé le premier essai en vrai.
        self.assertFalse(chat_oauth.MODELE_DEFAUT.endswith('-codex'))
        self.assertFalse(chat_oauth.MODELE_DEFAUT.endswith('-pro'))


class TestIndice(unittest.TestCase):
    def test_un_modele_refuse_gagne_le_mode_demploi(self):
        brut = ("HTTP 400 — The 'gpt-5.2-codex' model is not supported when "
                "using Codex with a ChatGPT account.")
        dit = chat_oauth.indice(brut)
        self.assertTrue(dit.startswith(brut))
        self.assertIn('/model', dit)

    def test_une_erreur_sans_rapport_reste_intacte(self):
        for brut in ('réseau injoignable — timeout', 'HTTP 500 — sans détail'):
            self.assertEqual(chat_oauth.indice(brut), brut)


class TestPage(unittest.TestCase):
    """La page servie au navigateur au retour du flux."""

    def _classe(self, reussi):
        trouve = re.search(r'<main class="([^"]*)"', chat_oauth.page(reussi))
        return trouve.group(1).split()

    def test_un_refus_naffiche_pas_reussi(self):
        # Sinon le navigateur et le panneau se contredisent sous les yeux de
        # l'utilisateur.
        self.assertIn('réussie', chat_oauth.page(True))
        self.assertNotIn('réussie', chat_oauth.page(False))
        self.assertIn('interrompue', chat_oauth.page(False))

    def test_la_variante_dechec_porte_sa_classe(self):
        # 'rate' apparaît toujours dans la feuille de style : c'est bien
        # l'attribut de <main> qu'il faut regarder, pas la page entière.
        self.assertNotIn('rate', self._classe(True))
        self.assertIn('rate', self._classe(False))

    def test_autonome_aucune_ressource_externe(self):
        # La boucle locale ne sert qu'un fichier : un lien externe donnerait
        # une page cassée, et ferait fuiter la visite à un tiers.
        for reussi in (True, False):
            rendu = chat_oauth.page(reussi)
            self.assertEqual(re.findall(r'(?:src|href)\s*=', rendu), [])
            self.assertNotIn('http://', rendu.replace('http://localhost', ''))
            self.assertNotIn('https://', rendu)

    def test_la_theiere_du_logo_est_bien_embarquee(self):
        # Le repli silencieux de logo() rendrait une page sans théière sans
        # que rien ne proteste : c'est exactement ce qu'il faut attraper ici.
        rendu = chat_oauth.logo()
        self.assertTrue(rendu.startswith('url("data:image/png;base64,'),
                        'logo introuvable depuis AppPaths')
        brut = base64.b64decode(rendu.split('base64,')[1].rstrip('")'))
        self.assertEqual(brut[:8], b'\x89PNG\r\n\x1a\n')   # vrai PNG, pas un 404
        self.assertIn(rendu, chat_oauth.page(True))

    def test_le_gabarit_vient_du_fichier_editable(self):
        source = chat_oauth.gabarit()
        self.assertNotEqual(source, chat_oauth._SECOURS,
                            '%s introuvable depuis AppPaths' % chat_oauth.GABARIT)
        self.assertIn('class="theiere"', source)

    def test_le_fichier_est_relu_a_chaque_rendu(self):
        # Sans relecture, éditer le HTML n'aurait d'effet qu'après un Reload
        # pyRevit — c'est tout l'intérêt de l'avoir sorti du Python.
        chemin = chat_oauth._ressource(chat_oauth.GABARIT)
        with io.open(chemin, encoding='utf-8') as f:
            avant = f.read()
        try:
            with io.open(chemin, 'w', encoding='utf-8') as f:
                f.write('<p>__TITRE__ à chaud</p>')
            self.assertIn('à chaud', chat_oauth.page(True))
        finally:
            with io.open(chemin, 'w', encoding='utf-8') as f:
                f.write(avant)
        self.assertIn('class="theiere"', chat_oauth.page(True))

    def test_le_logo_nest_embarque_quune_fois(self):
        # Citer le jeton du logo dans un commentaire du gabarit le ferait
        # remplacer lui aussi : un second data URI de 19 Ko, invisible à la
        # lecture et qui doublerait le poids servi.
        rendu = chat_oauth.page(True)
        self.assertEqual(rendu.count(chat_oauth.logo()), 1)
        self.assertLess(len(rendu.encode('utf-8')), 40 * 1024)

    def test_un_gabarit_manquant_ne_casse_pas_la_connexion(self):
        # À ce stade l'OAuth a réussi : lever ici ferait échouer une session
        # pourtant valide, pour une histoire de mise en forme.
        vrai = chat_oauth._ressource
        chat_oauth._ressource = lambda nom: os.path.join(
            tempfile.gettempdir(), 'nexiste-pas-418', nom)
        try:
            rendu = chat_oauth.page(True)
        finally:
            chat_oauth._ressource = vrai
        self.assertIn('réussie', rendu)
        self.assertEqual(re.findall(r'__[A-Z]+__', rendu), [])

    def test_tous_les_jetons_sont_remplaces(self):
        for reussi in (True, False):
            self.assertEqual(
                re.findall(r'__[A-Z]+__', chat_oauth.page(reussi)), [])

    def test_encodable_en_utf8_avec_ses_accents(self):
        # C'est l'octet servi qui compte : Content-Length est calculé dessus.
        for reussi in (True, False):
            self.assertTrue(len(chat_oauth.page(reussi).encode('utf-8')) > 0)


class TestSession(unittest.TestCase):
    """Stockage et expiration, sur un dossier jetable."""

    def setUp(self):
        self._dossier = tempfile.mkdtemp()
        self._vrai = chat_oauth.dossier
        chat_oauth.dossier = lambda: self._dossier
        chat_oauth.oublier()

    def tearDown(self):
        chat_oauth.oublier()
        chat_oauth.dossier = self._vrai
        shutil.rmtree(self._dossier, ignore_errors=True)

    def test_sans_session_pret_est_faux(self):
        self.assertFalse(chat_oauth.pret())
        try:
            chat_oauth.repondre([('user', 'x')])
            self.fail('aurait dû lever')
        except chat_oauth.ErreurOAuth as e:
            self.assertIn('/connect', '{0}'.format(e))

    def test_ecrire_puis_relire_apres_oubli_du_cache(self):
        chat_oauth._ecrire({'access_token': 'a', 'refresh_token': 'r',
                            'expire': time.time() + 3600})
        self.assertTrue(chat_oauth.pret())
        del chat_oauth._charge[:]      # force la relecture du fichier
        chat_oauth._jetons.clear()
        self.assertTrue(chat_oauth.pret())

    def test_expire_mais_rafraichissable_reste_pret(self):
        # Sinon on renverrait l'utilisateur au navigateur alors que
        # `repondre()` sait rafraîchir tout seul.
        chat_oauth._ecrire({'access_token': 'a', 'refresh_token': 'r',
                            'expire': time.time() - 10})
        self.assertTrue(chat_oauth.pret())

    def test_expire_sans_refresh_nest_pas_pret(self):
        chat_oauth._ecrire({'access_token': 'a', 'refresh_token': '',
                            'expire': time.time() - 10})
        self.assertFalse(chat_oauth.pret())

    def test_la_marge_declenche_avant_lecheance(self):
        presque = {'expire': time.time() + chat_oauth.MARGE / 2}
        self.assertTrue(chat_oauth._doit_rafraichir(presque))
        large = {'expire': time.time() + chat_oauth.MARGE * 10}
        self.assertFalse(chat_oauth._doit_rafraichir(large))
        self.assertFalse(chat_oauth._doit_rafraichir({'expire': 0}))

    def test_deconnecter_efface_le_fichier(self):
        chat_oauth._ecrire({'access_token': 'a'})
        self.assertTrue(os.path.isfile(chat_oauth.fichier()))
        chat_oauth.deconnecter()
        self.assertFalse(os.path.isfile(chat_oauth.fichier()))
        self.assertFalse(chat_oauth.pret())

    def test_le_jeton_ne_vit_pas_dans_le_depot(self):
        # CLAUDE.md : jamais de secret sous data/ — un dossier d'extension
        # se zippe et se partage.
        chemin = self._vrai()
        racine = os.path.abspath(os.path.join(_HERE, '..', '..', '..'))
        self.assertFalse(os.path.abspath(chemin).startswith(racine))


class TestEchange(unittest.TestCase):
    def setUp(self):
        self._dossier = tempfile.mkdtemp()
        self._vrai = chat_oauth.dossier
        chat_oauth.dossier = lambda: self._dossier
        chat_oauth._flux.update({'verifier': 'v', 'etat': 'bon-etat'})

    def tearDown(self):
        chat_oauth.oublier()
        chat_oauth._flux.clear()
        chat_oauth.dossier = self._vrai
        shutil.rmtree(self._dossier, ignore_errors=True)

    def _echoue(self, recu, extrait):
        try:
            chat_oauth._echanger(recu)
            self.fail('aurait dû lever')
        except chat_oauth.ErreurOAuth as e:
            self.assertIn(extrait, '{0}'.format(e))

    def test_etat_different_refuse(self):
        # Sans ça, une page ouverte pendant le flux pourrait pousser son
        # propre code sur notre boucle locale.
        self._echoue({'code': ['c'], 'state': ['pirate']}, 'état')

    def test_code_absent_refuse(self):
        self._echoue({'state': ['bon-etat']}, 'sans code')

    def test_erreur_du_fournisseur_remontee(self):
        self._echoue({'error': ['access_denied'], 'state': ['bon-etat']},
                     'access_denied')


class TestContrat(unittest.TestCase):
    """Les membres que OpenArchiConfig et le VM appellent à l'aveugle."""

    def test_les_membres_du_contrat_existent(self):
        for membre in ('pret', 'raison', 'connecter', 'deconnecter',
                       'modeles', 'repondre', 'attendre_connexion'):
            self.assertTrue(callable(getattr(chat_oauth, membre, None)),
                            membre)

    def test_modeles_est_vide(self):
        # Le backend Codex n'expose aucun catalogue ; coder une liste en dur
        # vieillirait sans que rien ne le signale (CLAUDE.md).
        self.assertEqual(chat_oauth.modeles(), ())

    def test_attendre_sans_flux_ouvert_rend_faux(self):
        chat_oauth._flux.pop('serveur', None)
        self.assertFalse(chat_oauth.attendre_connexion(timeout=0))


def _sse(evenements):
    return '\n'.join('data: {0}'.format(json.dumps(e, ensure_ascii=False))
                     for e in evenements) + '\ndata: [DONE]\n'


def _appel(nom='revit_status', arguments='{}', identifiant='call_1'):
    return {'type': 'function_call', 'name': nom, 'arguments': arguments,
            'call_id': identifiant}


def _flux_appel(**kwargs):
    return _sse([{'type': 'response.output_item.done', 'item': _appel(**kwargs)}])


def _flux_texte(texte):
    return _sse([{'type': 'response.output_item.done',
                  'item': {'type': 'message',
                           'content': [{'type': 'output_text', 'text': texte}]}}])


class TestLectureDesAppels(unittest.TestCase):
    def test_appel_lu_dans_les_items_un_a_un(self):
        lus = chat_oauth.appels(_flux_appel())
        self.assertEqual([a['name'] for a in lus], ['revit_status'])

    def test_repli_sur_l_instantane_final(self):
        brut = _sse([{'type': 'response.completed',
                      'response': {'output': [_appel()]}}])
        self.assertEqual(len(chat_oauth.appels(brut)), 1)

    def test_les_deux_sources_ne_se_cumulent_pas(self):
        # Les cumuler exécuterait chaque outil deux fois.
        brut = _sse([{'type': 'response.output_item.done', 'item': _appel()},
                     {'type': 'response.completed',
                      'response': {'output': [_appel()]}}])
        self.assertEqual(len(chat_oauth.appels(brut)), 1)

    def test_un_flux_de_texte_ne_declare_aucun_appel(self):
        self.assertEqual(chat_oauth.appels(_flux_texte('bonjour')), [])


class TestCorpsAvecOutils(unittest.TestCase):
    OUTIL = {'nom': 'revit_status', 'description': 'état',
             'parametres': {'type': 'object', 'properties': {}}}

    def test_forme_a_plat_sans_niveau_function(self):
        corps = chat_oauth.corps([], None, [self.OUTIL])
        outil = corps['tools'][0]
        self.assertEqual(outil['type'], 'function')
        # /v1/chat/completions imbrique sous « function » ; pas ce backend.
        self.assertNotIn('function', outil)
        self.assertEqual(outil['name'], 'revit_status')
        self.assertEqual(corps['tool_choice'], 'auto')

    def test_la_consigne_outils_suit_les_outils(self):
        avec = chat_oauth.corps([], None, [self.OUTIL])
        sans = chat_oauth.corps([], None, None)
        self.assertIn(chat_oauth.OUTILLE, avec['instructions'])
        # Sans outils, ne rien promettre : il n'y a pas de boucle derrière.
        self.assertEqual(sans['instructions'], chat_oauth.SYSTEME)
        self.assertNotIn('tools', sans)


class TestBoucleOutils(unittest.TestCase):
    """La boucle complète, sans réseau ni Revit."""

    def setUp(self):
        self.envois = []
        self.executes = []
        self._vrais = (chat_oauth._lire, chat_oauth._doit_rafraichir,
                       chat_oauth._poster, chat_oauth.revit_outils)
        chat_oauth._lire = lambda: {'access_token': 'jeton'}
        chat_oauth._doit_rafraichir = lambda _j: False
        chat_oauth._poster = self._poster
        chat_oauth.revit_outils = self

    def tearDown(self):
        (chat_oauth._lire, chat_oauth._doit_rafraichir,
         chat_oauth._poster, chat_oauth.revit_outils) = self._vrais

    # --- double de revit_outils ---
    TOURS_MAX = 3

    def disponible(self):
        return True, ''

    def outils(self):
        return [{'nom': 'revit_status', 'description': 'état',
                 'parametres': {'type': 'object', 'properties': {}}}]

    def executer(self, nom, arguments=None):
        self.executes.append((nom, arguments))
        return json.dumps({'document_title': 'SGP-M7'})

    # --- double du réseau ---
    def _poster(self, corps, _jetons, _timeout):
        self.envois.append(json.loads(corps))
        return self.reponses.pop(0)

    def test_un_appel_puis_la_reponse(self):
        self.reponses = [_flux_appel(), _flux_texte('Le document est SGP-M7.')]
        reponse = chat_oauth.repondre([('user', 'quel document ?')])

        self.assertEqual(reponse, 'Le document est SGP-M7.')
        self.assertEqual(self.executes, [('revit_status', {})])
        # Le backend ne garde rien (store=false) : il faut lui rendre l'appel
        # d'origine ET son résultat.
        entree = self.envois[1]['input']
        self.assertEqual(entree[1]['type'], 'function_call')
        self.assertEqual(entree[2]['type'], 'function_call_output')
        self.assertEqual(entree[2]['call_id'], 'call_1')
        self.assertIn('SGP-M7', entree[2]['output'])

    def test_sans_appel_aucun_outil_n_est_lance(self):
        self.reponses = [_flux_texte('bonjour')]
        self.assertEqual(chat_oauth.repondre([('user', 'salut')]), 'bonjour')
        self.assertEqual(self.executes, [])

    def test_arguments_illisibles_ne_font_pas_echouer_le_tour(self):
        self.reponses = [_flux_appel(arguments='{pas du json'),
                         _flux_texte('bon')]
        self.assertEqual(chat_oauth.repondre([('user', 'x')]), 'bon')
        self.assertEqual(self.executes, [('revit_status', {})])

    def test_plafond_de_tours_puis_reponse_forcee_sans_outils(self):
        # Un modèle qui boucle brûlerait l'abonnement en silence.
        self.reponses = ([_flux_appel()] * self.TOURS_MAX +
                         [_flux_texte('assez lu')])
        self.assertEqual(chat_oauth.repondre([('user', 'x')]), 'assez lu')
        self.assertEqual(len(self.executes), self.TOURS_MAX)
        self.assertEqual(len(self.envois), self.TOURS_MAX + 1)
        # Le dernier envoi retire les outils : sinon le modèle rappellerait.
        self.assertNotIn('tools', self.envois[-1])

    def test_maquette_injoignable_supprime_les_outils(self):
        self.disponible = lambda: (False, 'Maquette injoignable')
        self.reponses = [_flux_texte('sans les yeux')]
        self.assertEqual(chat_oauth.repondre([('user', 'x')]), 'sans les yeux')
        self.assertNotIn('tools', self.envois[0])

    def test_outils_vides_imposes_par_l_appelant(self):
        self.reponses = [_flux_texte('ok')]
        chat_oauth.repondre([('user', 'x')], outils=[])
        self.assertNotIn('tools', self.envois[0])


if __name__ == '__main__':
    unittest.main()
