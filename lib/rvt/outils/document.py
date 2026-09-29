# -*- coding: utf-8 -*-
"""Document et exécution de code : tout ce qui ne s'annule pas.

Aucun de ces outils ne pose de transaction. ``Ctrl+Z`` n'y peut rien, et
``synchroniser`` pousse sur le central — donc chez toute l'équipe. Ils sont
marqués ``irreversible`` dans le registre : le routeur les journalise en
WARNING avec leurs arguments, et l'invite système impose au modèle une
demande explicite avant de les appeler.
"""
from __future__ import unicode_literals
import sys

try:
    from rvt.registre import outil
    from rvt import base
except Exception:
    from lib.rvt.registre import outil
    from lib.rvt import base

try:
    from Autodesk.Revit import DB
except Exception:
    DB = None

try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO


@outil('enregistrer',
       'DANGER — enregistre le projet. IRRÉVERSIBLE : écrase la version sur '
       'disque, Ctrl+Z ne la ramène pas. Jamais sans demande explicite.',
       proprietes={'chemin': {
           'type': 'string',
           'description': 'pour un « enregistrer sous » ; sur place si omis'}},
       irreversible=True)
def enregistrer(doc, donnees=None):
    donnees = donnees or {}
    chemin = donnees.get('chemin')
    if chemin:
        options = DB.SaveAsOptions()
        options.OverwriteExistingFile = False
        doc.SaveAs(chemin, options)
        return {'enregistre': chemin}
    doc.Save()
    return {'enregistre': doc.PathName or doc.Title}


@outil('synchroniser',
       'DANGER — synchronise avec le fichier central. IRRÉVERSIBLE, et '
       'visible par toute l\'équipe. Jamais sans demande explicite.',
       proprietes={
           'commentaire': {'type': 'string'},
           'compacter': {'type': 'boolean'},
           'liberer_tout': {'type': 'boolean',
                            'description': 'libérer les emprunts (défaut oui)'}},
       irreversible=True)
def synchroniser(doc, donnees=None):
    donnees = donnees or {}
    if not doc.IsWorkshared:
        raise base.ErreurOutil('ce projet n\'est pas en travail partagé')
    options = DB.SynchronizeWithCentralOptions()
    options.Comment = donnees.get('commentaire') or ''
    options.Compact = bool(donnees.get('compacter'))
    liberer = DB.RelinquishOptions(False)
    if donnees.get('liberer_tout', True):
        liberer.StandardWorksets = True
        liberer.ViewWorksets = True
        liberer.FamilyWorksets = True
        liberer.UserWorksets = True
        liberer.CheckedOutElements = True
    options.SetRelinquishOptions(liberer)
    doc.SynchronizeWithCentral(DB.TransactWithCentralOptions(), options)
    return {'synchronise': doc.Title,
            'commentaire': options.Comment}


@outil('executer_code',
       'DANGER — exécute du code IronPython dans Revit. Irréversible si '
       'transaction vaut false. Dernier recours, quand aucun autre outil ne '
       'fait l\'affaire, et jamais sans l\'accord explicite de l\'architecte '
       'dans son dernier message. « doc » et « uidoc » sont disponibles, et '
       'ce que tu poses dans « resultat » est renvoyé.',
       proprietes={
           'code': {'type': 'string', 'description': 'IronPython 2.7'},
           'description': {'type': 'string',
                           'description': 'ce que fait le code, en français'},
           'transaction': {'type': 'boolean',
                           'description': 'true (défaut) = annulable'}},
       requis=('code',), irreversible=True, besoins=('doc', 'uidoc'))
def executer_code(doc, uidoc, donnees=None):
    donnees = donnees or {}
    code = donnees.get('code') or ''
    if not code.strip():
        raise base.ErreurOutil('aucun code fourni')
    portee = {'doc': doc, 'uidoc': uidoc, 'DB': DB, 'base': base,
              'resultat': None}
    sortie, ancienne = StringIO(), sys.stdout
    sys.stdout = sortie
    try:
        if donnees.get('transaction', True):
            with base.transaction(doc, '418 — {0}'.format(
                    donnees.get('description') or 'code')):
                exec(code, portee)
        else:
            exec(code, portee)
    except Exception as e:
        # On rend l'erreur ET ce qui avait déjà été imprimé : la sortie
        # partielle dit souvent où ça a cassé.
        raise base.ErreurOutil('{0}: {1}{2}'.format(
            type(e).__name__, e,
            ' | sortie : ' + sortie.getvalue().strip()[:400]
            if sortie.getvalue().strip() else ''))
    finally:
        sys.stdout = ancienne
    return {'sortie': sortie.getvalue().strip()[:4000],
            'resultat': _lisible(portee.get('resultat')),
            'annulable': bool(donnees.get('transaction', True))}


def _lisible(valeur):
    """Ce que le code a posé dans ``resultat``, ramené à du JSON transportable."""
    if valeur is None or isinstance(valeur, (bool, int, float)):
        return valeur
    if isinstance(valeur, (list, tuple)):
        return [_lisible(v) for v in valeur][:200]
    if isinstance(valeur, dict):
        return dict((str(c), _lisible(v)) for c, v in list(valeur.items())[:200])
    return '{0}'.format(valeur)[:2000]
