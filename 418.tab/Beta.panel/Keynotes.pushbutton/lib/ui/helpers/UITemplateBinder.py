# -*- coding: utf-8 -*-
try:
    from pyrevit import EXEC_PARAMS
    _verbose = EXEC_PARAMS.debug_mode
except Exception:
    _verbose = False

class UITemplateBinder(object):
    def __init__(self, window):
        self._win = window

    def bind(self, hosts_to_children):
        for host_name, child_names in (hosts_to_children or {}).items():
            try:
                host = getattr(self._win, host_name, None)
            except Exception:
                host = None
            if host is None:
                continue
            try:
                host.ApplyTemplate()
            except Exception:
                pass
            for cname in child_names:
                ctrl = None
                try:
                    tmpl = getattr(host, 'Template', None)
                    if tmpl is not None:
                        ctrl = tmpl.FindName(cname, host)
                except Exception:
                    ctrl = None
                if ctrl is not None:
                    try:
                        setattr(self._win, cname, ctrl)
                    except Exception:
                        pass
