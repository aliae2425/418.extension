# -*- coding: utf-8 -*-

"""Helpers: overlay hover text for burger menu.

Centralizes the lookup + show/hide logic for BurgerMenuHoverText.
"""


def _find_hover_text_block(win):
    tb = None
    try:
        tb = getattr(win, 'BurgerMenuHoverText', None)
    except Exception:
        tb = None

    if tb is None and hasattr(win, 'FindName'):
        try:
            tb = win.FindName('BurgerMenuHoverText')
        except Exception:
            tb = None

    return tb


def _find_name(win, name):
    obj = None
    try:
        obj = getattr(win, name, None)
    except Exception:
        obj = None

    if obj is None and hasattr(win, 'FindName'):
        try:
            obj = win.FindName(name)
        except Exception:
            obj = None
    return obj


def _hide_hover_content(win):
    try:
        from System.Windows import Visibility
    except Exception:
        return

    try:
        tb = _find_name(win, 'BurgerMenuHoverText')
        if tb is not None:
            tb.Text = ''
            tb.Visibility = Visibility.Collapsed
    except Exception:
        pass

    try:
        host = _find_name(win, 'BurgerMenuHoverContent')
        if host is not None:
            host.Content = None
            host.Visibility = Visibility.Collapsed
    except Exception:
        pass


def _ensure_hover_layer_visible(win):
    try:
        from System.Windows import Visibility
    except Exception:
        return

    try:
        layer = _find_name(win, 'BurgerMenuHoverLayer')
        if layer is not None and layer.Visibility != Visibility.Visible:
            layer.Visibility = Visibility.Visible
    except Exception:
        pass


def clear_hover(win):
    """Hide any hover overlay content (text or XAML)."""
    _hide_hover_content(win)


def set_hover_text(win, text):
    """Set hover overlay text. Pass empty/None to hide."""
    try:
        from System.Windows import Visibility
    except Exception:
        return False

    # Prefer the explicit text block if present; also ensure XAML-host is hidden.
    _hide_hover_content(win)

    if text:
        _ensure_hover_layer_visible(win)

    tb = _find_name(win, 'BurgerMenuHoverText')
    if tb is None:
        return False

    try:
        if text:
            tb.Text = text
            tb.Visibility = Visibility.Visible
            return True
        else:
            tb.Text = ''
            tb.Visibility = Visibility.Collapsed
            return False
    except Exception:
        return False


def set_hover_content(win, element):
    """Show an arbitrary WPF element inside the hover overlay."""
    try:
        from System.Windows import Visibility
    except Exception:
        return False

    _hide_hover_content(win)

    if element is not None:
        _ensure_hover_layer_visible(win)

    host = _find_name(win, 'BurgerMenuHoverContent')
    if host is None:
        return False

    try:
        if element is not None:
            host.Content = element
            host.Visibility = Visibility.Visible
            return True
        else:
            host.Content = None
            host.Visibility = Visibility.Collapsed
            return False
    except Exception:
        return False


def _resolve_gui_path(path_or_rel):
    """Resolve absolute or GUI-root-relative path."""
    if not path_or_rel:
        return None

    try:
        import os
        # Absolute path
        if os.path.isabs(path_or_rel):
            return path_or_rel
    except Exception:
        return None

    try:
        import os
        from ...core.AppPaths import AppPaths
        gui_root = AppPaths().gui_root()
        return os.path.join(gui_root, path_or_rel)
    except Exception:
        return None


def set_hover_xaml_path(win, xaml_path):
    """Load a XAML file (root must be a UIElement) and display it in hover overlay."""
    if not xaml_path:
        _hide_hover_content(win)
        return False

    try:
        import os
        if not os.path.exists(xaml_path):
            return False
    except Exception:
        return False

    # XAML parsing types (IronPython sometimes needs explicit references)
    XamlReader = None
    try:
        from System.Windows.Markup import XamlReader  # noqa: F401
    except Exception:
        try:
            import clr
            try:
                clr.AddReference('PresentationFramework')
                clr.AddReference('PresentationCore')
                clr.AddReference('WindowsBase')
            except Exception:
                pass
            try:
                clr.AddReference('System.Xaml')
            except Exception:
                pass
            from System.Windows.Markup import XamlReader  # noqa: F401
        except Exception:
            XamlReader = None

    if XamlReader is None:
        return False

    # Prefer Parse(string) to avoid System.Xml dependency issues.
    try:
        with open(xaml_path, 'r') as fp:
            xaml_text = fp.read()
        element = XamlReader.Parse(xaml_text)
        return bool(set_hover_content(win, element))
    except Exception as e_parse:
        # Fallback: stream-based load
        try:
            from System.IO import File
            from System.Xml import XmlReader
        except Exception:
            # As last resort, keep the hover disabled.
            try:
                print('HoverOverlay [001]: Failed to load hover XAML (no System.Xml): {}'.format(e_parse))
            except Exception:
                pass
            return False

        fs = None
        xr = None
        try:
            fs = File.OpenRead(xaml_path)
            xr = XmlReader.Create(fs)
            element = XamlReader.Load(xr)
            return bool(set_hover_content(win, element))
        except Exception as e_load:
            try:
                print('HoverOverlay [002]: Failed to load hover XAML: {}'.format(e_load))
            except Exception:
                pass
            return False
        finally:
            try:
                if xr is not None:
                    xr.Close()
            except Exception:
                pass
            try:
                if fs is not None:
                    fs.Close()
            except Exception:
                pass


def set_hover_xaml(win, path_or_rel):
    """Convenience wrapper supporting GUI-relative paths like 'hover/HelpHover.xaml'."""
    xaml_path = _resolve_gui_path(path_or_rel)
    if not xaml_path:
        return False
    return bool(set_hover_xaml_path(win, xaml_path))
