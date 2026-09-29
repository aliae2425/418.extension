# -*- coding: utf-8 -*-
"""Ce que tout outil Revit refait sinon : unités, ids, noms, transactions.

Chaque gestionnaire du serveur vendorisé recopiait sa lecture de paramètre,
sa conversion d'id, son ouverture de transaction. Ici c'est écrit une fois.

Les imports Revit sont sous garde : le module s'importe hors Revit, ce qui
permet de tester tout ce qui est pur (formatage, conversions numériques).
"""
from __future__ import unicode_literals

try:
    from Autodesk.Revit import DB
except Exception:
    DB = None


class ErreurOutil(Exception):
    """Échec attendu, à rendre à l'appelant en clair plutôt qu'en trace."""


# --- identité des éléments -----------------------------------------------

def id_valeur(identifiant):
    """``ElementId`` → entier. ``Value`` en 2024+, ``IntegerValue`` avant."""
    valeur = getattr(identifiant, 'Value', None)
    if valeur is None:
        valeur = getattr(identifiant, 'IntegerValue', None)
    return int(valeur) if valeur is not None else 0


def element_id(brut):
    """Entier → ``ElementId``. Accepte déjà un ElementId, ou une chaîne."""
    if DB is None:
        raise ErreurOutil('hors Revit')
    if isinstance(brut, DB.ElementId):
        return brut
    try:
        return DB.ElementId(int(brut))
    except (TypeError, ValueError):
        raise ErreurOutil('identifiant illisible : {0}'.format(brut))


def nom_element(element):
    """Nom d'un élément, '' s'il n'en expose pas.

    ``element.Name`` lève sur certains types sous IronPython — c'est le
    fameux « AttributeError: Name » qu'on voit passer dans les journaux.
    """
    try:
        return element.Name or ''
    except Exception:
        try:
            parametre = element.get_Parameter(
                DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
            return parametre.AsString() or '' if parametre else ''
        except Exception:
            return ''


def categorie_nom(element):
    try:
        return element.Category.Name if element.Category else 'Inconnue'
    except Exception:
        return 'Inconnue'


def decrire(element):
    """La carte d'identité minimale d'un élément, la même partout."""
    return {'id': id_valeur(element.Id), 'nom': nom_element(element),
            'categorie': categorie_nom(element)}


# --- unités ---------------------------------------------------------------

def unite_longueur(doc):
    """``(identifiant, symbole, par_pied, en_pieds)`` de l'unité du projet.

    Revit stocke tout en pieds ; l'architecte lit et écrit dans l'unité de
    son projet. Les deux sens sont rendus parce qu'on convertit dans les
    deux : ce qui sort de Revit, et ce qui y entre.
    """
    options = doc.GetUnits().GetFormatOptions(DB.SpecTypeId.Length)
    unite = options.GetUnitTypeId()
    return (unite.TypeId, symbole_unite(options),
            DB.UnitUtils.ConvertFromInternalUnits(1.0, unite),
            DB.UnitUtils.ConvertToInternalUnits(1.0, unite))


def symbole_unite(options):
    try:
        symbole = options.GetSymbolTypeId()
        if symbole and not symbole.Empty():
            return DB.LabelUtils.GetLabelForSymbol(symbole)
    except Exception:
        pass
    try:
        return DB.LabelUtils.GetLabelForUnit(options.GetUnitTypeId())
    except Exception:
        return ''


def vers_projet(doc, pieds):
    """Longueur interne → unité du projet."""
    return DB.UnitUtils.ConvertFromInternalUnits(
        float(pieds), doc.GetUnits().GetFormatOptions(
            DB.SpecTypeId.Length).GetUnitTypeId())


def vers_revit(doc, valeur):
    """Longueur en unité du projet → pieds internes."""
    return DB.UnitUtils.ConvertToInternalUnits(
        float(valeur), doc.GetUnits().GetFormatOptions(
            DB.SpecTypeId.Length).GetUnitTypeId())


def mesure(doc, valeur, specification):
    """Convertit une mesure interne vers l'unité du projet, avec son symbole.

    ``specification`` est un ``SpecTypeId`` — Area, Volume, Length… Les aires
    ne se convertissent PAS avec le facteur des longueurs : un pied carré
    vaut 0,0929 m², pas 0,3048. L'erreur est tentante et silencieuse.
    """
    try:
        options = doc.GetUnits().GetFormatOptions(specification)
        unite = options.GetUnitTypeId()
        return (round(DB.UnitUtils.ConvertFromInternalUnits(
            float(valeur), unite), 3), symbole_unite(options))
    except Exception:
        return float(valeur), ''


def aire(doc, valeur):
    return mesure(doc, valeur, DB.SpecTypeId.Area)


def volume(doc, valeur):
    return mesure(doc, valeur, DB.SpecTypeId.Volume)


def point(doc, brut):
    """``{"x":…,"y":…,"z":…}`` en unité projet → ``XYZ`` en pieds."""
    if not isinstance(brut, dict):
        raise ErreurOutil('position attendue sous la forme {x, y, z}')
    manquants = [cle for cle in ('x', 'y', 'z') if cle not in brut]
    if manquants:
        raise ErreurOutil('position incomplète, il manque : {0}'.format(
            ', '.join(manquants)))
    return DB.XYZ(*[vers_revit(doc, brut[cle]) for cle in ('x', 'y', 'z')])


# --- paramètres -----------------------------------------------------------

def valeur_parametre(doc, parametre):
    """``(valeur, unité)`` d'un paramètre, longueur déjà convertie.

    C'est ici que se règle « quels paramètres sur les murs » répondu en
    pieds : on regarde le type de donnée, pas le nom.
    """
    if parametre is None or not parametre.HasValue:
        return None, ''
    try:
        rangement = parametre.StorageType
        if rangement == DB.StorageType.String:
            return parametre.AsString(), ''
        if rangement == DB.StorageType.Integer:
            return parametre.AsInteger(), ''
        if rangement == DB.StorageType.ElementId:
            return id_valeur(parametre.AsElementId()), ''
        if rangement == DB.StorageType.Double:
            return _double(doc, parametre)
    except Exception:
        pass
    try:
        return parametre.AsValueString(), ''
    except Exception:
        return None, ''


def _double(doc, parametre):
    """Un réel : converti dans l'unité d'affichage de SON type de donnée."""
    brut = parametre.AsDouble()
    try:
        type_donnee = parametre.Definition.GetDataType()
        if not DB.UnitUtils.IsMeasurableSpec(type_donnee):
            return brut, ''
        options = doc.GetUnits().GetFormatOptions(type_donnee)
        unite = options.GetUnitTypeId()
        return (DB.UnitUtils.ConvertFromInternalUnits(brut, unite),
                symbole_unite(options))
    except Exception:
        return brut, ''


def poser_parametre(doc, parametre, valeur):
    """Écrit une valeur, en convertissant si c'est une mesure. Lève sinon."""
    if parametre is None:
        raise ErreurOutil('paramètre introuvable')
    if parametre.IsReadOnly:
        raise ErreurOutil('paramètre en lecture seule : {0}'.format(
            parametre.Definition.Name))
    rangement = parametre.StorageType
    if rangement == DB.StorageType.String:
        return parametre.Set('{0}'.format(valeur))
    if rangement == DB.StorageType.Integer:
        return parametre.Set(int(valeur))
    if rangement == DB.StorageType.ElementId:
        return parametre.Set(element_id(valeur))
    if rangement == DB.StorageType.Double:
        return parametre.Set(_double_entrant(doc, parametre, valeur))
    raise ErreurOutil('type de paramètre non pris en charge')


def _double_entrant(doc, parametre, valeur):
    try:
        type_donnee = parametre.Definition.GetDataType()
        if DB.UnitUtils.IsMeasurableSpec(type_donnee):
            unite = doc.GetUnits().GetFormatOptions(
                type_donnee).GetUnitTypeId()
            return DB.UnitUtils.ConvertToInternalUnits(float(valeur), unite)
    except Exception:
        pass
    return float(valeur)


# --- sélection d'éléments -------------------------------------------------

def elements_vises(doc, uidoc, donnees, defaut=50):
    """Les éléments sur lesquels un outil travaille, selon ce qu'on lui donne.

    Trois façons de désigner, dans l'ordre de précision : des ``ids``, la
    sélection courante, ou une catégorie dans la vue active. Écrite une fois
    ici plutôt que recopiée dans chaque outil qui agit sur des éléments.
    """
    ids = donnees.get('ids')
    if ids:
        elements = [doc.GetElement(element_id(i)) for i in ids]
        return [e for e in elements if e is not None]
    if donnees.get('selection') and uidoc is not None:
        return [doc.GetElement(i) for i in uidoc.Selection.GetElementIds()]
    nom = donnees.get('categorie')
    if nom:
        return list(collecteur_categorie(doc, nom, donnees.get('vue_active'))
                    .ToElements())[:int(donnees.get('limite', defaut))]
    raise ErreurOutil('préciser « ids », « selection » ou « categorie »')


def collecteur_categorie(doc, nom, vue_active=True):
    categorie = categorie_par_nom(doc, nom)
    if categorie is None:
        raise ErreurOutil('catégorie introuvable : {0}'.format(nom))
    vue = doc.ActiveView if vue_active else None
    collecteur = (DB.FilteredElementCollector(doc, vue.Id) if vue is not None
                  else DB.FilteredElementCollector(doc))
    return collecteur.OfCategoryId(categorie.Id).WhereElementIsNotElementType()


def categorie_par_nom(doc, nom):
    cible = (nom or '').strip().lower()
    for categorie in doc.Settings.Categories:
        if categorie.Name.lower() == cible:
            return categorie
    return None


# --- transactions ---------------------------------------------------------

class transaction(object):
    """``with transaction(doc, 'nom'):`` — un seul Ctrl+Z pour tout le bloc.

    Le socle a déjà ``core.transaction``, mais il importe Revit sans garde et
    ne vit pas dans ce paquet. Celle-ci annule sur exception, ce qui est le
    comportement qu'on veut ici : un outil qui échoue à mi-chemin ne doit
    pas laisser la maquette à moitié modifiée.
    """

    def __init__(self, doc, nom):
        self._transaction = DB.Transaction(doc, nom)

    def __enter__(self):
        self._transaction.Start()
        return self._transaction

    def __exit__(self, type_, valeur, trace):
        if type_ is None:
            self._transaction.Commit()
        else:
            self._transaction.RollBack()
        return False
