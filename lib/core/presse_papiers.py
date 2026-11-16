# -*- coding: utf-8 -*-
"""Historique de presse-papiers façon Win+V, pour éléments 3D et 2D.

L'API Revit ne lit pas le presse-papiers natif : on tient le nôtre. Chaque
Ctrl+C est intercepté (``BeforeExecuted`` seul, la commande native s'exécute
ensuite normalement) et un instantané des éléments sélectionnés est copié
dans un document caché, propre à la session. Coller recopie depuis ce
document vers le document actif.

``Historique``, ``libelle`` et ``decalage_niveau`` sont purs, testables hors
Revit. Le reste est de la glu Revit.
"""
from __future__ import unicode_literals
import datetime
import itertools
from collections import Counter

try:
    import clr
    clr.AddReference('System')
    from System.Collections.Generic import List
    from Autodesk.Revit.DB import (
        CopyPasteOptions, DuplicateTypeAction, ElementId,
        ElementTransformUtils, FilteredElementCollector,
        IDuplicateTypeNamesHandler, Transform, UnitSystem, ViewDrafting,
        ViewFamily, ViewFamilyType, XYZ,
    )
    from Autodesk.Revit.UI import (
        ExternalEvent, IExternalEventHandler, PostableCommand, RevitCommandId,
        UIDocument,
    )
    from Autodesk.Revit.Exceptions import OperationCanceledException
except Exception:
    List = None
    IDuplicateTypeNamesHandler = None
    IExternalEventHandler = None
    OperationCanceledException = None

try:
    from core.journal import journal
except ImportError:
    try:
        from lib.core.journal import journal
    except ImportError:
        journal = None

try:
    from core.transaction import revit_transaction
except ImportError:
    try:
        from lib.core.transaction import revit_transaction
    except ImportError:
        revit_transaction = None

MODES = ('meme_emplacement', 'vue_courante', 'normal')
LIMITE = 20
TRANSACTION_COLLER = "Coller depuis l'historique"

_log = journal('presse_papiers') if journal else None
_compteur = itertools.count(1)


# --- Logique pure -----------------------------------------------------------

def libelle(categories):
    """« 3 Murs, 1 Portes » : catégories par nombre décroissant, puis nom."""
    comptes = Counter(c or 'Sans catégorie' for c in categories)
    ordre = sorted(comptes.items(), key=lambda kv: (-kv[1], kv[0]))
    return ', '.join('{0} {1}'.format(n, nom) for nom, n in ordre)


def decalage_niveau(elevation_source, elevation_cible):
    """Décalage Z d'un niveau à l'autre, 0 si l'un des deux manque."""
    if elevation_source is None or elevation_cible is None:
        return 0.0
    return elevation_cible - elevation_source


class Entree(object):
    """Un instantané. Les attributs ``_*`` ne servent qu'au collage."""

    def __init__(self, libelle='', nb=0, ignores=None, doc_source='',
                 vue_source='', est_2d=False):
        self.id = next(_compteur)
        self.horodatage = datetime.datetime.now()
        self.libelle = libelle
        self.nb = nb
        self.ignores = list(ignores or [])
        self.nb_ignores = len(self.ignores)
        self.doc_source = doc_source
        self.vue_source = vue_source
        self.est_2d = est_2d
        self._ids_3d = []          # ids dans le document caché
        self._ids_2d = []          # ids dans la vue de dessin cachée
        self._vue_dessin = None    # ViewDrafting du document caché
        self._reference = None     # XYZ, coin min de la boîte du groupe
        self._elevation = None     # élévation du niveau de la vue source


class Historique(object):
    """Liste bornée d'entrées, la plus récente d'abord."""

    def __init__(self, limite=LIMITE):
        self.limite = limite
        self.entrees = []
        self._abonnes = []

    def abonner(self, fn):
        self._abonnes.append(fn)

    def _notifier(self):
        for fn in list(self._abonnes):
            try:
                fn()
            except Exception:
                if _log:
                    _log.exception('abonné en échec')

    def ajouter(self, entree):
        self.entrees.insert(0, entree)
        evincees = self.entrees[self.limite:]
        del self.entrees[self.limite:]
        self._notifier()
        return evincees

    def retirer(self, id):
        for i, e in enumerate(self.entrees):
            if e.id == id:
                del self.entrees[i]
                self._notifier()
                return e
        return None

    def vider(self):
        retirees, self.entrees = self.entrees, []
        self._notifier()
        return retirees


class CompteRendu(object):

    def __init__(self, nb_colles=0, ignores=None, annule=False):
        self.nb_colles = nb_colles
        self.ignores = list(ignores or [])
        self.annule = annule


_historique = Historique()


def historique():
    return _historique


# --- Glu Revit : file d'attente sur un seul ExternalEvent --------------------

_file = []
_etat = {'evenement': None, 'liaison': None, 'doc_cache': None}

if IExternalEventHandler is not None:

    class _Gestionnaire(IExternalEventHandler):
        def Execute(self, uiapp):
            while _file:
                fn = _file.pop(0)
                try:
                    fn(uiapp)
                except Exception:
                    if _log:
                        _log.exception('demande en échec')

        def GetName(self):
            return '418 presse-papiers'

    class _TypesDestination(IDuplicateTypeNamesHandler):
        def OnDuplicateTypeNamesFound(self, args):
            return DuplicateTypeAction.UseDestinationTypes


def demander(fn):
    """Met ``fn(uiapp)`` en file et lève l'ExternalEvent."""
    _file.append(fn)
    if _etat['evenement'] is not None:
        _etat['evenement'].Raise()


def _commande_copier():
    postable = getattr(PostableCommand, 'CopyToClipboard', None)
    if postable is not None:
        try:
            return RevitCommandId.LookupPostableCommandId(postable)
        except Exception:
            pass
    return RevitCommandId.LookupCommandId('ID_EDIT_COPY')


def installer(uiapp):
    """Crée l'ExternalEvent et lie Ctrl+C. Idempotent. False si non lié."""
    if IExternalEventHandler is None:
        return False
    if _etat['evenement'] is None:
        _etat['evenement'] = ExternalEvent.Create(_Gestionnaire())
    if _etat['liaison'] is not None:
        return True
    try:
        cmd = _commande_copier()
        if cmd is None or not cmd.CanHaveBinding or cmd.HasBinding:
            if _log:
                _log.warning('Ctrl+C non liable (déjà lié par une autre extension ?)')
            return False
        liaison = uiapp.CreateAddInCommandBinding(cmd)
        # Surtout pas Executed : ce serait remplacer la commande native.
        liaison.BeforeExecuted += _avant_copie
        _etat['liaison'] = liaison
        return True
    except Exception:
        if _log:
            _log.exception('liaison Ctrl+C en échec')
        return False


def _avant_copie(sender, args):
    try:
        doc = args.ActiveDocument
        if doc is None or doc.IsFamilyDocument:
            return
        ids = list(UIDocument(doc).Selection.GetElementIds())
        vue = doc.ActiveView
        if ids:
            demander(lambda uiapp: _capturer(uiapp.Application, doc, ids, vue))
    except Exception:
        if _log:
            _log.exception('lecture de la sélection en échec')


def _options():
    options = CopyPasteOptions()
    options.SetDuplicateTypeNamesHandler(_TypesDestination())
    return options


def _ids(liste):
    return List[ElementId](liste)


def _doc_cache(app):
    # ponytail: un document jamais fermé ni purgé pour la session ; à revoir
    # si sa taille gêne (les types copiés s'y accumulent).
    if _etat['doc_cache'] is None or not _etat['doc_cache'].IsValidObject:
        _etat['doc_cache'] = app.NewProjectDocument(UnitSystem.Metric)
    return _etat['doc_cache']


def _nom(elem):
    cat = elem.Category.Name if elem.Category else 'Sans catégorie'
    return '{0} {1}'.format(cat, elem.Id.IntegerValue)


def _copier(copie, source_ids):
    """Copie le lot, ou élément par élément s'il échoue. → (retenus, nouveaux, ignorés)."""
    try:
        return list(source_ids), list(copie(_ids(source_ids))), []
    except Exception:
        retenus, nouveaux, ignores = [], [], []
        for i in source_ids:
            try:
                nouveaux.extend(copie(_ids([i])))
                retenus.append(i)
            except Exception:
                ignores.append(i)
        return retenus, nouveaux, ignores


def _vue_dessin(doc_cache):
    vft = next(t for t in FilteredElementCollector(doc_cache).OfClass(ViewFamilyType)
               if t.ViewFamily == ViewFamily.Drafting)
    return ViewDrafting.Create(doc_cache, vft.Id)


def _capturer(app, doc, ids, vue):
    if not doc.IsValidObject or not vue.IsValidObject:
        return
    elems = [e for e in (doc.GetElement(i) for i in ids) if e is not None]
    modele = [e.Id for e in elems if e.OwnerViewId == ElementId.InvalidElementId]
    propres = [e.Id for e in elems if e.OwnerViewId == vue.Id]
    hors_vue = [e for e in elems if e.OwnerViewId not in (ElementId.InvalidElementId, vue.Id)]

    cache = _doc_cache(app)
    options = _options()
    entree = Entree(doc_source=doc.Title, vue_source=vue.Name)
    retenus, ignores = [], [_nom(e) for e in hors_vue]
    with revit_transaction(cache, 'Instantané'):
        if modele:
            r, entree._ids_3d, ign = _copier(
                lambda c: ElementTransformUtils.CopyElements(
                    doc, c, cache, Transform.Identity, options), modele)
            retenus += r
            ignores += [_nom(doc.GetElement(i)) for i in ign]
        if propres:
            dessin = _vue_dessin(cache)
            r, entree._ids_2d, ign = _copier(
                lambda c: ElementTransformUtils.CopyElements(
                    vue, c, dessin, Transform.Identity, options), propres)
            retenus += r
            ignores += [_nom(doc.GetElement(i)) for i in ign]
            if r:
                entree._vue_dessin = dessin
            else:
                cache.Delete(dessin.Id)
    if not retenus:
        if _log:
            _log.info('rien de copiable : %s', ', '.join(ignores))
        return

    gardes = [doc.GetElement(i) for i in retenus]
    entree.libelle = libelle(e.Category.Name if e.Category else None for e in gardes)
    entree.nb = len(retenus)
    entree.ignores = ignores
    entree.nb_ignores = len(ignores)
    entree.est_2d = bool(entree._ids_2d)
    entree._reference = _coin_min(gardes, vue)
    entree._elevation = _elevation(vue)
    _supprimer(_historique.ajouter(entree))


def _coin_min(elems, vue):
    boites = [b for b in (e.get_BoundingBox(None) or e.get_BoundingBox(vue)
                          for e in elems) if b is not None]
    if not boites:
        return XYZ.Zero
    return XYZ(min(b.Min.X for b in boites), min(b.Min.Y for b in boites),
               min(b.Min.Z for b in boites))


def _elevation(vue):
    niveau = getattr(vue, 'GenLevel', None)
    return niveau.Elevation if niveau is not None else None


def _supprimer(entrees):
    """Retire du document caché ce que les entrées y avaient copié."""
    cache = _etat['doc_cache']
    if not entrees or cache is None or not cache.IsValidObject:
        return
    ids = []
    for e in entrees:
        ids += e._ids_3d + e._ids_2d
        if e._vue_dessin is not None:
            ids.append(e._vue_dessin.Id)   # emporte ses éléments propres
    try:
        with revit_transaction(cache, 'Évincer'):
            for i in ids:
                if cache.GetElement(i) is not None:
                    cache.Delete(i)
    except Exception:
        if _log:
            _log.exception('éviction en échec')


def retirer(id):
    """Retire une entrée de l'historique ET du document caché (contexte API)."""
    entree = _historique.retirer(id)
    if entree is not None:
        _supprimer([entree])
    return entree


def vider():
    """Vide l'historique et le document caché (contexte API)."""
    _supprimer(_historique.vider())


def coller(uidoc, entree, mode):
    """Colle ``entree`` dans le document actif. À appeler en contexte API."""
    if mode not in MODES:
        raise ValueError('mode inconnu : {0}'.format(mode))
    doc = uidoc.Document
    vue = doc.ActiveView
    cache = _etat['doc_cache']
    if cache is None or not cache.IsValidObject:
        return CompteRendu(ignores=['instantané perdu'])

    dx = dy = dz = 0.0
    if mode != 'meme_emplacement':
        dz = decalage_niveau(entree._elevation, _elevation(vue))
    if mode == 'normal':
        try:
            p = uidoc.Selection.PickPoint('Point de collage')
        except OperationCanceledException:
            return CompteRendu(annule=True)
        except Exception as e:
            # Vue 3D sans plan de travail, feuille… : PickPoint refuse.
            return CompteRendu(ignores=['point de collage : {0}'.format(e)])
        dx, dy = p.X - entree._reference.X, p.Y - entree._reference.Y

    options = _options()
    nouveaux, ignores = [], []
    with revit_transaction(doc, TRANSACTION_COLLER):
        if entree._ids_3d:
            try:
                nouveaux += ElementTransformUtils.CopyElements(
                    cache, _ids(entree._ids_3d), doc,
                    Transform.CreateTranslation(XYZ(dx, dy, dz)), options)
            except Exception as e:
                ignores.append('3D : {0}'.format(e))
        if entree._ids_2d:
            try:
                nouveaux += ElementTransformUtils.CopyElements(
                    entree._vue_dessin, _ids(entree._ids_2d), vue,
                    Transform.CreateTranslation(XYZ(dx, dy, 0)), options)
            except Exception as e:
                ignores.append('2D : {0}'.format(e))
    if nouveaux:
        uidoc.Selection.SetElementIds(_ids(nouveaux))
    return CompteRendu(nb_colles=len(nouveaux), ignores=ignores)
