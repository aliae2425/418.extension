# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.RailWindow import RailWindow, Onglet
except Exception:
    from lib.ui.base.RailWindow import RailWindow, Onglet

try:
    from lib.views.EditeurWindowView import EditeurWindowView
except Exception:
    from views.EditeurWindowView import EditeurWindowView

_BOUTON = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))


class MainWindowView(RailWindow):
    """Fenêtre « Matériaux » : rail à quatre onglets.

    L'onglet Audit est le premier du rail ET le mode initial du VM : c'est un
    état des lieux en lecture seule, ouvert d'entrée de jeu. Aucun câblage —
    pas de bouton, pas de liste cochable.

    `RUN` du socle n'est pas utilisé : il ne câble qu'UN bouton et ferme la
    fenêtre derrière. Ici il en faut trois, et aucun ne doit fermer — on
    veut lire le rapport de remplacement ou l'aperçu de renommage juste
    après l'action. Les trois sont donc câblés dans `_load`.

    La coquille vient du socle (lib/ui/GUI/MainWindow.xaml) : cet outil n'a
    pas de MainWindow.xaml à lui.
    """

    ONGLETS = (
        Onglet(u'audit', 'AuditPage.xaml', 'AuditVM',
               icone=u'IconAudit', tooltip=u'Audit des matériaux'),
        Onglet(u'selection', 'CardsPage.xaml', 'SelectionVM',
               icone=u'IconMateriaux', tooltip=u'Matériaux'),
        Onglet(u'renommer', 'RenommerPage.xaml', 'RenommerVM',
               icone=u'IconRenommer', tooltip=u'Renommer'),
        Onglet(u'remplacer', 'RemplacerPage.xaml', 'RemplacerVM',
               icone=u'IconRemplacer', tooltip=u'Remplacer dans la maquette'),
    )
    # Plus d'enchaînement « Suivant » : l'onglet Matériaux ne mène plus à
    # Renommer mais à l'éditeur, via son propre bouton (cf. `_wire_editeur`).
    SUIVANTS = ()
    RUN = None
    # Largeur dictée par le tableau de l'onglet Renommer, le seul contenu à
    # largeur incompressible : 350 px de colonnes fixes (case, flèche, rendu,
    # surface, coupe, usages) + deux colonnes de nom qui doivent rester
    # lisibles + 40 de marge + 64 de rail + la barre de défilement. À 1040
    # chaque nom a ~230 px.
    # Les grilles des onglets Audit et Matériaux ne la dictent plus : leurs
    # UniformGrid (3 et 4 colonnes) se partagent la largeur disponible, donc
    # elles suivent la fenêtre au lieu de la contraindre.
    # La largeur MINI, elle, vient des cards : à 860 les 4 colonnes laissent
    # ~185 px par card, soit la pastille de 64 px et un nom encore lisible.
    TAILLE = (1040, 660)
    TAILLE_MINI = (860, 480)

    def __init__(self, view_model):
        super(MainWindowView, self).__init__(_BOUTON, view_model)

    def _load(self):
        super(MainWindowView, self)._load()
        if self._window is None:
            return
        self._wire_liste_renommer()
        self._wire_liste_remplacer()
        self._wire_editeur()
        self._action(u'remplacer', 'CocherPorteeButton',
                     lambda: self._vm.RemplacerVM.cocher_toute_la_portee())
        self._action(u'remplacer', 'DecocherPorteeButton',
                     lambda: self._vm.RemplacerVM.decocher_toute_la_portee())
        self._action(u'remplacer', 'AnalyserButton',
                     lambda: self._vm.RemplacerVM.analyser())
        self._action(u'remplacer', 'RemplacerButton',
                     lambda: self._vm.RemplacerVM.remplacer())
        self._action(u'renommer', 'RenommerButton',
                     lambda: self._vm.RenommerVM.renommer())

    def _action(self, mode, nom_bouton, callback):
        """Câble un bouton de page sur une action du VM, sans fermer."""
        page = self._page(mode)
        if page is None:
            return
        bouton = page.FindName(nom_bouton)
        if bouton is None:
            return
        bouton.Click += lambda sender, args: callback()

    # ------------------------------------------------------------------
    # Éditeur d'un matériau (onglet Matériaux)
    # ------------------------------------------------------------------

    def _wire_editeur(self):
        """Les deux chemins vers l'éditeur : le bouton, et le double-clic.

        Le clic simple, lui, ne fait que sélectionner — la sélection est
        exclusive sur cet onglet, il tient donc lieu de bouton radio. Le
        premier clic du double sélectionne au passage, ce qui est exactement
        ce qu'on veut avant d'ouvrir.
        """
        self._action(u'selection', 'EditerButton',
                     lambda: self._ouvrir_editeur(self._vm.carte_selectionnee()))
        page = self._page(u'selection')
        if page is None:
            return
        liste = page.FindName('ItemsList')
        if liste is None:
            return

        def _au_double_clic(sender, args):
            carte = getattr(args.OriginalSource, 'DataContext', None)
            self._ouvrir_editeur(carte)

        liste.MouseDoubleClick += _au_double_clic

    def _ouvrir_editeur(self, carte):
        vm = self._vm.editeur_pour(carte)
        if vm is None:
            return
        EditeurWindowView(vm, proprietaire=self._window).show()

    # ------------------------------------------------------------------
    # Listes cochables des onglets Renommer et Remplacer
    # ------------------------------------------------------------------

    def _wire_selection(self, page, nom_liste, selection):
        """Câble Tout/Aucun + le clic de ligne sur la page de sélection.

        `RailWindow._wire_selection_interactions` ne s'occupe que de la page
        `selection` (les cards) et de `vm.SelectionVM`. Les onglets Renommer
        et Remplacer ont leur PROPRE `SelectionPageVM` — d'où le passage
        explicite de `selection` ici plutôt qu'un `getattr` sur le VM racine.

        Les cases sont display-only (IsHitTestVisible=False, binding OneWay) :
        un seul handler de clic sur la liste suffit, ce qui évite un double
        déclenchement entre la case et la ligne.
        """
        if page is None or selection is None:
            return

        bouton = page.FindName('SelectAllButton')
        if bouton is not None:
            bouton.Click += lambda s, a: selection.select_all()
        bouton = page.FindName('DeselectAllButton')
        if bouton is not None:
            bouton.Click += lambda s, a: selection.deselect_all()

        def _bascule(carte):
            affichees = list(selection.FilteredItems)
            if carte not in affichees:
                return
            from System.Windows.Input import Keyboard, ModifierKeys
            mods = Keyboard.Modifiers
            selection.handle_row_click(
                affichees.index(carte),
                bool(int(mods) & int(ModifierKeys.Shift)),
                bool(int(mods) & int(ModifierKeys.Control)))

        self._clic_de_ligne(page, nom_liste, _bascule)

    def _wire_liste_renommer(self):
        vm = getattr(self._vm, 'RenommerVM', None)
        if vm is None:
            return
        self._wire_selection(self._page(u'renommer'), 'ItemsList',
                             vm.SelectionVM)

    def _wire_liste_remplacer(self):
        """Les deux colonnes de la page Remplacer : sources cochables à
        gauche, désignation de la cible à droite."""
        page = self._page(u'remplacer')
        vm = getattr(self._vm, 'RemplacerVM', None)
        if page is None or vm is None:
            return
        self._wire_selection(page, 'SourcesList', vm.SelectionVM)

        def _designe_cible(carte):
            vm.Cible = carte

        self._clic_de_ligne(page, 'CiblesList', _designe_cible)

    @staticmethod
    def _clic_de_ligne(page, nom_liste, callback):
        """Un handler unique sur la liste, appelé avec la ligne cliquée."""
        liste = page.FindName(nom_liste)
        if liste is None:
            return

        def _au_clic(sender, args):
            carte = getattr(args.OriginalSource, 'DataContext', None)
            if carte is not None:
                callback(carte)

        liste.PreviewMouseLeftButtonDown += _au_clic
