# BatchExport — Découpage de la main window (VM + XAML)

> Conception validée en brainstorming (approche **hybride C**), mécanisme d'arbre
> XAML embarqué **prouvé par spike** le 2026-07-24. Fait suite au nettoyage du code
> mort pré-MVVM (`cb32c80`).

## Goal

Rendre la main window de BatchExport maintenable en scindant ses deux monolithes —
`lib/viewmodels/MainViewModel.py` (~1350 l.) et `GUI/Views/MainWindow.xaml` (~1075 l.)
— en unités à responsabilité unique, sans changement fonctionnel visible.

## Contexte / état de départ

Architecture MVVM : `script.py` → `MainViewModel` (+ item-VMs) → services injectés →
`MainWindowView` (câblage) charge `MainWindow.xaml` (`DataContext = MainViewModel`).
La fenêtre = en-tête + rail nav + 3 pages (auto « par jeu » / manuel « feuille par
feuille » / paramètres) basculées par `Visibility` + footer (destination, export, statut).

Contraintes projet : Revit 2026 ; Python 2/3 (`unicode_literals`, utf-8) ; imports
Revit/WPF sous `try/except → None` ; **français** partout ; **pas de commit sans
validation** ; tests standalone `unittest` (199 verts). **Vérification faible** : pas de
compilateur ; les erreurs de binding WPF sont **silencieuses** ; seule vraie validation
UI = reload Revit manuel.

## Mécanisme retenu (prouvé par spike)

Vu la stack (`XamlReader.Load` + câblage manuel), une page embarquée avec son propre
`DataContext` se compose ainsi :

1. **Shell** = `MainWindow.xaml` réduit à : barre de titre + rail + footer + un
   `ContentControl` hôte **par page** (`x:Name="…Host"`), dont la `Visibility` est
   portée par le shell (`{Binding IsAuto|IsManual|IsSettings, Converter=…}`).
2. **Page** = fichier XAML autonome sous `GUI/Views/pages/`, racine `FrameworkElement`
   avec ses `xmlns`, chargé par `XamlReader.Load`, `DataContext` fixé **en code**, puis
   `host.Content = page`.
3. **Ressources** : le thème est en `DynamicResource` (100 %/5 côté shell) → résolu en
   **remontant l'arbre** une fois la page insérée dans la fenêtre (dictionnaires déjà
   fusionnés par `UIResourceLoader`). Corollaire prouvé : **les pages n'ont besoin
   d'aucune `StaticResource`** — le seul `StaticResource` (`BoolToVisibilityConverter`)
   reste dans le shell puisque la `Visibility` est sur l'hôte.

Spike (2026-07-24) : page Auto extraite + `AutoPageVM` data-holder + montage dans
`AutoPageHost` → liste des 3 collections rendue, badges colorés (DataTriggers +
DynamicResource) OK. Le spike sert de **fondation** (voir « Disposition du spike »).

## Architecture cible

### Layout des fichiers

```
GUI/Views/
  MainWindow.xaml            shell : titre + rail + footer + 3 ContentControl hôtes
  pages/
    AutoPage.xaml            liste collections « par jeu » (lecture seule)
    ManualPage.xaml          feuille par feuille : recherche + filtres + liste
    SettingsPage.xaml        4 cartes : mapping · destination · setups · nommage
lib/viewmodels/
  MainViewModel.py           coordinateur mince (nav, services partagés, coutures)
  AutoPageVM.py
  ManualPageVM.py
  SettingsVM.py              expose 4 sous-VMs
  settings/
    ParamMappingVM.py        ParamExport/Carnet/Dwg + ParametresDisponibles
    DestinationVM.py         DestinationPath, sous-dossiers, séparer formats
    SetupsVM.py              SetupsPdf/Dwg, SetupPdf/Dwg
    NamingPreviewVM.py       PatternFeuille/CarnetApercu
  FooterVM.py                StatusText, ProgressValue, lancer_export
  items.py                   SheetItemVM, CollectionItemVM, ManualSheetVM, FiltreItemVM
lib/views/
  MainWindowView.py          charge le shell + monte les 3 pages (généralise _load_page)
```

### Décomposition du ViewModel

`MainViewModel` devient un **coordinateur mince** qui :
- instancie les services **une fois** (config partagée `UserConfig('batch_export')`) et
  les **injecte** dans les sous-VMs (aucun sous-VM ne ré-instancie un service) ;
- expose `AutoPage` / `ManualPage` / `Settings` / `Footer` (bindables) + conserve l'état
  de navigation (`ActiveMode`, `IsAuto/IsManual/IsSettings`, `SurfaceTitre`) ;
- porte les **coutures inter-pages** (voir ci-dessous).

Chaque sous-VM dérive de `BaseViewModel`, possède ses propres propriétés/`notify_property`
et **son propre lot de tests standalone**. Les 4 item-VMs migrent tels quels dans
`items.py` (imports mis à jour). Dans le XAML, les cartes de la page Settings lient leurs
sous-VMs par **DataContext imbriqué** (`DataContext="{Binding Mapping}"`) — technique WPF
standard, sans câblage code.

### Couplage inter-pages (couture explicite)

Dépendance connue : changer `ParamExport/Carnet/Dwg` (page Settings) doit **requalifier**
les collections (page Auto). Couture : `MainViewModel` passe un **callback** à
`ParamMappingVM` (`on_mapping_changed`) ; à chaque changement persisté, le callback
appelle `AutoPageVM.refresh_par_jeu()`. Les sous-VMs ne se connaissent pas entre eux ; le
coordinateur est le seul point de couplage. Même schéma pour tout autre besoin
transversal (ex. Footer lançant l'export lit la config partagée, pas les sous-VMs).

### Vue / montage

`MainWindowView` généralise le montage du spike : `_load_page(filename)` +
`_mount_page(host_name, page_file, page_vm)`, appelés pour les 3 pages après
instanciation des sous-VMs. Le câblage résiduel (nav, boutons destination/export, modale
nommage) reste dans la vue.

## Séquencement (chaque étape = tests verts + checkpoint reload Revit)

Le risque est **quasi exclusivement dans le XAML** (les 199 tests couvrent la logique VM ;
extraire un sous-VM est mécaniquement sûr et attrapé par les tests). Ordre sûr→risqué :

1. **items.py** — extraire les 4 item-VMs. Tests verts. (zéro risque UI)
2. **Auto** — promouvoir `AutoPageVM` (stub spike → vrai VM : services injectés,
   `refresh_par_jeu`, notifications) ; `MainViewModel` délègue ; retirer les `print` du
   spike. Tests + reload.
3. **Manuel** — extraire `ManualPageVM` + `ManualPage.xaml` + hôte. Attention au `Popup`
   de filtres (ressources internes). Tests + reload.
4. **Settings** — extraire `SettingsVM` + 4 sous-VMs + `SettingsPage.xaml` (4 cartes en
   DataContext imbriqué) + **couture de couplage**. En dernier car il porte la
   dépendance vers Auto. Tests + reload.
5. **Footer** — extraire `FooterVM` + recâbler export/destination/statut. Tests + reload.
6. **Nettoyage final** — `MainViewModel` ne garde que coordination + nav ; supprimer le
   code déplacé. Tests + reload complet des 3 modes + export réel.

## Disposition du spike

Le spike est conservé comme **fondation** de l'étape 2 (Auto) : `AutoPage.xaml` est
l'extraction définitive ; `_load_page`/montage sont le mécanisme définitif (à
généraliser). Seul `AutoPageVM` (data-holder) et les `print` de diagnostic sont à
**promouvoir/retirer** en étape 2. Aucun rollback prévu (le spike n'est pas jeté).

## Non-objectifs

- Aucun changement fonctionnel ni visuel (iso-comportement).
- Pas de refonte des services métier ni de l'`ExportOrchestrator`.
- Pas de découpage XAML de la page Settings en 4 **fichiers** séparés (l'« éclatement »
  Settings se fait au niveau VM + DataContext imbriqué dans un seul `SettingsPage.xaml`) ;
  un découpage fichier ultérieur reste possible si le fichier reste trop gros.

## Risques & parades

- **Binding silencieux** après re-parentage → chaque étape validée par reload Revit ciblé
  sur la page concernée + les autres pages (non-régression).
- **Ressources internes à une page** (ex. `Popup` du mode manuel utilisant une
  `StaticResource`) → à repérer à l'extraction ; parade : définir la ressource dans les
  `Resources` de la page, ou fusionner un dict comme `merge_theme`.
- **Perte de notification** en déplaçant une propriété vers un sous-VM → couvert par les
  tests standalone de chaque sous-VM (assert `notify_property`).
```
