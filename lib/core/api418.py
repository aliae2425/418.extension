# -*- coding: utf-8 -*-
"""Les routes de 418, à côté de celles du serveur MCP vendorisé.

``vendor/mcp-server-for-revit`` est un miroir ``git subtree`` : on n'y touche
pas, sinon le prochain ``git subtree pull`` part en conflit. Ce qui lui manque
s'ajoute ici, sous notre propre ``routes.API('418')`` — le routeur de pyRevit
est global et sépare les API par leur nom, donc ``/418/...`` et
``/revit_mcp/...`` cohabitent sur le même serveur, le même port. Le jour où
l'amont ajoute l'une de ces routes, on retire la nôtre sans rien casser.

Ne pas confondre avec ``routes418.py``, qui dit seulement OÙ joindre le
serveur. Ici on dit ce qu'il sert.

Trois routes :

- ``GET  /418/unites/``         l'unité de longueur du projet, et de quoi
                               convertir dans les deux sens ;
- ``GET  /418/selection/``      ce que l'architecte a sélectionné dans Revit ;
- ``POST /418/filtre_couleur/`` colore une catégorie par un FILTRE DE VUE,
                               réutilisable et modifiable, là où le
                               ``color_splash`` vendorisé ne pose que des
                               remplacements graphiques élément par élément.

**Aucune socket, aucun fil, aucun WPF** : enregistrer une route pose une
fonction dans le routeur global, rien de plus. C'est ce que fait déjà le
``startup.py`` vendorisé.
"""
from __future__ import unicode_literals

try:
    from core.journal import journal
except Exception:
    from lib.core.journal import journal

_log = journal('api418')

try:
    from pyrevit import routes
    from Autodesk.Revit import DB
except Exception:                      # hors Revit : module importable, inerte
    routes = DB = None


NOM = '418'
# Préfixe des filtres qu'on crée : il les rend reconnaissables dans l'arbre du
# projet, et permet de les retrouver pour les remplacer plutôt que d'en
# empiler un nouveau à chaque appel.
PREFIXE_FILTRE = '418 · '


# --- logique pure, testable hors Revit -----------------------------------

def nom_filtre(categorie, parametre, valeur):
    """Nom lisible et stable d'un filtre. Stable = réutilisé, pas empilé."""
    return '{0}{1} · {2} = {3}'.format(
        PREFIXE_FILTRE, categorie, parametre, valeur if valeur != '' else '(vide)')


def couleurs(nombre):
    """``nombre`` couleurs distinctes, en (r, v, b).

    Reprend le générateur du vendor plutôt que d'en écrire un second : les
    deux façons de colorer doivent donner les mêmes teintes, sinon passer du
    remplacement au filtre changerait toutes les couleurs du projet.
    """
    try:
        from revit_mcp.colors import generate_distinct_colors
    except Exception:
        # Repli : teintes réparties sur le cercle, sans dépendre du vendor.
        return [_tsv_vers_rvb(360.0 * i / max(nombre, 1), 0.65, 0.95)
                for i in range(nombre)]
    return [_rvb(couleur) for couleur in generate_distinct_colors(nombre)]


def _rvb(couleur):
    """Une couleur, quelle que soit sa forme, en ``(r, v, b)``.

    ``generate_distinct_colors`` rend des ``DB.Color`` — pas des tuples, pas
    des chaînes hexa. Le supposer a fait échouer tout appel au filtre de
    couleur, et le repli testé hors Revit ne passait jamais par là.
    """
    for attributs in (('Red', 'Green', 'Blue'), ('R', 'G', 'B')):
        if all(hasattr(couleur, a) for a in attributs):
            return tuple(int(getattr(couleur, a)) for a in attributs)
    if isinstance(couleur, (tuple, list)) and len(couleur) == 3:
        return tuple(int(composante) for composante in couleur)
    # Dernier cas : une chaîne hexa, « #RRGGBB ».
    texte = '{0}'.format(couleur).lstrip('#')
    return tuple(int(texte[i:i + 2], 16) for i in (0, 2, 4))


def _tsv_vers_rvb(teinte, saturation, valeur):
    secteur = int(teinte // 60) % 6
    reste = (teinte / 60.0) - int(teinte // 60)
    clair = valeur * (1 - saturation)
    descend = valeur * (1 - saturation * reste)
    monte = valeur * (1 - saturation * (1 - reste))
    trio = ((valeur, monte, clair), (descend, valeur, clair),
            (clair, valeur, monte), (clair, descend, valeur),
            (monte, clair, valeur), (valeur, clair, descend))[secteur]
    return tuple(int(round(c * 255)) for c in trio)


# --- enregistrement -------------------------------------------------------

def enregistrer():
    """Pose les routes de 418 dans le routeur pyRevit. Sans effet hors Revit."""
    if routes is None or DB is None:
        return None
    api = routes.API(NOM)

    @api.route('/unites/', methods=['GET'])
    def unites(doc):                   # noqa: N802 — signature imposée
        """Unité de longueur du projet, et les deux facteurs de conversion.

        Revit stocke TOUT en pieds. Le modèle, lui, doit parler à
        l'architecte dans l'unité du projet — et recevoir ses coordonnées
        dans cette même unité. D'où les deux sens.
        """
        if not doc:
            return routes.make_response(
                data={'erreur': 'aucun document ouvert'}, status=503)
        try:
            options = doc.GetUnits().GetFormatOptions(DB.SpecTypeId.Length)
            unite = options.GetUnitTypeId()
            return routes.make_response(data={
                'unite': unite.TypeId,
                'libelle': _libelle_unite(unite),
                'symbole': _symbole_unite(options),
                # 1 pied interne vaut N unités d'affichage : pour convertir
                # ce qui SORT de Revit.
                'par_pied': DB.UnitUtils.ConvertFromInternalUnits(1.0, unite),
                # 1 unité d'affichage vaut N pieds : pour convertir ce qui
                # ENTRE, place_family en tête.
                'en_pieds': DB.UnitUtils.ConvertToInternalUnits(1.0, unite),
            })
        except Exception as e:
            _log.exception('lecture des unités')
            return routes.make_response(data={'erreur': '{0}'.format(e)},
                                        status=500)

    @api.route('/selection/', methods=['GET'])
    def selection(doc, uidoc):         # noqa: N802
        """Ce qui est sélectionné dans Revit, pour « fais ça sur ma sélection »."""
        if not doc or not uidoc:
            return routes.make_response(
                data={'erreur': 'aucun document ouvert'}, status=503)
        try:
            elements = []
            for identifiant in uidoc.Selection.GetElementIds():
                element = doc.GetElement(identifiant)
                if element is None:
                    continue
                categorie = element.Category
                elements.append({
                    'id': _valeur_id(identifiant),
                    'nom': _nom_element(element),
                    'categorie': categorie.Name if categorie else 'Inconnue',
                })
            return routes.make_response(data={'count': len(elements),
                                              'elements': elements})
        except Exception as e:
            _log.exception('lecture de la sélection')
            return routes.make_response(data={'erreur': '{0}'.format(e)},
                                        status=500)

    @api.route('/filtre_couleur/', methods=['POST'])
    def filtre_couleur(doc, uidoc, request):   # noqa: N802
        """Colore une catégorie par FILTRES DE VUE, un par valeur distincte.

        Différence avec le ``color_splash`` vendorisé : celui-ci pose un
        remplacement sur chaque élément, invisible dans l'arbre du projet et
        impossible à rejouer. Ici l'architecte récupère des filtres nommés,
        qu'il retrouve dans les propriétés de la vue, réutilise sur une autre
        vue et modifie à la main.

        Charge attendue :
        ``{"category_name": "Portes", "parameter_name": "Mark"}``
        """
        if not doc or not uidoc:
            return routes.make_response(
                data={'erreur': 'aucun document ouvert'}, status=503)
        donnees = _charge(request)
        categorie = donnees.get('category_name')
        parametre = donnees.get('parameter_name')
        if not categorie or not parametre:
            return routes.make_response(
                data={'erreur': 'category_name et parameter_name sont requis'},
                status=400)
        try:
            return routes.make_response(
                data=_poser_filtres(doc, uidoc.ActiveView, categorie,
                                    parametre))
        except Exception as e:
            _log.exception('pose des filtres de couleur')
            return routes.make_response(data={'erreur': '{0}'.format(e)},
                                        status=500)

    _log.info('routes 418 enregistrées (/%s/unites, /selection, '
              '/filtre_couleur)', NOM)
    return api


# --- mise en œuvre --------------------------------------------------------

def _poser_filtres(doc, vue, nom_categorie, nom_parametre):
    """Un filtre par valeur distincte, appliqué à la vue, en une transaction."""
    if vue is None or vue.IsTemplate:
        raise ValueError('aucune vue active où poser un filtre')
    if not vue.AreGraphicsOverridesAllowed():
        raise ValueError('cette vue n\'accepte pas de remplacement graphique '
                         '— se placer dans une vue de modèle, pas une feuille')

    categorie = _categorie(doc, nom_categorie)
    if categorie is None:
        raise ValueError('catégorie introuvable : {0}'.format(nom_categorie))

    elements = (DB.FilteredElementCollector(doc, vue.Id)
                .OfCategoryId(categorie.Id)
                .WhereElementIsNotElementType()
                .ToElements())
    if not elements:
        raise ValueError('aucun élément de « {0} » dans la vue active'.format(
            nom_categorie))

    identifiant_parametre, valeurs = _valeurs_distinctes(elements, nom_parametre)
    if identifiant_parametre is None:
        raise ValueError('paramètre introuvable sur cette catégorie : '
                         '{0}'.format(nom_parametre))
    if not valeurs:
        raise ValueError('le paramètre « {0} » est vide partout'.format(
            nom_parametre))

    palette = couleurs(len(valeurs))
    poses = []
    transaction = DB.Transaction(doc, 'Filtres couleur 418 — {0}'.format(
        nom_parametre))
    transaction.Start()
    try:
        for rang, valeur in enumerate(valeurs):
            nom = nom_filtre(nom_categorie, nom_parametre, valeur)
            filtre = _filtre_existant(doc, nom) or _creer_filtre(
                doc, nom, categorie.Id, identifiant_parametre, valeur)
            if filtre is None:
                continue
            if not vue.IsFilterApplied(filtre.Id):
                vue.AddFilter(filtre.Id)
            vue.SetFilterOverrides(filtre.Id,
                                   _remplacement(doc, palette[rang]))
            poses.append({'filtre': nom, 'valeur': valeur,
                          'couleur': palette[rang]})
        transaction.Commit()
    except Exception:
        transaction.RollBack()
        raise
    return {'status': 'success', 'vue': vue.Name, 'count': len(poses),
            'filtres': poses}


def _categorie(doc, nom):
    for categorie in doc.Settings.Categories:
        if categorie.Name == nom:
            return categorie
    return None


def _valeurs_distinctes(elements, nom_parametre):
    """``(id du paramètre, valeurs triées)``. Les vides sont écartées."""
    identifiant, vues = None, []
    for element in elements:
        parametre = element.LookupParameter(nom_parametre)
        if parametre is None:
            continue
        if identifiant is None:
            identifiant = parametre.Id
        valeur = _texte_parametre(parametre)
        if valeur and valeur not in vues:
            vues.append(valeur)
    return identifiant, sorted(vues)


def _texte_parametre(parametre):
    try:
        if parametre.StorageType == DB.StorageType.String:
            return parametre.AsString() or ''
        return parametre.AsValueString() or ''
    except Exception:
        return ''


def _filtre_existant(doc, nom):
    for filtre in (DB.FilteredElementCollector(doc)
                   .OfClass(DB.ParameterFilterElement)):
        if filtre.Name == nom:
            return filtre
    return None


def _creer_filtre(doc, nom, identifiant_categorie, identifiant_parametre,
                  valeur):
    from System.Collections.Generic import List
    categories = List[DB.ElementId]()
    categories.Add(identifiant_categorie)
    filtre = DB.ParameterFilterElement.Create(doc, nom, categories)
    filtre.SetElementFilter(DB.ElementParameterFilter(
        _regle_egale(identifiant_parametre, valeur)))
    return filtre


def _regle_egale(identifiant_parametre, valeur):
    """``CreateEqualsRule`` a perdu son argument ``caseSensitive`` en 2022.

    Les deux signatures coexistent selon la version de Revit ; choisir au
    hasard donne un TypeError que la route remonterait en « 500 » sans dire
    pourquoi. On tente la moderne, puis l'ancienne.
    """
    fabrique = DB.ParameterFilterRuleFactory
    try:
        return fabrique.CreateEqualsRule(identifiant_parametre, valeur)
    except TypeError:
        return fabrique.CreateEqualsRule(identifiant_parametre, valeur, False)


def _remplacement(doc, rvb):
    couleur = DB.Color(rvb[0], rvb[1], rvb[2])
    remplacement = DB.OverrideGraphicSettings()
    remplacement.SetProjectionLineColor(couleur)
    remplacement.SetCutLineColor(couleur)
    motif = _motif_plein(doc)
    if motif is not None:
        remplacement.SetSurfaceForegroundPatternId(motif)
        remplacement.SetSurfaceForegroundPatternColor(couleur)
        remplacement.SetCutForegroundPatternId(motif)
        remplacement.SetCutForegroundPatternColor(couleur)
    return remplacement


def _motif_plein(doc):
    for motif in (DB.FilteredElementCollector(doc)
                  .OfClass(DB.FillPatternElement)):
        if motif.GetFillPattern().IsSolidFill:
            return motif.Id
    return None


# --- petits utilitaires ---------------------------------------------------

def _charge(request):
    import json
    donnees = getattr(request, 'data', None)
    if isinstance(donnees, str):
        try:
            donnees = json.loads(donnees)
        except ValueError:
            return {}
    return donnees if isinstance(donnees, dict) else {}


def _libelle_unite(unite):
    try:
        return DB.LabelUtils.GetLabelForUnit(unite)
    except Exception:
        return unite.TypeId


def _symbole_unite(options):
    try:
        symbole = options.GetSymbolTypeId()
        if symbole and not symbole.Empty():
            return DB.LabelUtils.GetLabelForSymbol(symbole)
    except Exception:
        pass
    return ''


def _valeur_id(identifiant):
    # Revit 2024+ expose Value ; les versions d'avant, IntegerValue.
    return getattr(identifiant, 'Value', None) or getattr(
        identifiant, 'IntegerValue', 0)


def _nom_element(element):
    try:
        return element.Name
    except Exception:
        return ''
