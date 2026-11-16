# -*- coding: utf-8 -*-
"""Popup modale façon Win+V : sous le curseur, au clavier, refermée avant le
collage — le mode « point » (PickPoint) exige que plus rien ne soit modal."""
from __future__ import unicode_literals
import os

try:
    from core.AppPaths import AppPaths
    from core.journal import journal
except Exception:
    from lib.core.AppPaths import AppPaths
    from lib.core.journal import journal

try:
    from ui.base.BaseWindow import BaseWindow
    from ui.PressePapiersVM import MEME_EMPLACEMENT, VUE_COURANTE, NORMAL
except Exception:
    from lib.ui.base.BaseWindow import BaseWindow
    from lib.ui.PressePapiersVM import MEME_EMPLACEMENT, VUE_COURANTE, NORMAL

_log = journal('presse_papiers')


class PressePapiersPopup(BaseWindow):

    def __init__(self, vm, proprietaire=None):
        """``proprietaire`` : handle de la fenêtre Revit
        (``uiapp.MainWindowHandle``), pour rester au-dessus d'elle."""
        BaseWindow.__init__(self, os.path.join(AppPaths().ui_gui_dir(),
                                               'PressePapiersPopup.xaml'), vm)
        self._proprietaire = proprietaire
        self._mode = None
        self._fermee = False

    def ouvrir(self):
        """Affiche, attend le choix, PUIS colle (fenêtre déjà fermée)."""
        self._load()
        w = self._window
        if w is None:
            return
        try:
            from System.Windows.Input import Key
            touches = {
                Key.D1: MEME_EMPLACEMENT, Key.NumPad1: MEME_EMPLACEMENT,
                Key.Return: MEME_EMPLACEMENT,
                Key.D2: VUE_COURANTE, Key.NumPad2: VUE_COURANTE,
                Key.D3: NORMAL, Key.NumPad3: NORMAL,
            }

            def _touche(sender, args):
                if args.Key in touches:
                    self._fermer(touches[args.Key])
                elif args.Key == Key.Escape:
                    self._fermer(None)
                elif args.Key in (Key.Up, Key.Down):
                    self._vm.selectionner_decalage(-1 if args.Key == Key.Up else 1)
                    if self._vm.Selection is not None:
                        w.FindName('Liste').ScrollIntoView(self._vm.Selection)
                elif args.Key == Key.Delete:
                    self._vm.retirer()
                else:
                    return
                args.Handled = True

            w.PreviewKeyDown += _touche
            w.Deactivated += lambda s, a: self._fermer(None)
            w.FindName('Liste').MouseDoubleClick += \
                lambda s, a: self._fermer(MEME_EMPLACEMENT)
            w.SourceInitialized += lambda s, a: self._sous_le_curseur()
            w.Loaded += lambda s, a: w.Activate()
            if self._proprietaire is not None:
                from System.Windows.Interop import WindowInteropHelper
                WindowInteropHelper(w).Owner = self._proprietaire
        except Exception:
            _log.exception('câblage de la popup')
        w.ShowDialog()
        if self._mode is not None and self._vm.Selection is not None:
            self._vm.coller(self._mode)

    def _fermer(self, mode):
        # Deactivated tombe aussi PENDANT Close() : sans garde, second Close
        # sur une fenêtre en fermeture -> InvalidOperationException.
        if self._fermee:
            return
        self._fermee = True
        self._mode = mode
        self._window.Close()

    def _sous_le_curseur(self):
        """Curseur en pixels physiques -> unités WPF de CETTE fenêtre (DPI de
        son écran), puis bornée à l'écran virtuel (multi-écran compris)."""
        try:
            import clr
            clr.AddReference('System.Windows.Forms')
            from System.Windows import PresentationSource, Point, SystemParameters
            from System.Windows.Forms import Cursor
            w = self._window
            px = Cursor.Position
            source = PresentationSource.FromVisual(w)
            p = source.CompositionTarget.TransformFromDevice.Transform(Point(px.X, px.Y))
            droite = SystemParameters.VirtualScreenLeft + SystemParameters.VirtualScreenWidth
            bas = SystemParameters.VirtualScreenTop + SystemParameters.VirtualScreenHeight
            # ponytail: bornage sur l'écran virtuel et MaxHeight, pas sur la
            # zone de travail du moniteur du curseur ; passer par
            # Screen.FromPoint si la popup déborde sous une barre des tâches.
            w.Left = max(SystemParameters.VirtualScreenLeft, min(p.X, droite - w.Width))
            w.Top = max(SystemParameters.VirtualScreenTop, min(p.Y, bas - w.MaxHeight))
        except Exception:
            _log.exception('position de la popup')
