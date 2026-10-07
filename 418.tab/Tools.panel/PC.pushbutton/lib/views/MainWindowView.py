# -*- coding: utf-8 -*-
"""Fenêtre « Dossier d'urbanisme » : rail 3 onglets, coquille partagée.

Elle ne déclare que de la DONNÉE — les onglets, les enchaînements et le
bouton d'action. Tout le reste (le rail, les pages, le thème, la barre de
titre) vient de ``RailWindow`` et de la coquille du socle.
"""
from __future__ import unicode_literals
import os

try:
    from ui.base.RailWindow import RailWindow, Onglet
except Exception:
    from lib.ui.base.RailWindow import RailWindow, Onglet

_BOUTON = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))


class MainWindowView(RailWindow):

    ONGLETS = (
        Onglet(u'dossier', 'DossierPage.xaml', 'DossierVM',
               icone=u'IconPC', tooltip=u'Dossier'),
        Onglet(u'pieces', 'PiecesPage.xaml', 'PiecesVM',
               icone=u'IconSelection', tooltip=u'Pièces'),
        Onglet(u'apercu', 'ApercuPage.xaml', 'ApercuVM',
               icone=u'IconArborescence', tooltip=u'Aperçu'),
    )
    SUIVANTS = (
        (u'dossier', 'NextToPiecesButton', u'pieces'),
        (u'pieces', 'NextToApercuButton', u'apercu'),
    )
    RUN = (u'apercu', 'RunButton')
    # Les cinq types du CERFA. Les chips inactifs sont grisés par leur
    # IsEnabled, lié au catalogue — ici on ne fait que les câbler.
    RADIOS = (u'dossier',
              ('RadioDP', 'RadioPCMI', 'RadioPC', 'RadioPA', 'RadioPD'),
              'DossierVM', 'Type')
    TAILLE = (760, 600)
    TAILLE_MINI = (620, 480)

    def __init__(self, view_model):
        super(MainWindowView, self).__init__(_BOUTON, view_model)

    def _load(self):
        super(MainWindowView, self)._load()
        if self._window is None:
            return
        self._sync_type()
        self._wire_pieces_masse()

    def _sync_type(self):
        """Coche le chip du type courant à l'ouverture.

        `RailWindow` synchronise le rail (`_sync_nav`) mais pas les RADIOS :
        sans ça, le VM s'ouvre sur un type que rien n'affiche, et le premier
        clic semble ne rien changer puisqu'il repose la valeur déjà en place.
        """
        page = self._page(u'dossier')
        vm = getattr(self._vm, 'DossierVM', None)
        if page is None or vm is None:
            return
        bouton = page.FindName('Radio{0}'.format(vm.Type))
        if bouton is not None:
            bouton.IsChecked = True

    def _wire_pieces_masse(self):
        """Tout cocher / tout décocher de la page Pièces.

        Ces deux-là ne passent pas par SUIVANTS ni RUN : RailWindow ne câble
        que la navigation et l'action finale. Deux handlers, pas une
        surcouche.
        """
        page = self._page(u'pieces')
        vm = getattr(self._vm, 'PiecesVM', None)
        if page is None or vm is None:
            return
        for nom, action in (('SelectAllButton', vm.tout_cocher),
                            ('DeselectAllButton', vm.tout_decocher)):
            bouton = page.FindName(nom)
            if bouton is not None:
                self._bind_masse(bouton, action)

    @staticmethod
    def _bind_masse(bouton, action):
        # Fabrique dédiée : une closure définie dans la boucle capturerait la
        # variable de boucle, pas sa valeur.
        bouton.Click += lambda sender, args: action()

    def _apres_run(self, resultat):
        """La fenêtre vient de se refermer : c'est le seul endroit où dire
        ce qui s'est passé."""
        if not resultat:
            return
        try:
            from pyrevit import forms
            forms.alert(resultat, title='Dossier d\'urbanisme')
        except Exception:
            print(resultat)
