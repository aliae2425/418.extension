# -*- coding: utf-8 -*-
"""Page « Aperçu » : ce qui sera créé dans la maquette, avant de l'y créer.

L'aperçu n'est pas une courtoisie. L'outil ÉCRIT dans le projet — des
feuilles et des jeux que personne n'a demandés sont plus longs à retirer
qu'à créer. Ce qui s'affiche ici vient du même ``planifier()`` que ce qui
s'exécute : pas deux calculs qui se ressemblent, le même plan.
"""
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.services import FeuillesService as service
except Exception:
    from services import FeuillesService as service


class LigneVM(BaseViewModel):
    """Une ligne de l'arbre : un jeu, ou une feuille sous son jeu."""

    def __init__(self, dessin, nom, detail=u'', existe=False, jeu=False):
        super(LigneVM, self).__init__()
        self.Dessin = dessin
        self.Nom = nom
        self.Detail = detail
        self.DetailVisible = bool(detail)
        # « existe déjà » n'est pas une erreur : on n'y touche pas, et
        # l'outil se rejoue sur un dossier en cours sans rien écraser.
        self.Existe = bool(existe)
        self.EstJeu = bool(jeu)


class ApercuPageVM(BaseViewModel):

    def __init__(self):
        super(ApercuPageVM, self).__init__()
        self.Lignes = []
        self._plan = None

    def rafraichir(self, plan):
        self._plan = plan
        self.Lignes = list(self._lignes())
        for nom in ('Lignes', 'Resume', 'PeutCreer', 'Avertissement',
                    'AvertissementVisible'):
            self.notify_property(nom)

    def plan(self):
        return self._plan

    def _lignes(self):
        if self._plan is None:
            return
        for jeu in self._plan.jeux:
            yield LigneVM(u'▸', jeu.nom, existe=jeu.existe, jeu=True,
                          detail=u'jeu de feuilles')
            dernier = len(jeu.feuilles) - 1
            for index, feuille in enumerate(jeu.feuilles):
                dessin = u'   └──' if index == dernier else u'   ├──'
                # Le nom de la vue vit ICI et nulle part ailleurs : savoir
                # laquelle des trois coupes atterrit sur PC3.2 est utile à
                # la relecture, mais la feuille, elle, garde son titre
                # contractuel.
                yield LigneVM(dessin,
                              u'{0} — {1}'.format(feuille.numero, feuille.nom),
                              detail=(u'← {0}'.format(feuille.vue_nom)
                                      if feuille.vue_nom else u''),
                              existe=feuille.existe)

    @property
    def Resume(self):
        if self._plan is None:
            return u''
        feuilles = len(service.a_creer(self._plan))
        jeux = len([j for j in self._plan.jeux if not j.existe])
        if not feuilles:
            return u'Rien à créer : tout est déjà dans la maquette.'
        return u'{0} feuille(s) et {1} jeu(x) à créer'.format(feuilles, jeux)

    @property
    def PeutCreer(self):
        return bool(self._plan is not None and service.a_creer(self._plan))

    @property
    def Avertissement(self):
        """Ce qui empêche de créer, dit avant le clic plutôt qu'après."""
        if self._plan is None or not self._plan.jeux:
            return u'Aucune pièce cochée : onglet Pièces.'
        if not service.a_creer(self._plan):
            return u'Les feuilles de ces pièces existent déjà.'
        return u''

    @property
    def AvertissementVisible(self):
        return bool(self.Avertissement)
