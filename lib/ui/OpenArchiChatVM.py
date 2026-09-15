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
    ACCUEIL = ("Panneau OpenArchi prêt. Le moteur de conversation n'est pas "
               "encore branché.")

    def __init__(self):
        try:
            BaseViewModel.__init__(self)
        except Exception:
            pass
        self._saisie = ''
        self.Messages = (ObservableCollection[object]() if ObservableCollection
                         else _ListeSimple())
        self.EnvoyerCommand = (RelayCommand(self._envoyer, self._peut_envoyer)
                               if RelayCommand else None)
        self.Messages.Add(MessageVM('OpenArchi', self.ACCUEIL, False))

    @property
    def Saisie(self):
        return self._saisie

    @Saisie.setter
    def Saisie(self, valeur):
        self._saisie = valeur or ''
        self.notify_property('Saisie')

    def _peut_envoyer(self, _=None):
        return bool(self._saisie.strip())

    def _envoyer(self, _=None):
        texte = self._saisie.strip()
        if not texte:
            return
        self.Messages.Add(MessageVM('Moi', texte, True))
        self.Saisie = ''
        self.Messages.Add(MessageVM('OpenArchi', self.repondre(texte), False))

    # ponytail: réponse bouchon, synchrone. Brancher ici le service de chat
    # (appel réseau + réponse asynchrone via Dispatcher) quand il existera.
    def repondre(self, texte):
        return "Non branché — reçu : {}".format(texte)
