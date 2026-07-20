# -*- coding: utf-8 -*-


def apply_dark_mode(win, paths):
    try:
        from System.Windows import ResourceDictionary
        from System import Uri, UriKind
    except Exception as e:
        raise e

    rd = ResourceDictionary()
    rd.Source = Uri(paths.resource_path('ColorsDark.xaml'), UriKind.Absolute)
    win.Resources.MergedDictionaries.Add(rd)


def remove_dark_mode(win):
    md = win.Resources.MergedDictionaries
    if len(md) >= 1:
        md.RemoveAt(md.Count - 1)
