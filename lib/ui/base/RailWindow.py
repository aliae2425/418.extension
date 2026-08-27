# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

# Coquille de fenêtre à rail d'onglets, commune aux outils de Tools.panel
# (dupliquer/renommer × feuilles/vues). Les MainWindowView étaient identiques
# à quelques noms près ; ce qui variait devient de la DONNÉE : la liste des
# onglets, les enchaînements « Suivant », et le bouton d'action.
#
# Le XAML de la coquille est lui aussi partagé (lib/ui/GUI/MainWindow.xaml) :
# chaque bouton en portait une copie de 141 lignes qui ne différait que par
# le titre, la taille et les items de nav. Les RadioButton du rail sont
# construits ici depuis ONGLETS ; un outil qui a besoin d'une coquille à lui
# dépose un MainWindow.xaml dans son GUI/Views/, comme pour les pages.
#
# Contrat attendu du ViewModel racine :
#   - `Titre` -> titre affiché dans la barre et la légende
#   - `Mode` -> chaîne du mode courant (doit correspondre à un Onglet.mode)
#   - `set_mode(mode)`
#   - un attribut par onglet, nommé par `Onglet.vm_attr` (le DataContext de
#     la page correspondante)

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    try:
        from lib.ui.base.BaseWindow import BaseWindow
    except Exception:
        BaseWindow = object

try:
    from core.AppPaths import AppPaths
except Exception:
    try:
        from lib.core.AppPaths import AppPaths
    except Exception:
        AppPaths = None


class Onglet(object):
    """Un onglet du rail : la page, son DataContext, et son item de nav.

    `icone` est la CLÉ d'une géométrie de `lib/ui/GUI/resources/Icons.xaml`
    (ex. u'IconSelection'), pas un glyphe : les clés portent le rôle, donc
    deux outils qui déclarent le même rôle affichent le même dessin Lucide.
    `tooltip` est l'infobulle. Le RadioButton correspondant est construit par
    `RailWindow._construire_nav` — il n'y a plus de x:Name à tenir synchrone
    entre le XAML et cette déclaration.
    """

    def __init__(self, mode, xaml, vm_attr, icone=u'', tooltip=u''):
        self.mode = mode
        self.xaml = xaml
        self.vm_attr = vm_attr
        self.icone = icone
        self.tooltip = tooltip


class RailWindow(BaseWindow):
    """Fenêtre à rail. Sous-classer et définir :

    - `ONGLETS`  : tuple d'`Onglet`. Le premier sert de repli si `vm.Mode` ne
                   correspond à aucun onglet.
    - `SUIVANTS` : tuple de `(mode_page, nom_bouton, mode_cible)` — un bouton
                   « Suivant » qui coche le radio de `mode_cible`.
    - `RUN`      : `(mode_page, nom_bouton)` du bouton d'action final.
    - `RADIOS`   : optionnel, `(mode_page, (noms...), vm_attr, propriete)` —
                   des RadioButton dont le `.Tag` alimente `propriete`.
    - `TAILLE` / `TAILLE_MINI` : optionnel, `(largeur, hauteur)` de la
                   fenêtre. La coquille partagée fixe 720x560 / 560x420.

    Surcharger `_apres_run(resultat)` pour un post-traitement (ex. sélectionner
    dans Revit les éléments créés).
    """

    ONGLETS = ()
    SUIVANTS = ()
    RUN = None
    RADIOS = None
    TAILLE = None
    TAILLE_MINI = None

    def __init__(self, bouton_dir, view_model, cible=None):
        super(RailWindow, self).__init__(
            self._chemin_fenetre(bouton_dir), view_model)
        self._bouton_dir = bouton_dir
        self._vm = view_model
        # `cible` : donnée passée telle quelle à `vm.lancer()` (dictionnaire
        # id -> élément Revit, propre à chaque outil).
        self._cible = cible
        self._pages = {}
        self._navs = {}

    @staticmethod
    def _chemin_fenetre(bouton_dir):
        """Coquille du bouton si elle existe, sinon celle du socle."""
        local = os.path.join(bouton_dir, 'GUI', 'Views', 'MainWindow.xaml')
        if os.path.exists(local):
            return local
        if AppPaths is not None:
            return os.path.join(AppPaths().ui_gui_dir(), 'MainWindow.xaml')
        return local

    # ------------------------------------------------------------------
    # Chargement
    # ------------------------------------------------------------------

    def _load(self):
        super(RailWindow, self)._load()
        if self._window is None:
            return
        self._appliquer_taille()
        self._construire_nav()
        self._mount_pages()
        self._wire_nav()
        self._wire_suivants()
        self._wire_selection_interactions()
        self._wire_radios()
        self._wire_run()
        self._sync_nav()

    def _appliquer_taille(self):
        for attr, (prop_l, prop_h) in ((self.TAILLE, ('Width', 'Height')),
                                       (self.TAILLE_MINI, ('MinWidth', 'MinHeight'))):
            if not attr:
                continue
            try:
                setattr(self._window, prop_l, attr[0])
                setattr(self._window, prop_h, attr[1])
            except Exception:
                pass

    def _construire_nav(self):
        """Crée un RadioButton par onglet dans le conteneur `NavItems`.

        Les références sont gardées dans `self._navs` : pas de `FindName`,
        donc pas de nom à tenir synchrone entre XAML et `ONGLETS`.
        """
        hote = self._window.FindName('NavItems')
        if hote is None:
            return
        from System.Windows import Thickness
        from System.Windows.Controls import RadioButton
        try:
            style = self._window.FindResource('NavRailButtonStyle')
        except Exception:
            style = None
        dernier = len(self.ONGLETS) - 1
        for index, onglet in enumerate(self.ONGLETS):
            bouton = RadioButton()
            bouton.GroupName = 'nav'
            bouton.Content = self._icone(onglet.icone)
            if onglet.tooltip:
                bouton.ToolTip = onglet.tooltip
            if style is not None:
                bouton.Style = style
            if index != dernier:
                bouton.Margin = Thickness(0, 0, 0, 6)
            hote.Children.Add(bouton)
            self._navs[onglet.mode] = bouton

    def _icone(self, cle):
        """Le `Path` Lucide à poser en Content du bouton de rail.

        Tout l'habillage (taille, épaisseur, caps ronds, liaison du trait au
        Foreground du bouton) vient de `NavRailIconStyle`, le même style que
        les rails écrits en dur dans BatchExport et Audit — il n'y a ici que
        la géométrie à choisir.

        Résolu sur la FENÊTRE et pas sur le bouton : le bouton n'est pas encore
        rattaché à l'arbre quand on lui pose son Content, il ne verrait donc
        aucun des dictionnaires fusionnés par UIResourceLoader.

        Clé absente d'Icons.xaml -> bouton vide plutôt que fenêtre morte ;
        c'est `test_rail_window` qui garde la cohérence des clés.
        """
        from System.Windows.Shapes import Path as WpfPath
        geometrie = self._window.TryFindResource(cle)
        if geometrie is None:
            print('RailWindow: icone introuvable dans Icons.xaml: {}'.format(cle))
            return None
        chemin = WpfPath()
        chemin.Data = geometrie
        chemin.Style = self._window.TryFindResource('NavRailIconStyle')
        return chemin

    def _chemin_page(self, filename):
        """Cherche la page dans le bouton, puis dans le socle.

        Permet à un outil de surcharger une page partagée en déposant un
        fichier du même nom dans son propre GUI/Views/pages/.
        """
        local = os.path.join(self._bouton_dir, 'GUI', 'Views', 'pages', filename)
        if os.path.exists(local):
            return local
        if AppPaths is not None:
            partage = os.path.join(AppPaths().pages_dir(), filename)
            if os.path.exists(partage):
                return partage
        return local

    def _load_page(self, filename, data_context):
        from System.Windows.Markup import XamlReader
        from System.IO import FileStream, FileMode, FileAccess
        stream = FileStream(self._chemin_page(filename),
                            FileMode.Open, FileAccess.Read)
        try:
            page = XamlReader.Load(stream)
        finally:
            stream.Close()
        page.DataContext = data_context
        return page

    def _mount_pages(self):
        for onglet in self.ONGLETS:
            self._pages[onglet.mode] = self._load_page(
                onglet.xaml, getattr(self._vm, onglet.vm_attr, None))
        self._show_current_page()

    def _page(self, mode):
        return self._pages.get(mode)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _mode_courant(self):
        mode = getattr(self._vm, 'Mode', None)
        if mode in self._pages:
            return mode
        return self.ONGLETS[0].mode if self.ONGLETS else None

    def _show_current_page(self):
        host = self._window.FindName('PageHost')
        if host is None:
            return
        page = self._page(self._mode_courant())
        if page is not None:
            host.Content = page

    def _wire_nav(self):
        for mode, btn in self._navs.items():
            self._bind_nav(btn, mode)

    def _bind_nav(self, btn, mode):
        # Fabrique dédiée : une closure définie dans la boucle capturerait la
        # variable de boucle, pas sa valeur.
        def _on_checked(sender, args):
            self._vm.set_mode(mode)
            self._show_current_page()
        btn.Checked += _on_checked

    def _sync_nav(self):
        btn = self._navs.get(self._mode_courant())
        if btn is not None:
            btn.IsChecked = True

    def _wire_suivants(self):
        for (mode_page, nom_bouton, mode_cible) in self.SUIVANTS:
            page = self._page(mode_page)
            if page is None:
                continue
            btn = page.FindName(nom_bouton)
            if btn is None:
                continue
            self._bind_suivant(btn, mode_cible)

    def _bind_suivant(self, btn, mode_cible):
        def _on_next(sender, args):
            cible = self._navs.get(mode_cible)
            if cible is not None:
                cible.IsChecked = True
        btn.Click += _on_next

    # ------------------------------------------------------------------
    # Page Sélection : boutons de masse + clic de ligne
    # ------------------------------------------------------------------

    def _wire_selection_interactions(self):
        page = self._page(u'selection')
        if page is None:
            return
        vm = getattr(self._vm, 'SelectionVM', None)
        if vm is None:
            return

        btn_all = page.FindName('SelectAllButton')
        if btn_all is not None:
            btn_all.Click += lambda s, a: vm.select_all()
        btn_none = page.FindName('DeselectAllButton')
        if btn_none is not None:
            btn_none.Click += lambda s, a: vm.deselect_all()

        # Un seul handler de clic sur la liste : remonte l'index AFFICHÉ et
        # les modificateurs clavier.
        lst = page.FindName('ItemsList')
        if lst is None:
            return

        def _on_row_click(sender, args):
            from System.Windows.Input import Keyboard, ModifierKeys
            item = getattr(args.OriginalSource, 'DataContext', None)
            filtered = list(vm.FilteredItems)
            if item is None or item not in filtered:
                return
            mods = Keyboard.Modifiers
            vm.handle_row_click(
                filtered.index(item),
                bool(int(mods) & int(ModifierKeys.Shift)),
                bool(int(mods) & int(ModifierKeys.Control)))

        lst.PreviewMouseLeftButtonDown += _on_row_click

    # ------------------------------------------------------------------
    # Radios d'option + bouton d'action
    # ------------------------------------------------------------------

    def _wire_radios(self):
        if not self.RADIOS:
            return
        mode_page, noms, vm_attr, propriete = self.RADIOS
        page = self._page(mode_page)
        if page is None:
            return
        cible = getattr(self._vm, vm_attr, None)
        if cible is None:
            return
        for nom in noms:
            rb = page.FindName(nom)
            if rb is not None:
                self._bind_radio(rb, cible, propriete)

    @staticmethod
    def _bind_radio(rb, cible, propriete):
        def _on_checked(sender, args):
            setattr(cible, propriete, sender.Tag)
        rb.Checked += _on_checked

    def _wire_run(self):
        if not self.RUN:
            return
        mode_page, nom_bouton = self.RUN
        page = self._page(mode_page)
        if page is None:
            return
        btn = page.FindName(nom_bouton)
        if btn is None:
            return

        def _on_run(sender, args):
            try:
                resultat = self._vm.lancer(self._cible)
                self._apres_run(resultat)
            finally:
                self._window.Close()
        btn.Click += _on_run

    def _apres_run(self, resultat):
        """Crochet post-action. Ne fait rien par défaut."""
