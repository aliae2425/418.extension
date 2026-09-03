# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.services import contraintes as contraintes_module
except Exception:
    from services import contraintes as contraintes_module


# Couleurs sémantiques du verdict, en dur : vert / ambre / rouge ne dépendent
# pas du thème, et une chaîne « #AARRGGBB » se binde directement sur
# Foreground (WPF convertit). Évite un converter pour trois valeurs.
_COULEURS = {
    'ok': '#FF16A34A',
    'warning': '#FFD97706',
    'error': '#FFDC2626',
    '': '#FF9CA3AF',
}


def _texte(valeur):
    """Nombre -> champ de saisie. Deux décimales, vide si rien à afficher."""
    if valeur is None:
        return u''
    return u'{:.2f}'.format(valeur)


class ParametreVM(object):
    """Une ligne du tableau des paramètres. Lecture seule, donc pas de
    notification : la liste est reconstruite avec la fenêtre."""

    def __init__(self, nom, valeur):
        self.Nom = nom
        self.Valeur = valeur


class MainViewModel(BaseViewModel):
    """Panneau de gauche de la fenêtre « Rampe parking ».

    Les trois valeurs (hauteur, longueur, largeur) sont pré-remplies depuis la
    maquette mais restent éditables : la lecture peut être approximative
    (décalages ignorés, bbox en biais) et c'est l'utilisateur qui tranche.
    Chaque frappe recalcule pente, verdict et URL.
    """

    def __init__(self, contraintes):
        super(MainViewModel, self).__init__()
        self._contraintes = contraintes
        self._hauteur = _texte(contraintes.Denivelee)
        self._longueur = _texte(contraintes.Longueur)
        self._largeur = _texte(contraintes.Largeur)
        self.Parametres = [ParametreVM(nom, valeur)
                           for nom, valeur in contraintes.Parametres]

    # ---------------------------------------------------------------- infos

    @property
    def Titre(self):
        return u'Rampe de parking — NF P91-100'

    @property
    def Source(self):
        return self._contraintes.Source or u'Aucune sélection exploitable'

    @property
    def Avertissement(self):
        return self._contraintes.Avertissement

    @property
    def ADesParametres(self):
        return len(self.Parametres) > 0

    # -------------------------------------------------------- saisie éditable

    @property
    def Hauteur(self):
        return self._hauteur

    @Hauteur.setter
    def Hauteur(self, valeur):
        self._hauteur = valeur
        self._recalcule()

    @property
    def Longueur(self):
        return self._longueur

    @Longueur.setter
    def Longueur(self, valeur):
        self._longueur = valeur
        self._recalcule()

    @property
    def Largeur(self):
        return self._largeur

    @Largeur.setter
    def Largeur(self, valeur):
        self._largeur = valeur
        self._recalcule()

    # ------------------------------------------------------------- dérivés

    @property
    def _pente(self):
        return contraintes_module.pente_pct(
            contraintes_module.nombre(self._hauteur),
            contraintes_module.nombre(self._longueur))

    @property
    def Pente(self):
        pente = self._pente
        return u'—' if pente is None else u'{:.1f} %'.format(pente)

    @property
    def Verdict(self):
        return contraintes_module.verdict(self._pente)[1]

    @property
    def VerdictCouleur(self):
        return _COULEURS.get(contraintes_module.verdict(self._pente)[0],
                             _COULEURS[''])

    @property
    def UrlToolbox(self):
        return contraintes_module.url_toolbox(
            contraintes_module.nombre(self._hauteur),
            contraintes_module.nombre(self._largeur),
            self._pente)

    def _recalcule(self):
        for nom in ('Pente', 'Verdict', 'VerdictCouleur', 'UrlToolbox'):
            self.notify_property(nom)
