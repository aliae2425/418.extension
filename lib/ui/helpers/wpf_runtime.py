# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""Chargement des assemblies WPF (.NET).

Selon le moteur pyRevit (IronPython ou CPython), les assemblies WPF ne sont
pas toujours référencées par défaut : les imports `from System.Windows...`
échouent alors au chargement des modules. Ce helper charge explicitement les
assemblies nécessaires, comme le fait pyRevit lui-même. Hors .NET (exécution
standalone), il ne fait rien et signale que WPF est indisponible.
"""

_WPF_ASSEMBLIES = (
    'PresentationFramework',
    'PresentationCore',
    'WindowsBase',
    'System.Xaml',
    # System.dll : contient System.Uri / System.UriKind. Sous IronPython, le
    # namespace System de base (mscorlib) n'expose pas Uri tant que l'assembly
    # System n'est pas explicitement référencée -> « Cannot import name Uri ».
    'System',
)

_ensured = False


def ensure_wpf():
    """Référence les assemblies WPF si besoin.

    Retourne True si WPF est disponible, False sinon. Idempotent : les appels
    suivants sont sans effet une fois les assemblies chargées.
    """
    global _ensured
    try:
        import clr
    except Exception:
        return False
    if not _ensured:
        for name in _WPF_ASSEMBLIES:
            try:
                clr.AddReference(name)
            except Exception:
                pass
        _ensured = True
    try:
        from System.Windows.Markup import XamlReader  # noqa: F401
        return True
    except Exception:
        return False
