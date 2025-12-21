# -*- coding: utf-8 -*-


class HelpSectionController(object):
    def __init__(self, win):
        self._win = win

    def wire(self):
        try:
            if hasattr(self._win, 'HelpButton'):
                self._win.HelpButton.Click += self._on_help_click
        except Exception:
            pass

    def _on_help_click(self, sender, args):
        try:
            from ..HelpWindow import show_help
            content = (
                "Les paramètres de feuille permettent de contrôler quels jeux de feuilles sont exportés et comment.\n\n"
                "• Exportation : Paramètre Oui/Non pour activer l'export de la feuille.\n"
                "• Export PDF compilé : Paramètre Oui/Non pour inclure la feuille dans un carnet PDF unique.\n"
                "• Export en DWG : Paramètre Oui/Non pour générer également un fichier DWG pour cette feuille.\n\n"
                "Ces paramètres doivent être créés dans votre projet Revit en tant que paramètres de projet ou partagés, "
                "appliqués à la catégorie 'Feuilles'."
            )
            show_help(content)
        except Exception:
            pass
