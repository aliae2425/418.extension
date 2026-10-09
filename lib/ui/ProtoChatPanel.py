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
    from harnais import outils, secrets
except Exception:
    from lib.core.AppPaths import AppPaths
    from lib.core.journal import journal
    from lib.harnais import outils, secrets

try:
    from ui.helpers.UIResourceLoader import UIResourceLoader
    from ui.helpers.DarkMode import is_dark
except Exception:
    from lib.ui.helpers.UIResourceLoader import UIResourceLoader
    from lib.ui.helpers.DarkMode import is_dark

_log = journal('volet')

HOTE = '418.local'
PROFIL = 'webview2-proto'

# Ce que la page envoie en `Authorization`, et que l'hôte remplace. La clé
# ne traverse jamais la frontière : une XSS dans une bulle ne trouve rien.
#
# Pourquoi une sentinelle plutôt qu'un en-tête ajouté de rien : sans
# `Authorization` au départ, le navigateur ne l'annonce pas dans son préflight
# CORS, et on dépendrait de l'ordre entre son contrôle et notre interception.
# Avec, le préflight est exact et on ne fait que substituer une valeur.
SENTINELLE = 'Bearer 418-hote'

# Seule origine dont on signe les requêtes. Un filtre large signerait aussi
# ce que la page demande ailleurs — elle n'a rien à demander ailleurs, mais
# c'est le genre de porte qu'on laisse fermée.
API_OPENAI = 'https://api.openai.com/*'


def _dossier_web():
    """La racine servie, pas le sous-dossier de la vue.

    UNE seule origine pour `vue/` et `harnais/` : deux mappings virtuels
    feraient deux origines, donc des imports ES bloqués entre les deux.
    """
    return AppPaths().web_dir()


class ProtoChatPanel(forms.WPFPanel):

    panel_id = 'c9a41f27-6d8b-4e32-91af-7b04e5c2d6a3'
    panel_source = os.path.join(AppPaths().pages_dir(), 'ProtoChatPanel.xaml')
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
        """Pose l'interception qui remplace la sentinelle par la vraie clé.

        Appelée au montage ET après un `/connect` : la page a pu démarrer
        sans clé, auquel cas rien n'était armé. Idempotente — un second
        abonnement enverrait l'évènement deux fois et signerait deux fois.

        Si ça échoue, le volet marche quand même : la page retombera sur le
        modèle fictif, puisque la clé sera annoncée absente.
        """
        if coeur is None or self._signe:
            return None
        if not secrets.cle():
            return _log.info('aucune clé — modèle fictif')
        try:
            from Microsoft.Web.WebView2.Core import CoreWebView2WebResourceContext
            coeur.AddWebResourceRequestedFilter(
                API_OPENAI, CoreWebView2WebResourceContext.All)
            coeur.WebResourceRequested += self._sur_requete
            self._signe = True
            _log.info('signature des appels à %s en place', API_OPENAI)
        except Exception:
            _log.exception('interception impossible — la clé ne sera pas posée')

    def _sur_requete(self, sender, args):
        """Sur le fil d'interface. Ne lève JAMAIS : Revit tomberait."""
        try:
            entetes = args.Request.Headers
            # On ne signe QUE ce qui porte la sentinelle. Un en-tête absent
            # ou différent part tel quel et prend un 401 — un refus franc
            # vaut mieux qu'un appel anonyme qu'on aurait signé par hasard.
            if entetes.GetHeader('Authorization') != SENTINELLE:
                return
            valeur = secrets.cle()
            if not valeur:
                return                     # /logout est passé par là
            entetes.SetHeader('Authorization', 'Bearer ' + valeur)
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
            # Revit est la source de vérité du thème — pas Windows, que
            # `prefers-color-scheme` lirait.
            self._poster('theme',
                         {'valeur': 'sombre' if is_dark() else 'clair'})
            # On dit SI une clé existe, jamais laquelle. La page choisit son
            # fournisseur là-dessus et n'en saura pas plus.
            self._poster('config', {'cle': bool(secrets.cle())})
        elif ordre == 'source':
            # D'où vient la clé, jamais sa valeur.
            self._poster('reponse', {'ref': message.get('ref'),
                                     'sortie': secrets.source()})
        elif ordre == 'connecter':
            pose = secrets.poser_cle(message.get('cle') or '')
            if pose:
                # La page a pu démarrer sans clé : l'interception n'était
                # alors pas armée. Elle l'est maintenant, sans redémarrage.
                self._signer(self._coeur)
            self._poster('reponse', {'ref': message.get('ref'), 'sortie': pose})
        elif ordre == 'deconnecter':
            self._poster('reponse', {'ref': message.get('ref'),
                                     'sortie': secrets.oublier_cle()})
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
