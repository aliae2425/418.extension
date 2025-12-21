# -*- coding: utf-8 -*-


def apply_dark_mode(win, paths):
    try:
        from System.Windows import ResourceDictionary
        from System import Uri, UriKind
    except Exception as e:
        raise e

    dark_colors = paths.resource_path('ColorsDark.xaml')
    dark_styles = paths.resource_path('StylesDark.xaml')

    for path in (dark_colors, dark_styles):
        rd = ResourceDictionary()
        rd.Source = Uri(path, UriKind.Absolute)
        win.Resources.MergedDictionaries.Add(rd)


def remove_dark_mode(win):
    # Remove dark theme resources (assume last two dictionaries are dark)
    md = win.Resources.MergedDictionaries
    if len(md) >= 2:
        md.RemoveAt(md.Count - 1)
        md.RemoveAt(md.Count - 1)
