# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# L'éditeur d'UN matériau : sa propre fenêtre, comme avant la refonte.
#
# Une fenêtre et non un voile dans la page : on la déplace pour voir la
# maquette derrière, elle se redimensionne, et elle a sa barre de titre —
# c'est ce que faisait `EditeurWindow.xaml`, et c'est ce qu'on attend d'un
# éditeur qu'on garde ouvert en travaillant.

try:
    from lib.views.FenetreWeb import AUTRE, FenetreWeb
except Exception:
    from views.FenetreWeb import AUTRE, FenetreWeb

try:
    from lib.views.MotifWindowView import MotifWindowView
except Exception:
    from views.MotifWindowView import MotifWindowView


class EditeurWindowView(FenetreWeb):
    """418 · Éditer le matériau — identité, apparence, hachures."""

    PAGE = 'materiaux/editeur.html'
    TITRE = u'418 · Éditer le matériau'
    # Assez haut pour que les deux faces et leurs aperçus tiennent sans
    # défilement sur un écran normal.
    TAILLE = (1040, 860)
    TAILLE_MINI = (880, 560)
    BOUTONS_FENETRE = False

    def __init__(self, ordres, identifiant, proprietaire=None):
        super(EditeurWindowView, self).__init__(ordres,
                                                proprietaire=proprietaire)
        self._id = identifiant

    def contexte(self):
        return self._ordres.traiter({'ordre': 'editeur', 'id': self._id})

    def _ordre_vue(self, message):
        if message.get('ordre') != 'ouvrir_motif':
            return AUTRE
        # Le motif courant vient de la PAGE, pas de la maquette : l'utilisateur
        # a pu en changer sans encore enregistrer.
        return MotifWindowView(self._ordres, message,
                               proprietaire=self._window).ouvrir()
