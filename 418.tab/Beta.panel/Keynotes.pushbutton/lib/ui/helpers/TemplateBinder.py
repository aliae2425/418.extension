# -*- coding: utf-8 -*-


class TemplateBinder(object):
    """Bind named elements inside ControlTemplates onto the window.

    Motivation:
    - When UI is split into GUI/Controls/*.xaml via ControlTemplates, x:Name elements
      inside templates are not automatically exposed as attributes on the WPFWindow.
    - Existing Keynotes code expects attributes like self.catEditButtons.

    This binder mirrors the approach used in BatchExport: resolve template parts
    via template.FindName(name, host) and assign them on the window instance.
    """

    def __init__(self, win):
        self._win = win

    def _get_host(self, host_name):
        host = getattr(self._win, host_name, None)
        if host is None and hasattr(self._win, 'FindName'):
            try:
                host = self._win.FindName(host_name)
            except Exception:
                host = None
        return host

    def _bind_from_template(self, host, element_name):
        if host is None:
            return None
        try:
            host.ApplyTemplate()
        except Exception:
            pass

        try:
            host.UpdateLayout()
        except Exception:
            pass

        template = getattr(host, 'Template', None)
        if template is None:
            return self._find_in_visual_tree(host, element_name)

        try:
            found = template.FindName(element_name, host)
            if found is not None:
                return found
        except Exception:
            return None

        # Fallback: traverse visual tree to find FrameworkElement with Name
        return self._find_in_visual_tree(host, element_name)

    def _find_in_visual_tree(self, root, element_name):
        try:
            import System  # type: ignore
            VisualTreeHelper = System.Windows.Media.VisualTreeHelper
        except Exception:
            VisualTreeHelper = None

        if root is None or not element_name:
            return None

        # Prefer direct FrameworkElement.Name match
        try:
            if hasattr(root, 'Name') and root.Name == element_name:
                return root
        except Exception:
            pass

        if VisualTreeHelper is None:
            return None

        try:
            count = VisualTreeHelper.GetChildrenCount(root)
        except Exception:
            return None

        for i in range(count):
            try:
                child = VisualTreeHelper.GetChild(root, i)
            except Exception:
                child = None

            if child is None:
                continue

            try:
                if hasattr(child, 'Name') and child.Name == element_name:
                    return child
            except Exception:
                pass

            found = self._find_in_visual_tree(child, element_name)
            if found is not None:
                return found

        return None

    def bind(self, hosts_map):
        """hosts_map: { 'HostName': ['ElementName1', ...] }"""
        for host_name, element_names in (hosts_map or {}).items():
            host = self._get_host(host_name)
            for element_name in element_names:
                if hasattr(self._win, element_name):
                    continue
                el = self._bind_from_template(host, element_name)
                if el is not None:
                    try:
                        setattr(self._win, element_name, el)
                    except Exception:
                        pass
