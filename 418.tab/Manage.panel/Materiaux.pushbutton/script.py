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

try:
    from Autodesk.Revit.DB import (CategoryType, ElementId,
                                   FilteredElementCollector)
except Exception:
    CategoryType = None
    ElementId = None
    FilteredElementCollector = None

from lib.viewmodels.MainViewModel import MainViewModel
from lib.viewmodels.RemplacerPageVM import CategorieVM
from lib.viewmodels import lecture_materiau
from lib.views.MainWindowView import MainWindowView
from lib.services.MaterialService import MaterialService
from lib.services.journal import log, nouvelle_session
from core.selection import all_materials


def _categories_presentes():
    """Catégories de modèle qui contiennent au moins un élément.

    Alimente le menu déroulant de portée de l'onglet Remplacer. On liste ce
    qui est RÉELLEMENT dans la maquette plutôt que les ~200 catégories de
    Revit, sinon le menu est inutilisable.

    ponytail: une requête par catégorie, mais `FirstElementId()` s'arrête au
    premier élément trouvé — c'est bien moins cher qu'un balayage complet
    avec regroupement. Si l'ouverture de l'outil devient lente sur une grosse
    maquette, c'est le premier endroit à regarder.
    """
    if doc is None or CategoryType is None or FilteredElementCollector is None:
        return []
    presentes = []
    for categorie in doc.Settings.Categories:
        try:
            if categorie.CategoryType != CategoryType.Model:
                continue
            collecteur = FilteredElementCollector(doc).OfCategoryId(categorie.Id)
            if collecteur.FirstElementId() == ElementId.InvalidElementId:
                continue
            presentes.append(CategorieVM(categorie.Id, categorie.Name))
        except Exception:
            continue          # catégorie non filtrable (annotation, interne)
    return sorted(presentes, key=lambda c: c.Nom)


def _log_contexte(materiaux, categories):
    """Contexte du document : écarte d'emblée « maquette non modifiable »
    et « API Revit absente », les deux causes de remplacement muet qui ne
    ressemblent pas à un bug de l'outil."""
    if doc is None:
        log(u'AUCUN DOCUMENT ACTIF — aucune action n\'aura d\'effet')
        return
    log(u'document « {} » · modifiable={} · lecture seule={} · famille={}',
        getattr(doc, 'Title', u'?'),
        getattr(doc, 'IsModifiable', u'?'),
        getattr(doc, 'IsReadOnly', u'?'),
        getattr(doc, 'IsFamilyDocument', u'?'))
    log(u'{} matériau(x), {} catégorie(s) présentes',
        len(materiaux), len(categories))


if __name__ == '__main__':
    nouvelle_session(u'Matériaux')
    materiaux = all_materials(doc) if doc is not None else []
    materiaux_par_id = dict((m.Id, m) for m in materiaux)

    # Usages comptés AVANT l'affichage : les onglets Matériaux et Renommer
    # montrent le chiffre d'entrée de jeu, sans clic. C'est un parcours
    # complet de la maquette (cf. MaterialService.compter_utilisations) —
    # l'ouverture de l'outil en paie le prix une fois.
    service = MaterialService(doc)
    usages = service.compter_utilisations(list(materiaux_par_id.keys()))
    cartes = [lecture_materiau.carte(doc, m, usages.get(m.Id))
              for m in materiaux]

    categories = _categories_presentes()
    # Catalogues de l'éditeur, lus une fois pour toutes les fenêtres d'édition.
    motifs = lecture_materiau.motifs_du_document(doc)
    apparences = lecture_materiau.apparences_du_document(doc)
    _log_contexte(materiaux, categories)
    log(u'catalogues : {} motif(s), {} asset(s) d\'apparence',
        len(motifs), len(apparences))

    vm = MainViewModel(service=service, doc=doc)
    vm.charger(cartes, materiaux_par_id, categories, motifs, apparences)

    view = MainWindowView(vm)
    view.show()
