# -*- coding: utf-8 -*-
"""Page « Pièces » : ce qu'on dépose, et ce que le projet a déjà pour ça."""
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.models import pieces as catalogue
except Exception:
    from models import pieces as catalogue

# Hors Revit (tests), .NET est absent : on retombe sur une liste Python. Le VM
# reste testable, seule la notification WPF disparaît.
try:
    from System.Collections.ObjectModel import ObservableCollection
except Exception:
    ObservableCollection = None


class _Liste(list):
    """Liste Python exposant l'API d'ObservableCollection (tests hors .NET)."""
    Add = list.append

    def Clear(self):
        del self[:]


def _nouvelle_liste():
    return (ObservableCollection[object]() if ObservableCollection
            else _Liste())


class PieceVM(BaseViewModel):
    """Une ligne : la case, le code, l'intitulé, et ce que l'analyse a trouvé.

    ``vues`` sont les vues du projet qui alimentent cette pièce et n'ont pas
    encore de feuille. C'est « le besoin » : trois coupes sans feuille, trois
    feuilles à créer pour PC3. Une pièce qu'aucune vue n'alimente en reçoit
    une seule, à remplir à la main — une notice se dépose aussi.
    """

    def __init__(self, piece, vues=None):
        super(PieceVM, self).__init__()
        self._piece = piece
        self._coche = bool(piece.obligatoire)
        self.Vues = list(vues or [])

    @property
    def Code(self):
        return self._piece.code

    @property
    def Libelle(self):
        return self._piece.libelle

    @property
    def Obligatoire(self):
        return bool(self._piece.obligatoire)

    @property
    def Feuilles(self):
        """Combien de feuilles cette pièce demande. Jamais zéro."""
        return len(self.Vues) or 1

    @property
    def Mention(self):
        """Ce que l'analyse a conclu, en clair. C'est la colonne qui justifie
        le nombre de feuilles — sans elle, le compte paraît arbitraire."""
        exigee = u'exigée' if self.Obligatoire else u'selon le projet'
        if not self._piece.vues:
            return u'{0} · 1 feuille à remplir'.format(exigee)
        if not self.Vues:
            return u'{0} · aucune vue libre, 1 feuille'.format(exigee)
        return u'{0} · {1} vue(s) sans feuille'.format(exigee, len(self.Vues))

    @property
    def Coche(self):
        return self._coche

    @Coche.setter
    def Coche(self, valeur):
        self._coche = bool(valeur)
        self.notify_property('Coche')

    def piece(self):
        return self._piece

    def attribution(self):
        """``(piece, [(vue, nom)])`` — ce que le plan attend."""
        return (self._piece, list(self.Vues))


class PiecesPageVM(BaseViewModel):

    def __init__(self, analyser=None):
        super(PiecesPageVM, self).__init__()
        # Injectée : le VM ne connaît pas Revit, c'est le script qui sait
        # interroger la maquette. Les tests passent un double.
        self._analyser = analyser or (lambda _piece: [])
        self.Pieces = _nouvelle_liste()
        self._type = None

    @property
    def Type(self):
        return self._type

    def charger(self, type_dossier):
        """Remplit la liste pour ce type, en analysant le projet au passage.

        Sans effet si le type n'a pas changé : revenir sur l'onglet ne doit
        jamais effacer les cases cochées.
        """
        if type_dossier == self._type:
            return
        self._type = type_dossier
        self.Pieces.Clear()
        for piece in catalogue.pieces(type_dossier):
            self.Pieces.Add(PieceVM(piece, self._analyser(piece)))
        self.notify_property('Pieces')
        self.notify_property('Resume')

    def retenues(self):
        return [p for p in list(self.Pieces) if p.Coche]

    def attributions(self):
        return [p.attribution() for p in self.retenues()]

    def tout_cocher(self, _=None):
        for p in list(self.Pieces):
            p.Coche = True
        self.notify_property('Resume')

    def tout_decocher(self, _=None):
        """Décocher ne protège pas les obligatoires : l'architecte sait ce
        qu'il dépose, et un dossier se monte parfois par morceaux."""
        for p in list(self.Pieces):
            p.Coche = False
        self.notify_property('Resume')

    @property
    def Resume(self):
        retenues = self.retenues()
        feuilles = sum(p.Feuilles for p in retenues)
        return u'{0} pièce(s) sur {1} · {2} feuille(s)'.format(
            len(retenues), len(list(self.Pieces)), feuilles)
