# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from pyrevit import forms

try:
    from core.AppPaths import AppPaths
    from core.journal import journal
except Exception:
    from lib.core.AppPaths import AppPaths
    from lib.core.journal import journal

_log = journal('panneau')

try:
    from ui.helpers.UIResourceLoader import UIResourceLoader
    from ui.helpers.DarkMode import is_dark
    from ui.OpenArchiChatVM import OpenArchiChatVM
except Exception:
    from lib.ui.helpers.UIResourceLoader import UIResourceLoader
    from lib.ui.helpers.DarkMode import is_dark
    from lib.ui.OpenArchiChatVM import OpenArchiChatVM


class OpenArchiPanel(forms.WPFPanel):
    """Panneau de chat ancrable dans l'interface Revit.

    Enregistré par ``startup.py`` : l'API Revit n'accepte
    ``RegisterDockablePane`` que pendant OnStartup.
    """

    panel_id = '7f3c1a92-4b6e-4d18-9a55-0c2f8e1d4b07'
    panel_source = os.path.join(AppPaths().pages_dir(), 'OpenArchiPanel.xaml')
    panel_title = 'OpenArchi'

    def __init__(self):
        # Le thème 418 est fusionné AVANT le parse du XAML : les
        # DynamicResource du panneau se résolvent sur Page.Resources.
        try:
            UIResourceLoader(self, dark=is_dark()).merge_theme()
            forms.WPFPanel.__init__(self)
            vm = OpenArchiChatVM()
        except Exception:
            # Revit avale les exceptions de construction d'un volet ancré :
            # sans cette trace, le panneau reste vide sans un mot.
            _log.exception('construction du panneau impossible')
            raise
        self.DataContext = vm
        self._suivre_dernier_message(vm)
        self._curseur_en_fin(vm)
        self._depot_fichiers(vm)

    def _depot_fichiers(self, vm):
        """Glisser-déposer de fichiers sur le panneau.

        Deux points qui ne s'improvisent pas :

        - en *Preview* (tunneling), pas en bubbling : le champ de saisie est
          un TextBox, donc ``AllowDrop`` d'office, et il avale le dépôt avant
          que la Page le voie. On marque ``Handled`` en descendant.
        - ``DragDropEffects.None`` ne s'écrit pas en Python — ``None`` est un
          mot-clé, d'où le ``getattr``.
        """
        try:
            from System.Windows import DataFormats, DragDropEffects

            aucun = getattr(DragDropEffects, 'None')

            def _fichiers(args):
                try:
                    if not args.Data.GetDataPresent(DataFormats.FileDrop):
                        return None
                    return list(args.Data.GetData(DataFormats.FileDrop))
                except Exception:
                    return None

            def _survol(sender, args):
                args.Effects = (DragDropEffects.Copy if _fichiers(args)
                                else aucun)
                args.Handled = True

            def _depot(sender, args):
                chemins = _fichiers(args)
                if not chemins:
                    return
                args.Handled = True
                try:
                    vm.deposer(chemins)
                except Exception:
                    # Jamais laisser lever sur le fil d'UI : Revit tombe.
                    _log.exception('dépôt de %s', chemins)

            self.AllowDrop = True
            self.PreviewDragOver += _survol
            self.PreviewDrop += _depot
        except Exception:
            _log.exception('glisser-déposer indisponible')

    def _curseur_en_fin(self, _vm):
        """Après un rappel d'historique, remet le curseur en fin de ligne.

        Deux pièges, tous deux payés :

        - suivre ``PropertyChanged`` du VM ne marche pas : la notification
          part AVANT que la liaison ait écrit le texte dans le champ, donc
          WPF repose le curseur au début juste après nous. D'où le
          ``BeginInvoke`` en priorité Background, qui passe après elle.
        - ne réagir qu'aux flèches Haut et Bas, jamais à ``TextChanged`` :
          sinon chaque frappe renverrait le curseur au bout, et il
          deviendrait impossible de corriger le milieu d'une phrase.
        """
        try:
            from System import Action
            from System.Windows.Input import Key
            from System.Windows.Threading import DispatcherPriority

            def _au_bout():
                try:
                    self.Saisie.CaretIndex = len(self.Saisie.Text or '')
                except Exception:
                    pass               # jamais laisser lever sur le fil d'UI

            def _touche(sender, args):
                if args.Key not in (Key.Up, Key.Down):
                    return
                try:
                    self.Saisie.Dispatcher.BeginInvoke(
                        DispatcherPriority.Background, Action(_au_bout))
                except Exception:
                    pass

            self.Saisie.PreviewKeyDown += _touche
        except Exception:
            _log.exception('suivi du curseur impossible')

    def _suivre_dernier_message(self, vm):
        # Défilement automatique : sans cela le dernier message reste sous la
        # ligne de flottaison dès que la conversation dépasse la hauteur.
        try:
            def _defiler(sender, args):
                self.Conversation.ScrollToEnd()
            vm.Messages.CollectionChanged += _defiler
        except Exception:
            pass
