# -*- coding: utf-8 -*-
"""Le nom du dossier racine, résolu depuis un motif à jetons.

Même grammaire que le reste de l'extension : ``{projet_numero}``,
``{projet_nom}``, ``{type}``, plus les jetons de date du socle. Un jeton
qu'aucune valeur ne résout DISPARAÎT du nom — jamais de « {…} » brut sur un
dossier qu'un instructeur va ouvrir.

Les infos de projet sont lues ici parce que c'est le seul endroit qui touche
Revit dans cet outil ; l'import est gardé pour que le reste se teste hors
Revit.

``NamingService`` ferait mieux — mais il vit dans BatchExport, et un bouton
n'importe pas un autre bouton. Le jour où un troisième outil résout des
motifs, c'est LUI qu'il faut remonter dans le socle, pas ce fichier qu'il
faut étoffer.
"""
from __future__ import unicode_literals

try:
    from core.token_expander import TokenExpander, sans_jetons_restants
except Exception:
    from lib.core.token_expander import TokenExpander, sans_jetons_restants

try:
    from core.sanitize import sanitize
except Exception:
    from lib.core.sanitize import sanitize

try:
    from Autodesk.Revit.DB import BuiltInParameter
except Exception:
    BuiltInParameter = None


MOTIF_DEFAUT = u'{projet_numero} - {projet_nom} - {type}'


def infos_projet(doc):
    """``{'projet_numero':…, 'projet_nom':…}``, vides hors Revit.

    ``ProjectInformation`` n'expose pas Number et Name comme propriétés
    fiables selon les versions : on passe par les paramètres intégrés, qui
    eux ne bougent pas.
    """
    vides = {u'projet_numero': u'', u'projet_nom': u''}
    if doc is None or BuiltInParameter is None:
        return vides
    try:
        infos = doc.ProjectInformation
    except Exception:
        return vides
    return {
        u'projet_numero': _parametre(infos, BuiltInParameter.PROJECT_NUMBER),
        u'projet_nom': _parametre(infos, BuiltInParameter.PROJECT_NAME),
    }


def _parametre(infos, builtin):
    try:
        parametre = infos.get_Parameter(builtin)
        return parametre.AsString() or u'' if parametre else u''
    except Exception:
        return u''


def resoudre(motif, type_dossier, infos=None, expander=None):
    """Motif -> nom de dossier assaini. Jamais vide : le type sert de repli."""
    contexte = dict(infos or {})
    contexte[u'type'] = type_dossier or u''
    expander = expander or TokenExpander()
    nom = sans_jetons_restants(
        expander.expand(motif or MOTIF_DEFAUT, context=contexte))
    # Tous les jetons vides : plutôt le type nu qu'un dossier « sans titre ».
    return sanitize(nom or type_dossier or u'', fallback=u'dossier')
