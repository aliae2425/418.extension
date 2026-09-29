# -*- coding: utf-8 -*-
"""Les outils Revit de 418, servis sur ``routes.API('418')``.

Remplace ``vendor/mcp-server-for-revit``, supprimé. Le miroir ``git subtree``
interdisait d'éditer ce qu'on utilisait tous les jours : ``list_families``
filtrant sur le nom et pas sur la catégorie, aucune unité de projet, les
feuilles noyées dans un seau « other ». On reprend la surface fonctionnelle
de rvt-mcp (Apache-2.0, C#) en Python, à notre main.

**Trois routes, pas deux cent trente.** Le serveur vendorisé posait un
``@api.route`` par outil, et 418 tenait en face un catalogue écrit à la
main ; les deux ont divergé deux fois. Ici :

- ``GET  /418/outils/``        le catalogue, dérivé du registre ;
- ``POST /418/outil/<nom>``    exécute, quel que soit l'outil ;
- ``GET  /418/etat/``          le lien est-il vivant, quel document.

Un outil se déclare avec ``@registre.outil(...)`` dans ``rvt/outils/`` et
apparaît partout tout seul.

**Aucune socket, aucun fil, aucun WPF** : enregistrer une route pose une
fonction dans le routeur global de pyRevit, rien de plus.
"""
from __future__ import unicode_literals
import json

try:
    from core.journal import journal
except Exception:
    from lib.core.journal import journal

try:
    from rvt import registre
    from rvt.base import ErreurOutil
except Exception:
    from lib.rvt import registre
    from lib.rvt.base import ErreurOutil

try:
    from pyrevit import routes
except Exception:                      # hors Revit : module importable, inerte
    routes = None

_log = journal('rvt')

NOM = '418'


def charger_outils():
    """Importe les familles d'outils. Chacune se déclare au registre.

    Un import qui échoue ne doit pas emporter les autres : une famille en
    moins vaut mieux qu'un chat sans outils. Ce qui manque se lit dans le
    journal, et le catalogue le dira par son absence.
    """
    familles = ('requete', 'vues', 'feuilles', 'parametres', 'familles',
                'graphismes', 'document')
    charges = []
    for famille in familles:
        try:
            try:
                __import__('rvt.outils.' + famille)
            except ImportError:
                __import__('lib.rvt.outils.' + famille)
            charges.append(famille)
        except Exception:
            _log.exception('famille d\'outils « %s » non chargée', famille)
    return charges


def enregistrer():
    """Pose les routes de 418. Sans effet hors Revit."""
    if routes is None:
        return None
    charges = charger_outils()
    api = routes.API(NOM)

    @api.route('/etat/', methods=['GET'])
    def etat(doc):                     # noqa: N802
        """Le lien est-il vivant, et sur quel document."""
        if not doc:
            return routes.make_response(
                data={'actif': True, 'document': None,
                      'revit_disponible': False})
        return routes.make_response(data={
            'actif': True, 'revit_disponible': True,
            'document': doc.Title, 'outils': len(registre.OUTILS)})

    @api.route('/outils/', methods=['GET'])
    def outils():                      # noqa: N802
        """Le catalogue. Le chat le lit au lieu de l'écrire."""
        return routes.make_response(data={'outils': registre.catalogue()})

    @api.route('/outil/<nom>', methods=['POST'])
    def executer(doc, uidoc, request, nom):    # noqa: N802
        """Exécute un outil du registre. Une route pour tous.

        pyRevit choisit ce qu'il injecte d'après la signature du
        gestionnaire : on demande ``doc``, ``uidoc`` et ``request`` une
        bonne fois, et on ne passe à l'outil que ce qu'il a déclaré vouloir.
        """
        complet = nom if nom.startswith('revit_') else 'revit_' + nom
        cible = registre.OUTILS.get(complet)
        if cible is None:
            return routes.make_response(
                data={'erreur': 'outil inconnu : {0}'.format(complet)},
                status=404)
        if not doc:
            return routes.make_response(
                data={'erreur': 'aucun document Revit ouvert'}, status=503)
        contexte = {'doc': doc, 'uidoc': uidoc, 'request': request}
        arguments = _charge(request)
        if cible.irreversible:
            # La seule trace qui restera pour comprendre ce qui a été fait,
            # une fois que c'est fait.
            _log.warning('IRRÉVERSIBLE %s %s', complet, arguments)
        try:
            resultat = cible.fonction(
                *[contexte[besoin] for besoin in cible.besoins],
                **{'donnees': arguments})
            return routes.make_response(data=resultat)
        except ErreurOutil as e:
            # Échec attendu : l'appelant peut corriger sa demande.
            _log.info('%s refusé : %s', complet, e)
            return routes.make_response(data={'erreur': '{0}'.format(e)},
                                        status=400)
        except Exception as e:
            _log.exception('%s a échoué', complet)
            return routes.make_response(
                data={'erreur': '{0}: {1}'.format(type(e).__name__, e)},
                status=500)

    _log.info('routes 418 en place | %d outils, familles : %s',
              len(registre.OUTILS), ', '.join(charges))
    return api


def _charge(request):
    """Corps JSON d'une requête, ``{}`` s'il n'y en a pas d'exploitable."""
    donnees = getattr(request, 'data', None)
    if isinstance(donnees, bytes):
        try:
            donnees = donnees.decode('utf-8')
        except Exception:
            return {}
    if isinstance(donnees, str) or isinstance(donnees, type('')):
        try:
            donnees = json.loads(donnees)
        except ValueError:
            return {}
    return donnees if isinstance(donnees, dict) else {}
