# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# IMPORTANT : référencer les assemblies .NET AVANT d'importer
# System.ComponentModel. Sous IronPython, l'assembly `System` (qui contient
# INotifyPropertyChanged) n'est pas référencée par défaut ; sans ce préchargement,
# l'import ci-dessous échoue silencieusement et BaseViewModel retombe sur la
# branche `object` (notifications PropertyChanged inertes -> les bindings WPF ne
# se rafraîchissent jamais). BaseViewModel pouvant être importé AVANT BaseWindow
# (qui appelle déjà ensure_wpf), on doit garantir le référencement ici aussi.
try:
    from ui.helpers.wpf_runtime import ensure_wpf as _ensure_wpf
    _ensure_wpf()
except Exception:
    pass

try:
    from System.ComponentModel import INotifyPropertyChanged, PropertyChangedEventArgs
    _has_wpf = True
except Exception:
    INotifyPropertyChanged = object
    _has_wpf = False

try:
    from core.AppPaths import AppPaths as _AppPaths
except Exception:
    _AppPaths = None

try:
    from ui.helpers.DarkMode import is_dark as _is_dark
except Exception:
    def _is_dark():
        return False


def _resolve_logo_path():
    # Chemin absolu du logo selon le thème ; '' si indisponible.
    if _AppPaths is None:
        return ''
    try:
        dark = bool(_is_dark())
    except Exception:
        dark = False
    try:
        return _AppPaths().logo_path(dark=dark)
    except Exception:
        return ''


def _resolve_brand_logo_path():
    # Logo de la pastille de marque : le fond (dégradé accent) est TOUJOURS
    # foncé dans les deux thèmes, on force donc la variante claire (logo blanc)
    # pour garder le contraste. '' si indisponible.
    if _AppPaths is None:
        return ''
    try:
        return _AppPaths().logo_path(dark=True)
    except Exception:
        return ''


class _LogoMixin(object):
    """Propriétés de logo communes aux deux variantes de BaseViewModel."""

    @property
    def LogoPath(self):
        # Chemin absolu du logo commun, thème-aware. Bindable en Source.
        return _resolve_logo_path()

    @property
    def BrandLogoPath(self):
        # Logo pour la pastille de marque (fond foncé) : variante claire.
        return _resolve_brand_logo_path()


if _has_wpf:
    class BaseViewModel(_LogoMixin, INotifyPropertyChanged):
        def __init__(self):
            self._pc_handlers = []

        def add_PropertyChanged(self, handler):
            self._pc_handlers.append(handler)

        def remove_PropertyChanged(self, handler):
            try:
                self._pc_handlers.remove(handler)
            except ValueError:
                pass

        def notify_property(self, name):
            if not self._pc_handlers:
                return
            args = PropertyChangedEventArgs(name)
            for h in list(self._pc_handlers):
                try:
                    h(self, args)
                except Exception:
                    pass
else:
    class BaseViewModel(_LogoMixin):
        def __init__(self):
            pass

        def notify_property(self, name):
            pass
