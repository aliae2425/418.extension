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
    from ui.OpenArchiConfigVM import OpenArchiConfig
except Exception:
    from lib.ui.OpenArchiConfigVM import OpenArchiConfig

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
    """Une entrée de l'autocomplétion des commandes."""

    def __init__(self, nom, description):
        try:
            BaseViewModel.__init__(self)
        except Exception:
            pass
        self.Nom = nom
        self.Libelle = '/' + nom
        self.Description = description


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
    ACCUEIL = ("Panneau OpenArchi prêt. /config pour choisir le fournisseur, "
               "le modèle et le projet. #{Nom} pour citer un élément.")

    def __init__(self, config=None, ouvrir_config=None):
        try:
            BaseViewModel.__init__(self)
        except Exception:
            pass
        self._config = config if config is not None else OpenArchiConfig()
        # Injecté par le panneau : ouvrir une fenêtre WPF depuis le VM le
        # rendrait intestable hors Revit.
        self._ouvrir_config = ouvrir_config
        self._saisie = ''
        self.Messages = self._nouvelle_liste()
        # Déclarées AVANT toute écriture de Saisie : son setter rafraîchit
        # l'autocomplétion, qui lit COMMANDES et Suggestions.
        self.COMMANDES = {
            'config': ('choisir le fournisseur, le modèle et le projet',
                       self._commande_config),
            'aide': ('lister les commandes disponibles', self._commande_aide),
        }
        self.Suggestions = self._nouvelle_liste()
        self.EnvoyerCommand = (RelayCommand(self._envoyer, self._peut_envoyer)
                               if RelayCommand else None)
        self.ChoisirSuggestionCommand = (RelayCommand(self._choisir)
                                         if RelayCommand else None)
        self.CompleterCommand = (RelayCommand(self._completer)
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
    def Statut(self):
        return self._config.resume()

    # --- autocomplétion des commandes ------------------------------------

    @property
    def SuggestionsVisibles(self):
        return len(self.Suggestions) > 0

    def _rafraichir_suggestions(self):
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

    def _choisir(self, suggestion=None):
        if suggestion is None:
            return
        self.Saisie = '/{0} '.format(suggestion.Nom)

    def _completer(self, _=None):
        # Tab : complète sur la première proposition, comme un shell.
        if len(self.Suggestions) > 0:
            self._choisir(self.Suggestions[0])

    # --- envoi -----------------------------------------------------------

    def _peut_envoyer(self, _=None):
        return bool(self._saisie.strip())

    def _envoyer(self, _=None):
        texte = self._saisie.strip()
        if not texte:
            return
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

    # ponytail: pas d'appel au fournisseur, on se contente d'accuser réception
    # et de lister les références. Brancher ici le client de chat réel.
    def _conversation(self, analyse):
        if analyse.references:
            return ("Non branché. Éléments cités : {0}".format(
                ', '.join(analyse.references)))
        return "Non branché — reçu : {0}".format(analyse.texte)

    # --- commandes -------------------------------------------------------

    def _commande_aide(self, _arguments):
        lignes = ['Commandes disponibles :']
        for nom in sorted(self.COMMANDES):
            lignes.append('  /{0} — {1}'.format(nom, self.COMMANDES[nom][0]))
        return '\n'.join(lignes)

    def _commande_config(self, _arguments):
        if self._ouvrir_config is None:
            return "Configuration indisponible hors Revit.\n" + self.Statut
        self._ouvrir_config(self._config)
        self.notify_property('Statut')
        return "Configuration enregistrée : {0}".format(self.Statut)
