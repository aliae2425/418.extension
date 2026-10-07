# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import base64
import json
import os
import threading

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        BaseViewModel = object

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    try:
        from lib.ui.helpers.RelayCommand import RelayCommand
    except Exception:
        RelayCommand = None

try:
    from core.chat_syntaxe import analyser
except Exception:
    from lib.core.chat_syntaxe import analyser

try:
    from core import journal as _journal
except Exception:
    from lib.core import journal as _journal

try:
    from core import revit_outils
except Exception:
    try:
        from lib.core import revit_outils
    except Exception:
        revit_outils = None            # hors Revit : pas de bandeau d'alerte

try:
    from core import routes418
except Exception:
    try:
        from lib.core import routes418
    except Exception:
        routes418 = None               # hors Revit : /routes n'a rien à cocher

try:
    from core.markdown_simple import texte_nu as _md_nu
except Exception:
    try:
        from lib.core.markdown_simple import texte_nu as _md_nu
    except Exception:
        _md_nu = None

try:
    from ui.helpers import FlowMarkdown as _flow
except Exception:
    try:
        from lib.ui.helpers import FlowMarkdown as _flow
    except Exception:
        _flow = None                   # hors WPF : bulles en texte nu


def _texte_nu(texte):
    """Texte débarrassé de ses marques Markdown. Ne lève jamais.

    Une bulle qui n'affiche rien parce que le nettoyage a buté sur un
    caractère, c'est pire que des astérisques visibles.
    """
    if _md_nu is None:
        return texte
    try:
        return _md_nu(texte)
    except Exception:
        _log.exception('nettoyage markdown')
        return texte

def _proteger(travail):
    """Exécute en avalant tout. OBLIGATOIRE sur le fil d'interface.

    Ce qui s'exécute là touche des propriétés liées et ``Messages`` : une
    exception qui s'en échappe part non rattrapée sur le fil d'interface de
    Revit, et Revit meurt. C'est arrivé — PresentationCore,
    InvalidOperationException. Une bulle d'erreur vaut mieux qu'une session
    perdue.
    """
    try:
        return travail()
    except Exception:
        _log.exception('sur le fil d\'interface')


def _poids(octets):
    """« 2,1 Mo » / « 340 ko ». Virgule décimale : on écrit en français."""
    if octets >= 1024 * 1024:
        return '{0} Mo'.format(
            '{0:.1f}'.format(octets / (1024.0 * 1024.0)).replace('.', ','))
    return '{0} ko'.format(max(1, int(octets // 1024)))


# Au-delà, la bulle devient un mur : le détail complet reste à un
# revit_elements près, et le modèle sait maintenant que le DWG est là.
_CALQUES_MONTRES = 12


def _resume_dwg(brut):
    """La sortie de ``revit_lier_dwg`` en une phrase lisible."""
    try:
        charge = json.loads(brut)
    except (ValueError, TypeError):
        return 'DWG : réponse illisible de Revit. /journal pour le détail.'
    if not isinstance(charge, dict) or charge.get('erreur'):
        return 'DWG non lié : {0}'.format(
            (charge or {}).get('erreur') or 'échec sans message')
    calques = charge.get('calques') or []
    if not calques:
        suite = 'aucun calque nommé'
    else:
        montres = ', '.join(calques[:_CALQUES_MONTRES])
        reste = len(calques) - _CALQUES_MONTRES
        suite = '{0} calques : {1}{2}'.format(
            len(calques), montres, ' …' if reste > 0 else '')
    return '{0} lié dans « {1} » — {2}.'.format(
        charge.get('lie') or 'DWG', charge.get('vue') or 'la vue active',
        suite)


_log = _journal.journal('chat')

try:
    from ui.OpenArchiConfig import (OpenArchiConfig, CATALOGUE, ACTIFS,
                                    connexions_de, MODELE_DEFAUT, CLE_API)
except Exception:
    from lib.ui.OpenArchiConfig import (OpenArchiConfig, CATALOGUE, ACTIFS,
                                        connexions_de, MODELE_DEFAUT, CLE_API)

# Hors Revit (tests unitaires en CPython), .NET est absent : on retombe sur
# une liste Python. Le VM reste testable, seule la notification WPF disparaît.
try:
    from System.Collections.ObjectModel import ObservableCollection
except Exception:
    ObservableCollection = None

# Même repli : hors Revit, le VM répond sur place et reste synchrone, donc
# testable sans rien simuler.
try:
    from System import Action, TimeSpan
    from System.Threading import Thread, ThreadStart
    from System.Windows.Threading import Dispatcher, DispatcherTimer
except Exception:
    Action = Thread = ThreadStart = Dispatcher = None
    TimeSpan = DispatcherTimer = None

try:
    from core import attente as _attente
except Exception:
    try:
        from lib.core import attente as _attente
    except Exception:
        _attente = None                # repli : libellé figé, sans chronomètre

try:
    from System.Windows.Input import CommandManager
except Exception:
    CommandManager = None


def _dispatcher_interface():
    """Le dispatcher du fil d'interface, ``None`` hors .NET.

    ``Dispatcher.CurrentDispatcher`` en CRÉE un pour le fil appelant s'il n'y
    en a pas — on récupère alors un dispatcher sans boucle de messages, et
    tout ce qu'on lui confie s'exécute sur le mauvais fil. Celui de
    l'Application, quand elle existe, est celui qui possède réellement les
    liaisons.
    """
    if Dispatcher is None:
        return None
    try:
        from System.Windows import Application
        if Application.Current is not None:
            return Application.Current.Dispatcher
    except Exception:
        pass
    try:
        return Dispatcher.CurrentDispatcher
    except Exception:
        return None


class _ListeSimple(list):
    """Liste Python exposant l'API d'ObservableCollection (tests hors .NET)."""
    Add = list.append

    def Clear(self):
        del self[:]


class SuggestionVM(BaseViewModel):
    """Une entrée de la liste en place : commande ou fournisseur.

    ``libelle`` n'est fourni que pour les fournisseurs, qui s'affichent sans
    la barre oblique des commandes. ``actif`` à faux grise l'entrée : elle
    reste visible pour annoncer ce qui arrive, mais refuse le clic.
    """

    def __init__(self, nom, description='', libelle=None, actif=True):
        try:
            BaseViewModel.__init__(self)
        except Exception:
            pass
        self.Nom = nom
        self.Libelle = libelle if libelle is not None else '/' + nom
        self.Description = description
        self.Actif = bool(actif)


class MessageVM(BaseViewModel):
    """Une bulle de la conversation. Immuable : aucune notification requise."""

    def __init__(self, auteur, texte, de_utilisateur, duree='', affiche=None,
                 piece=None):
        try:
            BaseViewModel.__init__(self)
        except Exception:
            pass
        self.Auteur = auteur
        self.Texte = texte
        self.DeUtilisateur = bool(de_utilisateur)
        self.Alignement = 'Right' if de_utilisateur else 'Left'
        # Temps de réflexion, sous la bulle. '' sur tout ce qui n'a pas
        # demandé de réflexion : une commande locale répond instantanément,
        # afficher « 0 s » n'apprendrait rien.
        self.Duree = duree or ''
        self.DureeVisible = bool(self.Duree)
        # Repli texte, marques retirées : il sert quand WPF n'est pas là, et
        # c'est lui qu'affiche le gabarit sans mise en forme. `Texte` reste
        # brut — c'est lui qui repart au fournisseur dans l'historique, et
        # c'est lui que /journal doit pouvoir montrer.
        #
        # `affiche` découple les deux : une pièce jointe montre « plan.csv —
        # 12 ko » dans la bulle et emmène ses 12 ko dans l'historique.
        self.TexteAffiche = affiche if affiche is not None else _texte_nu(texte)
        # Fichier binaire à faire porter par l'appel (PDF). ``Texte`` ne peut
        # pas le transporter : il repart en base64 dans un bloc à part.
        self.Piece = piece
        self._document = None
        self._bati = False

    @property
    def MiseEnForme(self):
        """Toujours faux aujourd'hui : le gabarit riche est débranché.

        Construire le FlowDocument depuis une liaison, c'est le construire
        PENDANT l'inflation du DataTemplate — et là, la moindre erreur
        remonte en XamlParseException et tue Revit à l'ouverture d'un projet.
        Le rebrancher demande de bâtir le document AVANT, sur le fil
        d'interface, et de ne laisser à la liaison qu'un champ à lire.
        """
        return False

    @property
    def Document(self):
        return self._document


class OpenArchiChatVM(BaseViewModel):
    ACCUEIL = ("Panneau OpenArchi prêt. /connect pour choisir le fournisseur. "
               "#{Nom} pour citer un élément.")
    ATTENTE_DEFAUT = 'réflexion…'
    # Plafond d'une pièce jointe. Un CSV de projet entier noierait la fenêtre
    # de contexte, et le fournisseur le facturerait au jeton.
    PIECE_MAX = 200 * 1024
    # Plafond d'un PDF. Plus haut parce qu'il ne mange pas de contexte en
    # jetons de texte, plus bas qu'il n'y paraît parce qu'il repart dans
    # CHAQUE requête tant qu'il est dans la conversation.
    PDF_MAX = 8 * 1024 * 1024
    # Une image coûte des jetons à la hauteur de sa définition, pas de son
    # poids : au-delà, le fournisseur la réduit lui-même et on aura payé le
    # transfert pour rien.
    IMAGE_MAX = 4 * 1024 * 1024
    # Ce qu'un modèle sait regarder. Le format décide du bloc envoyé, pas
    # l'octet nul : un PNG est « binaire » et parfaitement lisible.
    IMAGES = {'.png': 'image/png', '.jpg': 'image/jpeg',
              '.jpeg': 'image/jpeg', '.gif': 'image/gif',
              '.webp': 'image/webp'}
    # Assez pour lire une erreur technique, assez peu pour ne pas rester en
    # travers du volet une fois la question suivante posée.
    DUREE_TOAST = 15
    # Au-delà, on considère que personne ne répondra — un panneau refermé
    # sans un clic laisserait sinon le fil de fond suspendu pour toujours.
    # Une expiration vaut un refus : on n'écrit pas dans la maquette parce
    # que l'architecte est parti déjeuner.
    DELAI_ACCORD = 300

    def __init__(self, config=None, client=None):
        try:
            BaseViewModel.__init__(self)
        except Exception:
            pass
        self._config = config if config is not None else OpenArchiConfig()
        # Injecté pour que les tests ne touchent ni le réseau ni un CLI ;
        # sinon le client suit le fournisseur choisi par /connect.
        self._client_injecte = client
        self._saisie = ''
        self._en_attente = False
        # Historique de saisie, façon terminal : Haut remonte, Bas redescend.
        # `_rang` à None = on n'y navigue pas ; `_brouillon` garde ce qui était
        # tapé quand on a commencé à remonter, pour le rendre en redescendant.
        self._saisies = []
        self._rang = None
        self._brouillon = ''
        # Vrai pendant qu'on pose une entrée d'historique : le setter de
        # Saisie doit alors savoir que ce n'est PAS une frappe de l'utilisateur.
        self._navigue = False
        self._phrase = self.ATTENTE_DEFAUT
        # Un libellé imposé (« connexion… ») ne tourne pas : il dit ce qui se
        # passe, une blague le remplacerait par du bruit.
        self._fixe = False
        self._secondes = 0
        self._horloge = None
        self._alerte = ''
        self._grave = False
        self._expiration = None
        self._dispatcher = _dispatcher_interface()
        self.Messages = self._nouvelle_liste()
        # Déclarées AVANT toute écriture de Saisie : son setter rafraîchit
        # l'autocomplétion, qui lit COMMANDES et Suggestions.
        self.COMMANDES = {
            'connect': ('choisir fournisseur, connexion et modèle',
                        self._commande_connect),
            'model': ('changer de modèle sur la connexion en cours',
                      self._commande_model),
            'logout': ('fermer la session du fournisseur en cours',
                       self._commande_logout),
            'journal': ('afficher les dernières lignes du journal',
                        self._commande_journal),
            'vider': ('repartir d\'une conversation neuve',
                      self._commande_vider),
            'routes': ('cocher « Routes » dans les réglages pyRevit',
                       self._commande_routes),
            'aide': ('lister les commandes disponibles', self._commande_aide),
        }
        self.Suggestions = self._nouvelle_liste()
        # La liste en place sert deux usages : l'autocomplétion pendant la
        # frappe, et l'assistant de /connect. Ses étapes s'enchaînent dans
        # l'ordre ci-dessous ; Échap remonte d'un cran.
        self._etape = None
        # DWG lâché, en attente de confirmation. Un seul à la fois : le
        # suivant remplace, comme une question qui chasse la précédente.
        self._depot = None
        # Accord demandé pour un outil irréversible : (réponse, signal). Le
        # fil de fond attend dessus, cf. _confirmer.
        self._question = None
        self.EnvoyerCommand = (RelayCommand(self._envoyer, self._peut_envoyer)
                               if RelayCommand else None)
        self.ChoisirSuggestionCommand = (RelayCommand(self._choisir)
                                         if RelayCommand else None)
        self.CompleterCommand = (RelayCommand(self._completer)
                                 if RelayCommand else None)
        self.RetourCommand = (RelayCommand(self._retour)
                              if RelayCommand else None)
        self.PrecedentCommand = (RelayCommand(self._precedent)
                                 if RelayCommand else None)
        self.SuivantCommand = (RelayCommand(self._suivant)
                               if RelayCommand else None)
        self.Messages.Add(MessageVM('OpenArchi', self.ACCUEIL, False))
        # PAS de vérification de la maquette ici. Le VM est construit pendant
        # que Revit bâtit le volet ancré, au démarrage : y lancer un fil de
        # fond qui revient notifier une propriété liée a fait lever WPF hors
        # du fil principal (InvalidOperationException, PresentationCore) et
        # tomber Revit au lancement. Le bandeau se remplit après le premier
        # échange, quand l'interface est bâtie et le dispatcher éprouvé.

    @staticmethod
    def _nouvelle_liste():
        return (ObservableCollection[object]() if ObservableCollection
                else _ListeSimple())

    # --- état affiché ----------------------------------------------------

    @property
    def Saisie(self):
        return self._saisie

    @Saisie.setter
    def Saisie(self, valeur):
        self._saisie = valeur or ''
        # Frappe libre : on quitte l'historique, la prochaine flèche Haut
        # repartira du message le plus récent.
        if not self._navigue:
            self._rang = None
        self.notify_property('Saisie')
        self._rafraichir_suggestions()

    # --- historique de saisie --------------------------------------------

    def _poser(self, texte):
        """Écrit dans le champ sans sortir de l'historique."""
        self._navigue = True
        try:
            self.Saisie = texte
        finally:
            self._navigue = False

    def _retenir(self, texte):
        """Ajoute au fond de l'historique. Ignore une répétition immédiate."""
        if not texte or self._saisies[-1:] == [texte]:
            return
        self._saisies.append(texte)

    def _precedent(self, _=None):
        """Flèche Haut : remonte vers les messages plus anciens."""
        if not self._saisies:
            return
        if self._rang is None:
            # Premier pas : mettre de côté ce qui était en train d'être tapé.
            self._brouillon = self._saisie
            self._rang = len(self._saisies)
        if self._rang == 0:
            return                     # déjà au plus ancien, on y reste
        self._rang -= 1
        self._poser(self._saisies[self._rang])

    def _suivant(self, _=None):
        """Flèche Bas : redescend, puis rend le brouillon mis de côté."""
        if self._rang is None:
            return
        self._rang += 1
        if self._rang >= len(self._saisies):
            self._rang = None
            return self._poser(self._brouillon)
        self._poser(self._saisies[self._rang])

    @property
    def TexteAttente(self):
        """Phrase d'attente et chronomètre, recomposés à chaque seconde."""
        if _attente is None:
            return self._phrase
        return _attente.libelle(self._phrase, self._secondes)

    @TexteAttente.setter
    def TexteAttente(self, valeur):
        """``None`` = laisser tourner les phrases ; une chaîne = la figer."""
        self._phrase = valeur or self._phrase_neuve()
        self._fixe = bool(valeur)
        self.notify_property('TexteAttente')

    def _phrase_neuve(self):
        if _attente is None:
            return self.ATTENTE_DEFAUT
        return _attente.autre(self._phrase)

    @property
    def EnAttente(self):
        """Vrai pendant que le fournisseur réfléchit : pilote l'animation."""
        return self._en_attente

    @EnAttente.setter
    def EnAttente(self, valeur):
        self._en_attente = bool(valeur)
        # Le chronomètre repart de zéro à chaque attente : c'est le temps de
        # CETTE réponse qui intéresse, pas le cumul de la session.
        self._secondes = 0
        if self._en_attente:
            self._demarrer_horloge()
        else:
            self._arreter_horloge()
        self.notify_property('EnAttente')
        self.notify_property('TexteAttente')
        # Le bouton Envoyer suit CanExecute : sans ce coup de semonce, il ne
        # se réactive qu'au prochain mouvement de souris.
        if CommandManager is not None:
            try:
                CommandManager.InvalidateRequerySuggested()
            except Exception:
                pass

    # --- chronomètre de l'attente ----------------------------------------

    def _tic(self, *_args):
        """Une seconde de plus. Appelé par le DispatcherTimer, donc sur le
        fil d'interface : rien d'autre ne doit toucher ces compteurs."""
        self._secondes += 1
        if not self._fixe and _attente is not None:
            if self._secondes % _attente.TOURNE == 0:
                self._phrase = _attente.autre(self._phrase)
        self.notify_property('TexteAttente')

    def _demarrer_horloge(self):
        # Créée à la première attente, pas à la construction du VM : rien de
        # WPF ne se fabrique pendant que Revit bâtit le volet.
        if DispatcherTimer is None or TimeSpan is None:
            return                     # hors .NET : pas de chronomètre
        if self._horloge is None:
            self._horloge = DispatcherTimer()
            self._horloge.Interval = TimeSpan.FromSeconds(1)
            self._horloge.Tick += self._tic
        self._horloge.Start()

    def _arreter_horloge(self):
        if self._horloge is not None:
            self._horloge.Stop()

    # --- bandeau d'alerte : le lien avec la maquette ----------------------

    @property
    def Alerte(self):
        """Ce qui empêche les outils de marcher, '' quand tout va bien."""
        return self._alerte

    @Alerte.setter
    def Alerte(self, valeur):
        self._alerte = valeur or ''
        if not self._alerte:
            self._grave = False
        self.notify_property('Alerte')
        self.notify_property('AlerteVisible')
        self.notify_property('AlerteGrave')

    @property
    def AlerteVisible(self):
        return bool(self._alerte)

    @property
    def AlerteGrave(self):
        """Vrai pour un échec d'outil : le bandeau passe en rouge.

        Un état (« aucun document ouvert ») et un échec (« AttributeError »)
        ne se lisent pas pareil — le premier décrit, le second s'est produit.
        """
        return self._grave

    def _toast(self, texte):
        """Affiche un échec d'outil en haut du volet, et le fait expirer.

        Le modèle reçoit l'erreur et en fait ce qu'il veut, parfois rien :
        sans ça, un outil qui casse est invisible pour l'architecte.
        """
        if not texte:
            return
        self._alerte = texte
        self._grave = True
        self.notify_property('Alerte')
        self.notify_property('AlerteVisible')
        self.notify_property('AlerteGrave')
        self._armer_expiration()

    def _armer_expiration(self):
        # Même prudence que le chronomètre : créé à la première utilisation,
        # jamais à la construction du VM, et il tique sur le fil d'interface.
        if DispatcherTimer is None or TimeSpan is None:
            return                     # hors .NET : le toast reste affiché
        if self._expiration is None:
            self._expiration = DispatcherTimer()
            self._expiration.Interval = TimeSpan.FromSeconds(self.DUREE_TOAST)
            self._expiration.Tick += self._expirer
        self._expiration.Stop()        # relance le décompte à chaque toast
        self._expiration.Start()

    def _expirer(self, *_args):
        if self._expiration is not None:
            self._expiration.Stop()
        # On ne vide pas aveuglément : l'état de la maquette, lui, reste vrai.
        self.Alerte = ''
        self._rafraichir_alerte()

    def _rafraichir_alerte(self):
        """Relit la dernière raison connue. AUCUN appel réseau ici.

        On ne relance pas de vérification : le client vient d'interroger la
        maquette pour bâtir son catalogue d'outils, la réponse est fraîche.
        Un second fil de fond qui repart taper le même serveur, c'était une
        requête concurrente de plus — et deux requêtes simultanées font
        s'écraser les handlers partagés du serveur de routes pyRevit.
        """
        if revit_outils is None:
            return
        if not self._grave:            # ne pas écraser un toast en cours
            self.Alerte = revit_outils.derniere_raison()

    def _signaler_echec(self):
        """Un outil en échec laisse une BULLE, pas seulement un bandeau.

        « L'erreur n'apparaît pas à chaque fois » vient de là : un bandeau
        expire au bout de 15 s, se fait écraser par l'état de la maquette et
        disparaît au message suivant. Une interface transitoire ne peut pas
        être le seul canal d'une erreur. La bulle, elle, reste dans le fil,
        se relit et se colle dans un rapport.
        """
        if revit_outils is None:
            return
        echec = revit_outils.dernier_echec()
        if not echec:
            return
        self._dire('Outil en échec — {0}'.format(echec))
        self._toast(echec)

    @property
    def _client(self):
        if self._client_injecte is not None:
            return self._client_injecte
        return self._config.client

    @property
    def Statut(self):
        """Fil d'Ariane : fournisseur · connexion · modèle."""
        provider = self._config.provider
        client = self._client
        if client is None:
            return '{0} — pas encore branché'.format(provider)
        if not client.pret():
            return '{0} · {1} — {2}'.format(
                provider, self._config.connexion, client.raison())
        return '{0} · {1} · {2}'.format(
            provider, self._config.connexion,
            self._config.modele or MODELE_DEFAUT)

    # --- liste en place : autocomplétion, ou assistant de connexion --------

    @property
    def SuggestionsVisibles(self):
        return len(self.Suggestions) > 0

    def _fermer_liste(self):
        self._etape = None
        self.Suggestions.Clear()
        self.notify_property('SuggestionsVisibles')

    def _rafraichir_suggestions(self):
        # Une étape de l'assistant attend un choix : la frappe ne la balaie
        # pas, contrairement à l'autocomplétion.
        if self._etape is not None:
            return
        self.Suggestions.Clear()
        debut = self._saisie
        # Uniquement pendant la frappe du nom : dès qu'une espace suit, la
        # commande est complète et la liste n'a plus rien à proposer.
        if debut.startswith('/') and ' ' not in debut:
            prefixe = debut[1:].lower()
            for nom in sorted(self.COMMANDES):
                if nom.startswith(prefixe):
                    self.Suggestions.Add(
                        SuggestionVM(nom, self.COMMANDES[nom][0]))
        self.notify_property('SuggestionsVisibles')

    # --- assistant de connexion : fournisseur → connexion → modèle --------

    ETAPES = ('fournisseurs', 'connexions', 'modeles')

    def _ouvrir(self, etape):
        """Remplace la liste en place par les entrées de l'étape."""
        self._etape = etape
        self.Suggestions.Clear()
        for suggestion in self._entrees(etape):
            self.Suggestions.Add(suggestion)
        self.notify_property('SuggestionsVisibles')

    def _entrees(self, etape):
        if etape == 'accord':
            # « Refuser » en tête, et ce n'est pas cosmétique : Tab complète
            # sur la PREMIÈRE entrée retenable. Une frappe distraite ne doit
            # pas pousser une synchronisation sur le central.
            return [SuggestionVM('refuser', 'ne rien écrire dans la maquette',
                                 libelle='Refuser'),
                    SuggestionVM('accorder', 'laisser l\'outil s\'exécuter',
                                 libelle='Accorder')]
        if etape == 'depot':
            # Confirmation d'un DWG lâché. Elle réutilise la liste en place
            # plutôt qu'un bouton dans la bulle : même mécanique que
            # /connect, aucun gabarit de message à toucher — et ce gabarit
            # a déjà fait tomber Revit trois fois (cf. OpenArchiPanel.xaml).
            return [SuggestionVM('lier', 'poser le DWG dans la vue active',
                                 libelle='Lier'),
                    SuggestionVM('annuler', 'ne rien écrire dans la maquette',
                                 libelle='Annuler')]
        if etape == 'fournisseurs':
            return [SuggestionVM(nom, self._resume(nom), libelle=nom,
                                 actif=nom in ACTIFS)
                    for nom, _connexions in CATALOGUE]
        if etape == 'connexions':
            return [SuggestionVM(nom, description, libelle=nom,
                                 actif=client is not None)
                    for nom, description, client
                    in connexions_de(self._config.provider)]
        # Un client qui n'expose pas ses modèles n'en laisse qu'un : le sien.
        modeles = self._client.modeles() if self._client else ()
        if not modeles:
            return [SuggestionVM(MODELE_DEFAUT, 'le fournisseur choisit',
                                 libelle=MODELE_DEFAUT)]
        return [SuggestionVM(nom, '', libelle=nom) for nom in modeles]

    @staticmethod
    def _resume(provider):
        """Ce qui est branché chez un fournisseur, vu depuis la liste."""
        branchees = [nom for nom, _d, client in connexions_de(provider)
                     if client is not None]
        return ' · '.join(branchees) if branchees else 'pas encore branché'

    def _retour(self, _=None):
        """Échap : remonte d'une étape, ou referme la liste."""
        if self._etape is None:
            return
        # 'depot' et 'accord' ne sont pas des étapes de /connect : Échap y
        # refuse, il ne remonte nulle part.
        if self._etape == 'depot':
            return self._annuler_depot()
        if self._etape == 'accord':
            return self._repondre_accord(False)
        rang = self.ETAPES.index(self._etape)
        if rang == 0:
            self._fermer_liste()
        else:
            self._ouvrir(self.ETAPES[rang - 1])

    def _choisir(self, suggestion=None):
        if suggestion is None:
            return
        # Le XAML désactive déjà le bouton ; Tab passe par ici sans lui.
        if not suggestion.Actif:
            return
        if self._etape == 'accord':
            return self._repondre_accord(suggestion.Nom == 'accorder')
        if self._etape == 'depot':
            return (self._lier_depot() if suggestion.Nom == 'lier'
                    else self._annuler_depot())
        if self._etape == 'fournisseurs':
            return self._choisir_provider(suggestion.Nom)
        if self._etape == 'connexions':
            return self._choisir_connexion(suggestion.Nom)
        if self._etape == 'modeles':
            return self._choisir_modele(suggestion.Nom)
        # Liste des commandes : cliquer exécute, sans passer par le champ.
        self.Saisie = '/{0}'.format(suggestion.Nom)
        self._envoyer()

    def _choisir_provider(self, provider):
        self._config.appliquer(provider)
        self.notify_property('Statut')
        self._ouvrir('connexions')

    def _choisir_connexion(self, connexion):
        self._config.appliquer_connexion(connexion)
        self.notify_property('Statut')
        client = self._client
        pret = client.pret()
        _log.info('connexion %s | pret=%s', connexion, pret)
        if pret:
            return self._ouvrir('modeles')
        # Pas prêt : soit le client sait ouvrir le navigateur — c'est le
        # moment de le faire — soit il ne reste qu'à dire ce qui manque.
        self._fermer_liste()
        try:
            ouverture = client.connecter()
            _log.info('connecter() -> %s', ouverture)
        except Exception as e:
            _log.exception('connecter() a levé')
            return self._dire('{0}'.format(e))
        if not ouverture:
            return self._dire(client.raison())
        self._dire(ouverture)
        # Le navigateur est ouvert : on guette la fin de la connexion pour
        # enchaîner tout seul, plutôt que d'exiger un second /connect.
        attente = getattr(client, 'attendre_connexion', None)
        if attente is None:
            return
        self.TexteAttente = 'connexion…'
        self.EnAttente = True
        self._en_arriere_plan(attente, self._sur_connexion)

    def _sur_connexion(self, ouverte):
        self.EnAttente = False
        self.notify_property('Statut')
        if not ouverte:
            return self._dire('Connexion non aboutie. /connect pour réessayer.')
        self._dire('Connecté. Choisir un modèle.')
        self._ouvrir('modeles')

    def _choisir_modele(self, modele):
        self._config.appliquer_modele(
            None if modele == MODELE_DEFAUT else modele)
        self._fermer_liste()
        self.notify_property('Statut')
        self._dire('Connecté — {0}'.format(self.Statut))

    def _dire(self, texte, duree=''):
        self.Messages.Add(MessageVM('OpenArchi', texte, False, duree))

    def _duree_reflexion(self):
        """« réfléchi 42 s », ou '' si ça n'a pas duré une seconde."""
        if _attente is None or self._secondes <= 0:
            return ''
        return 'réfléchi {0}'.format(_attente.duree(self._secondes))

    def _completer(self, _=None):
        # Tab : complète sur la première proposition retenable, comme un shell
        # — les entrées grisées sont sautées.
        for suggestion in self.Suggestions:
            if suggestion.Actif:
                self._choisir(suggestion)
                return

    # --- envoi -----------------------------------------------------------

    def _peut_envoyer(self, _=None):
        return bool(self._saisie.strip()) and not self._en_attente

    def _envoyer(self, _=None):
        texte = self._saisie.strip()
        if not texte or self._en_attente:
            return
        # Envoyer abandonne un choix de fournisseur en cours, et referme un
        # toast d'erreur : il parlait du message précédent.
        self._fermer_liste()
        if self._grave:
            self.Alerte = ''
        self.Messages.Add(MessageVM('Moi', texte, True))
        # Retenu AVANT de vider : la flèche Haut doit le retrouver, commande
        # comme message libre — c'est surtout pour rejouer une commande.
        self._retenir(texte)
        self._brouillon = ''
        self.Saisie = ''
        # Une commande répond sur place et touche l'interface (listes,
        # réglages) : elle doit rester sur le fil d'interface.
        if analyser(texte).est_commande:
            return self._dire(self.repondre(texte))
        # None : on laisse les phrases tourner. Une valeur les figerait.
        self.TexteAttente = None
        self.EnAttente = True
        self._en_arriere_plan(lambda: self.repondre(texte), self._sur_reponse)

    # --- pièces jointes --------------------------------------------------

    def deposer(self, chemins):
        """Fichiers lâchés sur le panneau. Trois voies, une par format.

        Le format décide, parce que leurs plafonds n'ont rien à voir :

        - **DWG** — aucun modèle ne lit du DWG. La seule chose qui sache
          ouvrir ce fichier ici, c'est Revit : on propose de le lier, et ce
          sont les outils ``rvt`` qui le décriront ensuite. Écrit dans la
          maquette, donc on demande d'abord.
        - **PDF et images** — partent en base64 au fournisseur, ce que seule
          la connexion « Clé API » accepte. Ailleurs : refus annoncé, pas un
          silence.
        - **le reste** — s'il se lit en texte, il se lit en texte.

        Aucune de ces voies n'envoie de message : le dépôt se pose dans la
        conversation, c'est la question suivante qui l'emmène. Un glissé de
        travers ne doit ni facturer un tour ni toucher la maquette.
        """
        for chemin in (chemins or []):
            try:
                self._deposer_un(chemin)
            except Exception as e:
                _log.exception('dépôt de %s', chemin)
                self._dire('Pièce jointe illisible : {0}'.format(e))

    def _deposer_un(self, chemin):
        nom = os.path.basename(chemin)
        if os.path.isdir(chemin):
            return self._dire(
                '{0} : c\'est un dossier, pas un fichier.'.format(nom))
        extension = os.path.splitext(nom)[1].lower()
        if extension == '.dwg':
            return self._proposer_dwg(chemin)
        if extension == '.pdf':
            return self._joindre_binaire(chemin, 'application/pdf',
                                         self.PDF_MAX, 'PDF')
        if extension in self.IMAGES:
            return self._joindre_binaire(chemin, self.IMAGES[extension],
                                         self.IMAGE_MAX, 'image')
        return self._joindre_texte(chemin)

    # --- texte -----------------------------------------------------------

    def _joindre_texte(self, chemin):
        nom, texte, ennui = self._lire_piece(chemin)
        if texte is None:
            return self._dire('{0} : {1}'.format(nom, ennui))
        self.Messages.Add(MessageVM(
            'Moi',
            'Pièce jointe « {0} » :\n\n{1}'.format(nom, texte),
            True,
            # Pas d'emoji trombone : U+1F4CE est hors du plan de base, et on
            # ne sait pas ce qu'en fait IronPython 2.7 à la lecture du
            # source. Du texte, ça s'affiche partout.
            affiche='Pièce jointe : {0} — {1}'.format(nom, ennui)))

    # --- PDF et images -----------------------------------------------------

    def _joindre_binaire(self, chemin, media, plafond, genre):
        """Le fichier part tel quel au fournisseur, en base64.

        Pas d'extraction locale : pyRevit tourne sur un CPython stdlib seul,
        et un extracteur écrit à la main rend n'importe quoi sur un PDF
        d'architecte (polices sous-ensemblées, CMap). Mieux vaut ne pas
        joindre que joindre du charabia — et une image, de toute façon, ne
        s'extrait pas : elle se regarde.
        """
        nom = os.path.basename(chemin)
        if self._config.connexion != CLE_API:
            return self._dire(
                '{0} : un fichier {1} ne passe que par la connexion « {2} ». '
                '« {3} » n\'accepte que du texte — /connect pour changer, '
                'ou lâchez plutôt un export texte.'.format(
                    nom, genre, CLE_API,
                    self._config.connexion or 'celle en cours'))
        taille = os.path.getsize(chemin)
        if taille > plafond:
            return self._dire(
                '{0} : {1}, au-delà du plafond de {2}. Une pièce repart au '
                'fournisseur à CHAQUE message : au-delà, la facture grimpe '
                'sans prévenir.'.format(nom, _poids(taille),
                                        _poids(plafond)))
        with open(chemin, 'rb') as fichier:
            brut = fichier.read()
        self.Messages.Add(MessageVM(
            'Moi', 'Pièce jointe « {0} » ({1}).'.format(nom, genre), True,
            affiche='Pièce jointe : {0} — {1}'.format(nom, _poids(taille)),
            piece={'nom': nom, 'media': media,
                   'b64': base64.b64encode(brut).decode('ascii')}))

    def _pieces(self):
        """Les fichiers joints de la conversation, pour le prochain appel.

        L'API est sans mémoire : une pièce repart à chaque tour, sinon le
        modèle l'a perdue. C'est le protocole, pas un oubli — et c'est ce qui
        justifie ``PDF_MAX``.
        """
        return [message.Piece for message in list(self.Messages)
                if getattr(message, 'Piece', None)]

    # --- DWG ---------------------------------------------------------------

    def _proposer_dwg(self, chemin):
        """Lier écrit dans la maquette : on demande avant, jamais après."""
        self._depot = chemin
        self._dire('{0} — {1}. Aucun modèle ne lit le DWG : Revit peut le '
                   'lier dans la vue active, et le modèle l\'interrogera '
                   'ensuite comme le reste de la maquette.'.format(
                       os.path.basename(chemin),
                       _poids(os.path.getsize(chemin))))
        self._ouvrir('depot')

    def _lier_depot(self):
        chemin, self._depot = self._depot, None
        self._fermer_liste()
        if not chemin:
            return
        if revit_outils is None:
            return self._dire('Hors Revit : rien à lier.')
        self.TexteAttente = 'liaison du DWG…'
        self.EnAttente = True
        self._en_arriere_plan(
            lambda: revit_outils.executer('revit_lier_dwg',
                                          {'chemin': chemin}),
            self._sur_dwg)

    def _sur_dwg(self, brut):
        self.EnAttente = False
        # Passe par _dire : le résultat devient un tour de la conversation,
        # donc le modèle sait que le DWG est là sans qu'on le lui répète.
        self._dire(_resume_dwg(brut))
        self._signaler_echec()

    def _annuler_depot(self):
        nom = os.path.basename(self._depot or '')
        self._depot = None
        self._fermer_liste()
        self._dire('{0} : rien lié.'.format(nom))

    def _lire_piece(self, chemin):
        """``(nom, texte, mention)``. ``texte`` à ``None`` = refusée.

        Détection du binaire à l'octet nul, comme git : pas de liste
        d'extensions à tenir à jour, et un .md sans extension passe quand
        même. Un .docx y est vu binaire — c'est juste, on ne sait pas
        l'extraire. Les PDF et les images, eux, n'arrivent jamais ici :
        ``_deposer_un`` les a aiguillés avant, sur leur extension.
        """
        nom = os.path.basename(chemin)
        if os.path.isdir(chemin):
            return nom, None, 'c\'est un dossier, pas un fichier.'
        with open(chemin, 'rb') as fichier:
            brut = fichier.read(self.PIECE_MAX + 1)
        if b'\x00' in brut:
            return (nom, None,
                    'format binaire, et on ne sait pas l\'extraire — du '
                    'texte, un PDF ou une image passeraient.')
        tronque = len(brut) > self.PIECE_MAX
        texte = brut[:self.PIECE_MAX].decode('utf-8', 'replace')
        if tronque:
            texte += '\n\n[…] pièce tronquée à {0} ko.'.format(
                self.PIECE_MAX // 1024)
        mention = '{0} ko{1}'.format(max(1, len(brut) // 1024),
                                     ', tronqué' if tronque else '')
        return nom, texte, mention

    def _sur_reponse(self, reponse):
        # Lu AVANT que EnAttente remette le compteur à zéro.
        duree = self._duree_reflexion()
        self.EnAttente = False
        self._dire(reponse, duree)
        # L'échec d'abord : il vient de se produire, l'état peut attendre.
        self._signaler_echec()
        # Le document a pu être fermé entre deux messages : le bandeau ne doit
        # pas rester périmé, dans un sens comme dans l'autre.
        self._rafraichir_alerte()

    def _sur_interface(self, travail):
        """Exécute ``travail`` sur le fil d'interface, d'où qu'on l'appelle.

        Hors .NET, sur place : le VM reste synchrone et se teste sans rien
        simuler.
        """
        if Action is None or self._dispatcher is None:
            return _proteger(travail)
        try:
            self._dispatcher.Invoke(Action(lambda: _proteger(travail)))
        except Exception:
            _log.exception('retour sur le fil d\'interface')

    def _en_arriere_plan(self, travail, suite):
        """``travail`` hors du fil d'interface, ``suite`` de retour dessus.

        Sans .NET (tests hors Revit), tout s'exécute sur place : le VM reste
        synchrone et se teste sans rien simuler.
        """
        if Thread is None or self._dispatcher is None:
            resultat = travail()
            return _proteger(lambda: suite(resultat))

        def _courir():
            try:
                resultat = travail()
            except Exception as e:                # ceinture : _conversation
                _log.exception('travail de fond')  # attrape déjà tout
                resultat = '{0}'.format(e)
            self._sur_interface(lambda: suite(resultat))

        fil = Thread(ThreadStart(_courir))
        # Sans cela, un appel en cours retiendrait la fermeture de Revit.
        fil.IsBackground = True
        fil.Start()

    # --- ce que le fil de fond a le droit de dire -------------------------

    def _avancement(self, phrase):
        """Remplace la blague d'attente par ce qui se passe vraiment.

        Appelé depuis la boucle d'outils, donc d'un fil de fond : toucher
        ``TexteAttente`` d'ici notifierait une liaison hors du fil
        d'interface, et c'est ce qui fait tomber Revit.
        """
        self._sur_interface(lambda: setattr(self, 'TexteAttente', phrase))

    def _confirmer(self, nom, donnees):
        """Demande l'accord de l'architecte avant un outil irréversible.

        Appelé depuis le fil de fond pendant la boucle d'outils : on pose la
        question sur le fil d'interface, et on attend ICI. Bloquer ce fil-là
        est sans danger — c'est celui de l'appel au modèle, pas celui de
        Revit, qui reste rendu à la main.

        Le délai n'est pas une politesse : sans lui, un panneau refermé sans
        répondre laisserait un fil suspendu pour toujours.
        """
        signal = threading.Event()
        reponse = {}
        self._sur_interface(
            lambda: self._poser_question(nom, donnees, reponse, signal))
        if Thread is None or self._dispatcher is None:
            # Hors .NET, `_sur_interface` s'exécute SUR PLACE : la question
            # vient d'être posée sur le fil même qui attendrait la réponse.
            # Personne ne peut cliquer — attendre serait cinq minutes
            # d'interblocage, alors on referme sur un refus.
            self._repondre_accord(False)
        else:
            signal.wait(self.DELAI_ACCORD)
        # On lit le dictionnaire, pas le retour de wait() : une expiration
        # vaut un refus, et c'est le même chemin.
        return bool(reponse.get('oui'))

    def _poser_question(self, nom, donnees, reponse, signal):
        self._question = (reponse, signal)
        self._dire('{0} est IRRÉVERSIBLE : aucun Ctrl+Z ne le défait. '
                   'Arguments : {1}'.format(nom, donnees or 'aucun'))
        self.TexteAttente = 'j\'attends votre accord…'
        self._ouvrir('accord')

    def _repondre_accord(self, oui):
        question, self._question = self._question, None
        self._fermer_liste()
        if question is None:
            return
        reponse, signal = question
        reponse['oui'] = bool(oui)
        self._dire('Accordé.' if oui else 'Refusé — rien n\'a été écrit.')
        # None : les phrases d'attente repartent, le modèle reprend la main.
        self.TexteAttente = None
        signal.set()

    def repondre(self, texte):
        analyse = analyser(texte)
        if analyse.est_commande:
            nom, execution = analyse.commande, None
            if nom in self.COMMANDES:
                execution = self.COMMANDES[nom][1]
            if execution is None:
                return "Commande /{0} inconnue.\n{1}".format(
                    nom, self._commande_aide(''))
            return execution(analyse.arguments)
        return self._conversation(analyse)

    # Appelé depuis un fil de fond (cf. _en_arriere_plan) : ne toucher ni
    # Messages ni une propriété liée d'ici.
    def _conversation(self, analyse):
        client = self._client
        if client is None:
            return ('{0} : pas encore branché. /connect pour en choisir un '
                    'autre.'.format(self._config.provider))
        try:
            # pieces=, avancement= et confirmer= sont facultatifs dans le
            # contrat : les clients qui n'en font rien les avalent par leur
            # **_kwargs, et _joindre_binaire a déjà refusé le dépôt chez ceux
            # qui ne portent pas de fichier.
            return client.repondre(self._historique(analyse.texte),
                                   modele=self._config.modele,
                                   pieces=self._pieces(),
                                   avancement=self._avancement,
                                   confirmer=self._confirmer)
        except Exception as e:
            _log.exception('repondre() a échoué')
            return '{0} : {1}'.format(self._config.provider, e)

    def _historique(self, texte):
        """Conversation à plat pour l'API, message d'accueil exclu."""
        couples = [('user' if message.DeUtilisateur else 'assistant',
                    message.Texte)
                   for message in list(self.Messages)[1:]]
        # repondre() peut être appelé sans passer par _envoyer : on ne compte
        # le message courant qu'une fois.
        if couples[-1:] != [('user', texte)]:
            couples.append(('user', texte))
        return couples

    # --- commandes -------------------------------------------------------

    def _commande_aide(self, _arguments):
        lignes = ['Commandes disponibles :']
        for nom in sorted(self.COMMANDES):
            lignes.append('  /{0} — {1}'.format(nom, self.COMMANDES[nom][0]))
        return '\n'.join(lignes)

    def _commande_vider(self, _arguments):
        """Efface la conversation — et avec elle ses pièces jointes.

        C'est la seule porte de sortie de trois impasses : la pièce lâchée de
        travers qui repart dans CHAQUE requête, la facture qui monte à mesure
        que l'historique s'allonge, et le « maximum context length » qui finit
        par tout bloquer. L'API est sans mémoire : seul ce qu'on lui renvoie
        existe, donc oublier est une opération locale et immédiate.
        """
        pieces = len(self._pieces())
        self.Messages.Clear()
        self.Messages.Add(MessageVM('OpenArchi', self.ACCUEIL, False))
        if pieces:
            return ('Conversation vidée — {0} pièce(s) jointe(s) '
                    'décrochée(s).'.format(pieces))
        return 'Conversation vidée.'

    def _commande_routes(self, _arguments):
        """Coche « Routes » dans pyRevit, au lieu de décrire où cliquer."""
        if routes418 is None:
            return 'Hors Revit : rien à cocher.'
        if routes418.base():
            return 'Le serveur de routes répond déjà : {0}'.format(
                routes418.base())
        return routes418.activer()

    def _commande_connect(self, _arguments):
        # Pas de fenêtre : on réutilise la liste en place au-dessus du champ,
        # comme le /connect d'opencode dans son terminal.
        self._ouvrir('fournisseurs')
        return 'Choisir un fournisseur. Actuel : {0}'.format(self.Statut)

    def _commande_logout(self, _arguments):
        client = self._client
        if client is None:
            return 'Aucune connexion active.'
        try:
            message = client.deconnecter()
        except Exception as e:
            _log.exception('deconnecter() a levé')
            return '{0} : {1}'.format(self._config.provider, e)
        self.notify_property('Statut')
        return message or 'Rien à fermer pour cette connexion.'

    def _commande_journal(self, arguments):
        """`/journal` affiche la fin du fichier, `/journal vider` le remet à zéro.

        Le texte des bulles est sélectionnable : ce qui s'affiche ici se colle
        tel quel dans un rapport de bug.
        """
        if arguments.strip().lower() in ('vider', 'clear'):
            _journal.vider()
            return 'Journal vidé.'
        fin = _journal.lire()
        return '{0}\n\n{1}'.format(
            _journal.chemin() or 'journal indisponible',
            fin or '(vide — rejouer l\'action à déboguer)')

    def _commande_model(self, arguments):
        client = self._client
        if client is None or not client.pret():
            return 'Aucune connexion active. /connect d\'abord.'
        # `/model <nom>` impose un modèle sans passer par la liste : le CLI
        # n'expose aucun catalogue, c'est la seule façon d'en viser un autre
        # que son défaut.
        nom = arguments.strip()
        if nom:
            self._config.appliquer_modele(nom)
            self.notify_property('Statut')
            return 'Modèle : {0}'.format(nom)
        self._ouvrir('modeles')
        message = 'Choisir un modèle. Actuel : {0}'.format(
            self._config.modele or MODELE_DEFAUT)
        if not client.modeles():
            message += ('\nCette connexion n\'expose pas de catalogue : '
                        '/model <nom> pour en imposer un.')
        return message
