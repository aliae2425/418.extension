# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Collecte Revit de l'outil « Gérer les filtres ».
#
# Le service ne fait QUE lire et mettre en dictionnaires : tout le comptage,
# le regroupement et la notation vivent dans les ViewModels, qui tournent donc
# hors Revit et se testent. Même partage que MaterialService / AuditPageVM.

try:
    from Autodesk.Revit.DB import (BuiltInCategory, BuiltInParameter, Category,
                                   Element, ElementId, ElementParameterFilter,
                                   FilteredElementCollector, FilterElement,
                                   FilterRule, ParameterFilterElement,
                                   ParameterFilterRuleFactory,
                                   ParameterFilterUtilities,
                                   SelectionFilterElement, SheetCollection,
                                   View, ViewPlan, Viewport)
except Exception:
    BuiltInCategory = None
    BuiltInParameter = None
    Category = None
    Element = None
    ElementId = None
    ElementParameterFilter = None
    FilteredElementCollector = None
    FilterElement = None
    FilterRule = None
    ParameterFilterElement = None
    ParameterFilterRuleFactory = None
    ParameterFilterUtilities = None
    SelectionFilterElement = None
    SheetCollection = None
    View = None
    ViewPlan = None
    Viewport = None

try:
    from System.Collections.Generic import List
except Exception:
    List = None

try:
    from core.transaction import revit_transaction
except Exception:
    try:
        from lib.core.transaction import revit_transaction
    except Exception:
        revit_transaction = None

# Les deux types de vue que l'onglet Coupes liste pour l'instant.
TYPES_COUPE = ('Section', 'Elevation')

#: Préfixe des filtres fabriqués par l'onglet Repérage. Sert de marque de
#: propriété : l'outil ne retire et ne réécrit QUE ce qui commence par là.
#: Le prototype, lui, supprimait tous les filtres de la vue — 418 ou pas.
PREFIXE_FILTRE = u'418_PDR_S'

#: Catégories des repères à masquer sur un plan de repérage, par ordre de
#: préférence. `OST_Elev` est le marqueur d'élévation (un `ElevationMarker`,
#: pas une vue) : rien ne garantit qu'il porte « Nom de la vue », d'où
#: l'essai dégressif de `_categories_et_parametre`.
_CATS_REPERES = ('OST_Sections', 'OST_Elev')

#: Nom impossible pour une vue : sert de règle « ne rien laisser passer »
#: quand un PDR ne doit montrer AUCUN repère. Une liste de règles vide n'est
#: pas un filtre valide, il faut donc bien une règle.
_AUCUN = u'418_PDR_AUCUN'

#: Sondes de surcharge graphique : (nom de propriété, « est-elle posée ? »).
#: Un filtre laissé visible ET sans aucune de ces surcharges ne change rien à
#: l'affichage — c'est ce que l'audit appelle « sans effet ».
#:
#: ponytail: liste de sondes plutôt qu'une comparaison à un
#: OverrideGraphicSettings neuf — la classe n'a pas d'égalité, et énumérer les
#: propriétés une à une reste lisible. Une surcharge exotique non sondée passe
#: pour « sans effet » ; ajouter la propriété ici suffit à la rattraper.
_SONDES = (
    ('Halftone', bool),
    ('Transparency', lambda v: int(v) > 0),
    ('DetailLevel', lambda v: v.ToString() != 'Undefined'),
    ('ProjectionLineColor', lambda v: bool(v.IsValid)),
    ('CutLineColor', lambda v: bool(v.IsValid)),
    ('ProjectionLineWeight', lambda v: int(v) > 0),
    ('CutLineWeight', lambda v: int(v) > 0),
    ('ProjectionLinePatternId', lambda v: _pose(v)),
    ('CutLinePatternId', lambda v: _pose(v)),
    ('SurfaceForegroundPatternId', lambda v: _pose(v)),
    ('SurfaceBackgroundPatternId', lambda v: _pose(v)),
    ('CutForegroundPatternId', lambda v: _pose(v)),
    ('CutBackgroundPatternId', lambda v: _pose(v)),
    # Les quatre drapeaux de visibilité de motif valent True par défaut :
    # c'est leur passage à False qui est une surcharge.
    ('SurfaceForegroundPatternVisible', lambda v: not v),
    ('SurfaceBackgroundPatternVisible', lambda v: not v),
    ('CutForegroundPatternVisible', lambda v: not v),
    ('CutBackgroundPatternVisible', lambda v: not v),
)


def _pose(element_id):
    """Vrai si l'ElementId désigne vraiment quelque chose."""
    return _entier(element_id) > 0


def _entier(element_id):
    """Valeur entière d'un ElementId, quel que soit le millésime.

    `IntegerValue` est déprécié depuis 2024 au profit de `Value` ; on tente
    donc `Value` d'abord. Sert de clé de dictionnaire : un ElementId n'est pas
    hachable de façon fiable sous IronPython.
    """
    for attribut in ('Value', 'IntegerValue'):
        try:
            return int(getattr(element_id, attribut))
        except Exception:
            continue
    return -1


class FiltresService(object):
    def __init__(self, doc=None):
        self._doc = doc

    # -- Onglet Coupes ----------------------------------------------------

    def collecter_coupes(self):
        """[{'id', 'nom', 'type', 'feuille', 'jeu'}] — coupes et élévations,
        triées par nom.

        `type` est le nom brut de `ViewType` ('Section' / 'Elevation') : le
        tri par nom de ViewType est la forme utilisée partout dans le dépôt,
        elle survit aux vues qui ne dérivent pas de la classe attendue.

        `feuille` / `jeu` : là où la vue est POSÉE. Vides si elle ne l'est pas
        — une coupe hors feuille n'a pas de jeu, donc pas de repérage « par
        jeu » possible.
        """
        if self._doc is None or FilteredElementCollector is None:
            return []
        place = self._placement()
        vues = []
        for vue in self._toutes_les_vues():
            if getattr(vue, 'IsTemplate', False):
                continue
            type_vue = self._type(vue)
            if type_vue in TYPES_COUPE:
                (feuille, jeu) = place.get(_entier(vue.Id), (u'', u''))
                vues.append({'id': vue.Id, 'nom': vue.Name, 'type': type_vue,
                             'feuille': feuille, 'jeu': jeu})
        vues.sort(key=lambda v: v['nom'])
        return vues

    def titre_document(self):
        """Titre du document, clé de rangement des règles dans la config.

        `UserConfig` est un fichier par utilisateur, pas par projet : sans
        cette clé, les règles d'un projet s'appliqueraient aux vues de même
        nom du projet suivant — et « Coupe AA » existe dans tous.
        """
        try:
            return self._doc.Title
        except Exception:
            return u''

    # -- Onglet Repérage ---------------------------------------------------

    def types_de_plan(self):
        """[{'id' (entier), 'nom'}] — les types de vue en plan du modèle.

        Le plan de repérage se reconnaît à SON TYPE de vue : c'est le réglage
        que l'outil mémorise, comme le prototype de `origin/section-filter`.
        Un type sert donc à désigner d'un coup tous les PDR du projet.
        """
        if self._doc is None or FilteredElementCollector is None:
            return []
        types = {}
        for vue in FilteredElementCollector(self._doc).OfClass(ViewPlan).ToElements():
            if getattr(vue, 'IsTemplate', False):
                continue
            entier = _entier(vue.GetTypeId())
            if entier <= 0 or entier in types:
                continue
            try:
                types[entier] = self._nom_de_type(self._doc.GetElement(vue.GetTypeId()))
            except Exception:
                continue
        resultat = [{'id': k, 'nom': v} for (k, v) in types.items() if v]
        resultat.sort(key=lambda t: t['nom'])
        return resultat

    def collecter_pdr(self, type_id):
        """[{'id', 'nom', 'feuille', 'jeu'}] — les plans de repérage.

        Un PDR est une vue en plan du type mémorisé. Celles qui ne sont
        posées sur aucune feuille sont gardées : elles restent filtrables, et
        les écarter en silence donnerait un « il en manque » inexplicable.
        Triées par feuille puis par nom, l'ordre dans lequel on les parcourt.
        """
        if self._doc is None or FilteredElementCollector is None or not type_id:
            return []
        try:
            attendu = int(type_id)
        except Exception:
            return []
        place = self._placement()
        pdrs = []
        for vue in FilteredElementCollector(self._doc).OfClass(ViewPlan).ToElements():
            if getattr(vue, 'IsTemplate', False):
                continue
            if _entier(vue.GetTypeId()) != attendu:
                continue
            (feuille, jeu) = place.get(_entier(vue.Id), (u'', u''))
            pdrs.append({'id': vue.Id, 'nom': vue.Name,
                         'feuille': feuille, 'jeu': jeu})
        pdrs.sort(key=lambda p: (p['feuille'], p['nom']))
        return pdrs

    def appliquer_reperage(self, cibles):
        """Pose sur chaque PDR le filtre qui masque les repères des AUTRES
        coupes. Une transaction, une liste de messages en retour.

        `cibles` : [{'id', 'nom', 'feuille', 'visibles': [noms de coupes]}].
        Le filtre est nommé d'après la feuille du PDR (ou son nom s'il n'est
        pas posé) et REPRIS s'il existe déjà : deux passages ne laissent
        qu'un filtre par plan.

        L'inversion est le cœur : Revit sait masquer ce qu'une règle
        SÉLECTIONNE, on lui fait donc sélectionner « toutes les vues dont le
        nom n'est aucun des noms visibles » (des `NotEquals` en ET), et on
        coupe la visibilité. C'est ce qui remplace le `NotContains` sur le
        numéro de feuille du prototype, qui ne savait dire que « même
        feuille ».
        """
        if self._doc is None or ParameterFilterElement is None or List is None:
            return [u'API Revit indisponible : rien n\'a été écrit.']
        if revit_transaction is None:
            return [u'Socle indisponible : transaction introuvable.']
        (categories, parametre, ecartees) = self._categories_et_parametre()
        if parametre is None:
            return [u'« Nom de la vue » n\'est filtrable pour aucune '
                    u'catégorie de repère : rien n\'a été écrit.']
        messages = []
        for nom in ecartees:
            messages.append(u'Catégorie « %s » écartée : elle ne porte pas '
                            u'« Nom de la vue ».' % nom)
        existants = self._filtres_par_nom()
        with revit_transaction(self._doc, u'Repérage des coupes'):
            for cible in cibles:
                messages.append(
                    self._poser_filtre(cible, categories, parametre, existants))
        return messages

    def _poser_filtre(self, cible, categories, parametre, existants):
        """`_ecrire_filtre` sous filet.

        Un plan qui échoue ne doit pas emporter les autres : sans ce filet,
        l'exception traverse le `with` et la transaction est annulée EN
        ENTIER — un seul filtre homonyme d'un autre genre suffirait à perdre
        tout le travail.
        """
        try:
            return self._ecrire_filtre(cible, categories, parametre, existants)
        except Exception as erreur:
            return u'%s : filtre non posé (%s).' % (cible.get('nom'), erreur)

    def _ecrire_filtre(self, cible, categories, parametre, existants):
        """Crée ou met à jour le filtre d'UN plan de repérage, et le pose."""
        vue = self._doc.GetElement(cible['id'])
        if vue is None:
            return u'%s : vue introuvable.' % cible.get('nom')
        visibles = cible.get('visibles') or []
        nom_filtre = PREFIXE_FILTRE + (cible.get('feuille') or cible.get('nom'))
        # List[FilterRule] et pas List[<type concret de la règle>] : IList
        # n'est pas covariant, un List[FilterStringRule] serait refusé par
        # ElementParameterFilter.
        regles = List[FilterRule]()
        for nom in (visibles or [_AUCUN]):
            regles.Add(ParameterFilterRuleFactory.CreateNotEqualsRule(
                parametre, nom))
        filtre = existants.get(nom_filtre)
        if filtre is None:
            filtre = ParameterFilterElement.Create(
                self._doc, nom_filtre, categories,
                ElementParameterFilter(regles))
            existants[nom_filtre] = filtre
        else:
            filtre.SetCategories(categories)
            filtre.SetElementFilter(ElementParameterFilter(regles))
        self._nettoyer(vue, nom_filtre)
        if _entier(filtre.Id) not in [_entier(f) for f in vue.GetFilters()]:
            vue.AddFilter(filtre.Id)
        vue.SetFilterVisibility(filtre.Id, False)
        return u'%s : %d repère%s visible%s.' % (
            cible['nom'], len(visibles),
            u's' if len(visibles) > 1 else u'',
            u's' if len(visibles) > 1 else u'')

    def _nettoyer(self, vue, garder):
        """Retire de la vue les filtres 418 qui ne sont plus le sien.

        `RemoveFilter` et pas `Delete` : le prototype supprimait le
        FilterElement du MODÈLE, ce qui le retirait aussi de toutes les
        autres vues qui l'utilisaient. Les filtres 418 devenus orphelins
        restent dans le modèle — l'onglet Audit les liste en « non
        utilisés », c'est là qu'on les purge.
        """
        try:
            ids = list(vue.GetFilters())
        except Exception:
            return
        for fid in ids:
            try:
                nom = self._doc.GetElement(fid).Name
            except Exception:
                continue
            if nom.startswith(PREFIXE_FILTRE) and nom != garder:
                try:
                    vue.RemoveFilter(fid)
                except Exception:
                    continue

    def _filtres_par_nom(self):
        filtres = {}
        for filtre in FilteredElementCollector(self._doc).OfClass(FilterElement).ToElements():
            try:
                filtres[filtre.Name] = filtre
            except Exception:
                continue
        return filtres

    def _categories_et_parametre(self):
        """(catégories, paramètre « Nom de la vue », noms écartés).

        Essai dégressif : les deux catégories de repères, puis les coupes
        seules. Un repère d'élévation est un `ElevationMarker` et non une
        vue ; s'il ne porte pas « Nom de la vue », le paramètre n'est plus
        commun aux deux catégories et Revit refuserait le filtre. Mieux vaut
        écarter la catégorie EN LE DISANT que de tout faire échouer.
        """
        if ParameterFilterUtilities is None or List is None:
            return ([], None, [])
        try:
            filtrables = set(_entier(c) for c in
                             ParameterFilterUtilities.GetAllFilterableCategories())
        except Exception:
            filtrables = None
        souhaitees = []
        for nom in _CATS_REPERES:
            bic = getattr(BuiltInCategory, nom, None)
            if bic is None:
                continue
            cat_id = ElementId(bic)
            if filtrables is None or _entier(cat_id) in filtrables:
                souhaitees.append((nom, cat_id))
        for taille in range(len(souhaitees), 0, -1):
            essai = souhaitees[:taille]
            categories = List[ElementId]()
            for (_, cat_id) in essai:
                categories.Add(cat_id)
            parametre = self._parametre_nom_de_vue(categories)
            if parametre is not None:
                return (categories, parametre,
                        [nom for (nom, _) in souhaitees[taille:]])
        return ([], None, [nom for (nom, _) in souhaitees])

    def _parametre_nom_de_vue(self, categories):
        """`VIEW_NAME` s'il est filtrable pour TOUTES ces catégories."""
        cible = ElementId(BuiltInParameter.VIEW_NAME)
        try:
            communs = ParameterFilterUtilities.GetFilterableParametersInCommon(
                self._doc, categories)
        except Exception:
            return None
        for pid in communs:
            if _entier(pid) == _entier(cible):
                return cible
        return None

    def _placement(self):
        """{id entier de vue: (n° de feuille, nom du jeu)} pour les vues posées.

        Un seul balayage des viewports : l'API ne donne pas le chemin inverse
        vue -> feuille, et `ViewSheet.GetAllPlacedViews` demanderait de
        balayer toutes les feuilles pour le même résultat.
        """
        place = {}
        if Viewport is None or self._doc is None:
            return place
        jeux = self._noms_de_jeu()
        try:
            viewports = FilteredElementCollector(self._doc).OfClass(Viewport).ToElements()
        except Exception:
            return place
        for viewport in viewports:
            try:
                feuille = self._doc.GetElement(viewport.SheetId)
                place[_entier(viewport.ViewId)] = (
                    feuille.SheetNumber,
                    jeux.get(_entier(getattr(feuille, 'SheetCollectionId', None)), u''))
            except Exception:
                continue
        return place

    def _noms_de_jeu(self):
        """{id entier du jeu de feuilles: nom}."""
        noms = {}
        if SheetCollection is None or self._doc is None:
            return noms
        try:
            collections = FilteredElementCollector(self._doc).OfClass(SheetCollection).ToElements()
        except Exception:
            return noms
        for collection in collections:
            try:
                noms[_entier(collection.Id)] = collection.Name
            except Exception:
                continue
        return noms

    @staticmethod
    def _nom_de_type(element):
        """Nom d'un type de vue, même quand `.Name` est masqué.

        Sur un `ViewFamilyType`, IronPython peut résoudre `.Name` vers la
        propriété de `View` plutôt que celle d'`Element` — d'où le détour du
        prototype par `Element.Name.__get__`, gardé ici.
        """
        for lecture in (lambda e: Element.Name.__get__(e), lambda e: e.Name):
            try:
                nom = lecture(element)
                if nom:
                    return nom
            except Exception:
                continue
        return u''

    # -- Onglet Audit -----------------------------------------------------

    def collecter_filtres(self):
        """[{...}] — un dictionnaire par filtre du modèle, trié par nom.

        Clés : `nom`, `genre` ('parametrique' | 'selection'), `categories`
        (noms lisibles), `vues` et `gabarits` (noms de ce qui l'applique),
        `effets` (nombre d'applications qui changent vraiment l'affichage).

        Que des types Python : l'AuditPageVM en dérive tous ses chiffres sans
        jamais retoucher au document, et se teste hors Revit.
        """
        if self._doc is None or FilteredElementCollector is None:
            return []
        usages = self._usages()
        filtres = []
        for filtre in FilteredElementCollector(self._doc).OfClass(FilterElement).ToElements():
            usage = usages.get(_entier(filtre.Id), None) or {
                'vues': [], 'gabarits': [], 'effets': 0}
            filtres.append({
                'nom': filtre.Name,
                'genre': self._genre(filtre),
                'categories': self._categories(filtre),
                'vues': sorted(usage['vues']),
                'gabarits': sorted(usage['gabarits']),
                'effets': usage['effets'],
            })
        filtres.sort(key=lambda f: f['nom'])
        return filtres

    def _usages(self):
        """{id entier du filtre: {'vues', 'gabarits', 'effets'}}.

        Un seul balayage des vues : `GetFilters()` est la seule façon de
        savoir où un filtre sert, il n'y a pas de chemin inverse dans l'API.
        Les vues qui n'admettent pas de filtre (légendes, feuilles, certaines
        nomenclatures) lèvent — d'où le try/except par vue.
        """
        usages = {}
        for vue in self._toutes_les_vues():
            try:
                ids = list(vue.GetFilters())
            except Exception:
                continue
            for fid in ids:
                entree = usages.setdefault(
                    _entier(fid), {'vues': [], 'gabarits': [], 'effets': 0})
                ou = 'gabarits' if getattr(vue, 'IsTemplate', False) else 'vues'
                entree[ou].append(vue.Name)
                if self._a_un_effet(vue, fid):
                    entree['effets'] += 1
        return usages

    @staticmethod
    def _a_un_effet(vue, fid):
        """Vrai si l'application du filtre change quelque chose à l'écran."""
        try:
            if not vue.GetFilterVisibility(fid):
                return True                 # le filtre masque : effet certain
        except Exception:
            pass
        try:
            surcharges = vue.GetFilterOverrides(fid)
        except Exception:
            return True                     # dans le doute, pas d'accusation
        for (propriete, est_posee) in _SONDES:
            try:
                if est_posee(getattr(surcharges, propriete)):
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    def _genre(filtre):
        if SelectionFilterElement is not None and isinstance(filtre, SelectionFilterElement):
            return 'selection'
        return 'parametrique'

    def _categories(self, filtre):
        """Noms des catégories ciblées. Vide pour un filtre de sélection."""
        try:
            ids = list(filtre.GetCategories())
        except Exception:
            return []
        noms = []
        for cat_id in ids:
            noms.append(self._nom_categorie(cat_id))
        return sorted(n for n in noms if n)

    def _nom_categorie(self, cat_id):
        try:
            categorie = Category.GetCategory(self._doc, cat_id)
        except Exception:
            categorie = None
        if categorie is None:
            return u'#{}'.format(_entier(cat_id))
        try:
            return categorie.Name
        except Exception:
            return u''

    # -- Commun -----------------------------------------------------------

    def _toutes_les_vues(self):
        """Toutes les vues du document, GABARITS COMPRIS.

        Contrairement à `core.selection.all_views`, qui les écarte : ici un
        gabarit est justement l'endroit où un filtre DEVRAIT vivre.
        """
        return list(FilteredElementCollector(self._doc).OfClass(View).ToElements())

    @staticmethod
    def _type(vue):
        try:
            return vue.ViewType.ToString()
        except Exception:
            return u''
