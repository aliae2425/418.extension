# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import os

# La fenêtre « Matériaux » : un hôte WebView2, et rien de plus.
#
# Toute l'interface vit dans `lib/web/materiaux/`. Ce module monte le
# navigateur, sert `lib/web/` sur une origine locale, et fait passer les
# ordres de la page à `services.ordres`. Il ne sait pas ce qu'est un onglet,
# une carte ou un motif.
#
# Pièges déjà payés ailleurs dans le dépôt, à ne pas redécouvrir :
#
# - la fenêtre N'EST PAS transparente (`WindowStyle="SingleBorderWindow"`,
#   pas d'`AllowsTransparency`). WebView2 est un contrôle à HWND : dans une
#   fenêtre WPF en couches il ne s'affiche pas du tout. C'est la barre de
#   titre maison qui saute, pas le navigateur (cf. RampeParking) ;
# - le WebView2 n'est pas déclaré dans le XAML — `XamlReader` résoudrait le
#   namespace clr au parse, ce qui échoue tant que l'assembly n'est pas
#   référencée. Il est injecté par `.Child` ;
# - la `Task` d'`EnsureCoreWebView2Async` est jetée, jamais attendue : `.Result`
#   sur le fil d'interface interbloque, la Task ne se complétant que par la
#   pompe de messages. Ici c'est celle de `ShowDialog` qui la sert.
#
# Le fil : la fenêtre est MODALE, donc tout ce code tourne dans le contexte
# d'API de la commande pyRevit. Les ordres sont traités sur place, sans fil de
# fond : une transaction partie d'ici est légale, et un `Thread` en rendrait
# justement l'inverse.

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    from lib.ui.base.BaseWindow import BaseWindow

try:
    from core.AppPaths import AppPaths
except Exception:
    from lib.core.AppPaths import AppPaths

try:
    from lib.services.journal import log
except Exception:
    from services.journal import log

_XAML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'GUI', 'Views', 'MainWindow.xaml')

HOTE = '418.local'

# Même profil que le volet OpenArchi : deux WebView2 du MÊME processus
# partagent un dossier de données sans se gêner, et un second profil coûterait
# une centaine de mégaoctets pour rien.
PROFIL = 'webview2'

PAGE = 'https://{0}/materiaux/index.html'.format(HOTE)


class MainWindowView(BaseWindow):
    """Hôte WebView2 de l'outil Matériaux."""

    def __init__(self, ordres):
        # Pas de DataContext : il n'y a plus de ViewModel, et le seul contrôle
        # de la fenêtre n'a rien à lier.
        super(MainWindowView, self).__init__(_XAML, None)
        self._ordres = ordres
        self._vue = None
        self._coeur = None

    # -- montage -----------------------------------------------------------

    def _load(self):
        super(MainWindowView, self)._load()
        if self._window is None:
            return
        try:
            self._monter()
        except Exception as erreur:
            # Sans ce repli la fenêtre s'ouvre vide et sans un mot : le runtime
            # WebView2 absent est le cas le plus probable sur un poste pas à
            # jour.
            log(u'montage du navigateur impossible : {}', erreur)
            self._message(u'Interface non affichable : {}'.format(erreur))

    def _monter(self):
        hote = self._window.FindName('WebHost')
        if hote is None:
            raise ValueError(u'WebHost absent du XAML')
        vue = _controle(os.path.join(AppPaths().data_dir(), PROFIL))
        hote.Child = vue
        self._vue = vue
        vue.CoreWebView2InitializationCompleted += self._sur_init
        vue.EnsureCoreWebView2Async()      # Task jetée : pas d'await en IPY 2.7

    def _message(self, texte):
        """Écrit dans le cartouche de repli resté sous le navigateur."""
        try:
            bloc = self._window.FindName('WebHostMessage')
            if bloc is not None:
                bloc.Text = texte
        except Exception:
            pass

    def _sur_init(self, sender, args):
        try:
            if not args.IsSuccess:
                log(u'init WebView2 : {}', args.InitializationException)
                return self._message(
                    u'Navigateur non initialisé : {}'.format(
                        args.InitializationException))
            coeur = self._vue.CoreWebView2
            if coeur is None:
                return self._message(u'Navigateur non initialisé.')
            self._coeur = coeur
            from Microsoft.Web.WebView2.Core import (
                CoreWebView2HostResourceAccessKind)
            # UNE seule origine pour toute `lib/web/` : la page de matériaux
            # importe le pont et les jetons de thème du volet, et deux
            # mappings virtuels feraient deux origines, donc des imports ES
            # bloqués entre les deux.
            coeur.SetVirtualHostNameToFolderMapping(
                HOTE, AppPaths().web_dir(),
                CoreWebView2HostResourceAccessKind.Allow)
            coeur.WebMessageReceived += self._sur_message
            coeur.Navigate(PAGE)
            log(u'navigateur monté')
        except Exception as erreur:
            log(u'initialisation du navigateur : {}', erreur)
            self._message(u'Navigateur non initialisé : {}'.format(erreur))

    # -- ce que la page demande --------------------------------------------

    def _sur_message(self, sender, args):
        """Sur le fil d'interface. Ne lève JAMAIS : Revit tomberait."""
        try:
            message = json.loads(args.TryGetWebMessageAsString() or '{}')
        except Exception as erreur:
            return log(u'message illisible : {}', erreur)
        ref = message.get('ref')
        ordre = message.get('ordre')
        if ordre == 'erreur':
            # Une fenêtre WebView2 n'a pas de console sous les yeux de
            # l'utilisateur : sans ce relais, une interface cassée reste muette.
            return log(u'interface : {}', message.get('message'))
        try:
            self._poster('reponse', {'ref': ref,
                                     'sortie': self._ordres.traiter(message)})
        except Exception as erreur:
            # Jamais de silence : une promesse sans réponse laisse la page
            # bloquée jusqu'au délai du pont.
            log(u'ordre {} : {}', ordre, erreur)
            self._poster('reponse', {'ref': ref,
                                     'erreur': u'{0}'.format(erreur)})

    def _poster(self, evenement, charge):
        if self._coeur is None:
            return
        try:
            # ensure_ascii=False : sous IronPython 2.7, laisser json échapper
            # les accents lève.
            self._coeur.PostWebMessageAsJson(json.dumps(
                {'evenement': evenement, 'charge': charge},
                ensure_ascii=False))
        except Exception as erreur:
            log(u'envoi de {} : {}', evenement, erreur)


def _controle(dossier_profil):
    """Un WebView2 prêt à initialiser.

    Les assemblies `Microsoft.Web.WebView2.*` sont livrées AVEC Revit 2026 et
    déjà chargées dans le process : rien à embarquer, et vendoriser une autre
    version serait un conflit.
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
