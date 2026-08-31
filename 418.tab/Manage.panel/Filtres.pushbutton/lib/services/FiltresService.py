# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Collecte et écriture Revit de l'outil « Gérer les filtres ».
#
# Le service ne DÉCIDE rien : `reperage` produit un arbre booléen, il le
# traduit en objets Revit ; les ViewModels comptent et notent. Tout ce qui
# n'est pas une conversation avec l'API vit ailleurs, et se teste hors Revit.

try:
    from Autodesk.Revit.DB import (BuiltInCategory, BuiltInParameter, Category,
                                   Element, ElementFilter, ElementId,
                                   ElementParameterFilter,
                                   FilteredElementCollector, FilterElement,
                                   FilterRule, LabelUtils, LogicalAndFilter,
                                   LogicalOrFilter, ParameterFilterElement,
                                   ParameterFilterRuleFactory,
                                   ParameterFilterUtilities,
                                   SelectionFilterElement, SheetCollection,
                                   View, ViewPlan, Viewport)
except Exception:
    BuiltInCategory = None
    BuiltInParameter = None
    Category = None
    Element = None
    ElementFilter = None
    ElementId = None
    ElementParameterFilter = None
    FilteredElementCollector = None
    FilterElement = None
    FilterRule = None
    LabelUtils = None
    LogicalAndFilter = None
    LogicalOrFilter = None
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
    from System import Enum
except Exception:
    Enum = None

try:
    from core.transaction import revit_transaction
except Exception:
    try:
        from lib.core.transaction import revit_transaction
    except Exception:
        revit_transaction = None

try:
    from lib.services import reperage
except Exception:
    from services import reperage

try:
    from lib.services.stockage import StockageReperage
except Exception:
    from services.stockage import StockageReperage

#: Le seul type de vue qui laisse un repère filtrable. Les élévations sont hors
#: du repérage : leur repère est un `ElevationMarker`, un élément d'annotation
#: qui ne porte pas les paramètres sur lesquels une règle s'exprime.
TYPES_COUPE = ('Section',)

#: La catégorie des repères de coupe. Une seule — d'où la disparition de
#: l'essai dégressif sur `OST_Elev` du premier jet.
CATEGORIE_REPERE = 'OST_Sections'

#: Marque de propriété des filtres de l'outil : il ne retire et ne réécrit QUE
#: ce qui commence par là. Attrape aussi les `418_PDR_S…` du prototype, ce qui
#: est voulu — c'est ce qui permet au bouton de retrait de nettoyer un modèle
#: qu'il avait touché.
PREFIXE_FILTRE = reperage.PREFIXE_FILTRE

#: Noms de `BuiltInParameter` tentés pour « Jeu de feuilles », dans l'ordre.
#: Le millésime qui l'expose n'est pas connu de façon fiable, d'où le repli sur
#: la recherche par libellé.
_CANDIDATS_JEU = ('VIEWPORT_SHEET_COLLECTION', 'SHEET_COLLECTION',
                  'SHEET_COLLECTION_NAME')

#: Libellés acceptés pour « Jeu de feuilles », comparés en minuscules. Deux
#: langues suffisent : l'outil tourne en français, la recherche par libellé
#: n'est qu'un filet.
_LIBELLES_JEU = (u'jeu de feuilles', u'sheet collection')

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
        self._stockage = StockageReperage(doc)
        self._parametres = None

    # -- Collecte ---------------------------------------------------------

    def collecter_coupes(self):
        """[{'nom', 'feuille', 'jeu'}] — les coupes, triées par nom.

        Ne sert plus qu'au mode « Coupes choisies » et à la détection de
        dérive : les deux autres modes n'ont besoin d'aucune coupe, c'est tout
        l'intérêt des règles vivantes.
        """
        if self._doc is None or FilteredElementCollector is None:
            return []
        place = self._placement()
        coupes = []
        for vue in self._toutes_les_vues():
            if getattr(vue, 'IsTemplate', False):
                continue
            if self._type(vue) not in TYPES_COUPE:
                continue
            (feuille, jeu) = place.get(_entier(vue.Id), (u'', u''))
            coupes.append({'nom': vue.Name, 'feuille': feuille, 'jeu': jeu})
        coupes.sort(key=lambda c: c['nom'])
        return coupes

    def collecter_plans(self):
        """[{'id', 'uid', 'nom', 'type', 'feuille', 'jeu'}] — TOUTES les vues en
        plan, triées par feuille puis par nom.

        Toutes, et pas seulement celles d'un type mémorisé : un plan de repérage
        se reconnaît à l'usage qu'on en fait, pas à son type de vue. Le type
        n'est plus qu'un critère de sélection préfabriqué, offert à côté de la
        recherche.

        `uid` est l'`UniqueId` : c'est LUI qui range les règles, de sorte qu'un
        plan renommé garde la sienne.
        """
        if self._doc is None or FilteredElementCollector is None:
            return []
        place = self._placement()
        plans = []
        for vue in FilteredElementCollector(self._doc).OfClass(ViewPlan).ToElements():
            if getattr(vue, 'IsTemplate', False):
                continue
            (feuille, jeu) = place.get(_entier(vue.Id), (u'', u''))
            plans.append({'id': vue.Id, 'uid': vue.UniqueId, 'nom': vue.Name,
                          'type': self._nom_de_type_de(vue),
                          'feuille': feuille, 'jeu': jeu})
        plans.sort(key=lambda p: (p['feuille'], p['nom']))
        return plans

    def lire_regles(self):
        """{uid de plan: Regle} — ce que le DOCUMENT porte."""
        return self._stockage.lire()

    def filtres_poses(self):
        """{uid de plan: [noms des filtres 418 posés]}.

        C'est la matière de la détection de dérive : le VM compare ces noms à
        celui que la règle produirait aujourd'hui.
        """
        poses = {}
        if self._doc is None or FilteredElementCollector is None:
            return poses
        for vue in FilteredElementCollector(self._doc).OfClass(ViewPlan).ToElements():
            if getattr(vue, 'IsTemplate', False):
                continue
            noms = [n for n in self._noms_de_filtres(vue)
                    if n.startswith(PREFIXE_FILTRE)]
            if noms:
                poses[vue.UniqueId] = noms
        return poses

    # -- Paramètres filtrables -------------------------------------------

    def parametres(self):
        """{reperage.FEUILLE|JEU|NOM: ElementId} — ceux qui sont filtrables.

        Une clé absente veut dire « ce modèle ne sait pas filtrer là-dessus » :
        le mode qui en dépend se grise, au lieu d'échouer à l'écriture.

        « Jeu de feuilles » est cherché par son LIBELLÉ et non par un
        `BuiltInParameter` supposé : le nom interne n'est pas connu de façon
        fiable, alors que le libellé est celui que l'utilisateur lit dans la
        boîte de dialogue des filtres.
        """
        if self._parametres is not None:
            return self._parametres
        self._parametres = self._resoudre_parametres()
        return self._parametres

    def _resoudre_parametres(self):
        trouves = {}
        categories = self._categories()
        if categories is None:
            return trouves
        try:
            communs = list(ParameterFilterUtilities
                           .GetFilterableParametersInCommon(self._doc, categories))
        except Exception:
            return trouves
        entiers = set(_entier(pid) for pid in communs)

        for (cle, nom_bip) in ((reperage.FEUILLE, 'VIEWPORT_SHEET_NUMBER'),
                               (reperage.NOM, 'VIEW_NAME')):
            pid = self._bip(nom_bip)
            if pid is not None and _entier(pid) in entiers:
                trouves[cle] = pid

        for nom_bip in _CANDIDATS_JEU:
            pid = self._bip(nom_bip)
            if pid is not None and _entier(pid) in entiers:
                trouves[reperage.JEU] = pid
                break
        else:
            pid = self._par_libelle(communs, _LIBELLES_JEU)
            if pid is not None:
                trouves[reperage.JEU] = pid
        return trouves

    @staticmethod
    def _bip(nom):
        """L'ElementId d'un `BuiltInParameter` désigné par son nom, ou None si
        ce millésime ne le connaît pas."""
        if BuiltInParameter is None or ElementId is None:
            return None
        valeur = getattr(BuiltInParameter, nom, None)
        if valeur is None:
            return None
        try:
            return ElementId(valeur)
        except Exception:
            return None

    def _par_libelle(self, communs, libelles):
        """Le premier paramètre filtrable dont le libellé est dans `libelles`.

        Résiste au changement de nom interne ET à la langue de l'installation,
        puisqu'on compare ce que Revit affiche.
        """
        if LabelUtils is None or Enum is None or BuiltInParameter is None:
            return None
        attendus = set(l.lower() for l in libelles)
        for pid in communs:
            entier = _entier(pid)
            if entier >= 0:
                continue          # un paramètre de projet, pas un BuiltIn
            try:
                bip = Enum.ToObject(BuiltInParameter, entier)
                libelle = LabelUtils.GetLabelFor(bip)
            except Exception:
                continue
            if libelle and libelle.lower() in attendus:
                return pid
        return None

    def _categories(self):
        """`List[ElementId]` de la seule catégorie de repères."""
        if List is None or ElementId is None or BuiltInCategory is None:
            return None
        bic = getattr(BuiltInCategory, CATEGORIE_REPERE, None)
        if bic is None:
            return None
        categories = List[ElementId]()
        categories.Add(ElementId(bic))
        return categories

    # -- Écriture ---------------------------------------------------------

    def appliquer(self, cibles):
        """Pose les filtres et enregistre les règles. UNE transaction.

        `cibles` : [{'plan': {...}, 'regle': Regle}] — tous les plans à l'écran,
        gérés ou non. Un plan « Non géré » voit ses filtres 418 retirés.

        Les règles et les filtres tombent dans la même transaction : un état
        « enregistré mais pas posé » ferait diverger l'intention du modèle,
        exactement ce que le stockage dans le document sert à empêcher.
        """
        manque = self._verifier(cibles)
        if manque:
            return manque

        messages = []
        regles = dict((c['plan']['uid'], c['regle']) for c in cibles
                      if c['regle'].mode != reperage.MODE_AUCUN)
        existants = self._filtres_par_nom()
        params = self.parametres()
        categories = self._categories()

        with revit_transaction(self._doc, u'Repérage des coupes'):
            for cible in cibles:
                message = self._poser(cible, params, categories, existants)
                if message:
                    messages.append(message)
            erreur = self._stockage.ecrire(regles)
            if erreur:
                messages.append(erreur)
        if not messages:
            messages.append(u'Aucun plan géré : rien à poser.')
        return messages

    def _verifier(self, cibles):
        """Les raisons de ne RIEN écrire, ou une liste vide.

        Tout se vérifie avant d'ouvrir la transaction : échouer à moitié est
        pire que ne pas commencer.
        """
        if self._doc is None or ParameterFilterElement is None or List is None:
            return [u'API Revit indisponible : rien n\'a été écrit.']
        if revit_transaction is None:
            return [u'Socle indisponible : transaction introuvable.']
        if self._categories() is None:
            return [u'Catégorie « Coupes » introuvable : rien n\'a été écrit.']
        params = self.parametres()
        besoins = set()
        for cible in cibles:
            arbre = reperage.masque(cible['regle'], cible['plan'])
            besoins.update(reperage.parametres_utilises(arbre))
        absents = sorted(b for b in besoins if b not in params)
        if absents:
            return [u'Paramètre non filtrable dans ce modèle : %s. '
                    u'Rien n\'a été écrit.' % u', '.join(absents)]
        return []

    def _poser(self, cible, params, categories, existants):
        """`_ecrire` sous filet.

        Un plan qui échoue ne doit pas emporter les autres : sans ce filet,
        l'exception traverse le `with` et la transaction est annulée EN ENTIER —
        un seul filtre homonyme d'un autre genre suffirait à perdre tout le
        travail.
        """
        try:
            return self._ecrire(cible, params, categories, existants)
        except Exception as erreur:
            return u'%s : filtre non posé (%s).' % (cible['plan'].get('nom'),
                                                    erreur)

    def _ecrire(self, cible, params, categories, existants):
        """Crée ou met à jour le filtre d'UN plan, et le pose."""
        plan = cible['plan']
        regle = cible['regle']
        vue = self._doc.GetElement(plan['id'])
        if vue is None:
            return u'%s : vue introuvable.' % plan.get('nom')

        arbre = reperage.masque(regle, plan)
        nom_filtre = reperage.nom_de_filtre(regle, plan) if arbre else None
        if nom_filtre is None:
            # Rien à poser. Un plan non géré ne mérite pas une ligne de compte
            # rendu — sinon 400 plans en produisent 400 et le seul message qui
            # compte se noie. Sauf s'il RESTAIT un filtre : ça, il faut le dire.
            retires = self._nettoyer(vue, None)
            if regle.mode != reperage.MODE_AUCUN:
                return u'%s : %s — aucun filtre posé.' % (
                    plan['nom'], reperage.phrase(regle, plan))
            if retires:
                return u'%s : non géré, %d filtre%s retiré%s.' % (
                    plan['nom'], retires, u's' if retires > 1 else u'',
                    u's' if retires > 1 else u'')
            return None

        filtre = existants.get(nom_filtre)
        element_filter = self._traduire(arbre, params)
        if filtre is None:
            filtre = ParameterFilterElement.Create(
                self._doc, nom_filtre, categories, element_filter)
            existants[nom_filtre] = filtre
        else:
            filtre.SetCategories(categories)
            filtre.SetElementFilter(element_filter)

        self._nettoyer(vue, nom_filtre)
        if _entier(filtre.Id) not in [_entier(f) for f in vue.GetFilters()]:
            vue.AddFilter(filtre.Id)
        vue.SetFilterVisibility(filtre.Id, False)
        return u'%s : %s.' % (plan['nom'], reperage.phrase(regle, plan))

    def _traduire(self, arbre, params):
        """Arbre booléen de `reperage` -> `ElementFilter` Revit.

        Le OU est la raison d'être de cette fonction : une liste de règles dans
        un `ElementParameterFilter` ne sait faire QUE des ET, et un retrait
        (« tout mon jeu sauf cette coupe ») est un OU une fois nié.
        """
        if arbre[0] in ('et', 'ou'):
            enfants = List[ElementFilter]()
            for noeud in arbre[1]:
                enfants.Add(self._traduire(noeud, params))
            return (LogicalAndFilter(enfants) if arbre[0] == 'et'
                    else LogicalOrFilter(enfants))
        return ElementParameterFilter(self._regle_revit(arbre, params))

    @staticmethod
    def _regle_revit(feuille, params):
        """Une feuille de l'arbre -> `FilterRule`."""
        (propriete, operateur, valeur) = feuille
        pid = params[propriete]
        if operateur == reperage.EGAL:
            return ParameterFilterRuleFactory.CreateEqualsRule(pid, valeur)
        if operateur == reperage.DIFFERENT:
            return ParameterFilterRuleFactory.CreateNotEqualsRule(pid, valeur)
        # PAS_VIDE — « la coupe est posée sur une feuille ».
        #
        # ponytail: `CreateHasValueRule` d'abord, repli sur « différent de la
        # chaîne vide ». Selon le millésime, un paramètre texte non renseigné
        # est tantôt sans valeur, tantôt une chaîne vide, et les deux règles ne
        # se recouvrent pas. Si les coupes non posées disparaissent des plans,
        # c'est ICI qu'il faut regarder.
        for fabrique in ('CreateHasValueRule', 'CreateHasValueParameterRule'):
            methode = getattr(ParameterFilterRuleFactory, fabrique, None)
            if methode is None:
                continue
            try:
                return methode(pid)
            except Exception:
                continue
        return ParameterFilterRuleFactory.CreateNotEqualsRule(pid, u'')

    def retirer_tout(self):
        """Retire de toutes les vues les filtres 418, sans rien supprimer.

        `RemoveFilter` et pas `Delete` : le prototype supprimait le
        `FilterElement` du MODÈLE, ce qui le retirait aussi de toutes les autres
        vues qui l'utilisaient. Les filtres devenus orphelins restent dans le
        modèle — l'onglet Audit les liste en « non utilisés », c'est là qu'on
        les purge.
        """
        if self._doc is None or revit_transaction is None:
            return [u'API Revit indisponible : rien n\'a été retiré.']
        compte = 0
        with revit_transaction(self._doc, u'Retirer les filtres 418'):
            for vue in self._toutes_les_vues():
                compte += self._nettoyer(vue, None)
        return [u'%d filtre%s retiré%s.' % (compte, u's' if compte > 1 else u'',
                                            u's' if compte > 1 else u'')]

    def _nettoyer(self, vue, garder):
        """Retire de la vue les filtres 418 qui ne sont pas `garder`.

        Retourne le nombre de retraits — de quoi rendre compte du bouton de
        retrait sans le compter deux fois.
        """
        retires = 0
        try:
            ids = list(vue.GetFilters())
        except Exception:
            return 0
        for fid in ids:
            try:
                nom = self._doc.GetElement(fid).Name
            except Exception:
                continue
            if nom.startswith(PREFIXE_FILTRE) and nom != garder:
                try:
                    vue.RemoveFilter(fid)
                    retires += 1
                except Exception:
                    continue
        return retires

    def _noms_de_filtres(self, vue):
        noms = []
        try:
            ids = list(vue.GetFilters())
        except Exception:
            return noms
        for fid in ids:
            try:
                noms.append(self._doc.GetElement(fid).Name)
            except Exception:
                continue
        return noms

    def _filtres_par_nom(self):
        filtres = {}
        for filtre in FilteredElementCollector(self._doc).OfClass(FilterElement).ToElements():
            try:
                filtres[filtre.Name] = filtre
            except Exception:
                continue
        return filtres

    # -- Placement --------------------------------------------------------

    def _placement(self):
        """{id entier de vue: (n° de feuille, nom du jeu)} pour les vues posées.

        Un seul balayage des viewports : l'API ne donne pas le chemin inverse
        vue -> feuille, et `ViewSheet.GetAllPlacedViews` demanderait de balayer
        toutes les feuilles pour le même résultat.
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

    def _nom_de_type_de(self, vue):
        try:
            return self._nom_de_type(self._doc.GetElement(vue.GetTypeId()))
        except Exception:
            return u''

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
                'categories': self._categories_de(filtre),
                'vues': sorted(usage['vues']),
                'gabarits': sorted(usage['gabarits']),
                'effets': usage['effets'],
            })
        filtres.sort(key=lambda f: f['nom'])
        return filtres

    def _usages(self):
        """{id entier du filtre: {'vues', 'gabarits', 'effets'}}.

        Un seul balayage des vues : `GetFilters()` est la seule façon de savoir
        où un filtre sert, il n'y a pas de chemin inverse dans l'API. Les vues
        qui n'admettent pas de filtre (légendes, feuilles, certaines
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

    def _categories_de(self, filtre):
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
