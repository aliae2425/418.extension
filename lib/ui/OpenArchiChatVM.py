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
    from System import Action
    from System.Threading import Thread, ThreadStart
    from System.Windows.Threading import Dispatcher
except Exception:
    Action = Thread = ThreadStart = Dispatcher = None

try:
    from System.Windows.Input import CommandManager
except Exception:
    CommandManager = None


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

    def __init__(self, auteur, texte, de_utilisateur):
        try:
            BaseViewModel.__init__(self)
        except Exception:
            pass
        self.Auteur = auteur
        self.Texte = texte
        self.DeUtilisateur = bool(de_utilisateur)
        self.Alignement = 'Right' if de_utilisateur else 'Left'


class OpenArchiChatVM(BaseViewModel):
    ACCUEIL = ("Panneau OpenArchi prêt. /connect pour choisir le fournisseur. "
               "#{Nom} pour citer un élément.")
    ATTENTE_DEFAUT = 'réflexion…'

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
        self._texte_attente = self.ATTENTE_DEFAUT
        # Capturé ici : le VM est construit sur le fil d'interface, et c'est
        # le seul par lequel Messages et les notifications peuvent passer.
        self._dispatcher = (Dispatcher.CurrentDispatcher
                            if Dispatcher is not None else None)
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
        self.Messages.Add(MessageVM('OpenArchi', self.ACCUEIL, False))

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
        self.notify_property('Saisie')
        self._rafraichir_suggestions()

    @property
    def TexteAttente(self):
        return self._texte_attente

    @TexteAttente.setter
    def TexteAttente(self, valeur):
        self._texte_attente = valeur or self.ATTENTE_DEFAUT
        self.notify_property('TexteAttente')

    @property
    def EnAttente(self):
        """Vrai pendant que le fournisseur réfléchit : pilote l'animation."""
        return self._en_attente

    @EnAttente.setter
    def EnAttente(self, valeur):
        self._en_attente = bool(valeur)
        self.notify_property('EnAttente')
        # Le bouton Envoyer suit CanExecute : sans ce coup de semonce, il ne
        # se réactive qu'au prochain mouvement de souris.
        if CommandManager is not None:
            try:
                CommandManager.InvalidateRequerySuggested()
            except Exception:
                pass

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

    def _dire(self, texte):
        self.Messages.Add(MessageVM('OpenArchi', texte, False))

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
        # Envoyer abandonne un choix de fournisseur en cours.
        self._fermer_liste()
        self.Messages.Add(MessageVM('Moi', texte, True))
        self.Saisie = ''
        # Une commande répond sur place et touche l'interface (listes,
        # réglages) : elle doit rester sur le fil d'interface.
        if analyser(texte).est_commande:
            return self._dire(self.repondre(texte))
        self.TexteAttente = self.ATTENTE_DEFAUT
        self.EnAttente = True
        self._en_arriere_plan(lambda: self.repondre(texte), self._sur_reponse)

    def _sur_reponse(self, reponse):
        self.EnAttente = False
        self._dire(reponse)

    def _en_arriere_plan(self, travail, suite):
        """``travail`` hors du fil d'interface, ``suite`` de retour dessus.

        Sans .NET (tests hors Revit), tout s'exécute sur place : le VM reste
        synchrone et se teste sans rien simuler.
        """
        if Thread is None or self._dispatcher is None:
            return suite(travail())

        def _courir():
            try:
                resultat = travail()
            except Exception as e:                # ceinture : _conversation
                _log.exception('travail de fond')  # attrape déjà tout
                resultat = '{0}'.format(e)
            try:
                self._dispatcher.Invoke(Action(lambda: suite(resultat)))
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
