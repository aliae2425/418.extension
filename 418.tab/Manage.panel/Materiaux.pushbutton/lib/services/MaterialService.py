# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from core.transaction import revit_transaction
except Exception:
    from lib.core.transaction import revit_transaction

try:
    from core.sanitize import sanitize_revit_name
except Exception:
    try:
        from lib.core.sanitize import sanitize_revit_name
    except Exception:
        def sanitize_revit_name(x):
            return x or u'SansNom'

try:
    from Autodesk.Revit.DB import (FilteredElementCollector, StorageType,
                                   HostObjAttributes)
except Exception:
    FilteredElementCollector = None
    StorageType = None
    HostObjAttributes = None


class LigneRapport(object):
    """Ce qu'une catégorie porte comme affectations du matériau."""

    def __init__(self, categorie):
        self.Categorie = categorie
        self.Types = 0
        self.Instances = 0

    @property
    def Total(self):
        return self.Types + self.Instances

    @property
    def Detail(self):
        morceaux = []
        if self.Types:
            morceaux.append(u'%d type%s' % (self.Types,
                                            u's' if self.Types > 1 else u''))
        if self.Instances:
            morceaux.append(u'%d instance%s' % (self.Instances,
                                                u's' if self.Instances > 1 else u''))
        return u' · '.join(morceaux)


class Rapport(object):
    """Résultat d'un balayage ou d'un remplacement, par catégorie."""

    def __init__(self):
        self._par_categorie = {}
        self.Peints = 0

    def ajouter(self, categorie, est_type):
        ligne = self._par_categorie.get(categorie)
        if ligne is None:
            ligne = LigneRapport(categorie)
            self._par_categorie[categorie] = ligne
        if est_type:
            ligne.Types += 1
        else:
            ligne.Instances += 1

    @property
    def Lignes(self):
        return sorted(self._par_categorie.values(),
                      key=lambda l: (-l.Total, l.Categorie))

    @property
    def Total(self):
        return sum(l.Total for l in self._par_categorie.values())

    @property
    def EstVide(self):
        return not self._par_categorie


def _categorie(element):
    try:
        categorie = element.Category
        if categorie is not None and categorie.Name:
            return categorie.Name
    except Exception:
        pass
    return u'Sans catégorie'


class MaterialService(object):
    """Lecture des porteurs d'un matériau, remplacement, renommage."""

    def __init__(self, doc):
        self._doc = doc

    # -- Balayage ----------------------------------------------------------

    def _elements(self, categorie_id=None):
        """Types puis instances du document, en un seul flux.

        `categorie_id` restreint le balayage à une catégorie (le choix du
        menu déroulant) ; None balaie tout le modèle.

        ponytail: sans catégorie, le balayage reste complet et O(éléments) —
        comptez quelques secondes sur une grosse maquette. `GetMaterialIds`
        sert de pré-filtre bon marché pour n'inspecter les paramètres que des
        éléments qui portent effectivement le matériau. Un
        `ElementParameterFilter` par paramètre matériau irait plus vite, au
        prix d'une liste de BuiltInParameter à maintenir.
        """
        if FilteredElementCollector is None or self._doc is None:
            return
        for est_type in (True, False):
            collecteur = FilteredElementCollector(self._doc)
            if categorie_id is not None:
                collecteur = collecteur.OfCategoryId(categorie_id)
            if est_type:
                collecteur = collecteur.WhereElementIsElementType()
            else:
                collecteur = collecteur.WhereElementIsNotElementType()
            for element in collecteur.ToElements():
                yield element, est_type

    def _balayer(self, ids_sources, categorie_id=None):
        """UN seul parcours du modèle -> (porteurs, nombre de faces peintes).

        `porteurs` : liste de (element, est_type) affectés par un des ids.
        Les faces peintes sont comptées pour être signalées, jamais
        modifiées : dépeindre/repeindre se fait face par face et l'API
        bronche sur les faces liées.
        """
        ids = set(ids_sources or [])
        porteurs = []
        peints = 0
        if not ids:
            return porteurs, peints
        for element, est_type in self._elements(categorie_id):
            try:
                if set(element.GetMaterialIds(False)) & ids:
                    porteurs.append((element, est_type))
            except Exception:
                pass
            try:
                if set(element.GetMaterialIds(True)) & ids:
                    peints += 1
            except Exception:
                pass
        return porteurs, peints

    def analyser(self, ids_sources, categorie_id=None):
        """Rapport de ce qui utilise ces matériaux. Ne modifie rien."""
        rapport = Rapport()
        porteurs, rapport.Peints = self._balayer(ids_sources, categorie_id)
        for element, est_type in porteurs:
            rapport.ajouter(_categorie(element), est_type)
        return rapport

    # -- Remplacement ------------------------------------------------------

    def remplacer(self, ids_sources, id_cible, categorie_id=None):
        """Remplace les affectations de `ids_sources` par `id_cible`.

        Traite les paramètres valués matériau (type et instance) et les
        couches des structures composées, dans la catégorie choisie ou dans
        tout le modèle. Retourne le `Rapport` de ce qui a RÉELLEMENT été
        modifié.
        """
        rapport = Rapport()
        ids = set(ids_sources or [])
        if not ids or id_cible is None:
            return rapport
        ids.discard(id_cible)          # remplacer un matériau par lui-même
        if not ids:
            return rapport

        porteurs, rapport.Peints = self._balayer(ids, categorie_id)
        with revit_transaction(self._doc, u'Remplacer le matériau'):
            for element, est_type in porteurs:
                touche = self._remplacer_couches(element, ids, id_cible)
                touche = self._remplacer_parametres(element, ids, id_cible) or touche
                if touche:
                    rapport.ajouter(_categorie(element), est_type)
        return rapport

    @staticmethod
    def _remplacer_parametres(element, ids, id_cible):
        if StorageType is None:
            return False
        touche = False
        try:
            parametres = list(element.Parameters)
        except Exception:
            return False
        for parametre in parametres:
            try:
                if parametre.IsReadOnly:
                    continue
                if parametre.StorageType != StorageType.ElementId:
                    continue
                if parametre.AsElementId() not in ids:
                    continue
                parametre.Set(id_cible)
                touche = True
            except Exception:
                continue          # paramètre verrouillé ou non assignable
        return touche

    @staticmethod
    def _remplacer_couches(element, ids, id_cible):
        """Couches de structure composée (murs, sols, toits, plafonds)."""
        if HostObjAttributes is None or not isinstance(element, HostObjAttributes):
            return False
        try:
            structure = element.GetCompoundStructure()
        except Exception:
            return False
        if structure is None:
            return False
        touche = False
        try:
            for index in range(structure.LayerCount):
                if structure.GetMaterialId(index) in ids:
                    structure.SetMaterialId(index, id_cible)
                    touche = True
            if touche:
                element.SetCompoundStructure(structure)
        except Exception:
            return False
        return touche

    # -- Renommage ---------------------------------------------------------

    def renommer(self, materiaux, rename_service):
        """Renomme les matériaux via `rename_service`. Retourne le nombre
        de noms effectivement changés."""
        if not materiaux or rename_service is None:
            return 0
        changes = 0
        with revit_transaction(self._doc, u'Renommer les matériaux'):
            for index, materiau in enumerate(materiaux, start=1):
                nouveau = sanitize_revit_name(
                    rename_service.apply(materiau.Name, index=index))
                if nouveau == materiau.Name:
                    continue
                if self._affecter_nom(materiau, nouveau):
                    changes += 1
        return changes

    @staticmethod
    def _affecter_nom(materiau, nom):
        """Affecte le nom, en suffixant `*` sur collision (noms uniques).

        ponytail: 3e copie de cette boucle (RenameViewsService,
        RenameSheetsService). À remonter dans core.rename_service le jour
        où un 4e outil renomme des éléments Revit.
        """
        candidat = nom
        for _ in range(5):
            try:
                materiau.Name = candidat
                return True
            except Exception:
                candidat += u'*'
        return False
