# -*- coding: utf-8 -*-
# Vue de l'éditeur de nommage (modale), mode TOKENS : charge
# GUI/Modals/NamingEditor.xaml sur la coquille commune (BaseWindow) et câble
# le motif, les jetons insérables (avec filtre par source) et le footer.
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = object

try:
    from System.Windows.Controls import Button
    from System.Windows import RoutedEventHandler
    _has_wpf = True
except Exception:
    Button = None
    RoutedEventHandler = None
    _has_wpf = False


def _xaml_path():
    here = os.path.dirname(os.path.abspath(__file__))
    button = os.path.abspath(os.path.join(here, '..', '..'))
    return os.path.join(button, 'GUI', 'Modals', 'NamingEditor.xaml')


class NamingEditorView(BaseWindow):
    def __init__(self, view_model):
        super(NamingEditorView, self).__init__(_xaml_path(), view_model)
        self._vm = view_model

    def _load(self):
        super(NamingEditorView, self)._load()
        self.wire_tokens()
        self.wire_filtre_source()
        self.wire_footer()

    # ------------------------------------------------------------------
    # Jetons : clic sur un badge -> insertion dans PatternTextBox au curseur
    # ------------------------------------------------------------------
    #
    # Câblage retenu : UN SEUL AddHandler(Button.ClickEvent, ...) posé sur
    # l'ItemsControl "TokensItemsControl" lui-même. Grâce au bubbling des
    # routed events WPF, ce handler capte le clic de N'IMPORTE QUEL badge
    # descendant, sans dépendre du DataTemplate (pas de x:Name/Click=
    # exploitable pour un item généré dynamiquement). Le jeton cliqué est lu
    # défensivement : `btn.DataContext.token` (TokenItemVM) en priorité,
    # repli sur `btn.Content` (déjà bindé à `token`) si le DataContext
    # n'est pas exploitable pour une raison quelconque.
    # ------------------------------------------------------------------

    def wire_tokens(self):
        if self._window is None or not _has_wpf:
            return
        items_control = self._window.FindName('TokensItemsControl')
        pattern_box = self._window.FindName('PatternTextBox')
        if items_control is None or pattern_box is None:
            return
        vm = self._vm

        def _on_token_click(sender, args):
            try:
                btn = args.OriginalSource
            except Exception:
                return
            if btn is None or Button is None or not isinstance(btn, Button):
                return

            token = None
            try:
                token = getattr(btn.DataContext, 'token', None)
            except Exception:
                token = None
            if not token:
                try:
                    token = btn.Content
                except Exception:
                    token = None
            if not token:
                return

            try:
                self._insert_at_caret(pattern_box, vm, token)
            except Exception:
                pass

        try:
            items_control.AddHandler(Button.ClickEvent, RoutedEventHandler(_on_token_click))
        except Exception:
            pass

    def _insert_at_caret(self, pattern_box, vm, token):
        """Insère `token` dans `pattern_box` à la position du curseur,
        repositionne le curseur juste après le jeton inséré, et répercute
        le nouveau texte sur `vm.Pattern` (le binding TwoWay le ferait déjà
        au prochain événement TextChanged, mais on force la synchronisation
        immédiate pour que l'Aperçu -- lié à `Apercu`, dérivée de `Pattern`
        -- se rafraîchisse sans attendre un focus-out)."""
        try:
            caret = pattern_box.CaretIndex
        except Exception:
            caret = None
        texte = u''
        try:
            texte = pattern_box.Text or u''
        except Exception:
            texte = u''

        if caret is None or caret < 0 or caret > len(texte):
            caret = len(texte)

        nouveau = texte[:caret] + token + texte[caret:]
        nouvelle_position = caret + len(token)

        try:
            pattern_box.Text = nouveau
        except Exception:
            pass
        try:
            pattern_box.CaretIndex = nouvelle_position
        except Exception:
            pass
        try:
            pattern_box.Focus()
        except Exception:
            pass
        try:
            vm.Pattern = nouveau
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Filtre de source : clic sur un bouton d'onglet -> FiltreSource
    # ------------------------------------------------------------------
    #
    # Même pattern de câblage que les jetons : UN SEUL AddHandler posé sur
    # le conteneur des boutons de filtre ("SourceFilterItemsControl"),
    # bubbling capte le clic de n'importe quel bouton généré par le
    # DataTemplate (SourceItemVM.valeur).
    # ------------------------------------------------------------------

    def wire_filtre_source(self):
        if self._window is None or not _has_wpf:
            return
        items_control = self._window.FindName('SourceFilterItemsControl')
        if items_control is None:
            return
        vm = self._vm

        def _on_filter_click(sender, args):
            try:
                btn = args.OriginalSource
            except Exception:
                return
            if btn is None or Button is None or not isinstance(btn, Button):
                return

            valeur = None
            try:
                valeur = getattr(btn.DataContext, 'valeur', None)
            except Exception:
                valeur = None
            if not valeur:
                return

            try:
                vm.FiltreSource = valeur
            except Exception:
                pass

        try:
            items_control.AddHandler(Button.ClickEvent, RoutedEventHandler(_on_filter_click))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Footer : Annuler (ferme sans sauver) / Enregistrer (sauve puis ferme)
    # ------------------------------------------------------------------

    def wire_footer(self):
        if self._window is None:
            return
        vm = self._vm

        btn_ok = self._window.FindName('OkButton')
        if btn_ok is not None:
            def _on_ok(sender, args):
                try:
                    vm.enregistrer()
                except Exception:
                    pass
                try:
                    self._window.Close()
                except Exception:
                    pass
            try:
                btn_ok.Click += _on_ok
            except Exception:
                pass

        btn_cancel = self._window.FindName('CancelButton')
        if btn_cancel is not None:
            def _on_cancel(sender, args):
                try:
                    self._window.Close()
                except Exception:
                    pass
            try:
                btn_cancel.Click += _on_cancel
            except Exception:
                pass
