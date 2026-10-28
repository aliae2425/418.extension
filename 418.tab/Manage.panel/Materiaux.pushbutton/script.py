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
    # Ni les motifs ni les catégories ici : les premiers se rendent au
    # premier accès (`Catalogue.motifs`), les secondes au retour de
    # l'inventaire. Les compter dans ce journal déclencherait justement le
    # travail qu'on a sorti de l'ouverture — `_lire_motifs` dit déjà combien
    # il en a lu.
    log(u'{} matériau(x), {} asset(s) d\'apparence',
        len(materiaux), len(catalogue.apparences) - 1)


if __name__ == '__main__':
    nouvelle_session(u'Matériaux')
    materiaux = all_materials(doc) if doc is not None else []
    par_id = dict((presentation.ident(m.Id), m) for m in materiaux)

    service = MaterialService(doc)

    # RIEN qui parcoure le modèle avant l'affichage. Les usages et les
    # catégories présentes demandaient chacun leur balayage — quelques
    # secondes sur une grosse maquette, Revit figé et pas un pixel à
    # l'écran. La page les réclame par l'ordre `inventaire` une fois peinte ;
    # la colonne des usages se remplit sous les yeux.
    catalogue = presentation.Catalogue(doc)
    cartes = [presentation.carte(doc, m, catalogue) for m in materiaux]
    _log_contexte(materiaux, catalogue)

    # Le thème n'est pas passé ici : chaque fenêtre le lit à son ouverture
    # (cf. `FenetreWeb`), ce qui le rend juste même si Revit bascule en cours
    # de route.
    MainWindowView(Ordres(doc=doc, service=service, catalogue=catalogue,
                          materiaux=par_id, cartes=cartes)).show()
