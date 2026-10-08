# -*- coding: utf-8 -*-
"""Prototype de chat : moteur Python, interface web, aucun modèle derrière.

Le banc d'essai a répondu aux questions de faisabilité — il a été retiré, ses
mesures sont dans le message de `08e3335`. Celui-ci répond à la seule qui
restait : **est-ce que ça fait un bon chat ?** Il monte le chemin complet,
en vrai —

    ProtoAgent (fil de fond) → Flux → parts JSON
        → PostWebMessageAsJson → app.js → DOM

— et ce chemin est exactement celui qu'un vrai client prendrait. Seul l'agent
est faux : rien n'appelle de modèle, rien ne touche la maquette.

Trois choses que le volet WPF actuel ne sait pas faire, et qu'on vient voir ici :

- le texte arrive **mot à mot** au lieu d'une bulle après 60 s ;
- le Markdown est **rendu** (gras, tableaux, code) au lieu d'être nettoyé —
  sans FlowDocument, donc hors de la classe de panne qui a tué Revit quatre fois ;
- l'accord sur un irréversible se demande **dans le fil**, pas dans une modale
  qui cacherait ce sur quoi on se prononce.

**Le fil de fond poste directement**, sans `Dispatcher` : le banc a mesuré que
`PostWebMessageAsJson` l'accepte hors du fil d'interface — on attendait
l'inverse, et c'est ce qui dispense d'un tampon par jeton.
"""
from __future__ import unicode_literals
import json
import os

from pyrevit import forms

try:
    from core.AppPaths import AppPaths
    from core.journal import journal
    from harnais import parts as cp
    from harnais.agent_factice import ProtoAgent
except Exception:
    from lib.core.AppPaths import AppPaths
    from lib.core.journal import journal
    from lib.harnais import parts as cp
    from lib.harnais.agent_factice import ProtoAgent

try:
    from ui.helpers.UIResourceLoader import UIResourceLoader
    from ui.helpers.DarkMode import is_dark
except Exception:
    from lib.ui.helpers.UIResourceLoader import UIResourceLoader
    from lib.ui.helpers.DarkMode import is_dark

_log = journal('proto')

HOTE = '418.local'
PROFIL = 'webview2-proto'

# Sans réponse, un irréversible est REFUSÉ. Le silence ne vaut pas accord —
# c'est la règle du volet actuel, et elle ne se négocie pas.
DELAI_ACCORD = 300


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
            _log.exception('construction du prototype impossible')
            raise
        self._vue = None
        self._coeur = None
        self._coupe = False
        self._flux = None
        self._accords = {}                 # id de part → (Event, [réponse])
        # Même init paresseuse que le banc : `EnsureCoreWebView2Async`
        # n'aboutit pas tant que le contrôle n'est pas visible, et le volet
        # naît `default_visible=False`.
        self.IsVisibleChanged += self._sur_visibilite
        self.Loaded += self._sur_visibilite

    # --- montage ----------------------------------------------------------

    def _sur_visibilite(self, sender, args):
        try:
            if self._vue is None:
                self._creer()
        except Exception:
            _log.exception('montage du prototype')

    def _creer(self):
        from System import Uri                                    # noqa: F401
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
            coeur.Navigate('https://{0}/vue/index.html'.format(HOTE))
            _log.info('prototype monté')
        except Exception:
            _log.exception('initialisation du prototype')

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
            self._poster('theme',
                         {'valeur': 'sombre' if is_dark() else 'clair'})
        elif ordre == 'envoyer':
            self._lancer(message.get('texte') or '')
        elif ordre == 'interrompre':
            # Lu entre deux morceaux par le fil de fond, jamais pendant.
            self._coupe = True
        elif ordre == 'accord':
            self._repondre_accord(message.get('id'), bool(message.get('oui')))
        elif ordre == 'erreur':
            _log.error('interface : %s', message.get('message'))

    # --- le tour ----------------------------------------------------------

    def _lancer(self, texte):
        from System.Threading import Thread, ThreadStart
        self._coupe = False
        flux = cp.Flux(self._poster)
        self._flux = flux
        agent = ProtoAgent(flux, accord=self._demander_accord,
                           coupe=lambda: self._coupe)

        def _courir():
            # `repondre` ne lève jamais et finit toujours par `tour.fini` :
            # sans ça l'interface resterait bloquée sur « réfléchit… ».
            agent.repondre(texte)

        fil = Thread(ThreadStart(_courir))
        # Sans cela, un tour en cours retiendrait la fermeture de Revit.
        fil.IsBackground = True
        fil.Start()

    def _poster(self, evenement, charge):
        """Du fil de fond vers la page, SANS Dispatcher.

        Le banc l'a mesuré (cf. `08e3335`) : `PostWebMessageAsJson` accepte un
        appel hors du fil d'interface, et le message arrive. Passer par le
        Dispatcher coûterait un marshal bloquant par jeton.
        """
        if self._coeur is None:
            return
        try:
            self._coeur.PostWebMessageAsJson(cp.encoder(evenement, charge))
        except Exception:
            _log.exception('envoi de %s', evenement)

    # --- l'accord ---------------------------------------------------------

    def _demander_accord(self, nom, arguments):
        """Appelé DEPUIS le fil de fond, et il a le droit de bloquer.

        La page a déjà dessiné les boutons : la part `outil` est née en
        `attente_accord`. On attend sa réponse, et l'absence de réponse est un
        refus — jamais un laissez-passer.
        """
        from System.Threading import ManualResetEventSlim
        # La part `outil` vient de naître en `attente_accord` : c'est elle que
        # la page a dessinée avec ses boutons, donc c'est son id qui reviendra.
        # ponytail: vrai tant qu'un tour ne demande qu'un accord à la fois. Le
        # jour où deux partent en parallèle, c'est l'agent qui doit passer l'id.
        identifiant = self._flux.dernier_id()
        signal = ManualResetEventSlim(False)
        reponse = [False]
        self._accords[identifiant] = (signal, reponse)
        _log.warning('IRRÉVERSIBLE %s %s — accord demandé', nom, arguments)
        try:
            signal.Wait(DELAI_ACCORD * 1000)
        finally:
            self._accords.pop(identifiant, None)
        if not reponse[0]:
            _log.warning('IRRÉVERSIBLE %s refusé', nom)
        return reponse[0]

    def _repondre_accord(self, identifiant, oui):
        attente = self._accords.get(identifiant)
        if attente is None:
            return _log.warning('accord sans demande en cours : %s', identifiant)
        signal, reponse = attente
        reponse[0] = oui
        signal.Set()


def _controle(dossier_profil):
    """Identique au banc : les assemblies sont livrées avec Revit 2026."""
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
    proprietes.UserDataFolder = dossier_profil
    vue = WebView2()
    vue.CreationProperties = proprietes
    return vue
