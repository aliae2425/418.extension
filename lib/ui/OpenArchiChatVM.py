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
        self.Messages = self._nouvelle_liste()
        # Déclarées AVANT toute écriture de Saisie : son setter rafraîchit
        # l'autocomplétion, qui lit COMMANDES et Suggestions.
        self.COMMANDES = {
            'connect': ('choisir fournisseur, connexion et modèle',
                        self._commande_connect),
            'model': ('changer de modèle sur la connexion en cours',
                      self._commande_model),
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
            ouverture = '{0}'.format(e)
        self._dire(ouverture or client.raison())

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
        return bool(self._saisie.strip())

    def _envoyer(self, _=None):
        texte = self._saisie.strip()
        if not texte:
            return
        # Envoyer abandonne un choix de fournisseur en cours.
        self._fermer_liste()
        self.Messages.Add(MessageVM('Moi', texte, True))
        self.Saisie = ''
        self.Messages.Add(MessageVM('OpenArchi', self.repondre(texte), False))

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

    # ponytail: appel bloquant, Revit se fige le temps de la réponse. Passer
    # en thread + Dispatcher.Invoke si l'attente devient gênante — le CLI est
    # sensiblement plus lent que l'API, c'est là que ça se verra d'abord.
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

    def _commande_model(self, _arguments):
        client = self._client
        if client is None or not client.pret():
            return 'Aucune connexion active. /connect d\'abord.'
        self._ouvrir('modeles')
        return 'Choisir un modèle. Actuel : {0}'.format(
            self._config.modele or MODELE_DEFAUT)
