# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Matériaux"
__doc__ = "Voir, éditer, remplacer et renommer les matériaux du modèle."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

try:
    uidoc = __revit__.ActiveUIDocument  # type: ignore
    doc = __revit__.ActiveUIDocument.Document  # type: ignore
except Exception:
    uidoc = None
    doc = None

from lib.services import presentation
from lib.services.MaterialService import MaterialService
from lib.services.journal import log, nouvelle_session
from lib.services.ordres import Ordres
from lib.views.MainWindowView import MainWindowView
from core.selection import all_materials


def _log_contexte(materiaux, catalogue):
    """Contexte du document : écarte d'emblée « maquette non modifiable » et
    « API Revit absente », les deux causes de remplacement muet qui ne
    ressemblent pas à un bug de l'outil."""
    if doc is None:
        log(u'AUCUN DOCUMENT ACTIF — aucune action n\'aura d\'effet')
        return
    log(u'document « {} » · modifiable={} · lecture seule={} · famille={}',
        getattr(doc, 'Title', u'?'),
        getattr(doc, 'IsModifiable', u'?'),
        getattr(doc, 'IsReadOnly', u'?'),
        getattr(doc, 'IsFamilyDocument', u'?'))
    log(u'{} matériau(x), {} catégorie(s) présentes, {} motif(s), '
        u'{} asset(s) d\'apparence', len(materiaux),
        len(catalogue.categories), len(catalogue.motifs) - 1,
        len(catalogue.apparences) - 1)


if __name__ == '__main__':
    nouvelle_session(u'Matériaux')
    materiaux = all_materials(doc) if doc is not None else []
    par_id = dict((presentation.ident(m.Id), m) for m in materiaux)

    service = MaterialService(doc)
    # Usages comptés AVANT l'affichage : les trois onglets montrent le chiffre
    # d'entrée de jeu, sans clic. C'est un parcours complet de la maquette
    # (cf. MaterialService.compter_utilisations) — l'ouverture de l'outil en
    # paie le prix une fois.
    usages = service.compter_utilisations([m.Id for m in materiaux])

    # Les catalogues (motifs, apparences, catégories présentes) sont lus une
    # fois pour toutes : ils alimentent l'éditeur ET la portée du
    # remplacement, et c'est aussi là que les vignettes de motif sont rendues.
    catalogue = presentation.Catalogue(doc)
    cartes = [presentation.carte(doc, m, catalogue, usages.get(m.Id))
              for m in materiaux]
    _log_contexte(materiaux, catalogue)

    # Le thème n'est pas passé ici : chaque fenêtre le lit à son ouverture
    # (cf. `FenetreWeb`), ce qui le rend juste même si Revit bascule en cours
    # de route.
    MainWindowView(Ordres(doc=doc, service=service, catalogue=catalogue,
                          materiaux=par_id, cartes=cartes)).show()
