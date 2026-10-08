# -*- coding: utf-8 -*-
"""Banc d'essai WebView2 en volet ancrable. Ne se connecte à rien.

RampeParking prouve déjà qu'IronPython 2.7 sait monter un WebView2 — mais
dans une **fenêtre**, et en se contentant de `Source = Uri(...)`, ce qui
initialise implicitement sans jamais toucher l'objet `CoreWebView2`. Or les
trois API dont un chat a besoin vivent dessus.

Ce banc ne mesure donc que ce que RampeParking ne pouvait pas couvrir :

1. l'initialisation aboutit-elle quand le volet naît **invisible** ;
2. `CoreWebView2` est-il réellement atteignable ;
3. `SetVirtualHostNameToFolderMapping` sert-il une page locale (modules ES,
   `fetch`) ;
4. l'aller-retour `PostWebMessageAsJson` → `WebMessageReceived`, et sa latence ;
5. **le contrôle à HWND survit-il à ancrer / désancrer / flotter / ré-ancrer** —
   c'est la seule question qui peut tout faire tomber, et la même famille de
   problème que l'airspace déjà rencontré dans RampeParking ;
6. `PostWebMessageAsJson` depuis un **fil de fond** : légal, ou affinité STA ?

Tout part dans ``data/418.log`` sous ``openarchi.spike`` et s'affiche dans le
volet, sélectionnable pour être collé dans un rapport.

**À supprimer une fois la décision prise.** Ce module n'a pas vocation à vivre.
"""
from __future__ import unicode_literals
import os

from pyrevit import forms

try:
    from core.AppPaths import AppPaths
    from core.journal import journal
except Exception:
    from lib.core.AppPaths import AppPaths
    from lib.core.journal import journal

try:
    from ui.helpers.UIResourceLoader import UIResourceLoader
    from ui.helpers.DarkMode import is_dark
except Exception:
    from lib.ui.helpers.UIResourceLoader import UIResourceLoader
    from lib.ui.helpers.DarkMode import is_dark

_log = journal('spike')

# Racine web servie au WebView2. Un nom en `.local` et non un vrai domaine :
# rien ne doit pouvoir sortir si la résolution tourne mal.
HOTE = '418.local'

# Dossier de profil Chromium PROPRE au banc. Surtout pas `data/webview2`, qui
# appartient à RampeParking : deux contrôles vivants sur le même profil se
# disputent un verrou de fichier, et on diagnostiquerait ça au lieu du volet.
PROFIL = 'webview2-spike'

TOURS = 100


def _dossier_web():
    return os.path.join(AppPaths().ui_gui_dir(), 'web', 'spike')


class SpikeWebPanel(forms.WPFPanel):
    """Volet ancrable jetable. `panel_id` distinct : zéro risque pour OpenArchi."""

    panel_id = 'b2e6c4d1-9f73-4a85-8c10-5d3e7a1f6b92'
    panel_source = os.path.join(AppPaths().pages_dir(), 'SpikeWebPanel.xaml')
    panel_title = 'Spike WebView2'

    def __init__(self):
        try:
            UIResourceLoader(self, dark=is_dark()).merge_theme()
            forms.WPFPanel.__init__(self)
        except Exception:
            # Revit avale les exceptions de construction d'un volet ancré :
            # sans cette trace, le panneau reste vide sans un mot.
            _log.exception('construction du banc impossible')
            raise
        self._vue = None
        self._coeur = None
        self._chrono = None
        self._tours = 0
        self._chrono_tours = None
        self._attente_preuve = False
        self._lignes = []
        self._dire('volet construit — WebView2 PAS créé (init paresseuse)')
        # Le volet s'enregistre `default_visible=False` : on attend qu'il soit
        # montré. `EnsureCoreWebView2Async` n'aboutit pas sur un contrôle
        # invisible, et c'est ce qui faisait planter le spike RevitMCP.
        # `Loaded` en ceinture : si Revit n'émet pas `IsVisibleChanged` en
        # affichant le volet, rien ne se créerait et le banc ne mesurerait
        # rien. La garde `_vue is None` rend le doublon inoffensif.
        self.IsVisibleChanged += self._sur_visibilite
        self.Loaded += self._sur_visibilite
        try:
            self.Verifier.Click += self._sur_verifier
        except Exception:
            _log.exception('bouton Vérifier non câblé')

    # --- affichage ---------------------------------------------------------

    def _dire(self, texte):
        """Une ligne au journal ET dans le volet. Ne lève jamais."""
        _log.info('%s', texte)
        try:
            self._lignes.append(texte)
            self.Verdict.Text = '\n'.join(self._lignes)
            self.Verdict.ScrollToEnd()
        except Exception:
            pass                           # jamais laisser lever sur le fil d'UI

    def _echec(self, etape, erreur):
        _log.exception('%s', etape)
        self._dire('ECHEC {0} : {1}'.format(etape, erreur))

    # --- construction paresseuse ------------------------------------------

    def _sur_visibilite(self, sender, args):
        try:
            visible = bool(args.NewValue)
        except Exception:
            visible = True
        self._dire('visibilité → {0}'.format('affiché' if visible else 'masqué'))
        if visible and self._vue is None:
            self._creer()
        elif visible and self._coeur is not None:
            # Réaffichage après un désancrage : c'est ICI que se lit la survie
            # du HWND, sans attendre que l'utilisateur presse « Vérifier ».
            self._etat_apres_ancrage()

    def _creer(self):
        """Monte le contrôle et lance l'initialisation. Ne lève jamais."""
        try:
            from System.Diagnostics import Stopwatch
            vue = _controle(os.path.join(AppPaths().data_dir(), PROFIL))
        except Exception as e:
            return self._echec('création du contrôle', e)
        try:
            self.Hote.Child = vue
            self._vue = vue
            vue.CoreWebView2InitializationCompleted += self._sur_init
            self._chrono = Stopwatch.StartNew()
            # La Task est volontairement jetée : IronPython 2.7 n'a pas
            # d'`await`, et lire `.Result` sur le fil d'interface interbloque —
            # la Task ne se complète que par la pompe de messages WPF.
            vue.EnsureCoreWebView2Async()
            self._dire('EnsureCoreWebView2Async() lancé, Task ignorée')
        except Exception as e:
            self._echec('montage du contrôle', e)

    def _sur_init(self, sender, args):
        try:
            ok = bool(args.IsSuccess)
        except Exception:
            ok = False
        millisecondes = self._chrono.ElapsedMilliseconds if self._chrono else -1
        if not ok:
            erreur = getattr(args, 'InitializationException', None)
            return self._dire(
                'ECHEC init après {0} ms : {1}'.format(millisecondes, erreur))
        self._dire('[1] init OK en {0} ms'.format(millisecondes))
        coeur = getattr(self._vue, 'CoreWebView2', None)
        if coeur is None:
            # Le point que RampeParking ne pouvait pas couvrir : il navigue
            # par `Source`, donc il n'a jamais besoin de cet objet.
            return self._dire('[2] CoreWebView2 est NUL — tout le reste tombe')
        self._coeur = coeur
        self._dire('[2] CoreWebView2 atteignable')
        self._servir(coeur)

    def _servir(self, coeur):
        try:
            from Microsoft.Web.WebView2.Core import (
                CoreWebView2HostResourceAccessKind)
            coeur.SetVirtualHostNameToFolderMapping(
                HOTE, _dossier_web(), CoreWebView2HostResourceAccessKind.Allow)
            self._dire('[3] mapping virtuel posé sur {0}'.format(_dossier_web()))
        except Exception as e:
            return self._echec('SetVirtualHostNameToFolderMapping', e)
        try:
            coeur.WebMessageReceived += self._sur_message
            # Sans ce gestionnaire, une navigation refusée ou un `import` qui
            # lève dans la page ne produisent AUCUN `pret` : le banc attendrait
            # indéfiniment, et ça se lirait « WebView2 ne marche pas ».
            coeur.NavigationCompleted += self._sur_navigation
            coeur.Navigate('https://{0}/index.html'.format(HOTE))
            self._dire('[3] navigation lancée vers https://{0}/'.format(HOTE))
        except Exception as e:
            self._echec('navigation', e)

    def _sur_navigation(self, sender, args):
        try:
            if not args.IsSuccess:
                self._dire('[3] navigation ECHOUEE : {0}'.format(
                    args.WebErrorStatus))
        except Exception as e:
            self._echec('lecture de NavigationCompleted', e)

    # --- dialogue avec la page --------------------------------------------

    def _sur_message(self, sender, args):
        """Messages de la page. Ne lève jamais : on est sur le fil d'interface."""
        try:
            brut = args.TryGetWebMessageAsString()
        except Exception:
            try:
                brut = args.WebMessageAsJson
            except Exception as e:
                return self._echec('lecture du message', e)
        try:
            self._traiter(brut or '')
        except Exception as e:
            self._echec('traitement du message « {0} »'.format(brut), e)

    def _traiter(self, brut):
        import json
        try:
            message = json.loads(brut)
        except ValueError:
            return self._dire('message illisible : {0}'.format(brut[:120]))
        genre = message.get('type')
        if genre == 'pret':
            self._dire('[3] page chargée — modules ES : {0} · fetch : {1}'.format(
                message.get('modules'), message.get('fetch')))
            self._theme()
            self._lancer_tours()
        elif genre == 'pong':
            self._pong()
        elif genre == 'fond-recu':
            # L'écho qui distingue « l'appel n'a pas levé » de « le message est
            # réellement passé ». C'est sur cette réponse que se décide le
            # tampon du streaming : la confondre coûterait cher.
            self._dire('[8] message du fil de fond REÇU par la page')
        else:
            self._dire('message : {0}'.format(brut[:200]))

    def _theme(self):
        try:
            sombre = 'sombre' if is_dark() else 'clair'
            self._poster('{{"type":"theme","valeur":"{0}"}}'.format(sombre))
            self._dire('[7] thème « {0} » poussé à la page'.format(sombre))
        except Exception as e:
            self._echec('poussée du thème', e)

    def _poster(self, charge):
        self._coeur.PostWebMessageAsJson(charge)

    # --- mesure de latence -------------------------------------------------

    def _lancer_tours(self):
        from System.Diagnostics import Stopwatch
        self._tours = 0
        self._chrono_tours = Stopwatch.StartNew()
        self._poster('{"type":"ping"}')

    def _pong(self):
        # Un pong attendu APRÈS la campagne : c'est la preuve de survie du
        # HWND demandée par `_etat_apres_ancrage`, pas un tour de mesure.
        if self._attente_preuve:
            self._attente_preuve = False
            return self._dire('[5] aller-retour OK après ancrage — HWND vivant')
        if self._chrono_tours is None:
            return                         # pong en retard : ne rien rejouer
        self._tours += 1
        if self._tours < TOURS:
            return self._poster('{"type":"ping"}')
        total = self._chrono_tours.ElapsedMilliseconds
        # Fermer la campagne AVANT de dire : un pong de plus relancerait
        # sinon `_script()` et `_fil_de_fond()` avec un ms/tour faux.
        self._chrono_tours = None
        self._dire('[4] {0} allers-retours postMessage en {1} ms '
                   '({2:.2f} ms/tour)'.format(TOURS, total, float(total) / TOURS))
        self._script()
        self._fil_de_fond()

    def _script(self):
        try:
            # Fire-and-forget : on jette la Task, même règle que l'init.
            self._coeur.ExecuteScriptAsync(
                'document.title = "piloté par IronPython"')
            self._dire('[6] ExecuteScriptAsync accepté (fire-and-forget)')
        except Exception as e:
            self._echec('ExecuteScriptAsync', e)

    def _fil_de_fond(self):
        """`PostWebMessageAsJson` hors du fil d'interface : légal ou non ?

        `CoreWebView2` est COM/STA. Si l'appel lève ici, tout streaming
        token par token devra passer par le Dispatcher — donc par un tampon,
        sinon c'est un marshal bloquant par jeton.
        """
        try:
            from System.Threading import Thread, ThreadStart
        except Exception as e:
            return self._echec('import Thread', e)

        def essai():
            try:
                self._coeur.PostWebMessageAsJson('{"type":"fond"}')
                verdict = '[8] PostWebMessageAsJson depuis un fil de fond : ACCEPTE'
            except Exception as e:
                verdict = ('[8] PostWebMessageAsJson depuis un fil de fond : '
                           'REFUSE ({0}) — tampon + Dispatcher obligatoires'
                           .format(type(e).__name__))
            _log.info('%s', verdict)
            try:
                self.Dispatcher.Invoke(_Action(lambda: self._dire(verdict)))
            except Exception:
                pass                       # le journal a déjà la réponse

        try:
            fil = Thread(ThreadStart(essai))
            fil.IsBackground = True
            fil.Start()
        except Exception as e:
            self._echec('lancement du fil de fond', e)

    # --- relecture à la demande -------------------------------------------

    def _sur_verifier(self, sender, args):
        """Après avoir ancré, désancré, fait flotter, ré-ancré le volet."""
        try:
            self._etat_apres_ancrage()
            self._memoire()
        except Exception as e:
            self._echec('vérification après ancrage', e)

    def _etat_apres_ancrage(self):
        """Le point 5 — et il doit pouvoir répondre NON.

        Relire `self._coeur` ne prouverait rien : c'est une référence Python,
        elle ne devient jamais nulle toute seule. On relit donc l'objet sur le
        contrôle, et surtout on exige une **preuve par aller-retour** : seul un
        pong dit que le HWND est encore vivant derrière la référence.
        """
        coeur = getattr(self._vue, 'CoreWebView2', None) if self._vue else None
        vivant = coeur is not None and coeur == self._coeur
        try:
            # Mesurer le WebView2 lui-même, pas son Border : un hôte bien
            # dimensionné autour d'un contrôle non arrangé passerait le test.
            largeur = int(self._vue.ActualWidth) if self._vue else -1
            hauteur = int(self._vue.ActualHeight) if self._vue else -1
        except Exception:
            largeur = hauteur = -1
        try:
            url = coeur.Source if coeur is not None else '—'
        except Exception as e:
            url = 'illisible ({0})'.format(e)
        self._dire('[5] après ancrage : contrôle {0} · vue {1}×{2} · url {3}'
                   .format('présent' if vivant else 'PERDU',
                           largeur, hauteur, url))
        if vivant and (largeur <= 0 or hauteur <= 0):
            self._dire('[5] ATTENTION vue de taille nulle — airspace probable')
        if coeur is None:
            return
        try:
            self._attente_preuve = True
            coeur.PostWebMessageAsJson('{"type":"ping"}')
            self._dire('[5] preuve demandée — un pong doit suivre')
        except Exception as e:
            self._attente_preuve = False
            self._echec('aller-retour après ancrage', e)

    def _memoire(self):
        """Ce que coûte NOTRE WebView2, pas celui de toute la machine.

        Compter tous les `msedgewebview2` annonçait 3,7 Go : Revit embarque
        lui-même WebView2 (écran d'accueil, Sentiment), Dynamo aussi, et la
        moitié des applications Office. On ne garde que les process dont la
        ligne de commande porte notre dossier de profil — le vrai chiffre est
        douze fois plus bas, et c'est celui qui décide.
        """
        try:
            from System.Diagnostics import Process
            tous = list(Process.GetProcessesByName('msedgewebview2'))
        except Exception as e:
            return self._echec('lecture mémoire', e)
        octets, nombre, aveugle = 0, 0, False
        for processus in tous:
            verdict = _du_banc(processus)
            if verdict is None:
                aveugle = True
                break
            if not verdict:
                continue
            nombre += 1
            try:
                octets += processus.WorkingSet64
            except Exception:
                pass
        if aveugle:
            # Dire « 0 process » parce qu'on n'a pas pu demander serait un
            # mensonge, et il se lirait comme une panne. On rend le total
            # machine en disant que c'en est un.
            total = 0
            for processus in tous:
                try:
                    total += processus.WorkingSet64
                except Exception:
                    pass
            return self._dire(
                '[9] part du banc INDÉTERMINÉE (WMI injoignable) — {0} process '
                'sur la machine, {1} Mo, Revit et Dynamo compris'.format(
                    len(tous), total // (1024 * 1024)))
        self._dire('[9] banc : {0} process, {1} Mo — ({2} sur la machine, '
                   'Revit et Dynamo compris)'.format(
                       nombre, octets // (1024 * 1024), len(tous)))


def _du_banc(processus):
    """Ce process sert-il NOTRE profil ? ``None`` si la question est illisible.

    La ligne de commande n'est pas exposée par ``System.Diagnostics`` : il faut
    WMI, et sous CoreCLR ``System.Management`` n'est pas toujours chargeable.
    Les trois réponses sont distinctes — oui, non, et « je ne peux pas
    savoir » — parce que les confondre ferait passer une mesure impossible
    pour une mesure nulle.
    """
    try:
        import clr
        clr.AddReference('System.Management')
        from System.Management import ManagementObjectSearcher
    except Exception:
        return None
    try:
        requete = ('SELECT CommandLine FROM Win32_Process WHERE ProcessId = {0}'
                   .format(processus.Id))
        for trouve in ManagementObjectSearcher(requete).Get():
            return PROFIL in (trouve['CommandLine'] or '')
    except Exception:
        return None
    return False


def _Action(fonction):
    from System import Action
    return Action(fonction)


def _controle(dossier_profil):
    """Un WebView2 prêt à initialiser.

    Repris de ``RampeParking`` — les assemblies sont livrées AVEC Revit 2026 et
    déjà chargées dans le process ; rien à embarquer, et vendoriser une autre
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
