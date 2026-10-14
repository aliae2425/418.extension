# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# La fenêtre principale : les trois onglets, et la porte vers l'éditeur.

try:
    from lib.views.FenetreWeb import AUTRE, FenetreWeb
except Exception:
    from views.FenetreWeb import AUTRE, FenetreWeb

try:
    from lib.views.EditeurWindowView import EditeurWindowView
except Exception:
    from views.EditeurWindowView import EditeurWindowView

try:
    from lib.services import presentation
except Exception:
    from services import presentation


class MainWindowView(FenetreWeb):
    """418 · Matériaux — cartes, renommage, remplacement."""

    PAGE = 'materiaux/index.html'
    TITRE = u'418 · Matériaux'
    # Largeur dictée par le tableau de l'onglet Renommer, le seul contenu à
    # largeur incompressible : deux colonnes de nom qui doivent rester
    # lisibles, plus 350 px de colonnes fixes et le rail.
    TAILLE = (1240, 800)
    TAILLE_MINI = (960, 600)

    def contexte(self):
        return self._ordres.etat()

    def _ordre_vue(self, message):
        if message.get('ordre') != 'ouvrir_editeur':
            return AUTRE
        # Une fenêtre NEUVE à chaque ouverture : l'éditeur relit le matériau
        # au montage, donc recycler la précédente afficherait l'état d'avant.
        editeur = EditeurWindowView(
            self._ordres, presentation.entier(message.get('id')),
            proprietaire=self._window)
        # Rend la carte relue, ou None si l'utilisateur a annulé : la page
        # principale rafraîchit la carte sur cette seule base.
        return editeur.ouvrir()
