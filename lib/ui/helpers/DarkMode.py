# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def is_dark():
    """Retourne True si Revit est en thème sombre.

    Source de vérité : l'API Revit ``UIThemeManager.CurrentTheme`` — le même
    mécanisme que les fenêtres de BatchExport. L'ancienne implémentation lisait
    l'option pyRevit ``colorize_docs`` (colorisation des onglets), sans rapport
    avec le thème de l'UI, d'où un dark mode incohérent.

    Hors Revit (exécution standalone), l'import échoue et on retombe sur False.
    """
    try:
        from Autodesk.Revit.UI import UIThemeManager, UITheme
        return UIThemeManager.CurrentTheme == UITheme.Dark
    except Exception:
        return False
