# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import io
import datetime
from xml.sax.saxutils import escape as _xml_escape

try:
    from models import libelle as libelle_gravite
except Exception:
    from lib.models import libelle as libelle_gravite

try:
    from core.sanitize import sanitize
except Exception:
    from lib.core.sanitize import sanitize


def _esc(txt):
    """Échappe pour du contenu HTML. `escape` couvre & < > ; on ajoute le
    guillemet double, utilisé tel quel dans les attributs du gabarit."""
    s = u'' if txt is None else u'{}'.format(txt)
    return _xml_escape(s, {u'"': u'&quot;'})


def construire_html(res):
    meta = res.meta or {}
    parts = [u'<!DOCTYPE html>', u'<html lang="fr"><head><meta charset="utf-8">',
             u'<title>Audit — {}</title>'.format(_esc(meta.get('fichier', u''))),
             u'<style>body{font-family:Segoe UI,Arial,sans-serif;margin:24px;'
             u'color:#1a1a1a}h1{font-size:22px}.score{font-size:40px;font-weight:700}'
             u'table{border-collapse:collapse;width:100%;margin:12px 0}'
             u'th,td{border:1px solid #e0e0e0;padding:8px;text-align:left;font-size:13px}'
             u'th{background:#f3f3f3}.crit{color:#d13438;font-weight:700}'
             u'.warn{color:#c77914;font-weight:700}</style></head><body>']
    parts.append(u'<h1>Audit de maquette — {}</h1>'.format(
        _esc(meta.get('fichier', u'(modèle)'))))
    parts.append(u'<p>Généré le {} · Score de santé : '
                 u'<span class="score">{}</span>/100</p>'.format(
                     _esc(meta.get('horodatage', u'')), res.score))
    for t in res.themes:
        parts.append(u'<h2>{} ({})</h2>'.format(_esc(t.libelle), t.compte))
        if not t.disponible:
            parts.append(u'<p><em>Contrôle indisponible : {}</em></p>'.format(
                _esc(t.message)))
            continue
        if not t.issues:
            parts.append(u'<p>Aucun problème détecté.</p>')
            continue
        parts.append(u'<table><tr><th>Élément</th><th>Emplacement</th>'
                     u'<th>Type</th><th>Gravité</th><th>Détail</th></tr>')
        for i in t.issues:
            cls = u'crit' if libelle_gravite(i.gravite) == u'Critique' else u'warn'
            parts.append(
                u'<tr><td>{}</td><td>{}</td><td>{}</td>'
                u'<td class="{}">{}</td><td>{}</td></tr>'.format(
                    _esc(i.nom), _esc(i.emplacement), _esc(i.type),
                    cls, _esc(libelle_gravite(i.gravite)), _esc(i.message)))
        parts.append(u'</table>')
    parts.append(u'</body></html>')
    return u'\n'.join(parts)


def exporter(res, dossier=None):
    meta = res.meta or {}
    if dossier is None:
        dossier = os.path.expanduser(u'~/Documents')
    fichier = sanitize(meta.get('fichier', u'modele'))
    date = datetime.datetime.now().strftime('%Y%m%d')
    chemin = os.path.join(dossier, u'Audit_{}_{}.html'.format(fichier, date))
    html = construire_html(res)
    with io.open(chemin, 'w', encoding='utf-8') as f:
        f.write(html)
    return chemin
