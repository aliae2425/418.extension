# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from core.rename_service import RenameService
except Exception:
    from lib.core.rename_service import RenameService


class RenommerPageVM(BaseViewModel):
    """Onglet Renommer : renommage en masse des matériaux cochés.

    La page porte SA liste — recherche, cases, Tout/Aucun — mais pas SA
    sélection : c'est la `SelectionPageVM` de l'onglet Matériaux qui est
    affichée, donc cocher ici coche la card là-bas (et réciproquement),
    exactement comme la colonne source de l'onglet Remplacer. Le filtre de
    recherche est lui aussi celui de la page de sélection : chercher dans un
    onglet cherche dans les deux.

    Il n'y a pas de liste d'aperçu séparée : le nom obtenu vit sur la card
    (`MaterialCardVM.NouveauNom`), recalculé à chaque frappe, et le tableau
    de la page affiche les deux colonnes côte à côte. Une seule liste, donc
    rien à tenir synchrone avec la sélection.

    Toute la transformation vient de `core.rename_service` (littéral ou
    regex, préfixe/suffixe, tokens {n}/{date}/{annee}...) — le même moteur
    que les outils « Rechercher/Remplacer » sur les feuilles et les vues.

    ponytail: 3e exemplaire du couple champs+aperçu (FindReplace_Sheets,
    FindReplace - Views, ici). Candidat à monter dans lib/ui/base/ le jour
    du refactor de coquille — les trois ne diffèrent que par l'élément visé.
    """

    def __init__(self, service=None, selection_vm=None, materiaux_par_id=None):
        super(RenommerPageVM, self).__init__()
        self._service = service
        # MÊME SelectionPageVM que l'onglet Matériaux : le XAML s'y lie par
        # `SelectionVM.FilteredItems` / `SelectionVM.FilterText`.
        self.SelectionVM = selection_vm
        self._materiaux_par_id = dict(materiaux_par_id or {})
        self._ids = []
        self._Rechercher = u''
        self._Remplacer = u''
        self._Prefixe = u''
        self._Suffixe = u''
        self._UseRegex = False
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
    def _cartes(self):
        return list(self.SelectionVM.AllItems) if self.SelectionVM else []

    @property
    def _cartes_cochees(self):
        """Les cards cochées, dans l'ordre de la liste — c'est cet ordre qui
        numérote {n} ET qui est passé au service, les deux doivent coïncider."""
        coches = set(self._ids)
        return [carte for carte in self._cartes if carte.Id in coches]

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
    def NombreChanges(self):
        return sum(1 for carte in self._cartes_cochees if carte.NomChange)

    @property
    def Recapitulatif(self):
        nombre = len(self._ids)
        if not nombre:
            return u'Aucun matériau coché.'
        changes = self.NombreChanges
        if not changes:
            return u'%d matériau(x) coché(s) · aucun changement de nom.' % nombre
        return u'%d matériau(x) coché(s) · %d renommage(s).' % (nombre, changes)

    @property
    def PeutRenommer(self):
        return (bool(self._ids) and self._service is not None
                and not self._RegexError and self.NombreChanges > 0)

    def set_sources(self, ids):
        """`ids` : ids des cards cochées, tels que renvoyés par la page de
        sélection. Appelé par `MainViewModel` à chaque changement."""
        self._ids = list(ids or [])
        self._Etat = u''
        self.notify_property('Etat')
        self._recalculer()

    def _construire_service(self):
        return RenameService(
            prefixe=self._Prefixe, rechercher=self._Rechercher,
            remplacer=self._Remplacer, suffixe=self._Suffixe,
            use_regex=self._UseRegex)

    def _recalculer(self):
        """Écrit `NouveauNom` sur chaque card : le nom obtenu pour les
        cochées, vide pour les autres. {n} ne numérote que les cochées."""
        svc = self._construire_service()
        self._RegexError = svc.regex_error
        coches = set(self._ids)
        index = 0
        for carte in self._cartes:
            if carte.Id not in coches:
                carte.NouveauNom = u''
                continue
            index += 1
            carte.NouveauNom = svc.apply(carte.Nom, index=index)
        for nom in ('RegexError', 'HasRegexError', 'NombreChanges',
                    'Recapitulatif', 'PeutRenommer'):
            self.notify_property(nom)

    # -- Action ------------------------------------------------------------

    def renommer(self):
        if not self.PeutRenommer:
            return
        cartes = self._cartes_cochees
        materiaux = [self._materiaux_par_id[carte.Id] for carte in cartes
                     if carte.Id in self._materiaux_par_id]
        changes = self._service.renommer(materiaux, self._construire_service())
        # Le service assainit et suffixe `*` sur collision : la card reprend
        # le nom que Revit a réellement accepté, pas celui de l'aperçu.
        for carte in cartes:
            materiau = self._materiaux_par_id.get(carte.Id)
            if materiau is not None:
                carte.Nom = materiau.Name
        self._Etat = u'%d matériau(x) renommé(s).' % changes
        self.notify_property('Etat')
        self._recalculer()
