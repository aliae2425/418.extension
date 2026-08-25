# -*- coding: utf-8 -*-
"""Écriture d'un DXF R12 ASCII minimal : une POLYLINE par tracé.

Logique pure, testable hors Revit. Le DXF est une suite de paires
(code, valeur), une valeur par ligne : verbeux mais trivial à produire, et R12
est la version la plus largement acceptée à l'import.

Tout est écrit sur le calque « 0 », qui existe toujours : pas de section TABLES
à déclarer. Une POLYLINE par figure au lieu d'un segment par droite, c'est tout
l'intérêt face à la création de lignes de détail une à une.
"""
from __future__ import unicode_literals
import io


def _paire(code, valeur):
    return '{0}\n{1}\n'.format(code, valeur)


def polyligne(points, fermee=False):
    """Entité POLYLINE R12 (POLYLINE + VERTEX… + SEQEND) pour des (x, y)."""
    morceaux = [
        _paire(0, 'POLYLINE'),
        _paire(8, '0'),
        _paire(66, 1),                    # « des VERTEX suivent » : requis en R12
        _paire(70, 1 if fermee else 0),   # bit 1 = polyligne fermée
        _paire(10, '0.0'), _paire(20, '0.0'), _paire(30, '0.0'),
    ]
    for x, y in points:
        morceaux.extend([
            _paire(0, 'VERTEX'),
            _paire(8, '0'),
            _paire(10, '{0:.6f}'.format(x)),
            _paire(20, '{0:.6f}'.format(y)),
            _paire(30, '0.0'),
        ])
    morceaux.extend([_paire(0, 'SEQEND'), _paire(8, '0')])
    return ''.join(morceaux)


def ecrire(chemin, polylignes):
    """Écrit `polylignes` — des (points, fermée) — dans un DXF R12.

    Retourne le nombre de POLYLINE écrites ; celles de moins de deux points
    sont ignorées (Revit refuse une polyligne dégénérée).
    """
    ecrites = 0
    corps = []
    for points, fermee in polylignes:
        if len(points) < 2:
            continue
        corps.append(polyligne(points, fermee))
        ecrites += 1

    with io.open(chemin, 'w', encoding='ascii') as fichier:
        fichier.write(_paire(0, 'SECTION'))
        fichier.write(_paire(2, 'HEADER'))
        fichier.write(_paire(9, '$ACADVER'))
        fichier.write(_paire(1, 'AC1009'))          # R12
        fichier.write(_paire(0, 'ENDSEC'))
        fichier.write(_paire(0, 'SECTION'))
        fichier.write(_paire(2, 'ENTITIES'))
        for entite in corps:
            fichier.write(entite)
        fichier.write(_paire(0, 'ENDSEC'))
        fichier.write(_paire(0, 'EOF'))
    return ecrites
