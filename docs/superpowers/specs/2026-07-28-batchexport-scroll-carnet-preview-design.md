# BatchExport — Overflow scroll (Réglages) + Preview titre de carnet

Date : 2026-07-28
Périmètre : `418.tab/Export.panel/BatchExport.pushbutton`

## Contexte

Deux ajustements issus de `issus.md` (liste `enhance`) :

1. « ajouter un overflow scroll dans reglage. »
2. « ajouter preview des titre quand carnet est activé. »

## Task 1 — Overflow scroll dans Réglages

**Problème** : `PanneauParametres` (`GUI/Views/MainWindow.xaml:572`) est un
`StackPanel` de 4 cartes `Expander` posé dans `Grid.Row="1"` (`Height="*"`).
Quand plusieurs cartes sont dépliées, le contenu déborde la surface sans
barre de défilement.

**Solution** : envelopper `PanneauParametres` dans un `ScrollViewer`
(`VerticalScrollBarVisibility="Auto"`, `HorizontalScrollBarVisibility="Disabled"`),
à l'identique de `AutoPage.xaml` et de la liste manuelle. La `Visibility`
liée à `IsSettings` reste portée par le conteneur. Barre de défilement au
ras du bord de la surface (marge conservée sur le `StackPanel` interne, pas
de padding qui repousse la barre). Aucun changement Python.

## Task 2 — Preview du titre de carnet (mode « par jeu »)

**But** : quand une collection a l'export en carnet actif (`FlagCarnet`),
afficher sous le titre du jeu, dans l'en-tête de la carte, un aperçu du nom
de fichier PDF que produira le carnet.

**Emplacement retenu** (validé) : sous-ligne dans l'en-tête de la carte,
toujours visible (même carte repliée), uniquement si carnet actif.

### Données — `MainViewModel` / `CollectionItemVM`

- `CollectionItemVM` reçoit deux propriétés en lecture seule :
  - `CarnetApercu` (str) : nom de fichier de carnet résolu **+ `.pdf`**,
    `''` si le motif `set` est vide.
  - `CarnetApercuVisible` (bool) = `FlagCarnet and bool(CarnetApercu)`.
    Ce booléen évite d'afficher une icône 📖 seule sans texte quand le
    carnet est actif mais que le motif `set` est absent/vide (un
    `DataTrigger` ne peut pas tester « chaîne non vide » sans convertisseur).
  - Le constructeur reçoit un paramètre `carnet_apercu` (défaut `''`).
- `refresh_par_jeu` :
  - hisser `set_pattern, set_rows = self._naming_service.load('set')` avant
    la boucle (comme `_pattern`/`rows_sheet` pour les feuilles) ;
  - par collection disposant d'un `coll_elem`, résoudre via
    `naming_service.resolve_for_element(coll_elem, set_pattern or set_rows)`
    et ajouter `.pdf` si le résultat est non vide ; même discipline
    `try/except` + repli que `nom_projete`.

### Vue — `GUI/Views/pages/AutoPage.xaml`

- Dans l'en-tête de carte, envelopper le `TextBlock` `Titre` (colonne 0)
  dans un `StackPanel` vertical et ajouter une 2ᵉ ligne : 📖 +
  `{Binding CarnetApercu}` — `Foreground=TextSecondaryBrush`,
  `FontFamily=Consolas`, `FontSize=11`, `TextTrimming=CharacterEllipsis`.
- Défaut `Visibility="Collapsed"`, basculée par un `DataTrigger` sur
  `CarnetApercuVisible == True` dans `DataTemplate.Triggers`.
  Raison : `AutoPage.xaml` n'a **pas** de `BoolToVisibilityConverter`
  (la `Visibility IsAuto` est portée par l'hôte) → on suit le patron des
  badges existants (trigger, pas convertisseur).

### Câblage du rafraîchissement (écart identifié — requis)

`AutoPage` est lié à un `AutoPageVM` **distinct**, peuplé une seule fois au
montage (`_mount_auto_page_spike`). `refresh_par_jeu` réassigne
`MainViewModel._collections` mais ne le propage jamais à `AutoPageVM` ; la
navigation ne re-monte pas la page. Conséquence actuelle : changer les
paramètres ou le motif de nommage ne rafraîchit pas la page « par jeu ».
Pont minimal :

- `_mount_auto_page_spike` mémorise `self._auto_page_vm`.
- `MainViewModel` reçoit un callback optionnel `_on_collections_changed_cb`
  (défaut `None`), invoqué à la fin de `refresh_par_jeu`. `MainWindowView`
  le branche sur `_sync_auto_page()` qui appelle
  `self._auto_page_vm.set_collections(self._vm.Collections)`.
- `_open_naming_editor` : après fermeture de la modale, appeler aussi
  `refresh_par_jeu()` (aujourd'hui seul `refresh_patterns_apercu()` est
  appelé) pour que l'édition du motif de carnet (`set`) mette à jour les
  aperçus.

### Tests

Étendre `tests/test_main_viewmodel.py` avec des cas `CarnetApercu` /
`CarnetApercuVisible` (services factices + motif `set` factice), en
réutilisant le montage de services factices des tests `FlagCarnet`
existants (l. 214, 358). Vérification hors Revit — pas de reload requis.

## Limite assumée

L'aperçu résout le motif `set` et ajoute `.pdf` pour coller à la maquette
validée, mais n'applique **pas** `DestinationStore.sanitize` (cohérent avec
le `nom_projete` des feuilles, lui aussi non nettoyé). Des caractères
exotiques (`:*?"<>|`) pourraient donc différer légèrement du nom de fichier
réel — simplification délibérée et mineure.

## Fichiers touchés

- `GUI/Views/MainWindow.xaml` (Task 1 : ScrollViewer)
- `GUI/Views/pages/AutoPage.xaml` (Task 2 : sous-ligne + trigger)
- `lib/viewmodels/MainViewModel.py` (`CollectionItemVM`, `refresh_par_jeu`,
  `_on_collections_changed_cb`)
- `lib/views/MainWindowView.py` (`_mount_auto_page_spike`, `_sync_auto_page`,
  `_open_naming_editor`)
- `tests/test_main_viewmodel.py`
