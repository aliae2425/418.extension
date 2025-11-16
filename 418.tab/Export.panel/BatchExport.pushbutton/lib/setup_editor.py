"""Facade: expose Setup Editor UI from ui.setup_editor_window."""

from .ui.setup_editor_window import open_setup_editor, SetupEditorWindow  # re-export

__all__ = ['open_setup_editor', 'SetupEditorWindow']
