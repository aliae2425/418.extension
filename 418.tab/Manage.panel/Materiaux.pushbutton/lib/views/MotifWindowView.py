# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Le choix d'un motif de remplissage, dans sa fenêtre.
#
# Sa raison d'être n'a pas changé depuis la version WPF : une liste
# déroulante ne montre qu'une ligne à la fois et se referme à chaque frappe.
# Une maquette compte des dizaines de motifs qui se ressemblent par le nom —
# il faut les voir côte à côte, et pouvoir filtrer sans perdre la liste.

try:
    from lib.views.FenetreWeb import FenetreWeb
except Exception:
    from views.FenetreWeb import FenetreWeb


class MotifWindowView(FenetreWeb):
    """418 · Choisir un motif — grille filtrable des motifs du document."""

    PAGE = 'materiaux/motif.html'
    TITRE = u'418 · Choisir un motif'
    TAILLE = (760, 620)
    TAILLE_MINI = (520, 420)
    BOUTONS_FENETRE = False

    def __init__(self, ordres, demande, proprietaire=None):
        super(MotifWindowView, self).__init__(ordres,
                                              proprietaire=proprietaire)
        # L'emplacement qui demande : c'est lui qui décide des motifs offerts
        # (un seul des quatre accepte un motif de modèle).
        self._demande = dict(demande or {})

    def contexte(self):
        demande = dict(self._demande)
        demande['ordre'] = 'selecteur'
        return self._ordres.traiter(demande)
