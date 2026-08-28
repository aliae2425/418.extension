# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Le repérage des coupes : QUELS repères restent visibles sur QUEL plan de
# repérage (PDR).
#
# Rien de Revit ici — des dictionnaires en entrée, des dictionnaires en
# sortie. `FiltresService` lit le modèle et écrit les filtres ; tout ce qui se
# DÉCIDE se décide dans ce module, qui tourne donc hors Revit et se teste.
#
# Reprise du prototype de la branche `origin/section-filter`, où le repérage
# était figé : un PDR ne montrait que les coupes de SA feuille (règle
# `NotContains` sur le numéro de feuille). Ici chaque coupe porte sa propre
# liste de règles, et « une coupe par feuille » n'est plus qu'un cas parmi
# trois.

#: Les trois façons de désigner les PDR où le repère d'une coupe apparaît.
#: `cle` est ce qui se persiste, `libelle` ce qui s'affiche dans le menu.
MODES = (
    ('jeu', u'Par jeu'),
    ('plan', u'Plan de repérage'),
    ('specifique', u'Spécifique'),
)

#: Entrée de menu du mode `jeu` qui veut dire « celui de la coupe », par
#: opposition à un jeu nommé. Une règle `jeu` sans cible EST ce cas : le
#: libellé n'est qu'un affichage, il n'est jamais persisté.
JEU_DE_LA_COUPE = u'— le jeu de la coupe —'


class Regle(object):
    """Un ensemble de PDR où le repère d'une coupe doit rester visible.

    - `jeu`        : les PDR des feuilles du jeu visé. Aucune cible = le jeu
                     de la coupe elle-même, ce qui suit la coupe si elle
                     change de feuille.
    - `plan`       : le PDR visé.
    - `specifique` : les PDR cochés un par un.

    `plan` et `specifique` se résolvent à l'identique — ils ne diffèrent que
    par l'arité à l'écran (un menu contre des cases). Un seul chemin de code,
    un seul format persisté.
    """

    def __init__(self, mode=u'jeu', cibles=None):
        self.mode = mode if mode in dict(MODES) else u'jeu'
        self.cibles = [c for c in (cibles or []) if c]

    def en_dict(self):
        return {'mode': self.mode, 'cibles': list(self.cibles)}

    @classmethod
    def depuis_dict(cls, brut):
        brut = brut or {}
        return cls(brut.get('mode'), brut.get('cibles'))


def pdr_vises(regle, coupe, pdrs):
    """Les PDR (dictionnaires) que cette règle désigne pour cette coupe."""
    if regle.mode == u'jeu':
        jeux = set(regle.cibles) or set([coupe.get('jeu')])
        return [p for p in pdrs if p.get('jeu') and p.get('jeu') in jeux]
    cibles = set(regle.cibles)
    return [p for p in pdrs if p.get('nom') in cibles]


def visibles_sur(coupe, pdrs):
    """Les noms de PDR où le repère de cette coupe reste visible.

    Une coupe SANS règle n'est pas contrainte : son repère reste visible
    partout. C'est le choix sûr — vider les règles d'une coupe ne doit pas la
    faire disparaître de tous les plans d'un coup.
    """
    regles = coupe.get('regles') or []
    if not regles:
        return [p['nom'] for p in pdrs]
    vus = []
    for regle in regles:
        for pdr in pdr_vises(regle, coupe, pdrs):
            if pdr['nom'] not in vus:
                vus.append(pdr['nom'])
    return vus


def resoudre(coupes, pdrs):
    """{nom de PDR: [noms de coupes visibles]}, dans l'ordre des coupes.

    C'est l'entrée de l'écriture : le filtre posé sur un PDR masque tout ce
    qui N'EST PAS dans sa liste.
    """
    visibles = dict((p['nom'], []) for p in pdrs)
    for coupe in coupes:
        for nom in visibles_sur(coupe, pdrs):
            if nom in visibles:
                visibles[nom].append(coupe['nom'])
    return visibles


def demo():
    """Contrôle exécutable : python lib/services/reperage.py"""
    pdrs = [{'nom': u'PDR 01', 'feuille': u'A01', 'jeu': u'PC'},
            {'nom': u'PDR 02', 'feuille': u'A02', 'jeu': u'PC'},
            {'nom': u'PDR 10', 'feuille': u'B01', 'jeu': u'DCE'}]

    # Aucune règle : aucune contrainte, la coupe reste partout.
    libre = {'nom': u'Coupe AA', 'feuille': u'A01', 'jeu': u'PC'}
    assert visibles_sur(libre, pdrs) == [u'PDR 01', u'PDR 02', u'PDR 10']

    # `jeu` sans cible : les PDR du jeu de la coupe, pas les autres.
    sienne = dict(libre, regles=[Regle(u'jeu')])
    assert visibles_sur(sienne, pdrs) == [u'PDR 01', u'PDR 02']

    # `jeu` avec cible, `plan` et `specifique` désignent explicitement.
    autre = dict(libre, regles=[Regle(u'jeu', [u'DCE'])])
    assert visibles_sur(autre, pdrs) == [u'PDR 10']
    un = dict(libre, regles=[Regle(u'plan', [u'PDR 02'])])
    assert visibles_sur(un, pdrs) == [u'PDR 02']

    # Plusieurs règles : union, sans doublon, dans l'ordre des règles.
    cumul = dict(libre, regles=[Regle(u'plan', [u'PDR 10']),
                                Regle(u'jeu'),
                                Regle(u'specifique', [u'PDR 02'])])
    assert visibles_sur(cumul, pdrs) == [u'PDR 10', u'PDR 01', u'PDR 02']

    # Une cible qui ne désigne aucun PDR ne masque rien de plus : la liste
    # est vide, et le filtre du PDR masquera donc TOUT.
    fantome = dict(libre, regles=[Regle(u'plan', [u'PDR inexistant'])])
    assert visibles_sur(fantome, pdrs) == []

    assert resoudre([sienne, autre], pdrs) == {
        u'PDR 01': [u'Coupe AA'], u'PDR 02': [u'Coupe AA'],
        u'PDR 10': [u'Coupe AA']}

    assert Regle.depuis_dict(Regle(u'plan', [u'x']).en_dict()).cibles == [u'x']
    assert Regle(u'nawak').mode == u'jeu'
    print(u'reperage : OK')


if __name__ == '__main__':
    demo()
