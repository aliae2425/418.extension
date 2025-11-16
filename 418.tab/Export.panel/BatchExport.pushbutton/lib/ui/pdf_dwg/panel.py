# -*- coding: utf-8 -*-

# Réglages PDF / DWG: initialisation et création

# TODO: découper davantage si nécessaire (séparer PDF et DWG)


def init_pdf_dwg_controls(win):
    # Initialise les combos et boutons PDF/DWG
    try:
        doc = __revit__.ActiveUIDocument.Document  # type: ignore
    except Exception:
        doc = None
    # PDF setups
    try:
        from ...pdf_export import list_all_pdf_setups, get_saved_pdf_setup, set_saved_pdf_setup, get_saved_pdf_separate, set_saved_pdf_separate
        if hasattr(win, 'PDFSetupCombo'):
            pdf_names = list_all_pdf_setups(doc)
            win.PDFSetupCombo.Items.Clear()
            if pdf_names:
                for n in pdf_names:
                    win.PDFSetupCombo.Items.Add(n)
                saved = get_saved_pdf_setup()
                if saved and saved in pdf_names:
                    win.PDFSetupCombo.SelectedIndex = pdf_names.index(saved)
                else:
                    win.PDFSetupCombo.SelectedIndex = 0
            else:
                win.PDFSetupCombo.Items.Add('(Aucun réglage PDF)')
                win.PDFSetupCombo.SelectedIndex = 0
            win.PDFSetupCombo.SelectionChanged += lambda s,a: set_saved_pdf_setup(str(getattr(win.PDFSetupCombo,'SelectedItem', '')))
        if hasattr(win, 'PDFSeparateCheck'):
            win.PDFSeparateCheck.IsChecked = get_saved_pdf_separate(False)
            win.PDFSeparateCheck.Checked += lambda s,a: set_saved_pdf_separate(True)
            win.PDFSeparateCheck.Unchecked += lambda s,a: set_saved_pdf_separate(False)
        if hasattr(win, 'PDFCreateButton'):
            win.PDFCreateButton.Click += win._on_create_pdf_setup
    except Exception as e:
        print('[info] PDF setups non initialisés:', e)
    # DWG setups
    try:
        from ...dwg_export import list_all_dwg_setups, get_saved_dwg_setup, set_saved_dwg_setup, get_saved_dwg_separate, set_saved_dwg_separate
        if hasattr(win, 'DWGSetupCombo'):
            dwg_names = list_all_dwg_setups(doc)
            win.DWGSetupCombo.Items.Clear()
            if dwg_names:
                for n in dwg_names:
                    win.DWGSetupCombo.Items.Add(n)
                saved = get_saved_dwg_setup()
                if saved and saved in dwg_names:
                    win.DWGSetupCombo.SelectedIndex = dwg_names.index(saved)
                else:
                    win.DWGSetupCombo.SelectedIndex = 0
            else:
                win.DWGSetupCombo.Items.Add('(Aucun réglage DWG)')
                win.DWGSetupCombo.SelectedIndex = 0
            win.DWGSetupCombo.SelectionChanged += lambda s,a: set_saved_dwg_setup(str(getattr(win.DWGSetupCombo,'SelectedItem', '')))
        if hasattr(win, 'DWGSeparateCheck'):
            win.DWGSeparateCheck.IsChecked = get_saved_dwg_separate(False)
            win.DWGSeparateCheck.Checked += lambda s,a: set_saved_dwg_separate(True)
            win.DWGSeparateCheck.Unchecked += lambda s,a: set_saved_dwg_separate(False)
        if hasattr(win, 'DWGCreateButton'):
            win.DWGCreateButton.Click += win._on_create_dwg_setup
    except Exception as e:
        print('[info] DWG setups non initialisés:', e)


def refresh_pdf_combo(win):
    try:
        doc = __revit__.ActiveUIDocument.Document  # type: ignore
    except Exception:
        doc = None
    try:
        from ...pdf_export import list_all_pdf_setups, get_saved_pdf_setup
        if not hasattr(win, 'PDFSetupCombo'):
            return
        names = list_all_pdf_setups(doc)
        win.PDFSetupCombo.Items.Clear()
        for n in names:
            win.PDFSetupCombo.Items.Add(n)
        saved = get_saved_pdf_setup()
        if saved and saved in names:
            win.PDFSetupCombo.SelectedIndex = names.index(saved)
        elif names:
            win.PDFSetupCombo.SelectedIndex = 0
    except Exception:
        pass


def refresh_dwg_combo(win):
    try:
        doc = __revit__.ActiveUIDocument.Document  # type: ignore
    except Exception:
        doc = None
    try:
        from ...dwg_export import list_all_dwg_setups, get_saved_dwg_setup
        if not hasattr(win, 'DWGSetupCombo'):
            return
        names = list_all_dwg_setups(doc)
        win.DWGSetupCombo.Items.Clear()
        for n in names:
            win.DWGSetupCombo.Items.Add(n)
        saved = get_saved_dwg_setup()
        if saved and saved in names:
            win.DWGSetupCombo.SelectedIndex = names.index(saved)
        elif names:
            win.DWGSetupCombo.SelectedIndex = 0
    except Exception:
        pass
