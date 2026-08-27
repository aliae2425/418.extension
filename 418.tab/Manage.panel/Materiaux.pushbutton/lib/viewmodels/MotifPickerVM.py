# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# ViewModel de la modale « choisir un motif de remplissage ».
#
# Sa raison d'être : une liste déroulante ne montre qu'une ligne à la fois et
# se referme à chaque frappe. Une maquette compte des dizaines de motifs qui
# se ressemblent tous par le nom — il faut les voir côte à côte, et pouvoir
# filtrer sans perdre la liste.

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from core.text_filter import filtrer
except Exception:
    from lib.core.text_filter import filtrer


class MotifPickerVM(BaseViewModel):
    """Liste filtrable des motifs offerts à UN emplacement.

    `Resultat` reste None tant que l'utilisateur n'a pas validé : c'est ce qui
    distingue « Annuler » d'un choix, la vue n'a rien d'autre à retourner.
    """

    def __init__(self, titre, motifs, courant=None):
        super(MotifPickerVM, self).__init__()
        self.Titre = titre or u'Choisir un motif'
        self.Motifs = list(motifs or [])
        self._recherche = u''
        self._selection = courant
        self.Resultat = None

    # -- Recherche ---------------------------------------------------------

    @property
    def Recherche(self):
        return self._recherche

    @Recherche.setter
    def Recherche(self, valeur):
        valeur = valeur or u''
        if valeur == self._recherche:
            return
        self._recherche = valeur
        self.notify_property('Recherche')
        self.notify_property('MotifsFiltres')
        # Dans cet ordre : la liste reconstruit d'abord ses lignes, puis
        # re-sélectionne le motif courant s'il est de retour. Sans ça,
        # relâcher le filtre laisse la liste sans sélection visible.
        self.notify_property('Selection')

    @property
    def MotifsFiltres(self):
        """Un vrai filtre : ce qui ne correspond pas ne s'affiche pas, y
        compris le motif sélectionné et l'entrée « Aucun ».

        Porte sur le nom ET sur le type, taper « modèle » ne laisse donc que
        les motifs de modèle, sans case à cocher de plus.
        """
        return filtrer(self.Motifs, self._recherche,
                       [lambda ref: ref.Nom, lambda ref: ref.Type])

    # -- Sélection ---------------------------------------------------------

    @property
    def Selection(self):
        return self._selection

    @Selection.setter
    def Selection(self, valeur):
        """Le None est ignoré.

        WPF vide `SelectedItem` dès que la ligne sélectionnée quitte
        l'ItemsSource, ce qui arrive à chaque frappe dans le filtre. Le choix
        de l'utilisateur ne doit pas s'évaporer parce qu'il a tapé une lettre
        de plus.
        """
        if valeur is None or valeur is self._selection:
            return
        self._selection = valeur
        self.notify_property('Selection')

    @property
    def PeutValider(self):
        return self._selection is not None

    def valider(self):
        """Fige le choix. False si rien n'est sélectionné — la vue ne ferme
        pas."""
        if self._selection is None:
            return False
        self.Resultat = self._selection
        return True
