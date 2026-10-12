# -*- coding: utf-8 -*-
"""Le volet OpenArchi : un hôte, et rien de plus.

Depuis J4, **le moteur tourne dans la page**. Ce module ne sait plus ce qu'est
un tour de conversation, une part ou un accord : il monte le WebView2, sert
`lib/web/` sur une origine locale, dit quel thème Revit affiche, et encaisse
le journal. C'est tout, et c'est le but.

Ce qui a disparu avec le moteur : le `Thread` de fond, le `Flux`, l'agent
factice, l'attente bloquante sur l'accord, le `PostWebMessageAsJson` par
jeton. Le streaming ne traverse plus aucune frontière — il n'en a plus à
traverser.

Ce que Python gardera : les capacités système que JS n'a pas. L'égress vers
un fournisseur qui refuse CORS (J7), la danse OAuth qui écoute sur une socket
(J7), et l'exécution des outils sur le fil API de Revit (J6). Rien d'autre
n'a de raison de remonter ici.

Pièges déjà payés, à ne pas redécouvrir :

- le WebView2 n'est PAS déclaré dans le XAML — `XamlReader` devrait résoudre
  le namespace clr au parse, ce qui échoue tant que l'assembly n'est pas
  référencée. Il est injecté par `.Child` ;
- `EnsureCoreWebView2Async()` n'aboutit pas tant que le contrôle est
  invisible, et le volet naît `default_visible=False` : d'où l'init
  paresseuse sur `IsVisibleChanged` ;
- la `Task` est jetée, jamais attendue : `.Result` sur le fil d'interface
  interbloque, la Task ne se complétant que par la pompe de messages.
"""
from __future__ import unicode_literals
import json
import os

from pyrevit import forms

try:
    from core.AppPaths import AppPaths
    from core.journal import journal
    from harnais import outils, secrets, oauth
except Exception:
    from lib.core.AppPaths import AppPaths
    from lib.core.journal import journal
    from lib.harnais import outils, secrets, oauth

try:
    from ui.helpers.UIResourceLoader import UIResourceLoader
    from ui.helpers.DarkMode import is_dark
except Exception:
    from lib.ui.helpers.UIResourceLoader import UIResourceLoader
    from lib.ui.helpers.DarkMode import is_dark

_log = journal('volet')

HOTE = '418.local'
PROFIL = 'webview2'

# Ce que la page envoie, et que l'hôte remplace. La clé ne traverse jamais
# la frontière : une XSS dans une bulle ne trouve rien.
#
# Pourquoi une sentinelle plutôt qu'un en-tête ajouté de rien : sans l'en-tête
# au départ, le navigateur ne l'annonce pas dans son préflight CORS, et on
# dépendrait de l'ordre entre son contrôle et notre interception. Avec, le
# préflight est exact et on ne fait que substituer une valeur.
#
# Chaque fournisseur a SON en-tête — `Authorization: Bearer` chez OpenAI,
# `x-api-key` nu chez Anthropic — et donc sa propre sentinelle. Les filtres
# restent étroits : la page n'a rien à demander ailleurs, mais c'est le genre
# de porte qu'on laisse fermée.
SIGNATURES = (
    {'fournisseur': 'openai',
     'filtre': 'https://api.openai.com/*',
     'entete': 'Authorization',
     'sentinelle': 'Bearer 418-hote',
     'valeur': lambda cle: 'Bearer ' + cle},
    {'fournisseur': 'anthropic',
     'filtre': 'https://api.anthropic.com/*',
     'entete': 'x-api-key',
     'sentinelle': '418-hote',
     'valeur': lambda cle: cle},
)


def _dossier_web():
    """La racine servie, pas le sous-dossier de la vue.

    UNE seule origine pour `vue/` et `harnais/` : deux mappings virtuels
    feraient deux origines, donc des imports ES bloqués entre les deux.
    """
    return AppPaths().web_dir()


class OpenArchiPanel(forms.WPFPanel):

    panel_id = 'c9a41f27-6d8b-4e32-91af-7b04e5c2d6a3'
    panel_source = os.path.join(AppPaths().pages_dir(), 'OpenArchiPanel.xaml')
    panel_title = 'OpenArchi'

    def __init__(self):
        try:
            UIResourceLoader(self, dark=is_dark()).merge_theme()
            forms.WPFPanel.__init__(self)
        except Exception:
            # Revit avale les exceptions de construction d'un volet ancré :
            # sans cette trace, le panneau reste vide sans un mot.
            _log.exception('construction du volet impossible')
            raise
        self._vue = None
        self._coeur = None
        self._signe = False
        self.IsVisibleChanged += self._sur_visibilite
        self.Loaded += self._sur_visibilite

    # --- montage ----------------------------------------------------------

    def _sur_visibilite(self, sender, args):
        try:
            if self._vue is None:
                self._creer()
        except Exception:
            _log.exception('montage du volet')

    def _creer(self):
        vue = _controle(os.path.join(AppPaths().data_dir(), PROFIL))
        self.Hote.Child = vue
        self._vue = vue
        vue.CoreWebView2InitializationCompleted += self._sur_init
        vue.EnsureCoreWebView2Async()      # Task jetée : pas d'await en IPY 2.7

    def _sur_init(self, sender, args):
        try:
            if not args.IsSuccess:
                return _log.error('init WebView2 : %s',
                                  args.InitializationException)
            coeur = self._vue.CoreWebView2
            if coeur is None:
                return _log.error('CoreWebView2 nul')
            self._coeur = coeur
            from Microsoft.Web.WebView2.Core import (
                CoreWebView2HostResourceAccessKind)
            coeur.SetVirtualHostNameToFolderMapping(
                HOTE, _dossier_web(), CoreWebView2HostResourceAccessKind.Allow)
            coeur.WebMessageReceived += self._sur_message
            self._signer(coeur)
            coeur.Navigate('https://{0}/vue/index.html'.format(HOTE))
            _log.info('volet monté')
        except Exception:
            _log.exception('initialisation du volet')

    def _signer(self, coeur):
        """Pose les interceptions qui remplacent la sentinelle par la vraie clé.

        Appelée au montage ET après un `/connect` : la page a pu démarrer
        sans clé, auquel cas rien n'était armé. Idempotente — un second
        abonnement poserait deux fois le même en-tête.

        On arme TOUS les fournisseurs dès qu'une clé existe, quelle qu'elle
        soit : armer au cas par cas obligerait à ré-armer à chaque /connect,
        et un filtre sans clé ne fait rien de toute façon.

        Si ça échoue, le volet marche quand même : la page le verra à
        l'absence de clé annoncée.
        """
        if coeur is None or self._signe:
            return None
        if not any(secrets.cle(s['fournisseur']) for s in SIGNATURES):
            return _log.info('aucune clé — aucune signature armée')
        try:
            from Microsoft.Web.WebView2.Core import CoreWebView2WebResourceContext
            for signature in SIGNATURES:
                coeur.AddWebResourceRequestedFilter(
                    signature['filtre'], CoreWebView2WebResourceContext.All)
            coeur.WebResourceRequested += self._sur_requete
            self._signe = True
            _log.info('signature armée pour %s',
                      ', '.join(s['fournisseur'] for s in SIGNATURES))
        except Exception:
            _log.exception('interception impossible — la clé ne sera pas posée')

    def _sur_requete(self, sender, args):
        """Sur le fil d'interface. Ne lève JAMAIS : Revit tomberait."""
        try:
            entetes = args.Request.Headers
            for signature in SIGNATURES:
                # On ne signe QUE ce qui porte la sentinelle. Un en-tête
                # absent ou différent part tel quel et prend un 401 — un refus
                # franc vaut mieux qu'un appel anonyme signé par hasard.
                if entetes.GetHeader(signature['entete']) != signature['sentinelle']:
                    continue
                valeur = secrets.cle(signature['fournisseur'])
                if not valeur:
                    return                 # /logout est passé par là
                entetes.SetHeader(signature['entete'], signature['valeur'](valeur))
                return
        except Exception:
            _log.exception('signature de la requête')

    # --- ce que la page demande -------------------------------------------

    def _sur_message(self, sender, args):
        """Sur le fil d'interface. Ne lève JAMAIS : Revit tomberait."""
        try:
            message = json.loads(args.TryGetWebMessageAsString() or '{}')
        except Exception:
            return _log.exception('message illisible')
        try:
            self._ordre(message)
        except Exception:
            _log.exception('ordre %s', message.get('ordre'))

    def _ordre(self, message):
        ordre = message.get('ordre')
        if ordre == 'pret':
            # Le thème part tout de suite : il ne coûte rien et évite un
            # éclair clair sur un Revit sombre.
            self._poster('theme',
                         {'valeur': 'sombre' if is_dark() else 'clair'})
            # L'état de connexion, lui, peut demander un rafraîchissement de
            # jeton — donc du réseau, donc le fil de fond.
            self._verifier_connexion()
        elif ordre == 'connecter':
            chez = secrets.poser_cle(message.get('cle') or '',
                                     message.get('fournisseur') or 'openai')
            if chez:
                # La page a pu démarrer sans clé : l'interception n'était
                # alors pas armée. Elle l'est maintenant, sans redémarrage.
                self._signer(self._coeur)
            # On rend le fournisseur RETENU, pas celui demandé : un préfixe
            # sans ambiguïté l'emporte, et le volet doit afficher où la clé
            # est réellement allée.
            self._poster('reponse', {'ref': message.get('ref'),
                                     'sortie': chez})
        elif ordre == 'deconnecter':
            # Sans fournisseur, on efface TOUT : « me déconnecter » qui
            # laisserait une clé derrière serait une déconnexion qui n'en est
            # pas une. Avec, on n'en débranche qu'un — les autres tiennent.
            self._poster('reponse', {
                'ref': message.get('ref'),
                'sortie': secrets.oublier_cle(message.get('fournisseur'))})
        elif ordre == 'oauth':
            # Le navigateur s'ouvre tout de suite, l'attente part en fond :
            # cinq minutes sur le fil d'interface gèleraient Revit.
            self._en_fond(message, self._oauth)
        elif ordre == 'oauth_logout':
            self._poster('reponse', {'ref': message.get('ref'),
                                     'sortie': bool(oauth.deconnecter())})
        elif ordre == 'diffuser':
            self._en_fond(message, lambda: self._diffuser(message))
        elif ordre == 'outils':
            self._en_fond(message, lambda: outils.outils())
        elif ordre == 'outil':
            self._en_fond(message, lambda: outils.executer(
                message.get('nom') or '', message.get('arguments')))
        elif ordre == 'erreur':
            # Un volet ancré n'a aucune fenêtre de sortie pyRevit : sans ce
            # relais, une interface cassée reste muette.
            _log.error('interface : %s', message.get('message'))
        else:
            _log.warning('ordre inconnu : %s', ordre)

    # --- l'état de la connexion -------------------------------------------

    def _verifier_connexion(self):
        """Dit à la page ce qui répond, et si ça tient encore.

        « Un jeton existe » et « un jeton marche » sont deux choses. Un
        `refresh_token` révoqué, ou tourné par un autre client, ne se voit
        qu'en le présentant — sinon la panne arrive au milieu du premier
        message, après vingt secondes d'attente, et ressemble à un bug du
        volet.

        Sur un fil de fond : `verifier()` peut appeler le réseau, et geler le
        fil d'interface gèlerait Revit.
        """
        from System.Threading import Thread, ThreadStart

        def _courir():
            try:
                # Avant de dire ce qui est branché, remettre d'aplomb ce qui
                # ne l'est pas : une clé Anthropic rangée dans la case OpenAI
                # se présenterait chez OpenAI, qui répond 401 sans dire
                # pourquoi. Sans ça il faudrait un `/logout` à l'aveugle.
                secrets.reparer()
            except Exception:
                _log.exception('remise en place des clés')
            try:
                lu = oauth.verifier()
            except Exception:
                _log.exception('vérification de la session')
                lu = {'session': False, 'raison': 'vérification impossible'}
            # La clé n'est PAS validée : ça coûterait une requête à chaque
            # ouverture du volet pour une panne que le premier message dira
            # en clair. On annonce qu'elle est posée, pas qu'elle marche.
            # Quelles clés existent, jamais leur valeur. La page choisit
            # son fournisseur là-dessus et n'en saura pas plus.
            self._poster('config', {
                'cles': dict((s['fournisseur'],
                              bool(secrets.cle(s['fournisseur'])))
                             for s in SIGNATURES),
                'oauth': bool(lu.get('session')),
                'raison': lu.get('raison') or '',
            })

        fil = Thread(ThreadStart(_courir))
        fil.IsBackground = True
        fil.Start()

    # --- l'abonnement ChatGPT ---------------------------------------------

    def _oauth(self):
        """Ouvre le navigateur, puis attend son retour. Bloque — d'où le fond."""
        oauth.connecter()
        return bool(oauth.attendre())

    def _diffuser(self, message):
        """Poste un corps Responses et repousse chaque ligne au fil de l'eau.

        Les lignes partent par le même `ref` que la demande : le pont les
        apparie, et la promesse ne se résout qu'à la fin du flux.
        """
        ref = message.get('ref')

        def _ligne(texte):
            self._poster('ligne', {'ref': ref, 'ligne': texte})

        return oauth.diffuser(message.get('corps') or '{}', _ligne)

    # --- la maquette ------------------------------------------------------

    def _en_fond(self, message, travail):
        """Fait le travail HORS du fil d'interface, puis répond.

        `outils.executer` fait un aller-retour HTTP bloquant vers le serveur
        de routes pyRevit — c'est lui qui marshale vers le fil API de Revit.
        Le tenir sur le fil d'interface gèlerait Revit pendant tout l'appel.

        La réponse part depuis le fil de fond, sans Dispatcher : le banc a
        mesuré que `PostWebMessageAsJson` l'accepte.
        """
        from System.Threading import Thread, ThreadStart
        ref = message.get('ref')

        def _courir():
            try:
                self._poster('reponse', {'ref': ref, 'sortie': travail()})
            except Exception as e:
                # Jamais de silence : une promesse sans réponse laisse le
                # tour pendu jusqu'au délai du pont.
                _log.exception('ordre %s', message.get('ordre'))
                self._poster('reponse', {'ref': ref,
                                         'erreur': '{0}'.format(e)})

        fil = Thread(ThreadStart(_courir))
        # Sans cela, un appel en cours retiendrait la fermeture de Revit.
        fil.IsBackground = True
        fil.Start()

    def _poster(self, evenement, charge):
        if self._coeur is None:
            return
        try:
            # ensure_ascii=False : sous IronPython 2.7, laisser json échapper
            # les accents lui-même lève. On encode explicitement derrière.
            self._coeur.PostWebMessageAsJson(json.dumps(
                {'evenement': evenement, 'charge': charge},
                ensure_ascii=False))
        except Exception:
            _log.exception('envoi de %s', evenement)


def _controle(dossier_profil):
    """Un WebView2 prêt à initialiser.

    Les assemblies `Microsoft.Web.WebView2.*` sont livrées AVEC Revit 2026 et
    déjà chargées dans le process : rien à embarquer, et vendoriser une autre
    version serait un conflit (CoreCLR 2026, plus de binding redirect).
    """
    import clr
    try:
        clr.AddReference('Microsoft.Web.WebView2.Wpf')
        clr.AddReference('Microsoft.Web.WebView2.Core')
    except Exception:
        from System import AppDomain
        for nom in ('Microsoft.Web.WebView2.Wpf.dll',
                    'Microsoft.Web.WebView2.Core.dll'):
            clr.AddReferenceToFileAndPath(os.path.join(
                AppDomain.CurrentDomain.BaseDirectory, nom))
    from Microsoft.Web.WebView2.Wpf import (WebView2,
                                            CoreWebView2CreationProperties)
    proprietes = CoreWebView2CreationProperties()
    # Sans dossier explicite, WebView2 écrit à côté de Revit.exe — non
    # inscriptible pour un utilisateur standard, et l'init échoue sans message.
    proprietes.UserDataFolder = dossier_profil
    vue = WebView2()
    vue.CreationProperties = proprietes
    return vue
