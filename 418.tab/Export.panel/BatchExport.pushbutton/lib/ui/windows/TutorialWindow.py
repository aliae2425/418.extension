# -*- coding: utf-8 -*-
from pyrevit import forms
import os

class TutorialWindow(forms.WPFWindow):
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GUI', 'Modals', 'Tutorial.xaml')
        forms.WPFWindow.__init__(self, xaml_path)
        
        if hasattr(self, 'CloseButton'):
            self.CloseButton.Click += self._on_close

    def _on_close(self, sender, args):
        self.Close()

def show_tutorial():
    win = TutorialWindow()
    win.ShowDialog()
