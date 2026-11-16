# -*- coding: utf-8 -*-
"""ViewModel de l'historique du presse-papiers, partagé par le panneau
ancrable et la popup façon Win+V.

Deux choses sont injectées, et c'est tout ce qui distingue les deux surfaces :

- ``historique`` — le magasin des entrées (``core.presse_papiers``) ;
- ``executer(fn)`` — fait tourner ``fn(uidoc)`` en contexte API. La popup
  passe un exécuteur direct (elle vit dans la commande du bouton), le panneau
  un exécuteur qui passe par ``demander`` (ExternalEvent) : un volet non
  modal n'a pas le droit de toucher la maquette lui-même.
"""
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel
    from lib.ui.helpers.RelayCommand import RelayCommand

try:
    from core.journal import journal
except Exception:
    from lib.core.journal import journal

try:
    from System import Action
    from System.Collections.ObjectModel import ObservableCollection
except Exception:
    Action = ObservableCollection = None

_log = journal('presse_papiers')

# Le contrat de core.presse_papiers.MODES, recopié pour que le VM se teste
# sans le module (qui importe l'API Revit).
MEME_EMPLACEMENT, VUE_COURANTE, NORMAL = 'meme_emplacement', 'vue_courante', 'normal'


class _ListeSimple(list):
    """Liste Python exposant l'API d'ObservableCollection (tests hors .NET)."""
    Add = list.append

    def Clear(self):
        del self[:]


def _pluriel(n, mot):
    return '{0} {1}{2}'.format(n, mot, 's' if n > 1 else '')


class LigneVM(BaseViewModel):
    """Une entrée de l'historique, mise en forme. Immuable."""

    def __init__(self, entree):
        try:
            BaseViewModel.__init__(self)
        except Exception:
            pass
        self.Entree = entree
        self.Id = entree.id
        self.Libelle = entree.libelle
        self.Heure = entree.horodatage.strftime('%H:%M:%S')
        self.Source = '{0} · {1}'.format(entree.doc_source, entree.vue_source)
        self.Badge = '2D' if entree.est_2d else '3D'
        self.Ignores = (_pluriel(entree.nb_ignores, 'ignoré')
                        if entree.nb_ignores > 0 else '')
        self.IgnoresVisible = bool(self.Ignores)


class PressePapiersVM(BaseViewModel):

    def __init__(self, historique, executer, noyau=None, dispatcher=None,
                 suivre=True):
        """``noyau`` : ce qui porte ``coller``, ``retirer`` et ``vider`` en
        contexte API — ``core.presse_papiers`` par défaut, un double en test.
        Retirer passe par lui et non par ``historique`` : l'instantané vit
        aussi dans un document caché, qu'il faut purger.

        ``dispatcher`` : celui du fil d'interface, pour y ramener les
        notifications de l'historique. ``None`` (tests, popup) : sur place.

        ``suivre=False`` pour la popup : l'historique n'a pas de
        désabonnement, et une popup refermée resterait sinon abonnée à
        chaque Ctrl+C jusqu'à la fin de la session.
        """
        try:
            BaseViewModel.__init__(self)
        except Exception:
            pass
        self._historique = historique
        self._executer = executer
        self._noyau = noyau
        self._dispatcher = dispatcher
        self._selection = None
        self._etat = ''
        self.Lignes = (ObservableCollection[object]()
                       if ObservableCollection is not None else _ListeSimple())

        a_selection = lambda _p: self._selection is not None
        self.CollerMemeEmplacementCommand = RelayCommand(
            lambda _p: self.coller(MEME_EMPLACEMENT), a_selection)
        self.CollerVueCouranteCommand = RelayCommand(
            lambda _p: self.coller(VUE_COURANTE), a_selection)
        self.CollerNormalCommand = RelayCommand(
            lambda _p: self.coller(NORMAL), a_selection)
        self.RetirerCommand = RelayCommand(lambda _p: self.retirer(), a_selection)
        self.ViderCommand = RelayCommand(lambda _p: self.vider())

        self.rafraichir()
        if suivre:
            historique.abonner(self._sur_changement)

    # --- propriétés liées -------------------------------------------------

    @property
    def Selection(self):
        return self._selection

    @Selection.setter
    def Selection(self, valeur):
        if valeur is self._selection:
            return
        self._selection = valeur
        self.notify_property('Selection')

    @property
    def Etat(self):
        return self._etat

    @Etat.setter
    def Etat(self, valeur):
        self._etat = valeur
        self.notify_property('Etat')

    @property
    def EstVide(self):
        return len(self.Lignes) == 0

    # --- fil d'interface --------------------------------------------------

    def _sur_le_fil(self, fn):
        # ENVELOPPE OBLIGATOIRE : une exception qui s'échappe sur le fil
        # d'interface de Revit tue Revit (cf. OpenArchiChatVM).
        def _sur():
            try:
                fn()
            except Exception:
                _log.exception('presse-papiers, fil d\'interface')
        d = self._dispatcher
        if d is None or Action is None or d.CheckAccess():
            return _sur()
        d.Invoke(Action(_sur))

    def _sur_changement(self):
        self._sur_le_fil(self.rafraichir)

    # --- logique ------------------------------------------------------------

    def rafraichir(self):
        """Reconstruit les lignes ; garde la sélection si l'entrée existe
        encore, sinon sélectionne la plus récente."""
        garde = self._selection.Id if self._selection is not None else None
        self.Lignes.Clear()
        choix = None
        for entree in self._historique.entrees:
            ligne = LigneVM(entree)
            self.Lignes.Add(ligne)
            if ligne.Id == garde:
                choix = ligne
        if choix is None and len(self.Lignes):
            choix = self.Lignes[0]
        self._selection = None          # force la notification
        self.Selection = choix
        self.notify_property('EstVide')

    def selectionner_decalage(self, pas):
        """Flèches de la popup : déplace la sélection, bornée à la liste."""
        if not len(self.Lignes):
            return
        try:
            i = list(self.Lignes).index(self._selection)
        except ValueError:
            i = 0
        self.Selection = self.Lignes[max(0, min(len(self.Lignes) - 1, i + pas))]

    def coller(self, mode):
        ligne = self._selection
        if ligne is None:
            self.Etat = 'Aucune entrée sélectionnée.'
            return
        entree = ligne.Entree

        def _travail(uidoc):
            try:
                cr = self._le_noyau().coller(uidoc, entree, mode)
            except Exception as e:
                _log.exception('collage')
                texte = 'Échec du collage : {0}'.format(e)
            else:
                texte = _compte_rendu(cr)
            self._sur_le_fil(lambda: setattr(self, 'Etat', texte))

        self._lancer(_travail)

    def retirer(self):
        if self._selection is not None:
            id = self._selection.Id
            self._lancer(lambda _uidoc: self._puis_rafraichir(
                self._le_noyau().retirer, id))

    def vider(self):
        self._lancer(lambda _uidoc: self._puis_rafraichir(self._le_noyau().vider))

    def _puis_rafraichir(self, fn, *args):
        # Rafraîchir soi-même : la popup (suivre=False) n'est pas abonnée.
        try:
            fn(*args)
        finally:
            self._sur_le_fil(self.rafraichir)

    def _lancer(self, travail):
        try:
            self._executer(travail)
        except Exception as e:
            _log.exception('exécuteur')
            self.Etat = 'Action impossible : {0}'.format(e)

    def _le_noyau(self):
        if self._noyau is None:
            try:
                from core import presse_papiers
            except Exception:
                from lib.core import presse_papiers
            self._noyau = presse_papiers
        return self._noyau


def _compte_rendu(cr):
    if cr.annule:
        return 'Collage annulé.'
    texte = '{0} collé{1}.'.format(_pluriel(cr.nb_colles, 'élément'),
                                    's' if cr.nb_colles > 1 else '')
    if cr.ignores:
        texte += ' {0}.'.format(_pluriel(len(cr.ignores), 'ignoré'))
    return texte
