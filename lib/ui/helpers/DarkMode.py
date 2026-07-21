# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from pyrevit.userconfig import user_config as _UC
    def is_dark():
        try:
            theme = _UC.core.get_option('colorize_docs', 'default')
            return str(theme).lower() in ('dark', 'true', '1')
        except Exception:
            return False
except Exception:
    def is_dark():
        return False


def apply_dark_mode(win, paths):
    try:
        from System.Windows import ResourceDictionary
        from System import Uri, UriKind
    except Exception as e:
        print('DarkMode: WPF non disponible: {}'.format(e))
        return
    for name in ('ColorsDark.xaml', 'StylesDark.xaml'):
        path = paths.resource_path(name)
        try:
            rd = ResourceDictionary()
            uri_str = 'file:///' + path.replace('\\', '/').replace(':', ':/')
            rd.Source = Uri(uri_str, UriKind.Absolute)
            win.Resources.MergedDictionaries.Add(rd)
        except Exception as e:
            print('DarkMode: Impossible de charger {}: {}'.format(name, e))
