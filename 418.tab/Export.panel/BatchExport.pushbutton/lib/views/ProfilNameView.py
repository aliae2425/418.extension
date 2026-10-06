# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = object  # type: ignore


def _xaml_path():
    here = os.path.dirname(os.path.abspath(__file__))
    button = os.path.abspath(os.path.join(here, '..', '..'))
    return os.path.join(button, 'GUI', 'Modals', 'ProfilName.xaml')


class ProfilNameView(BaseWindow):
    """Saisie du nom d'un profil, dans la DA de l'outil (remplace
    `pyrevit.forms.ask_for_string`).

    Modale (`show()` -> `ShowDialog`) : après l'appel, `self.Nom` contient
    le nom saisi, ou `None` si l'utilisateur a annulé/fermé la fenêtre.
    `reserves` liste les noms refusés (« Défaut ») -- refusés DANS la modale,
    avec un message en place, plutôt qu'après coup dans la barre d'état de la
    fenêtre principale. Réutiliser le nom d'un profil EXISTANT reste permis :
    c'est la façon normale de le mettre à jour.
    """

    def __init__(self, defaut=u'', reserves=None):
        super(ProfilNameView, self).__init__(_xaml_path(), view_model=None)
        self._defaut = defaut or u''
        self._reserves = set(reserves or ())
        self.Nom = None

    def _load(self):
        super(ProfilNameView, self)._load()
        if self._window is None:
            return

        box = self._window.FindName(u'NomTextBox')
        erreur = self._window.FindName(u'ErreurBlock')
        if box is not None:
            try:
                box.Text = self._defaut
                box.SelectAll()
                box.Focus()
            except Exception:
                pass

        def _afficher_erreur(message):
            if erreur is None:
                return
            try:
                from System.Windows import Visibility
                erreur.Text = message
                erreur.Visibility = Visibility.Visible
            except Exception:
                pass

        def _valider(sender, args):
            nom = u''
            if box is not None:
                try:
                    nom = (box.Text or u'').strip()
                except Exception:
                    nom = u''
            if not nom:
                _afficher_erreur(u'Saisissez un nom de profil.')
                return
            if nom in self._reserves:
                _afficher_erreur(
                    u'« {} » est un nom réservé : choisissez-en un autre.'.format(nom))
                return
            self.Nom = nom
            try:
                self._window.Close()
            except Exception:
                pass

        def _annuler(sender, args):
            self.Nom = None
            try:
                self._window.Close()
            except Exception:
                pass

        for name, handler in ((u'ValiderButton', _valider),
                              (u'AnnulerButton', _annuler)):
            btn = self._window.FindName(name)
            if btn is None:
                continue
            try:
                btn.Click += handler
            except Exception:
                pass
