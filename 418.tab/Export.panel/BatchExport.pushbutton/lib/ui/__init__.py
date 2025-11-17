# -*- coding: utf-8 -*-
"""Module interface utilisateur de l'extension 418 Export.

Ce module gère toute l'interface graphique de l'application, incluant:
- Les fenêtres principales (MainWindow, Piker, SetupEditor)
- Les gestionnaires d'événements
- Les composants UI réutilisables
- Les helpers et validateurs UI

Structure:
    windows/    - Fenêtres WPF principales
    handlers/   - Gestionnaires d'événements UI
    components/ - Composants réutilisables (preview, progress)
    helpers/    - Utilitaires UI (combos, état, chargement XAML)
    validation/ - Validateurs d'entrées utilisateur
"""

# Import principal pour usage simplifié
from .windows.main_window import ExportMainWindow as MainWindow

__all__ = ['MainWindow']
