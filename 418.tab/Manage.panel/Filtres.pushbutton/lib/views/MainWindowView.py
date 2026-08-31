# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.RailWindow import RailWindow, Onglet
except Exception:
    from lib.ui.base.RailWindow import RailWindow, Onglet

_BOUTON = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))


class MainWindowView(RailWindow):
    """Fenêtre « Gérer les filtres » : l'audit, puis le repérage des coupes.

    Comme « Matériaux », l'Audit ouvre le rail ET sert de mode initial : un
    état des lieux en lecture seule, sans câblage.

    `RUN_GARDE_OUVERT` : « Appliquer » n'referme plus la fenêtre. Régler un
    repérage est itératif, et la page rend compte elle-même — la console pyRevit
    n'est plus consultable d'un coup d'œil quand la fenêtre est encore devant.

    La fenêtre reste MODALE : Revit est bloqué tant qu'elle est ouverte, donc
    aller voir un plan demande de la fermer. C'est ce que fait « Aller au
    plan » : il applique, ferme, et laisse le script activer la vue.
    """

    ONGLETS = (
        Onglet(u'audit', 'AuditPage.xaml', 'AuditVM',
               icone=u'IconAudit', tooltip=u'Audit des filtres'),
        Onglet(u'reperage', 'ReperagePage.xaml', 'ReperageVM',
               icone=u'IconSelection', tooltip=u'Repérage des coupes'),
    )
    SUIVANTS = ()
    RUN = (u'reperage', 'AppliquerButton')
    RUN_GARDE_OUVERT = True
    SELECTION = (u'reperage', 'SelectionVM')
    TAILLE = (1020, 660)
    TAILLE_MINI = (860, 540)

    def __init__(self, view_model):
        super(MainWindowView, self).__init__(_BOUTON, view_model)
        self._plan_a_activer = None

    def _load(self):
        super(MainWindowView, self)._load()
        if self._window is None:
            return
        page = self._page(u'reperage')
        bouton = page.FindName('AllerAuPlanButton') if page is not None else None
        if bouton is not None:
            bouton.Click += self._on_aller_au_plan

    def _on_aller_au_plan(self, sender, args):
        """Applique, retient le plan à activer, ferme.

        L'activation de la vue est laissée au script : elle demande
        l'`ActiveUIDocument`, et surtout que cette fenêtre modale ne soit plus
        là.
        """
        try:
            self._plan_a_activer = self._vm.ReperageVM.plan_selectionne()
            for message in (self._vm.lancer(self._cible) or []):
                print(message)
        finally:
            self._window.Close()

    def plan_a_activer(self):
        """L'`ElementId` du plan que le script doit activer, ou None."""
        return self._plan_a_activer
