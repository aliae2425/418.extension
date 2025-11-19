# -*- coding: utf-8 -*-
# Liaison des éléments nommés à l'intérieur des ControlTemplates vers des attributs Python

try:
    from pyrevit import EXEC_PARAMS
    _verbose = EXEC_PARAMS.debug_mode
except Exception:
    _verbose = False

class UITemplateBinder(object):
    def __init__(self, window):
        self._win = window

    # Expose chaque contrôle enfant nommé comme attribut de la fenêtre
    def bind(self, hosts_to_children):
        # hosts_to_children: dict host_name -> [childName, ...]
        for host_name, child_names in (hosts_to_children or {}).items():
            try:
                host = getattr(self._win, host_name, None)
            except Exception as e:
                print('[error] Failed to get host {}: {}'.format(host_name, e))
                host = None
            if host is None:
                if _verbose:
                    print('[warning] Host {} not found in window'.format(host_name))
                continue
            try:
                host.ApplyTemplate()
                if _verbose:
                    print('[debug] Applied template to {}'.format(host_name))
            except Exception as e:
                print('[error] Failed to apply template to {}: {}'.format(host_name, e))
                pass
            for cname in child_names:
                ctrl = None
                try:
                    tmpl = getattr(host, 'Template', None)
                    if tmpl is not None:
                        ctrl = tmpl.FindName(cname, host)
                    else:
                        if _verbose:
                            print('[warning] No template found for {}'.format(host_name))
                except Exception as e:
                    print('[error] Failed to find {} in {}: {}'.format(cname, host_name, e))
                    ctrl = None
                if ctrl is not None:
                    try:
                        setattr(self._win, cname, ctrl)
                        if _verbose:
                            print('[debug] Bound {} from {}'.format(cname, host_name))
                    except Exception as e:
                        print('[error] Failed to bind {}: {}'.format(cname, e))
                        pass
                else:
                    if _verbose:
                        print('[warning] Control {} not found in template of {}'.format(cname, host_name))
