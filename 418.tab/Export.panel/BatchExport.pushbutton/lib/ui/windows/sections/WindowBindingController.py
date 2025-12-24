# -*- coding: utf-8 -*-


class WindowBindingController(object):
    def __init__(self, win, paths, resource_loader_cls, template_binder_cls, verbose=False):
        self._win = win
        self._paths = paths
        self._res_loader_cls = resource_loader_cls
        self._binder_cls = template_binder_cls
        self._verbose = bool(verbose)

    def merge_and_bind(self):
        merge_ok = False
        try:
            merge_ok = self._res_loader_cls(self._win, self._paths).merge_all()
        except Exception:
            merge_ok = False

        if not merge_ok and self._verbose:
            pass

        hosts = {
            'ParameterSelectorHost': [
                'CollectionExpander', 'ParamWarningText', 'UniqueErrorText',
                'ExportationCombo', 'CarnetCombo', 'DWGCombo', 'HelpButton', 'DarkModeToggle'
            ],
            'ExportOptionsHost': [
                'PDFExpander', 'PDFSetupCombo', 'PDFSeparateCheck', 'PDFCreateButton',
                'DWGExpander', 'DWGSetupCombo', 'DWGSeparateCheck', 'DWGCreateButton'
            ],
            'DestinationPickerHost': [
                'BrowseButton', 'PathTextBox', 'CreateSubfoldersCheck', 'SeparateByFormatCheck'
            ],
            'NamingConfigHost': [
                'NamingExpander', 'SheetNamingButton', 'SetNamingButton'
            ],
            'CollectionPreviewHost': [
                'ExportProgressBar', 'PreviewCounterText', 'CollectionGrid', 'ExportStatusText', 'ExportButton'
            ],
        }

        try:
            self._binder_cls(self._win).bind(hosts)
        except Exception:
            pass

        if self._verbose:
            if not hasattr(self._win, 'CollectionExpander'):
                pass
            if not hasattr(self._win, 'ExportationCombo'):
                pass
