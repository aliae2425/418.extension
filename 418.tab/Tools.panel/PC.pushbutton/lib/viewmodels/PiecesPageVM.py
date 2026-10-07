# -*- coding: utf-8 -*-
"""Page « Pièces » : ce qu'on dépose, et le jeu de feuilles qui le nourrit."""
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


AUCUN_JEU = u'— aucun —'


class _Liste(list):
    """Liste Python exposant l'API d'ObservableCollection (tests hors .NET)."""
    Add = list.append

    def Clear(self):
        del self[:]


def _nouvelle_liste():
    return (ObservableCollection[object]() if ObservableCollection
            else _Liste())


class PieceVM(BaseViewModel):
    """Une ligne : la case, le code, l'intitulé, et le jeu retenu.

    ``Jeu`` est le NOM du jeu de feuilles, pas l'élément Revit : le VM reste
    sérialisable et testable, et c'est le script qui retrouvera l'élément au
    moment d'exporter. Une pièce qui n'a pas de feuilles (une notice, une
    photo) garde ``AUCUN_JEU`` — c'est un cas normal, pas un oubli.
    """

    def __init__(self, piece, jeux=None):
        super(PieceVM, self).__init__()
        self._piece = piece
        self._coche = bool(piece.obligatoire)
        self._jeu = AUCUN_JEU
        self.Jeux = list(jeux or [AUCUN_JEU])

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
    def Mention(self):
        """Ce qui se lit à droite de l'intitulé."""
        return u'exigée' if self.Obligatoire else u'selon le projet'

    @property
    def Coche(self):
        return self._coche

    @Coche.setter
    def Coche(self, valeur):
        self._coche = bool(valeur)
        self.notify_property('Coche')

    @property
    def Jeu(self):
        return self._jeu

    @Jeu.setter
    def Jeu(self, valeur):
        self._jeu = valeur or AUCUN_JEU
        self.notify_property('Jeu')

    @property
    def JeuRetenu(self):
        """Le nom du jeu, ou '' quand la pièce n'en porte pas."""
        return u'' if self._jeu == AUCUN_JEU else self._jeu

    def piece(self):
        return self._piece


class PiecesPageVM(BaseViewModel):
    def __init__(self, jeux=None):
        super(PiecesPageVM, self).__init__()
        # AUCUN_JEU en tête : c'est le défaut, et la majorité des pièces d'un
        # dossier d'urbanisme ne sortent pas de la maquette.
        self._jeux = [AUCUN_JEU] + list(jeux or [])
        self.Pieces = _nouvelle_liste()
        self._type = None

    @property
    def Type(self):
        return self._type

    def charger(self, type_dossier):
        """Remplit la liste pour ce type. Sans effet si le type n'a pas changé.

        C'est ce qui permet de revenir sur l'onglet sans perdre ses cases :
        la navigation ne doit jamais effacer un choix.
        """
        if type_dossier == self._type:
            return
        self._type = type_dossier
        self.Pieces.Clear()
        for piece in catalogue.pieces(type_dossier):
            self.Pieces.Add(PieceVM(piece, self._jeux))
        self.notify_property('Pieces')
        self.notify_property('Resume')

    def retenues(self):
        """Les PieceVM cochées, dans l'ordre du bordereau."""
        return [p for p in list(self.Pieces) if p.Coche]

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
        total = len(list(self.Pieces))
        return u'{0} pièce(s) sur {1}'.format(len(self.retenues()), total)
