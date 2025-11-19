# -*- coding: utf-8 -*-
# Liaison des éléments nommés à l'intérieur des ControlTemplates vers des attributs Python

class UITemplateBinder(object):
    def __init__(self, window):
        self._win = window

    # Expose chaque contrôle enfant nommé comme attribut de la fenêtre
    def bind(self, hosts_to_children):
        # hosts_to_children: dict host_name -> [childName, ...]
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
