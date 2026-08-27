# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    try:
        from lib.ui.base.BaseWindow import BaseWindow
    except Exception:
        BaseWindow = object

try:
    from lib.viewmodels.EditeurVM import hex_de_rgb, rgb_de_hex
except Exception:
    from viewmodels.EditeurVM import hex_de_rgb, rgb_de_hex

try:
    from lib.viewmodels.MotifPickerVM import MotifPickerVM
except Exception:
    from viewmodels.MotifPickerVM import MotifPickerVM

try:
    from lib.views.MotifPickerWindowView import MotifPickerWindowView
except Exception:
    from views.MotifPickerWindowView import MotifPickerWindowView

# Sélecteur de couleur : celui de WinForms. WPF n'en fournit aucun, et
# celui-là est livré avec le framework, familier de tout le monde, et gère la
# palette personnalisée. Écrire le nôtre serait un composant à part entière.
try:
    import clr
    clr.AddReference('System.Windows.Forms')
    clr.AddReference('System.Drawing')
    from System.Windows.Forms import ColorDialog, DialogResult
    from System.Drawing import Color as CouleurGdi
except Exception:
    ColorDialog = None
    DialogResult = None
    CouleurGdi = None

_XAML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'GUI', 'Views', 'EditeurWindow.xaml')


def couleur_choisie(hex_actuel):
    """Ouvre le sélecteur de couleur de Windows. Hex retenu, ou None."""
    if ColorDialog is None:
        # Silencieux, l'utilisateur croirait à un clic qui n'a pas pris.
        print('EditeurWindowView: System.Windows.Forms indisponible, '
              'pas de sélecteur de couleur — saisissez la valeur hex.')
        return None
    rouge, vert, bleu = rgb_de_hex(hex_actuel)
    dialogue = ColorDialog()
    dialogue.FullOpen = True          # panneau de mélange déplié d'emblée
    dialogue.AnyColor = True
    dialogue.Color = CouleurGdi.FromArgb(rouge, vert, bleu)
    if dialogue.ShowDialog() != DialogResult.OK:
        return None
    retenue = dialogue.Color
    return hex_de_rgb((retenue.R, retenue.G, retenue.B))


class EditeurWindowView(BaseWindow):
    """Fenêtre modale d'édition d'un matériau.

    `Annuler` porte IsCancel et se ferme tout seul ; `Enregistrer` est câblé
    ici parce qu'il ne doit fermer QUE si Revit a tout accepté — sinon la
    fenêtre reste ouverte avec la liste des propriétés refusées en pied.

    Les boutons de motif et de couleur vivent dans un DataTemplate répété
    quatre fois : pas de x:Name, donc pas de `FindName`. Ils passent par des
    `RelayCommand` du socle que cette vue branche sur ses deux dialogues —
    un binding `Command` ne dépend ni de la remontée d'un événement routé ni
    de la réalisation des conteneurs de l'ItemsControl.
    """

    def __init__(self, view_model, proprietaire=None):
        super(EditeurWindowView, self).__init__(_XAML, view_model)
        self._proprietaire = proprietaire

    def _load(self):
        super(EditeurWindowView, self)._load()
        if self._window is None:
            return
        # Owner : rend la modale vraiment modale par rapport à la fenêtre
        # Matériaux, et donne son sens à WindowStartupLocation=CenterOwner.
        if self._proprietaire is not None:
            try:
                self._window.Owner = self._proprietaire
            except Exception:
                pass
        bouton = self._window.FindName('EnregistrerButton')
        if bouton is not None:
            bouton.Click += self._on_enregistrer
        self._vm.brancher_dialogues(self._choisir_motif, self._choisir_couleur)

    def _on_enregistrer(self, sender, args):
        if self._vm.enregistrer():
            self._window.Close()

    # ------------------------------------------------------------------
    # Les deux dialogues branchés sur les commandes du ViewModel
    # ------------------------------------------------------------------

    def _choisir_motif(self, emplacement):
        """Modale de choix. `Motifs` est déjà filtré des motifs que Revit
        refuserait ici ; `Contrainte` dit pourquoi, le cas échéant."""
        picker = MotifPickerVM(emplacement.Titre, emplacement.Motifs,
                               emplacement.Motif,
                               contrainte=emplacement.Contrainte)
        MotifPickerWindowView(picker, proprietaire=self._window).show()
        if picker.Resultat is not None:
            emplacement.Motif = picker.Resultat

    @staticmethod
    def _choisir_couleur(contexte):
        """Marche pour la couleur du matériau comme pour celle d'un
        emplacement : les deux exposent une propriété `Couleur` en hex."""
        retenue = couleur_choisie(getattr(contexte, 'Couleur', None))
        if retenue:
            contexte.Couleur = retenue
