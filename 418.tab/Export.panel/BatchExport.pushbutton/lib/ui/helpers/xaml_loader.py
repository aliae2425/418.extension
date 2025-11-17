# -*- coding: utf-8 -*-
"""Helper pour le chargement des fichiers XAML.

Ce module fournit des fonctions pour localiser et charger les fichiers XAML
de l'application, en gérant les chemins relatifs correctement.
"""

import os


def get_xaml_path(relative_path):
    """Retourne le chemin absolu vers un fichier XAML.
    
    Args:
        relative_path (str): Chemin relatif depuis le dossier GUI/
            Ex: 'Views/MainWindow.xaml' ou 'Controls/ParameterSelector.xaml'
    
    Returns:
        str: Chemin absolu vers le fichier XAML
    
    Examples:
        >>> get_xaml_path('Views/MainWindow.xaml')
        '/path/to/GUI/Views/MainWindow.xaml'
    """
    # Remonter depuis lib/ui/helpers/ vers le dossier racine du bouton
    current_dir = os.path.dirname(__file__)  # lib/ui/helpers/
    button_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # Racine du bouton
    gui_dir = os.path.join(button_root, 'GUI')
    xaml_path = os.path.join(gui_dir, relative_path)
    return xaml_path


def get_legacy_xaml_path(filename):
    """Retourne le chemin absolu vers un fichier XAML dans l'ancienne structure.
    
    Pour compatibilité avec l'ancien code qui cherchait directement dans GUI/.
    
    Args:
        filename (str): Nom du fichier XAML
            Ex: 'MainWindow.xaml', 'Piker.xaml'
    
    Returns:
        str: Chemin absolu vers le fichier XAML
    """
    # Chercher d'abord dans Views/ (nouvelle structure)
    views_path = get_xaml_path(os.path.join('Views', filename))
    if os.path.exists(views_path):
        return views_path
    
    # Fallback: racine de GUI/ (ancienne structure)
    current_dir = os.path.dirname(__file__)
    button_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    legacy_path = os.path.join(button_root, 'GUI', filename)
    return legacy_path


__all__ = ['get_xaml_path', 'get_legacy_xaml_path']
