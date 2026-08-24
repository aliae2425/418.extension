# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from core.UserConfig import UserConfig
from ui.base.BaseViewModel import BaseViewModel
from ui.helpers.RelayCommand import RelayCommand
from services.AuditRunner import AuditRunner
from services.ReportExporter import exporter
from viewmodels.ScoreVM import ScoreVM
from viewmodels.ThemeCardVM import ThemeCardVM
from viewmodels.IssueRowVM import IssueRowVM


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None, runner=None):
        try:
            super(MainViewModel, self).__init__()
        except Exception:
            pass
        self._doc = doc
        self._runner = runner or AuditRunner()
        self._resultat = None
        self.Titre = u'Audit — Santé du modèle'
        self.ScoreVM = None
        self.Cartes = []
        self.TopCritiques = []
        self.Meta = {}
        # Fournie par la View (fenêtre.Close) après chargement du XAML.
        self.on_fermer = None
        self.relancer_cmd = RelayCommand(lambda p: self.lancer_audit()) if RelayCommand else None
        self.exporter_cmd = RelayCommand(lambda p: self._exporter()) if RelayCommand else None
        self.lancer_audit()

    def lancer_audit(self):
        # Exécute l'audit sous une barre de progression pyRevit si disponible ;
        # dégrade silencieusement hors Revit / sans pyrevit.
        res = None
        try:
            from pyrevit import forms
            with forms.ProgressBar(title=u'Audit en cours…', indeterminate=True):
                res = self._runner.run(self._doc)
        except Exception:
            res = self._runner.run(self._doc)
        self._appliquer(res)

    def _appliquer(self, res):
        self._resultat = res
        self.ScoreVM = ScoreVM(res)
        self.Cartes = [ThemeCardVM(t, on_selectionner=self._selectionner_et_fermer) for t in res.themes]
        self.TopCritiques = [IssueRowVM(i, on_selectionner=self._selectionner_et_fermer) for i in res.top_critiques]
        self.Meta = res.meta
        for prop in ('ScoreVM', 'Cartes', 'TopCritiques', 'Meta'):
            try:
                self.notify_property(prop)
            except Exception:
                pass

    def _exporter(self):
        """Exporte le rapport HTML puis ouvre le dossier contenant.

        Gardé : ni un dossier de destination illisible ni l'absence de
        `os.startfile` (hors Windows) ne doivent empêcher l'export lui-même.
        """
        try:
            dossier = UserConfig('audit').get('report_dir', None)
        except Exception:
            dossier = None
        chemin = exporter(self._resultat, dossier)
        try:
            os.startfile(os.path.dirname(chemin))
        except Exception:
            pass

    def _selectionner_et_fermer(self, element_id):
        # Sélectionne l'élément dans Revit (API directe, gardée : __revit__
        # n'existe pas hors Revit -> NameError intercepté) puis ferme la
        # fenêtre via le callback fourni par la View.
        try:
            from Autodesk.Revit.DB import ElementId
            from System.Collections.Generic import List
            uidoc = __revit__.ActiveUIDocument  # global injecté par pyRevit
            if element_id is not None and uidoc is not None:
                ids = List[ElementId]()
                ids.Add(element_id)
                uidoc.Selection.SetElementIds(ids)
                try:
                    uidoc.ShowElements(element_id)
                except Exception:
                    pass
        except Exception:
            pass
        if getattr(self, 'on_fermer', None):
            try:
                self.on_fermer()
            except Exception:
                pass
