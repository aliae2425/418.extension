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
        self._deplacer(-1)

    def descendre(self):
        self._deplacer(1)

    def _deplacer(self, pas):
        """Déplace la ligne sélectionnée de `pas` rangs et la garde
        sélectionnée. Hors bornes : ne fait rien (les boutons sont déjà
        désactivés par PeutMonter/PeutDescendre, mais la touche clavier ou
        un double-clic rapide peuvent arriver après coup)."""
        depart = self._index
        arrivee = depart + pas
        if depart < 0 or arrivee < 0 or arrivee >= len(self._feuilles):
            return
        item = self._feuilles.pop(depart)
        self._feuilles.insert(arrivee, item)
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
