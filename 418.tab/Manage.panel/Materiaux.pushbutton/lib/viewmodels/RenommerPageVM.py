# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        class BaseViewModel(object):
            def __init__(self):
                pass

            def notify_property(self, name):
                pass

try:
    from core.rename_service import RenameService
except Exception:
    from lib.core.rename_service import RenameService


class ApercuVM(object):
    """Une ligne d'aperçu : nom actuel -> nom obtenu."""

    def __init__(self, ancien, nouveau):
        self.Ancien = ancien
        self.Nouveau = nouveau

    @property
    def Change(self):
        return self.Ancien != self.Nouveau


class RenommerPageVM(BaseViewModel):
    """Onglet Renommer : renommage en masse des matériaux cochés.

    Toute la transformation vient de `core.rename_service` (littéral ou
    regex, préfixe/suffixe, tokens {n}/{date}/{annee}...) ; cette VM ne fait
    que la piloter et rafraîchir l'aperçu à chaque frappe.

    ponytail: 3e exemplaire du couple champs+aperçu (FindReplace_Sheets,
    FindReplace - Views, ici). Candidat à monter dans lib/ui/base/ le jour
    du refactor de coquille — les trois ne diffèrent que par l'élément visé.
    """

    def __init__(self, service=None):
        super(RenommerPageVM, self).__init__()
        self._service = service
        self._materiaux = []
        self._Rechercher = u''
        self._Remplacer = u''
        self._Prefixe = u''
        self._Suffixe = u''
        self._UseRegex = False
        self._Apercus = []
        self._RegexError = u''
        self._Etat = u''

    # -- Champs ------------------------------------------------------------

    def _maj(self, nom, value):
        """Affecte le champ et rafraîchit l'aperçu si la valeur a changé."""
        value = value or u''
        if value != getattr(self, '_' + nom):
            setattr(self, '_' + nom, value)
            self.notify_property(nom)
            self._recalculer()

    @property
    def Rechercher(self):
        return self._Rechercher

    @Rechercher.setter
    def Rechercher(self, value):
        self._maj('Rechercher', value)

    @property
    def Remplacer(self):
        return self._Remplacer

    @Remplacer.setter
    def Remplacer(self, value):
        self._maj('Remplacer', value)

    @property
    def Prefixe(self):
        return self._Prefixe

    @Prefixe.setter
    def Prefixe(self, value):
        self._maj('Prefixe', value)

    @property
    def Suffixe(self):
        return self._Suffixe

    @Suffixe.setter
    def Suffixe(self, value):
        self._maj('Suffixe', value)

    @property
    def UseRegex(self):
        return self._UseRegex

    @UseRegex.setter
    def UseRegex(self, value):
        value = bool(value)
        if value != self._UseRegex:
            self._UseRegex = value
            self.notify_property('UseRegex')
            self._recalculer()

    # -- Aperçu ------------------------------------------------------------

    @property
    def Apercus(self):
        return self._Apercus

    @property
    def HasApercu(self):
        return bool(self._Apercus)

    @property
    def RegexError(self):
        return self._RegexError

    @property
    def HasRegexError(self):
        return bool(self._RegexError)

    @property
    def Etat(self):
        return self._Etat

    @property
    def PeutRenommer(self):
        return (bool(self._materiaux) and self._service is not None
                and not self._RegexError
                and any(a.Change for a in self._Apercus))

    def set_sources(self, materiaux):
        """`materiaux` : éléments Revit exposant `.Name`."""
        self._materiaux = list(materiaux or [])
        self._Etat = u''
        self.notify_property('Etat')
        self._recalculer()

    def _construire_service(self):
        return RenameService(
            prefixe=self._Prefixe, rechercher=self._Rechercher,
            remplacer=self._Remplacer, suffixe=self._Suffixe,
            use_regex=self._UseRegex)

    def _recalculer(self):
        svc = self._construire_service()
        self._RegexError = svc.regex_error
        self._Apercus = [
            ApercuVM(m.Name, svc.apply(m.Name, index=i))
            for i, m in enumerate(self._materiaux, start=1)
        ]
        for nom in ('Apercus', 'HasApercu', 'RegexError', 'HasRegexError',
                    'PeutRenommer'):
            self.notify_property(nom)

    # -- Action ------------------------------------------------------------

    def renommer(self):
        if not self.PeutRenommer:
            return
        changes = self._service.renommer(self._materiaux,
                                         self._construire_service())
        self._Etat = u'%d matériau(x) renommé(s).' % changes
        self.notify_property('Etat')
        self._recalculer()
