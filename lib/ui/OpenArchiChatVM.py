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
    """Liste Python exposant l'API .Add d'ObservableCollection (tests hors .NET)."""
    Add = list.append


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
        self.Messages = (ObservableCollection[object]() if ObservableCollection
                         else _ListeSimple())
        self.EnvoyerCommand = (RelayCommand(self._envoyer, self._peut_envoyer)
                               if RelayCommand else None)
        self.COMMANDES = {
            'config': ('choisir le fournisseur, le modèle et le projet',
                       self._commande_config),
            'aide': ('lister les commandes disponibles', self._commande_aide),
        }
        self.Messages.Add(MessageVM('OpenArchi', self.ACCUEIL, False))

    # --- état affiché ----------------------------------------------------

    @property
    def Saisie(self):
        return self._saisie

    @Saisie.setter
    def Saisie(self, valeur):
        self._saisie = valeur or ''
        self.notify_property('Saisie')

    @property
    def Statut(self):
        return self._config.resume()

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
