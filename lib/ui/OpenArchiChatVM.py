# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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

_log = _journal.journal('chat')

try:
    from ui.OpenArchiConfig import (OpenArchiConfig, CATALOGUE, ACTIFS,
                                    connexions_de, MODELE_DEFAUT)
except Exception:
    from lib.ui.OpenArchiConfig import (OpenArchiConfig, CATALOGUE, ACTIFS,
                                        connexions_de, MODELE_DEFAUT)

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

    def __init__(self, auteur, texte, de_utilisateur, duree=''):
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
        self.TexteAffiche = _texte_nu(texte)
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
    # Assez pour lire une erreur technique, assez peu pour ne pas rester en
    # travers du volet une fois la question suivante posée.
    DUREE_TOAST = 15

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
            'aide': ('lister les commandes disponibles', self._commande_aide),
        }
        self.Suggestions = self._nouvelle_liste()
        # La liste en place sert deux usages : l'autocomplétion pendant la
        # frappe, et l'assistant de /connect. Ses étapes s'enchaînent dans
        # l'ordre ci-dessous ; Échap remonte d'un cran.
        self._etape = None
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
        # Un échec d'outil prime sur l'état : il vient de se produire.
        echec = revit_outils.dernier_echec()
        if echec:
            return self._toast(echec)
        if not self._grave:            # ne pas écraser un toast en cours
            self.Alerte = revit_outils.derniere_raison()

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

    def _sur_reponse(self, reponse):
        # Lu AVANT que EnAttente remette le compteur à zéro.
        duree = self._duree_reflexion()
        self.EnAttente = False
        self._dire(reponse, duree)
        # Le document a pu être fermé entre deux messages : le bandeau ne doit
        # pas rester périmé, dans un sens comme dans l'autre.
        self._rafraichir_alerte()

    def _en_arriere_plan(self, travail, suite):
        """``travail`` hors du fil d'interface, ``suite`` de retour dessus.

        Sans .NET (tests hors Revit), tout s'exécute sur place : le VM reste
        synchrone et se teste sans rien simuler.
        """
        def _sur_le_fil(resultat):
            # ENVELOPPE OBLIGATOIRE. Ce qui s'exécute ici touche des
            # propriétés liées et Messages : une exception qui s'en échappe
            # part non rattrapée sur le fil d'interface de Revit, et Revit
            # meurt. C'est arrivé — PresentationCore, InvalidOperationException.
            # Une bulle d'erreur vaut mieux qu'une session perdue.
            try:
                suite(resultat)
            except Exception:
                _log.exception('suite() sur le fil d\'interface')

        if Thread is None or self._dispatcher is None:
            return _sur_le_fil(travail())

        def _courir():
            try:
                resultat = travail()
            except Exception as e:                # ceinture : _conversation
                _log.exception('travail de fond')  # attrape déjà tout
                resultat = '{0}'.format(e)
            try:
                self._dispatcher.Invoke(Action(lambda: _sur_le_fil(resultat)))
            except Exception:
                _log.exception('retour sur le fil d\'interface')

        fil = Thread(ThreadStart(_courir))
        # Sans cela, un appel en cours retiendrait la fermeture de Revit.
        fil.IsBackground = True
        fil.Start()

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
            return client.repondre(self._historique(analyse.texte),
                                   modele=self._config.modele)
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
