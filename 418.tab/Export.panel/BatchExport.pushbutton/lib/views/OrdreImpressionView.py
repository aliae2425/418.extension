# -*- coding: utf-8 -*-
# Vue de la modale « Ordre d'impression » : charge GUI/Modals/OrdreImpression.xaml
# sur la coquille commune (BaseWindow), câble les 5 boutons et le
# glisser-déposer de la liste.
#
# Rien d'autre : le déplacement, le tri et la validation sont dans
# `OrdreImpressionViewModel`, donc testables hors WPF. Les deux gestes
# aboutissent au MÊME `deplacer_vers()` — le glisser ne double pas la logique
# des flèches, il lui donne seulement un départ et une arrivée.
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = object

# Contenu du DataObject pendant le glisser. Il n'identifie rien par lui-même
# (le rang de départ est gardé côté Python) : il sert à REFUSER les dépôts
# venus d'ailleurs — l'Explorateur, une autre fenêtre — qui tomberaient
# sinon dans le gestionnaire de dépôt avec un rang de départ périmé.
_MARQUEUR = u'418.ordre-impression'


def _xaml_path():
    here = os.path.dirname(os.path.abspath(__file__))
    button = os.path.abspath(os.path.join(here, '..', '..'))
    return os.path.join(button, 'GUI', 'Modals', 'OrdreImpression.xaml')


class OrdreImpressionView(BaseWindow):
    def __init__(self, view_model):
        super(OrdreImpressionView, self).__init__(_xaml_path(), view_model)
        self._vm = view_model

    def _load(self):
        super(OrdreImpressionView, self)._load()
        self.wire_boutons()
        self.wire_glisser_deposer()

    def wire_boutons(self):
        """Câblage best-effort, comme le reste de l'outil : un bouton absent
        du XAML (FindName -> None) laisse la fenêtre charger sans lever."""
        if self._window is None:
            return
        vm = self._vm

        def _fermer():
            try:
                self._window.Close()
            except Exception:
                pass

        def _valider():
            # `valider()` d'abord : c'est le drapeau que l'appelant lit au
            # retour de ShowDialog pour savoir s'il doit appliquer l'ordre.
            try:
                vm.valider()
            except Exception:
                pass
            _fermer()

        actions = (
            (u'MonterButton', lambda: vm.monter()),
            (u'DescendreButton', lambda: vm.descendre()),
            (u'TrierButton', lambda: vm.trier_numero()),
            (u'ValiderButton', _valider),
            (u'AnnulerButton', _fermer),
        )
        for nom, action in actions:
            btn = self._window.FindName(nom)
            if btn is None:
                continue
            self._brancher(btn, action)

    @staticmethod
    def _brancher(btn, action):
        def _handler(sender, args):
            try:
                action()
            except Exception:
                pass
        try:
            btn.Click += _handler
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Glisser-déposer
    # ------------------------------------------------------------------
    #
    # WPF ne sait pas réordonner une ListBox : il faut les quatre
    # évènements à la main. Le schéma est celui qu'on retrouve partout, et
    # chacune de ses étapes règle un problème précis :
    #
    #   PreviewMouseLeftButtonDown  note le point et le rang, sans rien
    #                               marquer traité — sinon la ListBox perd
    #                               sa sélection au clic ;
    #   PreviewMouseMove            n'ouvre le glisser qu'au-delà du seuil
    #                               système, sinon un clic un peu tremblant
    #                               déplacerait une feuille ;
    #   DragOver                    dit « déplacement » (le curseur suit) ;
    #   Drop                        résout le rang d'arrivée et bouge.
    #
    # Le rang de départ ne voyage PAS dans le DataObject : il reste dans
    # `etat`, côté Python. Faire transiter un entier par un DataObject
    # fonctionne, mais oblige à le re-typer au retour — pour une valeur que
    # cette fenêtre modale est seule à produire et à consommer.
    # ------------------------------------------------------------------

    def wire_glisser_deposer(self):
        if self._window is None:
            return
        try:
            from System.Windows import (DragDrop, DragDropEffects, DataFormats,
                                        SystemParameters)
            from System.Windows.Controls import ListBoxItem
            from System.Windows.Input import MouseButtonState
            from System.Windows.Media import VisualTreeHelper
        except Exception:
            return

        liste = self._window.FindName(u'FeuillesListBox')
        if liste is None:
            return

        vm = self._vm
        # `DragDropEffects.None` est un mot-clé Python : seul getattr y accède.
        aucun = getattr(DragDropEffects, 'None')
        etat = {'origine': None, 'rang': None, 'en_cours': None}

        def _rang_sous(source):
            """Rang de la ligne sous `source` dans `vm.Feuilles`, ou None."""
            courant = source
            while courant is not None:
                if isinstance(courant, ListBoxItem):
                    try:
                        return vm.Feuilles.index(courant.DataContext)
                    except Exception:
                        return None
                try:
                    courant = VisualTreeHelper.GetParent(courant)
                except Exception:
                    return None
            return None

        def _on_down(sender, args):
            try:
                etat['origine'] = args.GetPosition(liste)
                etat['rang'] = _rang_sous(args.OriginalSource)
            except Exception:
                etat['origine'] = None
                etat['rang'] = None

        def _on_move(sender, args):
            depart = etat.get('rang')
            if depart is None or etat.get('origine') is None:
                return
            try:
                if args.LeftButton != MouseButtonState.Pressed:
                    etat['rang'] = None
                    return
                ici = args.GetPosition(liste)
                la = etat['origine']
                if (abs(ici.X - la.X) < SystemParameters.MinimumHorizontalDragDistance
                        and abs(ici.Y - la.Y) < SystemParameters.MinimumVerticalDragDistance):
                    return
            except Exception:
                return
            # Une seule prise par appui : sans ça, chaque pixel parcouru
            # rouvrirait un glisser par-dessus le précédent.
            etat['rang'] = None
            etat['en_cours'] = depart
            try:
                DragDrop.DoDragDrop(liste, _MARQUEUR, DragDropEffects.Move)
            except Exception:
                pass
            finally:
                # Lâché hors de la fenêtre : `Drop` n'a jamais tiré, c'est
                # ici que le glisser se termine.
                etat['en_cours'] = None

        def _on_drag_over(sender, args):
            try:
                args.Effects = (DragDropEffects.Move
                                if etat.get('en_cours') is not None else aucun)
                args.Handled = True
            except Exception:
                pass

        def _on_drop(sender, args):
            depart = etat.get('en_cours')
            etat['en_cours'] = None
            if depart is None:
                return
            try:
                if not args.Data.GetDataPresent(DataFormats.StringFormat):
                    return
                if args.Data.GetData(DataFormats.StringFormat) != _MARQUEUR:
                    return
                arrivee = _rang_sous(args.OriginalSource)
                if arrivee is None:
                    # Lâché sous la dernière ligne, dans le vide du
                    # ScrollViewer : la feuille va en fin de liste.
                    arrivee = len(vm.Feuilles) - 1
                vm.deplacer_vers(depart, arrivee)
                args.Handled = True
            except Exception:
                pass

        # Abonnements un par un : `evenement += handler` est une FORME que
        # IronPython traduit à la compilation. Passer par getattr/__iadd__
        # pour en faire une boucle ne s'abonne pas de façon fiable.
        try:
            liste.PreviewMouseLeftButtonDown += _on_down
        except Exception:
            pass
        try:
            liste.PreviewMouseMove += _on_move
        except Exception:
            pass
        try:
            liste.DragOver += _on_drag_over
        except Exception:
            pass
        try:
            liste.Drop += _on_drop
        except Exception:
            pass
