# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    from lib.ui.base.BaseWindow import BaseWindow

_XAML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'GUI', 'Views', 'MainWindow.xaml')


def _controle_webview(url, dossier_donnees):
    """Un contrôle WebView2 prêt à naviguer, ou une exception explicite.

    Les assemblies `Microsoft.Web.WebView2.*` sont livrées AVEC Revit 2026 et
    déjà chargées dans le process (Revit s'en sert pour son écran d'accueil),
    et le runtime Edge WebView2 est présent sur toute machine Windows 11 à
    jour. Rien à embarquer dans le dépôt, rien à installer.
    """
    import clr
    try:
        clr.AddReference('Microsoft.Web.WebView2.Wpf')
    except Exception:
        # Résolution par nom refusée : on va chercher la DLL dans le dossier
        # d'installation de Revit, sans coder en dur le numéro de version.
        from System import AppDomain
        clr.AddReferenceToFileAndPath(os.path.join(
            AppDomain.CurrentDomain.BaseDirectory,
            'Microsoft.Web.WebView2.Wpf.dll'))
    from Microsoft.Web.WebView2.Wpf import (WebView2,
                                            CoreWebView2CreationProperties)
    from System import Uri

    proprietes = CoreWebView2CreationProperties()
    # Sans dossier explicite, WebView2 écrit à côté de Revit.exe — dossier
    # non inscriptible pour un utilisateur standard, et l'initialisation
    # échoue alors sans message.
    proprietes.UserDataFolder = dossier_donnees
    vue = WebView2()
    vue.CreationProperties = proprietes
    vue.Source = Uri(url)
    return vue


class MainWindowView(BaseWindow):
    """Fenêtre à deux colonnes : contraintes lues à gauche, calculateur web
    embarqué à droite.

    Pas de rail : l'outil n'a qu'un écran. `RailWindow` demanderait des
    onglets qui n'existent pas.
    """

    def __init__(self, view_model, dossier_donnees):
        super(MainWindowView, self).__init__(_XAML, view_model)
        self._dossier_donnees = dossier_donnees
        self._navigateur = None

    def _load(self):
        super(MainWindowView, self)._load()
        if self._window is None:
            return
        self._monte_navigateur()
        self._cable('EnvoyerButton', self._envoyer)
        self._cable('NavigateurButton', self._ouvrir_navigateur)

    def _cable(self, nom, callback):
        bouton = self._window.FindName(nom)
        if bouton is not None:
            bouton.Click += lambda sender, args: callback()

    def _monte_navigateur(self):
        hote = self._window.FindName('WebHost')
        if hote is None:
            return
        try:
            self._navigateur = _controle_webview(self._vm.UrlToolbox,
                                                 self._dossier_donnees)
            hote.Child = self._navigateur
        except Exception as erreur:
            message = self._window.FindName('WebHostMessage')
            if message is not None:
                message.Text = (
                    u'Calculateur non affichable ici : {}\n\n'
                    u'Utilisez « Ouvrir dans le navigateur ».'.format(erreur))

    def _envoyer(self):
        """Rejoue l'URL avec les valeurs courantes.

        On ne navigue pas à chaque frappe : chaque navigation recharge la page
        et ferait perdre les tronçons que l'utilisateur vient d'y ajuster.
        """
        if self._navigateur is None:
            self._ouvrir_navigateur()
            return
        from System import Uri
        self._navigateur.Source = Uri(self._vm.UrlToolbox)

    def _ouvrir_navigateur(self):
        os.startfile(self._vm.UrlToolbox)
