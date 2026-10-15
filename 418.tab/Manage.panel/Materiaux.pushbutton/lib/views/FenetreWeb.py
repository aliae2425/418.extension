# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import os
import time

# Une fenêtre = un WebView2 = une page. Ce module est l'hôte, et rien d'autre.
#
# Les trois fenêtres de l'outil (la principale, l'éditeur, le sélecteur de
# motif) héritent d'ici et ne déclarent que de la donnée : un titre, une
# taille, une page, et le contexte que la page reçoit à son `pret`. Même
# geste que `RailWindow` pour les outils à onglets — ce qui variait d'une
# fenêtre à l'autre n'était que de la donnée.
#
# Pièges payés, à ne pas redécouvrir :
#
# - la fenêtre est borderless mais PAS transparente. WebView2 est un contrôle
#   à HWND : dans une fenêtre WPF en couches (`AllowsTransparency`) il ne
#   s'affiche pas du tout. Les coins arrondis sont rendus au système, qui
#   sait les faire depuis Windows 11 ;
# - le contrôle n'est pas déclaré dans le XAML : `XamlReader` résoudrait le
#   namespace clr au parse, ce qui échoue tant que l'assembly n'est pas
#   référencée. Il est injecté par `.Child` ;
# - la `Task` d'`EnsureCoreWebView2Async` est jetée, jamais attendue :
#   `.Result` sur le fil d'interface interbloque, la Task ne se complétant
#   que par la pompe de messages — ici celle de `ShowDialog`.
#
# Le fil : toutes ces fenêtres sont MODALES, donc tout ce code tourne dans le
# contexte d'API de la commande pyRevit. Les transactions partent du
# gestionnaire de messages, sans fil de fond ni ExternalEvent.

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
    'GUI', 'Views', 'FenetreWeb.xaml')

HOTE = '418.local'

# Même profil que le volet OpenArchi : plusieurs WebView2 du MÊME processus
# partagent un dossier de données sans se gêner, et un second profil coûterait
# une centaine de mégaoctets pour rien.
PROFIL = 'webview2'

#: Rendu par `_ordre_vue` quand la fenêtre ne connaît pas l'ordre : il part
#: alors aux services. Un `None` ne ferait pas l'affaire — c'est une réponse
#: légitime.
AUTRE = object()

#: `DWMWA_WINDOW_CORNER_PREFERENCE` et `DWMWCP_ROUND` (dwmapi.h, Windows 11).
#: Le rayon est celui du système — on demande des coins arrondis, pas une
#: valeur en pixels : c'est Windows qui tient la charte, pas nous.
DWMWA_COINS = 33
DWMWCP_ARRONDI = 2


class FenetreWeb(BaseWindow):
    """Fenêtre borderless dont tout le contenu est une page de `lib/web/`."""

    #: Page servie, relative à `lib/web/`.
    PAGE = None
    TITRE = u'418'
    TAILLE = (1240, 800)
    TAILLE_MINI = (960, 600)
    #: Réduire/agrandir n'a de sens que sur la fenêtre principale ; une
    #: fenêtre fille ne garde que la croix.
    BOUTONS_FENETRE = True

    def __init__(self, ordres, proprietaire=None):
        # Pas de DataContext : il n'y a plus de ViewModel, et le seul contrôle
        # de la fenêtre n'a rien à lier.
        super(FenetreWeb, self).__init__(_XAML, None)
        self._ordres = ordres
        self._proprietaire = proprietaire
        self._vue = None
        self._coeur = None
        self._hote = None
        self._cartouche = None
        #: Ce que la page a renvoyé en se fermant. `None` = annulé — c'est la
        #: seule chose qui distingue « Annuler » d'un choix.
        self.resultat = None

    # -- ce que les filles déclarent ---------------------------------------

    def contexte(self):
        """L'état que la page reçoit en réponse à son ordre `pret`."""
        raise NotImplementedError

    def _ordre_vue(self, message):
        """Les ordres que SEULE une fenêtre peut servir (en ouvrir une autre).

        Rendre `AUTRE` laisse l'ordre descendre aux services.
        """
        return AUTRE

    # -- ouverture ---------------------------------------------------------

    def ouvrir(self):
        """Affiche en modal et rend ce que la page a renvoyé en se fermant."""
        self.show()
        return self.resultat

    def _load(self):
        super(FenetreWeb, self)._load()
        if self._window is None:
            return
        self._habiller()
        # Le navigateur se monte sur `Loaded`, PAS ici : `_load` tourne avant
        # `ShowDialog`, donc sur une fenêtre qui n'est pas encore affichée, et
        # `EnsureCoreWebView2Async` n'aboutit JAMAIS tant que le contrôle est
        # invisible. Le contrôle existe, il n'a pas de cœur, et il peint un
        # rectangle noir — sans une ligne de journal, puisque rien n'a échoué.
        # Même piège, même parade que le volet OpenArchi, qui monte le sien à
        # la première visibilité.
        self._window.Loaded += self._sur_affichage

    def _sur_affichage(self, sender, args):
        """La fenêtre est à l'écran : le navigateur peut s'initialiser."""
        if self._vue is not None:
            return                     # `Loaded` peut repasser, pas le montage
        try:
            self._monter()
        except Exception as erreur:
            # Sans ce repli la fenêtre s'ouvre vide et sans un mot : le
            # runtime WebView2 absent est le cas le plus probable sur un poste
            # qui n'est pas à jour.
            log(u'montage du navigateur impossible : {}', erreur)
            self._message(u'Interface non affichable : {}'.format(erreur))

    def _habiller(self):
        fenetre = self._window
        # Le cartouche est résolu ICI, et depuis la FENÊTRE : c'est elle qui
        # porte la portée de noms, et surtout `_habiller` tourne toujours.
        # Le chercher dans `_monter` le rendait muet exactement quand on en a
        # besoin — quand le montage échoue.
        self._cartouche = fenetre.FindName('WebHostMessage')
        # Les coins se posent quand le HWND existe — donc pas maintenant, et
        # surtout pas par `EnsureHandle()` : créer la poignée avant l'affichage
        # fait rater son placement à la fenêtre (centrée écran ou propriétaire).
        fenetre.SourceInitialized += self._sur_poignee
        fenetre.Title = self.TITRE
        fenetre.Width, fenetre.Height = self.TAILLE
        fenetre.MinWidth, fenetre.MinHeight = self.TAILLE_MINI
        titre = fenetre.FindName('TitreFenetre')
        if titre is not None:
            titre.Text = self.TITRE
        if not self.BOUTONS_FENETRE:
            for nom in ('MinimizeButton', 'MaximizeRestoreButton'):
                bouton = fenetre.FindName(nom)
                if bouton is not None:
                    from System.Windows import Visibility
                    bouton.Visibility = Visibility.Collapsed
        if self._proprietaire is not None:
            # Fille d'une fenêtre : elle s'ouvre devant, se centre sur elle et
            # ne se retrouve jamais derrière dans la barre des tâches.
            from System.Windows import WindowStartupLocation
            fenetre.Owner = self._proprietaire
            fenetre.WindowStartupLocation = WindowStartupLocation.CenterOwner
            fenetre.ShowInTaskbar = False

    def _sur_poignee(self, sender, args):
        """Demande à DWM d'arrondir les coins de la fenêtre.

        `WindowStyle="None"` prive WPF du cadre que Windows arrondit tout
        seul, et la parade habituelle — `AllowsTransparency` plus un `Border`
        à `CornerRadius` — est justement celle qui fait disparaître WebView2.
        On passe donc par l'attribut DWM : c'est le système qui découpe la
        fenêtre, enfants HWND compris, et c'est lui qui tient le rayon.

        Si ça échoue, la fenêtre reste carrée et tout le reste marche — d'où
        le silence de ce `except`, une trace dans le journal et rien de plus.

        ponytail: `ctypes` plutôt qu'un vrai P/Invoke. Sous IronPython il
        porte quelques verrues, mais l'appel est de la forme la plus simple
        qui soit (un entier par référence). S'il venait à manquer, le repli
        est `DefinePInvokeMethod` via Reflection.Emit, vingt lignes de plus.
        """
        try:
            import ctypes
            from System.Windows.Interop import WindowInteropHelper
            poignee = WindowInteropHelper(self._window).Handle
            prefere = ctypes.c_int(DWMWCP_ARRONDI)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(poignee.ToInt64()), DWMWA_COINS,
                ctypes.byref(prefere), ctypes.sizeof(prefere))
        except Exception as erreur:
            log(u'coins arrondis refusés par DWM : {}', erreur)

    def _monter(self):
        hote = self._window.FindName('WebHost')
        if hote is None:
            raise ValueError(u'WebHost absent du XAML')
        self._hote = hote
        vue = _controle(os.path.join(AppPaths().data_dir(), PROFIL))
        # SOUS le cartouche, qui reste au-dessus jusqu'à la page chargée : le
        # contrôle met plusieurs secondes à naître et peint un rectangle vide
        # en attendant.
        hote.Children.Insert(0, vue)
        self._vue = vue
        vue.CoreWebView2InitializationCompleted += self._sur_init
        vue.EnsureCoreWebView2Async()      # Task jetée : pas d'await en IPY 2.7
        log(u'navigateur demandé ({})', self.PAGE)

    def _message(self, texte):
        """Ce que dit le cartouche posé par-dessus le navigateur."""
        try:
            if self._cartouche is not None:
                from System.Windows import Visibility
                self._cartouche.Text = texte
                self._cartouche.Visibility = Visibility.Visible
        except Exception as erreur:
            log(u'affichage du message « {} » : {}', texte, erreur)

    def _effacer_message(self):
        """La page est là : le cartouche s'efface et découvre le navigateur."""
        try:
            if self._cartouche is not None:
                from System.Windows import Visibility
                self._cartouche.Visibility = Visibility.Collapsed
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
            # UNE seule origine pour toute `lib/web/` : les pages de l'outil
            # importent le pont et les jetons de thème du volet, et deux
            # mappings virtuels feraient deux origines, donc des imports ES
            # bloqués entre les deux.
            coeur.SetVirtualHostNameToFolderMapping(
                HOTE, AppPaths().web_dir(),
                CoreWebView2HostResourceAccessKind.Allow)
            coeur.WebMessageReceived += self._sur_message
            # La navigation est le dernier endroit où ça peut casser en
            # silence : un fichier absent ou une origine mal mappée rendent
            # une page blanche, et sans cette trace on cherche côté Python.
            coeur.NavigationCompleted += self._sur_navigation
            coeur.Navigate('https://{0}/{1}'.format(HOTE, self.PAGE))
            log(u'navigateur monté, origine {} -> {}',
                HOTE, AppPaths().web_dir())
        except Exception as erreur:
            log(u'initialisation du navigateur : {}', erreur)
            self._message(u'Navigateur non initialisé : {}'.format(erreur))

    def _sur_navigation(self, sender, args):
        try:
            if args.IsSuccess:
                self._effacer_message()
                return log(u'page chargée : {}', self.PAGE)
            log(u'page NON chargée ({}) : {}', self.PAGE, args.WebErrorStatus)
            self._message(u'Page non chargée : {0}'.format(
                args.WebErrorStatus))
        except Exception:
            pass

    # -- ce que la page demande --------------------------------------------

    def _sur_message(self, sender, args):
        """Sur le fil d'interface. Ne lève JAMAIS : Revit tomberait."""
        try:
            message = json.loads(args.TryGetWebMessageAsString() or '{}')
        except Exception as erreur:
            return log(u'message illisible : {}', erreur)
        ordre = message.get('ordre')
        if ordre == 'erreur':
            # Une fenêtre WebView2 n'a pas de console sous les yeux de
            # l'utilisateur : sans ce relais, une interface cassée est muette.
            return log(u'interface : {}', message.get('message'))
        if ordre == 'fermer':
            # La page a fini : elle rend son résultat, la fenêtre se retire.
            self.resultat = message.get('resultat')
            try:
                return self._window.Close()
            except Exception as erreur:
                return log(u'fermeture : {}', erreur)
        if (ordre or '').startswith('ouvrir_'):
            # Une fenêtre fille BLOQUE ce gestionnaire tant qu'elle est
            # ouverte, et un matériau s'édite en plusieurs minutes. Répondre à
            # la demande serait répondre longtemps après que le pont a rendu
            # la main : on pousse donc un évènement à la fermeture, et la page
            # n'attend aucune promesse.
            try:
                return self._poster(ordre, {'resultat': self._ordre_vue(message)})
            except Exception as erreur:
                return log(u'ordre {} : {}', ordre, erreur)
        debut = time.time()
        try:
            sortie = self._traiter(message)
        except Exception as erreur:
            # Jamais de silence : une promesse sans réponse laisse la page
            # bloquée jusqu'au délai du pont.
            log(u'ordre {} : {}', ordre, erreur)
            return self._poster('reponse', {'ref': message.get('ref'),
                                            'erreur': u'{0}'.format(erreur)})
        # Tracé même quand tout va bien : une page vide sans la moindre ligne
        # de journal ne dit pas si l'ordre n'est jamais arrivé ou s'il a mis
        # huit secondes. Le temps est là pour la même raison.
        log(u'ordre {} servi en {} ms', ordre,
            int((time.time() - debut) * 1000))
        self._poster('reponse', {'ref': message.get('ref'), 'sortie': sortie})

    def _traiter(self, message):
        if message.get('ordre') == 'pret':
            return self.contexte()
        sortie = self._ordre_vue(message)
        if sortie is not AUTRE:
            return sortie
        return self._ordres.traiter(message)

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
