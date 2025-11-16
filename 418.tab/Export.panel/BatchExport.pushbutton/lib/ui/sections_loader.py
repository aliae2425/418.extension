# -*- coding: utf-8 -*-

# Chargement des XAML et enregistrement des éléments nommés
import os
import sys

GUI_FILE = os.path.join('GUI', 'MainWindow.xaml')
PIKER_FILE = os.path.join('GUI', 'Piker.xaml')


def _first_existing(paths):
    for p in paths:
        try:
            if p and os.path.exists(p):
                return p
        except Exception:
            continue
    return paths[0] if paths else ''


def _candidate_bases():
    bases = []
    try:
        # lib/ui -> lib
        base_lib = os.path.dirname(os.path.dirname(__file__))
        bases.append(base_lib)
        # lib -> BatchExport.pushbutton (one more up)
        base_root = os.path.dirname(base_lib)
        bases.append(base_root)
    except Exception:
        pass
    try:
        bases.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    except Exception:
        pass
    try:
        main_file = getattr(sys.modules.get('__main__'), '__file__', None)
        if main_file:
            bases.append(os.path.dirname(os.path.abspath(main_file)))  # BatchExport.pushbutton
    except Exception:
        pass
    # Dédupliquer en conservant l'ordre
    out = []
    for b in bases:
        if b and b not in out:
            out.append(b)
    return out


def _get_xaml_path():
    # Cherche GUI/MainWindow.xaml à partir de bases candidates
    bases = _candidate_bases()
    candidates = [os.path.join(b, GUI_FILE) for b in bases]
    return _first_existing(candidates)


def _get_piker_xaml_path():
    # Cherche GUI/Piker.xaml à partir de bases candidates
    bases = _candidate_bases()
    candidates = [os.path.join(b, PIKER_FILE) for b in bases]
    return _first_existing(candidates)


def _get_section_path(filename):
    # Chemin absolu vers un fichier XAML de section dans GUI/
    bases = _candidate_bases()
    candidates = [os.path.join(b, 'GUI', filename) for b in bases]
    return _first_existing(candidates)


def _register_named_elements(win, root):
    # Parcourt l'arbre logique pour exposer les éléments nommés en attributs sur win
    try:
        from System.Windows import FrameworkElement  # type: ignore
        from System.Windows import LogicalTreeHelper  # type: ignore
    except Exception:
        FrameworkElement = None  # type: ignore
        LogicalTreeHelper = None  # type: ignore
    if root is None or LogicalTreeHelper is None:
        return

    def _walk(node):
        try:
            if FrameworkElement is not None and isinstance(node, FrameworkElement):
                try:
                    nm = getattr(node, 'Name', None)
                except Exception:
                    nm = None
                if nm:
                    try:
                        setattr(win, nm, node)
                    except Exception:
                        pass
            try:
                children = list(LogicalTreeHelper.GetChildren(node))
            except Exception:
                children = []
            for ch in children:
                _walk(ch)
        except Exception:
            pass

    _walk(root)


def _load_section_into(win, host_name, section_filename):
    # Charge un XAML de section et l'insère dans le ContentControl host_name
    try:
        host = getattr(win, host_name, None)
    except Exception:
        host = None
    if host is None:
        return False
    xaml_path = _get_section_path(section_filename)
    if not os.path.exists(xaml_path):
        return False
    try:
        # Charger le XAML en tant qu'arbre WPF
        try:
            from System.Windows.Markup import XamlReader  # type: ignore
            from System.IO import FileStream, FileMode  # type: ignore
            fs = FileStream(xaml_path, FileMode.Open)
            try:
                element = XamlReader.Load(fs)
            finally:
                try:
                    fs.Close()
                except Exception:
                    pass
        except Exception:
            try:
                from System.Windows.Markup import XamlReader  # type: ignore
            except Exception:
                XamlReader = None  # type: ignore
            element = None
            try:
                with open(xaml_path, 'r') as f:
                    xml = f.read()
                if XamlReader is not None:
                    element = XamlReader.Parse(xml)
            except Exception:
                element = None
        if element is None:
            return False
        try:
            host.Content = element
        except Exception:
            pass
        _register_named_elements(win, element)
        return True
    except Exception as e:
        print('[info] Chargement section {} échoué: {}'.format(section_filename, e))
        return False
