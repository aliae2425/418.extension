# -*- coding: utf-8 -*-

# Etat et constantes partagées pour l'UI

# Visibilité WPF (fallback si hors Revit/.NET)
try:
    from System.Windows import Visibility  # type: ignore
except Exception:
    class _V:  # type: ignore
        # TODO: compléter si besoin d'autres états (Hidden)
        Visible = 0
        Collapsed = 2
    Visibility = _V()

# Brosses WPF (couleurs) avec fallback
try:
    from System.Windows.Media import Brushes  # type: ignore
except Exception:
    Brushes = None  # type: ignore

# Disponibilité de l'API Revit
REVIT_API_AVAILABLE = False
try:
    from Autodesk.Revit.DB import FilteredElementCollector, ViewSheet  # noqa: F401
    REVIT_API_AVAILABLE = True
except Exception:
    REVIT_API_AVAILABLE = False

# Config utilisateur (namespace batch_export)
from ..config import UserConfigStore as UC  # noqa: E402
CONFIG = UC('batch_export')

# Noms des ComboBox de paramètres
_PARAM_COMBOS = ["ExportationCombo", "CarnetCombo", "DWGCombo"]

# Titre de la fenêtre principale
EXPORT_WINDOW_TITLE = u"418 • Exportation"
