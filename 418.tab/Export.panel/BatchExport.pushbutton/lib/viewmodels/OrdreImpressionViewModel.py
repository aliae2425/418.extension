# -*- coding: utf-8 -*-
# ViewModel de la modale « Ordre d'impression ».
#
# Réordonne une liste de feuilles DÉJÀ construite par MainViewModel (des
# SheetItemVM pour un jeu, des ManualSheetVM pour le PDF combiné). Il manipule
# les objets REÇUS, jamais des copies : l'appelant retrouve ses propres items
# dans `Feuilles`, ce qui permet à `services.ordre.reposer` de les reconnaître
# en mode manuel.
#
# Aucun accès Revit, aucune config : la persistance appartient au VM parent
# (`appliquer_ordre_jeu` / `appliquer_ordre_manuel`), qui seul sait sous
# quelle clé l'ordre se range.

from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

try:
    from services.ordre import ordonner
except Exception:
    from lib.services.ordre import ordonner


class OrdreImpressionViewModel(BaseViewModel):

    def __init__(self, feuilles, sous_titre=u''):
        super(OrdreImpressionViewModel, self).__init__()
        self._feuilles = list(feuilles or ())
        self._sous_titre = sous_titre or u''
        self._index = 0 if self._feuilles else -1
        # Mis à True par `valider()`. La vue ne lit QUE ce drapeau pour
        # décider si l'ordre doit être appliqué : fermer par la croix ou par
        # Annuler laisse donc la liste du parent intacte.
        self.Valide = False

    # ------------------------------------------------------------------
    # Données
    # ------------------------------------------------------------------

    @property
    def SousTitre(self):
        return self._sous_titre

    @property
    def Feuilles(self):
        return self._feuilles

    @property
    def NbFeuilles(self):
        return len(self._feuilles)

    @property
    def Numeros(self):
        """L'ordre courant, sous la forme persistée (liste de numéros)."""
        return [getattr(f, 'Numero', u'') or u'' for f in self._feuilles]

    @property
    def SelectedIndex(self):
        return self._index

    @SelectedIndex.setter
    def SelectedIndex(self, value):
        try:
            value = int(value)
        except Exception:
            return
        if value == self._index:
            return
        self._index = value
        for name in (u'SelectedIndex', u'PeutMonter', u'PeutDescendre'):
            self.notify_property(name)

    @property
    def PeutMonter(self):
        return 0 < self._index < len(self._feuilles)

    @property
    def PeutDescendre(self):
        return 0 <= self._index < len(self._feuilles) - 1

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def monter(self):
        self.deplacer_vers(self._index, self._index - 1)

    def descendre(self):
        self.deplacer_vers(self._index, self._index + 1)

    def deplacer_vers(self, depart, arrivee):
        """Déplace la ligne `depart` au rang `arrivee` et l'y garde
        sélectionnée. C'est le seul mouvement du VM : les flèches comme le
        glisser-déposer y aboutissent.

        Hors bornes : ne fait rien. Les flèches sont déjà grisées par
        PeutMonter/PeutDescendre, mais un glisser peut viser n'importe où,
        et le clavier arrive parfois après coup.
        """
        try:
            depart = int(depart)
            arrivee = int(arrivee)
        except Exception:
            return
        dernier = len(self._feuilles) - 1
        if not (0 <= depart <= dernier) or not (0 <= arrivee <= dernier):
            return
        if depart == arrivee:
            return
        self._feuilles.insert(arrivee, self._feuilles.pop(depart))
        self._index = arrivee
        self._notifier()

    def trier_numero(self):
        """Retour à l'ordre naturel des numéros (`A9` avant `A10`), celui que
        l'outil applique quand aucun ordre n'a été réorganisé à la main."""
        self._feuilles = ordonner(self._feuilles, [],
                                  cle=lambda f: getattr(f, 'Numero', u'') or u'')
        self._index = 0 if self._feuilles else -1
        self._notifier()

    def valider(self):
        self.Valide = True

    def _notifier(self):
        """Notifier `Feuilles` régénère les lignes de la ListBox, qui pousse
        alors `SelectedIndex = -1` par son binding TwoWay — AVANT que cette
        méthode ait fini. La cible est donc relue après coup, sinon la
        sélection saute à chaque déplacement et le deuxième ↑ ne fait rien.
        """
        cible = self._index
        self.notify_property(u'Feuilles')
        self._index = cible
        for name in (u'SelectedIndex', u'PeutMonter', u'PeutDescendre'):
            self.notify_property(name)
