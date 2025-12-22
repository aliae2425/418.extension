# -*- coding: utf-8 -*-
from pyrevit import forms

class OrderManagerWindow(forms.WPFWindow):
    def __init__(self, xaml_path, items, is_dark_mode=False):
        forms.WPFWindow.__init__(self, xaml_path)

        # Charge les ressources (même base que UIResourceLoader)
        try:
            from ...core.AppPaths import AppPaths
            from System.Windows import ResourceDictionary
            from System import Uri, UriKind
            paths = AppPaths()

            # Base resources (light) via windows.xaml
            winres = ResourceDictionary()
            winres.Source = Uri('file:///' + paths.windows_xaml().replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
            self.Resources.MergedDictionaries.Add(winres)

            # Dark overrides
            if is_dark_mode:
                for filename in ('ColorsDark.xaml', 'StylesDark.xaml'):
                    path = paths.resource_path(filename)
                    rd = ResourceDictionary()
                    rd.Source = Uri('file:///' + path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
                    self.Resources.MergedDictionaries.Add(rd)

        except Exception as e:
            print('OrderManagerWindow [001]: Error loading resources: {}'.format(e))

        try:
            if hasattr(self, 'CloseButton'):
                self.CloseButton.Click += self.OnCancelClick
            if hasattr(self, 'TitleBar'):
                self.TitleBar.MouseLeftButtonDown += self._on_title_bar_mouse_down
        except Exception:
            pass

        self._items = list(items) # Copy list
        self._update_orders()

        self.ItemsList.ItemsSource = self._items
        self.response = None

        # Drag & drop state
        self._drag_start_point = None
        self._drag_item_index = None
        self._is_dragging = False

    def _on_title_bar_mouse_down(self, sender, args):
        try:
            self.DragMove()
        except Exception:
            pass

    def _update_orders(self):
        for i, item in enumerate(self._items):
            item['Order'] = i + 1

    def _get_listview_item_container_at(self, position):
        try:
            from System.Windows.Media import VisualTreeHelper
            from System.Windows.Controls import ListViewItem
        except Exception:
            return None

        try:
            element = self.ItemsList.InputHitTest(position)
        except Exception:
            element = None

        while element is not None:
            try:
                if isinstance(element, ListViewItem):
                    return element
            except Exception:
                pass
            try:
                element = VisualTreeHelper.GetParent(element)
            except Exception:
                element = None
        return None

    def OnListPreviewMouseLeftButtonDown(self, sender, args):
        try:
            self._drag_start_point = args.GetPosition(self.ItemsList)
            self._drag_item_index = self.ItemsList.SelectedIndex
            self._is_dragging = False

            # Prefer item under cursor (more natural than current selection)
            container = self._get_listview_item_container_at(self._drag_start_point)
            if container is not None:
                idx = self.ItemsList.ItemContainerGenerator.IndexFromContainer(container)
                if idx is not None and idx >= 0:
                    self._drag_item_index = idx
                    self.ItemsList.SelectedIndex = idx
        except Exception:
            self._drag_start_point = None
            self._drag_item_index = None
            self._is_dragging = False

    def OnListPreviewMouseMove(self, sender, args):
        try:
            if self._drag_start_point is None:
                return
            if self._is_dragging:
                return
            if args.LeftButton.ToString() != 'Pressed':
                return
            if self._drag_item_index is None or self._drag_item_index < 0:
                return
            if self._drag_item_index >= len(self._items):
                return

            pos = args.GetPosition(self.ItemsList)

            from System import Math
            from System.Windows import SystemParameters
            dx = Math.Abs(pos.X - self._drag_start_point.X)
            dy = Math.Abs(pos.Y - self._drag_start_point.Y)
            if dx < SystemParameters.MinimumHorizontalDragDistance and dy < SystemParameters.MinimumVerticalDragDistance:
                return

            from System.Windows import DragDrop
            from System.Windows import DragDropEffects

            self._is_dragging = True
            DragDrop.DoDragDrop(self.ItemsList, self._drag_item_index, DragDropEffects.Move)
        except Exception:
            pass
        finally:
            self._is_dragging = False

    def OnListDragOver(self, sender, args):
        try:
            from System.Windows import DragDropEffects
            args.Effects = DragDropEffects.Move
            args.Handled = True
        except Exception:
            pass

    def OnListDrop(self, sender, args):
        try:
            if self._drag_item_index is None:
                return
            if self._drag_item_index < 0 or self._drag_item_index >= len(self._items):
                return

            dragged_index = int(self._drag_item_index)
            dragged_item = self._items[dragged_index]

            drop_pos = args.GetPosition(self.ItemsList)
            container = self._get_listview_item_container_at(drop_pos)

            # Default: drop at end if not over an item
            target_index = len(self._items)
            if container is not None:
                idx = self.ItemsList.ItemContainerGenerator.IndexFromContainer(container)
                if idx is not None and idx >= 0:
                    target_index = int(idx)

                    # Insert after item when dropping in lower half
                    try:
                        rel = args.GetPosition(container)
                        if rel.Y > (container.ActualHeight / 2.0):
                            target_index += 1
                    except Exception:
                        pass

            # No-op if effectively same place
            if target_index == dragged_index or target_index == dragged_index + 1:
                return

            # Remove then insert (adjust index when moving downward)
            self._items.pop(dragged_index)
            if target_index > dragged_index:
                target_index -= 1
            if target_index < 0:
                target_index = 0
            if target_index > len(self._items):
                target_index = len(self._items)
            self._items.insert(target_index, dragged_item)

            self._update_orders()
            self.ItemsList.Items.Refresh()
            self.ItemsList.SelectedIndex = target_index
        except Exception:
            pass
        finally:
            self._drag_start_point = None
            self._drag_item_index = None
            self._is_dragging = False

    def OnUpClick(self, sender, args):
        idx = self.ItemsList.SelectedIndex
        if idx > 0:
            item = self._items.pop(idx)
            self._items.insert(idx - 1, item)
            self._update_orders()
            self.ItemsList.Items.Refresh()
            self.ItemsList.SelectedIndex = idx - 1

    def OnDownClick(self, sender, args):
        idx = self.ItemsList.SelectedIndex
        if idx < len(self._items) - 1 and idx != -1:
            item = self._items.pop(idx)
            self._items.insert(idx + 1, item)
            self._update_orders()
            self.ItemsList.Items.Refresh()
            self.ItemsList.SelectedIndex = idx + 1

    def OnOkClick(self, sender, args):
        self.response = self._items
        self.Close()

    def OnCancelClick(self, sender, args):
        self.Close()

    def OnTopClick(self, sender, args):
        idx = self.ItemsList.SelectedIndex
        if idx > 0:
            item = self._items.pop(idx)
            self._items.insert(0, item)
            self._update_orders()
            self.ItemsList.Items.Refresh()
            self.ItemsList.SelectedIndex = 0

    def OnBottomClick(self, sender, args):
        idx = self.ItemsList.SelectedIndex
        if idx < len(self._items) - 1 and idx != -1:
            item = self._items.pop(idx)
            self._items.append(item)
            self._update_orders()
            self.ItemsList.Items.Refresh()
            self.ItemsList.SelectedIndex = len(self._items) - 1
