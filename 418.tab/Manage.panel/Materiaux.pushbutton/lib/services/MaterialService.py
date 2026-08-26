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
    from lib.services.journal import log, nom as _nom
except Exception:
    try:
        from services.journal import log, nom as _nom
    except Exception:
        def log(gabarit, *args):
            pass

        def _nom(element):
            return u'<?>'

try:
    from Autodesk.Revit.DB import (ElementId, ElementMulticategoryFilter,
                                   FilteredElementCollector, StorageType,
                                   HostObjAttributes)
except Exception:
    ElementId = None
    ElementMulticategoryFilter = None
    FilteredElementCollector = None
    StorageType = None
    HostObjAttributes = None

try:
    from System.Collections.Generic import List as _NetList
except Exception:
    _NetList = None


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


def _ids_couches(element):
    """Ids matériau des couches de structure composée, ou set() vide.

    Indispensable à la DÉTECTION, pas seulement à l'écriture :
    `Element.GetMaterialIds` est piloté par la géométrie, donc il ne renvoie
    rien sur un `ElementType`. Un `WallType` qui porte le matériau dans ses
    couches restait invisible au balayage, alors que c'est le SEUL endroit où
    l'affectation est inscriptible — l'instance `Wall`, elle, remonte bien le
    matériau mais n'a rien à modifier.
    """
    if HostObjAttributes is None or not isinstance(element, HostObjAttributes):
        return set()
    try:
        structure = element.GetCompoundStructure()
        if structure is None:
            return set()
        return set(structure.GetMaterialId(index)
                   for index in range(structure.LayerCount))
    except Exception:
        return set()


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

    @staticmethod
    def _filtre_categories(categorie_ids):
        """`ElementMulticategoryFilter` sur les catégories cochées, ou None.

        None (aucune catégorie cochée) = tout le modèle.
        """
        if not categorie_ids or ElementMulticategoryFilter is None:
            return None
        if _NetList is None or ElementId is None:
            return None
        liste = _NetList[ElementId]()
        for categorie_id in categorie_ids:
            liste.Add(categorie_id)
        return ElementMulticategoryFilter(liste)

    def _elements(self, categorie_ids=None):
        """Types puis instances du document, en un seul flux.

        `categorie_ids` restreint le balayage aux catégories cochées dans la
        section de portée ; None ou vide balaie tout le modèle.

        ponytail: sans catégories, le balayage reste complet et O(éléments) —
        comptez quelques secondes sur une grosse maquette. `GetMaterialIds`
        PLUS les couches de structure composée (`_ids_couches`) servent de
        pré-filtre pour n'inspecter les paramètres que des éléments qui
        portent effectivement le matériau. Un `ElementParameterFilter` par
        paramètre matériau irait plus vite, au prix d'une liste de
        BuiltInParameter à maintenir.
        """
        if FilteredElementCollector is None or self._doc is None:
            return
        filtre = self._filtre_categories(categorie_ids)
        for est_type in (True, False):
            collecteur = FilteredElementCollector(self._doc)
            if filtre is not None:
                collecteur = collecteur.WherePasses(filtre)
            if est_type:
                collecteur = collecteur.WhereElementIsElementType()
            else:
                collecteur = collecteur.WhereElementIsNotElementType()
            for element in collecteur.ToElements():
                yield element, est_type

    def _balayer(self, ids_sources, categorie_ids=None):
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
            log(u'balayage annulé : aucune source')
            return porteurs, peints
        log(u'balayage : {} source(s) {} · portée {}',
            len(ids), [str(i) for i in ids],
            u'tout le modèle' if not categorie_ids
            else u'%d catégorie(s)' % len(categorie_ids))
        vus = 0
        sans_materiau = 0
        for element, est_type in self._elements(categorie_ids):
            vus += 1
            try:
                materiaux = set(element.GetMaterialIds(False))
            except Exception as erreur:
                log(u'GetMaterialIds(False) a levé sur {} : {}',
                    _nom(element), erreur)
                materiaux = set()
            materiaux |= _ids_couches(element)
            if not materiaux:
                sans_materiau += 1
            if materiaux & ids:
                porteurs.append((element, est_type))
                log(u'porteur {} [{}] · matériaux={}', _nom(element),
                    type(element).__name__, [str(m) for m in materiaux])
            try:
                if set(element.GetMaterialIds(True)) & ids:
                    peints += 1
            except Exception:
                pass
        log(u'balayage terminé : {} élément(s) vus, {} sans matériau, '
            u'{} porteur(s), {} peint(s)', vus, sans_materiau, len(porteurs),
            peints)
        if vus and not porteurs:
            log(u'AUCUN porteur : les ids sources ne sortent pas de '
                u'GetMaterialIds — soit le matériau n\'est utilisé nulle part, '
                u'soit la portée exclut ses catégories.')
        return porteurs, peints

    def analyser(self, ids_sources, categorie_ids=None):
        """Rapport de ce qui utilise ces matériaux. Ne modifie rien."""
        rapport = Rapport()
        porteurs, rapport.Peints = self._balayer(ids_sources, categorie_ids)
        for element, est_type in porteurs:
            rapport.ajouter(_categorie(element), est_type)
        return rapport

    # -- Remplacement ------------------------------------------------------

    def remplacer(self, ids_sources, id_cible, categorie_ids=None):
        """Remplace les affectations de `ids_sources` par `id_cible`.

        Traite les paramètres valués matériau (type et instance) et les
        couches des structures composées, dans les catégories cochées ou dans
        tout le modèle. Retourne le `Rapport` de ce qui a RÉELLEMENT été
        modifié.
        """
        rapport = Rapport()
        ids = set(ids_sources or [])
        log(u'remplacer : sources {} -> cible {}',
            [str(i) for i in ids], id_cible)
        if not ids or id_cible is None:
            log(u'abandon : sources vides ou cible absente')
            return rapport
        ids.discard(id_cible)          # remplacer un matériau par lui-même
        if not ids:
            log(u'abandon : la seule source EST la cible, rien à faire')
            return rapport

        porteurs, rapport.Peints = self._balayer(ids, categorie_ids)
        intacts = []
        transaction = None
        with revit_transaction(self._doc, u'Remplacer le matériau') as transaction:
            for element, est_type in porteurs:
                couches = self._remplacer_couches(element, ids, id_cible)
                parametres = self._remplacer_parametres(element, ids, id_cible)
                if couches or parametres:
                    rapport.ajouter(_categorie(element), est_type)
                    log(u'modifié {} : couches={} paramètres={}',
                        _nom(element), couches, parametres)
                elif len(intacts) < 20:
                    intacts.append(element)
        for element in intacts:
            log(u'INTACT {} — porte le matériau mais ni couche ni paramètre '
                u'accessible en écriture', _nom(element))
        # Une transaction annulée par un gestionnaire d'échec Revit commite
        # « proprement » et ne change rien : le statut est le seul témoin.
        log(u'remplacement terminé : {} élément(s) modifié(s) sur {} '
            u'porteur(s) · transaction {}', rapport.Total, len(porteurs),
            getattr(transaction, 'GetStatus', lambda: u'?')())
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
            except Exception as erreur:
                # Silencieux à l'origine — c'est ici que se perd un
                # remplacement qui « ne fait rien » : paramètre verrouillé,
                # non assignable, ou élément de lien.
                log(u'paramètre « {} » refusé sur {} : {}',
                    getattr(parametre.Definition, 'Name', u'?'),
                    _nom(element), erreur)
                continue
        return touche

    @staticmethod
    def _remplacer_couches(element, ids, id_cible):
        """Couches de structure composée (murs, sols, toits, plafonds)."""
        if HostObjAttributes is None:
            log(u'couches ignorées sur {} : HostObjAttributes non importé',
                _nom(element))
            return False
        if not isinstance(element, HostObjAttributes):
            # Cas NORMAL et fréquent : une instance (`Wall`) remonte les
            # matériaux des couches de son type mais n'a pas de structure à
            # elle. C'est le `WallType` qui est modifié, de son côté.
            return False
        try:
            structure = element.GetCompoundStructure()
        except Exception as erreur:
            log(u'GetCompoundStructure a levé sur {} : {}',
                _nom(element), erreur)
            return False
        if structure is None:
            log(u'{} n\'a pas de structure composée', _nom(element))
            return False
        touche = False
        try:
            couches = [(i, structure.GetMaterialId(i))
                       for i in range(structure.LayerCount)]
            log(u'{} : couches {}', _nom(element),
                [(i, str(mid)) for (i, mid) in couches])
            for index, id_couche in couches:
                if id_couche in ids:
                    structure.SetMaterialId(index, id_cible)
                    touche = True
            if touche:
                element.SetCompoundStructure(structure)
        except Exception as erreur:
            log(u'structure composée refusée sur {} : {}', _nom(element), erreur)
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
