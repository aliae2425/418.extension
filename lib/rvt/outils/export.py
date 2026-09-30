# -*- coding: utf-8 -*-
"""Export : un seul outil pour PDF, DWG, IFC, NWC et images.

rvt-mcp en fait cinq handlers. Les cinq partagent la sélection des vues, la
préparation du dossier et le nommage ; seul l'appel final change. Un outil
paramétré par ``format`` évite d'écrire cinq fois la même description — et
cinq fois le même piège de nommage.

À noter : 418 a déjà un **bouton BatchExport** autrement plus complet
(motifs à jetons, sous-dossiers, unicité). Cet outil-là sert au modèle pour
un export ponctuel, pas à remplacer le bouton.
"""
from __future__ import unicode_literals
import os

try:
    from rvt.registre import outil
    from rvt import base
except Exception:
    from lib.rvt.registre import outil
    from lib.rvt import base

try:
    from core.sanitize import sanitize
except Exception:
    try:
        from lib.core.sanitize import sanitize
    except Exception:
        sanitize = None

try:
    from Autodesk.Revit import DB
except Exception:
    DB = None

FORMATS = ('pdf', 'dwg', 'ifc', 'nwc', 'image')


@outil('exporter',
       'DANGER — exporte des vues ou des feuilles. IRRÉVERSIBLE : écrit des '
       'fichiers sur le disque et écrase ce qui porte le même nom. Jamais '
       'sans demande explicite. Formats : pdf, dwg, ifc, nwc, image. '
       'Sans « vues », exporte la vue active.',
       proprietes={
           'format': {'type': 'string', 'enum': list(FORMATS)},
           'dossier': {'type': 'string',
                       'description': 'dossier de destination'},
           'vues': {'type': 'array', 'items': {'type': 'string'},
                    'description': 'noms de vues ou numéros de feuilles'},
           'feuilles': {'type': 'boolean',
                        'description': 'exporter toutes les feuilles'}},
       requis=('format', 'dossier'), irreversible=True,
       besoins=('doc', 'uidoc'))
def exporter(doc, uidoc, donnees=None):
    donnees = donnees or {}
    format_ = (donnees.get('format') or '').strip().lower()
    if format_ not in FORMATS:
        raise base.ErreurOutil('format inconnu : {0} — attendu {1}'.format(
            format_, ', '.join(FORMATS)))
    dossier = donnees.get('dossier')
    if not dossier:
        raise base.ErreurOutil('préciser « dossier »')
    if not os.path.isdir(dossier):
        try:
            os.makedirs(dossier)
        except Exception as e:
            raise base.ErreurOutil(
                'dossier inaccessible : {0} — {1}'.format(dossier, e))

    # IFC et NWC exportent le MODÈLE, pas des vues : leur demander une
    # sélection de vues n'a pas de sens.
    if format_ in ('ifc', 'nwc'):
        return _modele(doc, dossier, format_)

    vues = _vues(doc, uidoc, donnees)
    if not vues:
        raise base.ErreurOutil('aucune vue à exporter')
    if format_ == 'pdf':
        return _pdf(doc, dossier, vues)
    if format_ == 'dwg':
        return _dwg(doc, dossier, vues)
    return _image(doc, dossier, vues)


def _vues(doc, uidoc, donnees):
    if donnees.get('feuilles'):
        return sorted(DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet),
                      key=lambda f: f.SheetNumber or '')
    voulues = donnees.get('vues')
    if not voulues:
        vue = uidoc.ActiveView
        return [vue] if vue is not None else []
    cibles = set(v.strip().lower() for v in voulues)
    trouvees = []
    for vue in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if vue.IsTemplate:
            continue
        numero = getattr(vue, 'SheetNumber', '') or ''
        if base.nom_element(vue).strip().lower() in cibles \
                or numero.strip().lower() in cibles:
            trouvees.append(vue)
    if not trouvees:
        raise base.ErreurOutil(
            'aucune vue ne correspond — vérifier avec revit_vues ou '
            'revit_feuilles')
    return trouvees


def _nom(vue):
    brut = '{0}{1}'.format(
        (getattr(vue, 'SheetNumber', '') or '') and
        getattr(vue, 'SheetNumber', '') + ' - ', base.nom_element(vue))
    return sanitize(brut) if sanitize else brut.replace('/', '-')


def _ids(vues):
    from System.Collections.Generic import List
    identifiants = List[DB.ElementId]()
    for vue in vues:
        identifiants.Add(vue.Id)
    return identifiants


def _pdf(doc, dossier, vues):
    options = DB.PDFExportOptions()
    options.Combine = False
    options.FileName = _nom(vues[0]) if len(vues) == 1 else 'export'
    doc.Export(dossier, _ids(vues), options)
    return {'format': 'pdf', 'dossier': dossier, 'vues': len(vues),
            'noms': [_nom(v) for v in vues[:20]]}


def _dwg(doc, dossier, vues):
    options = DB.DWGExportOptions()
    doc.Export(dossier, _nom(vues[0]) if len(vues) == 1 else 'export',
               _ids(vues), options)
    return {'format': 'dwg', 'dossier': dossier, 'vues': len(vues),
            'noms': [_nom(v) for v in vues[:20]]}


def _image(doc, dossier, vues):
    options = DB.ImageExportOptions()
    options.ExportRange = DB.ExportRange.SetOfViews
    options.SetViewsAndSheets(_ids(vues))
    options.HLRandWFViewsFileType = DB.ImageFileType.PNG
    options.ShadowViewsFileType = DB.ImageFileType.PNG
    options.ImageResolution = DB.ImageResolution.DPI_150
    options.FilePath = os.path.join(dossier, _nom(vues[0]))
    doc.ExportImage(options)
    return {'format': 'image', 'dossier': dossier, 'vues': len(vues)}


def _modele(doc, dossier, format_):
    nom = sanitize(doc.Title) if sanitize else doc.Title
    if format_ == 'ifc':
        options = DB.IFCExportOptions()
        doc.Export(dossier, nom, options)
        return {'format': 'ifc', 'dossier': dossier, 'fichier': nom}
    # NWC passe par l'exportateur Navisworks, absent si le greffon ne l'est
    # pas — on le dit plutôt que de laisser une trace incompréhensible.
    try:
        options = DB.NavisworksExportOptions()
        doc.Export(dossier, nom, options)
    except Exception as e:
        raise base.ErreurOutil(
            'export NWC indisponible — le greffon Navisworks Exporter '
            'est-il installé ? ({0})'.format(e))
    return {'format': 'nwc', 'dossier': dossier, 'fichier': nom}
