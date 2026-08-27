# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os


def _load_wpf():
    """Charge et retourne les types WPF nécessaires, ou None si indisponible.

    IMPORTANT : l'import est fait AU MOMENT DE L'USAGE (et non à l'import du
    module). Évaluer la disponibilité WPF à l'import est fragile : selon l'ordre
    d'import, le module pouvait être chargé avant que les assemblies WPF soient
    référencées, figeant alors un état « indisponible » pour toute la session
    même si la fenêtre s'affiche ensuite correctement. On appelle donc
    ``ensure_wpf`` puis on importe juste avant d'en avoir besoin.
    """
    try:
        from ui.helpers.wpf_runtime import ensure_wpf
        ensure_wpf()
    except Exception:
        pass
    try:
        from System import Uri, UriKind
        from System.Windows import ResourceDictionary
        return Uri, UriKind, ResourceDictionary
    except Exception:
        return None


try:
    from core.AppPaths import AppPaths as _AppPaths
except Exception:
    _AppPaths = None


class UIResourceLoader(object):
    def __init__(self, window, dark=False):
        self._win = window
        self._dark = dark
        self._paths = _AppPaths() if _AppPaths is not None else None

    def merge_theme(self):
        wpf = _load_wpf()
        if wpf is None:
            print('UIResourceLoader: WPF non disponible')
            return False
        Uri, UriKind, ResourceDictionary = wpf
        if self._paths is None:
            print('UIResourceLoader: AppPaths non disponible')
            return False
        # SEULES les couleurs changent selon le thème. Le dictionnaire de
        # styles est unique : il ne contient aucune couleur littérale, tout
        # passe par DynamicResource, y compris les opacités d'ombre.
        suffix = 'Dark' if self._dark else ''
        for name in ('Colors{}.xaml'.format(suffix), 'Icons.xaml', 'Styles.xaml'):
            path = self._paths.resource_path(name)
            if not os.path.exists(path):
                print('UIResourceLoader: ressource introuvable: {}'.format(path))
                continue
            try:
                rd = ResourceDictionary()
                uri_str = 'file:///' + path.replace('\\', '/').replace(':', ':/')
                rd.Source = Uri(uri_str, UriKind.Absolute)
                self._win.Resources.MergedDictionaries.Add(rd)
            except Exception as e:
                print('UIResourceLoader: Erreur chargement {}: {}'.format(name, e))
        return True

    def merge_resource(self, xaml_path):
        if not os.path.exists(xaml_path):
            return False
        wpf = _load_wpf()
        if wpf is None:
            return False
        Uri, UriKind, ResourceDictionary = wpf
        try:
            rd = ResourceDictionary()
            uri_str = 'file:///' + xaml_path.replace('\\', '/').replace(':', ':/')
            rd.Source = Uri(uri_str, UriKind.Absolute)
            self._win.Resources.MergedDictionaries.Add(rd)
            return True
        except Exception as e:
            print('UIResourceLoader: Erreur merge_resource {}: {}'.format(xaml_path, e))
            return False
