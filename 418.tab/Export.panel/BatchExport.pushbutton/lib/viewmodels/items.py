# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Les 4 items bindables de BatchExport, sortis de MainViewModel.py où ils
# occupaient 228 lignes avant même que la VM racine ne commence. Tous les
# autres outils du dépôt tiennent leurs items dans des modules à part.
#
# Ils dérivent de `BaseViewModel` pour que `{Binding Numero}` & co résolvent
# via de vraies propriétés CLR : un `dict` Python n'expose pas ces
# propriétés et ne bind pas de façon fiable via `{Binding [Cle]}`.

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel


class SheetItemVM(BaseViewModel):
    """Item bindable pour une feuille au sein d'une collection (mode « par
    jeu »). Dérive de `BaseViewModel` (comme le reste du projet) pour que
    `{Binding Numero}` etc. résolvent via de vraies propriétés CLR — un
    `dict` Python n'expose pas ces propriétés et ne bind pas de façon
    fiable via `{Binding [Cle]}`."""

    def __init__(self, numero, nom, nom_projete):
        super(SheetItemVM, self).__init__()
        self._numero = numero
        self._nom = nom
        self._nom_projete = nom_projete

    @property
    def Numero(self):
        return self._numero

    @property
    def Nom(self):
        return self._nom

    @property
    def NomProjete(self):
        return self._nom_projete


class CollectionItemVM(BaseViewModel):
    """Item bindable pour une collection (jeu) au sein du mode « par jeu ».

    Les trois flags (`FlagExport`/`FlagCarnet`/`FlagDwg`) sont SETTABLES pour
    le mode « par jeu — choix manuel », où les badges deviennent cliquables et
    pilotent l'export DEPUIS LA MÉMOIRE (aucune écriture de paramètre Revit :
    en travail collaboratif, la SheetCollection appartient souvent à un autre
    utilisateur). Chaque toggle notifie ses propriétés puis appelle
    `on_change(self)` (callback du VM parent), même patron que `ManualSheetVM`
    — l'item se passe lui-même pour que le parent sache QUEL jeu a été
    touché, et ne reporte que ceux-là lors d'un `refresh_par_jeu()`.

    Dans le mode « par jeu » automatique, la page est de fait en lecture seule
    (badges affichés via DataTrigger) : les setters n'y sont jamais sollicités.
    """

    def __init__(self, titre, cid, flag_export, flag_carnet, flag_dwg, sheets,
                 carnet_apercu=u'', on_change=None):
        super(CollectionItemVM, self).__init__()
        self._titre = titre
        self._id = cid
        self._flag_export = bool(flag_export)
        self._flag_carnet = bool(flag_carnet)
        self._flag_dwg = bool(flag_dwg)
        self._sheets = sheets  # list[SheetItemVM]
        # Aperçu du nom de fichier de carnet (motif `set` résolu + `.pdf`),
        # ou '' si aucun motif carnet n'est configuré. Cf. refresh_par_jeu.
        self._carnet_apercu = carnet_apercu or u''
        self._on_change = on_change

    @property
    def Titre(self):
        return self._titre

    @property
    def Id(self):
        return self._id

    @property
    def FlagExport(self):
        return self._flag_export

    @FlagExport.setter
    def FlagExport(self, value):
        value = bool(value)
        if value == self._flag_export:
            return
        self._flag_export = value
        # `Qualified` n'est qu'une vue de ce flag : la notifier aussi, sinon
        # le compteur de jeux qualifiés ne suit pas le clic.
        self.notify_property(u'FlagExport')
        self.notify_property(u'Qualified')
        if callable(self._on_change):
            self._on_change(self)

    @property
    def FlagCarnet(self):
        return self._flag_carnet

    @FlagCarnet.setter
    def FlagCarnet(self, value):
        value = bool(value)
        if value == self._flag_carnet:
            return
        self._flag_carnet = value
        # `CarnetApercuVisible` dépend du flag : la ligne d'aperçu doit
        # apparaître/disparaître avec le badge.
        self.notify_property(u'FlagCarnet')
        self.notify_property(u'CarnetApercuVisible')
        if callable(self._on_change):
            self._on_change(self)

    @property
    def FlagDwg(self):
        return self._flag_dwg

    @FlagDwg.setter
    def FlagDwg(self, value):
        value = bool(value)
        if value == self._flag_dwg:
            return
        self._flag_dwg = value
        self.notify_property(u'FlagDwg')
        if callable(self._on_change):
            self._on_change(self)

    @property
    def Qualified(self):
        return self._flag_export

    @property
    def CarnetApercu(self):
        return self._carnet_apercu

    @property
    def CarnetApercuVisible(self):
        # Visible uniquement si le carnet est actif ET qu'un aperçu non vide
        # a pu être résolu : évite d'afficher l'icône seule sans texte quand
        # le motif `set` est absent/vide.
        return bool(self._flag_carnet) and bool(self._carnet_apercu)

    @property
    def Sheets(self):
        return self._sheets


class ManualSheetVM(BaseViewModel):
    """Item bindable pour une feuille en mode « feuille par feuille »
    (sélection manuelle). `ExportPdf`/`ExportDwg` sont TWO-WAY (cases à
    cocher) ; chaque toggle notifie sa propriété puis appelle `on_change`
    (callback fourni par le VM parent) pour permettre la recomputation des
    compteurs `NbPdf`/`NbDwg` sans que ce VM connaisse `MainViewModel`.

    `JeuNom`/`NomProjete` sont en LECTURE SEULE : calculés une fois par
    `refresh_manuel()` (mapping CollectionId->Titre et résolution du
    pattern de nommage FEUILLE), jamais recalculés à la volée par ce VM.

    `Selected` (case de sélection de ligne) est TWO-WAY et pilotée par
    `core.bulk_edit` via `MainViewModel.select_all_manuel()` /
    `deselect_all_manuel()`. Elle ne conditionne PAS `selection_manuelle()`
    (qui se base UNIQUEMENT sur ExportPdf/ExportDwg).
    """

    def __init__(self, numero, nom, collection_id=None, elem=None,
                 export_pdf=True, export_dwg=False,
                 jeu_nom=u'', nom_projete=u'', on_change=None,
                 on_format_change=None):
        super(ManualSheetVM, self).__init__()
        self._numero = numero
        self._nom = nom
        self._collection_id = collection_id
        self._elem = elem
        self._export_pdf = bool(export_pdf)
        self._export_dwg = bool(export_dwg)
        self._jeu_nom = jeu_nom or u''
        self._nom_projete = nom_projete or u''
        self._on_change = on_change
        self._on_format_change = on_format_change
        self._selected = False

    @property
    def Numero(self):
        return self._numero

    @property
    def Nom(self):
        return self._nom

    @property
    def CollectionId(self):
        return self._collection_id

    @property
    def Elem(self):
        return self._elem

    @property
    def JeuNom(self):
        return self._jeu_nom

    @property
    def NomProjete(self):
        return self._nom_projete

    @property
    def ExportPdf(self):
        return self._export_pdf

    @ExportPdf.setter
    def ExportPdf(self, value):
        value = bool(value)
        if value == self._export_pdf:
            return
        self._export_pdf = value
        self.notify_property(u'ExportPdf')
        if callable(self._on_format_change):
            self._on_format_change(self, u'ExportPdf', value)
        if callable(self._on_change):
            self._on_change()

    @property
    def ExportDwg(self):
        return self._export_dwg

    @ExportDwg.setter
    def ExportDwg(self, value):
        value = bool(value)
        if value == self._export_dwg:
            return
        self._export_dwg = value
        self.notify_property(u'ExportDwg')
        if callable(self._on_format_change):
            self._on_format_change(self, u'ExportDwg', value)
        if callable(self._on_change):
            self._on_change()

    @property
    def Selected(self):
        return self._selected

    @Selected.setter
    def Selected(self, value):
        value = bool(value)
        if value == self._selected:
            return
        self._selected = value
        self.notify_property(u'Selected')
        if callable(self._on_change):
            self._on_change()


class FiltreItemVM(BaseViewModel):
    """Item bindable pour le sélecteur de filtre du mode manuel (un par
    collection/jeu, un par set d'impression -- PLUS d'item « Toutes les
    feuilles » pseudo, cf. sémantique multi-filtre de
    `MainViewModel.SheetsManuelFiltrees`).

    `.Label` et `.IsActif` sont bindés côté WPF (case à cocher par filtre).
    `kind`/`coll_id`/`sheet_ids` sont des attributs internes lus uniquement
    par `MainViewModel.SheetsManuelFiltrees`. `kind` vaut `'collection'` ou
    `'set'`. `on_change` (callback du VM parent) est appelé à chaque
    toggle de `IsActif`, comme pour `ManualSheetVM.ExportPdf`/`ExportDwg`.
    """

    def __init__(self, label, kind, coll_id=None, sheet_ids=None,
                 is_actif=False, on_change=None):
        super(FiltreItemVM, self).__init__()
        self._label = label
        self.kind = kind
        self.coll_id = coll_id
        self.sheet_ids = sheet_ids or set()
        self._is_actif = bool(is_actif)
        self._on_change = on_change

    @property
    def Label(self):
        return self._label

    @property
    def IsActif(self):
        return self._is_actif

    @IsActif.setter
    def IsActif(self, value):
        value = bool(value)
        if value == self._is_actif:
            return
        self._is_actif = value
        self.notify_property(u'IsActif')
        if callable(self._on_change):
            self._on_change()
