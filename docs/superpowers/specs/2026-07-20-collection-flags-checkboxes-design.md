# Spec — Toggles (Checkboxes) pour les flags de collection dans le récap des jeux

**Date** : 2026-07-20  
**Branche** : feat/BatchExport  
**Scope** : `BatchExport.pushbutton` uniquement

---

## Problème

Le récap des jeux de feuilles (`CollectionPreview`) affiche les flags d'export de chaque collection (`export`, `carnet PDF`, `DWG`) sous forme de texte en lecture seule (`CollectionExportInfo` : `"export : [✔️] | Compilé : [✔️] | DWG : [❌]"`). L'utilisateur doit fermer la fenêtre, modifier le paramètre dans Revit, puis rouvrir pour changer un flag.

## Objectif

Remplacer ce texte par 3 `CheckBox` interactives dans l'en-tête de chaque groupe de collection, permettant de basculer les flags directement depuis la modal. Les modifications sont écrites immédiatement dans les paramètres Revit de la `SheetCollection`.

---

## Architecture retenue : Approach A — in-place update, event handlers

Pas de MVVM (refactor ultérieur possible). Aucun nouveau fichier. Tout reste dans les fichiers existants.

---

## Section 1 — Données

**Nouveaux champs ajoutés à chaque `ObservableItem`** dans `CollectionPreviewComponent.populate()` :

| Clé | Type | Description |
|---|---|---|
| `CollectionExportFlag` | bool | Flag export (alias de `CollectionIsExported`) |
| `CollectionCarnetFlag` | bool | Flag carnet PDF compilé |
| `CollectionDwgFlag` | bool | Flag export DWG |
| `CollectionId` | `ElementId` | Id Revit de la `SheetCollection` pour write-back |
| `ParamExport` | str | Nom du paramètre Revit lié à `ExportationCombo` |
| `ParamCarnet` | str | Nom du paramètre Revit lié à `CarnetCombo` |
| `ParamDwg` | str | Nom du paramètre Revit lié à `DWGCombo` |

Les valeurs de `ParamExport/Carnet/Dwg` proviennent de `selected_names` déjà passé à `populate()` — pas de nouvel accès config.

---

## Section 2 — XAML (`GUI/Controls/CollectionPreview.xaml`)

### Remplacement dans `GroupStyle.HeaderTemplate`

Remplacer le `TextBlock` lié à `CollectionExportInfo` par :

```xml
<StackPanel Orientation="Horizontal">
    <CheckBox Content="Export"
              Tag="export"
              IsChecked="{Binding Items[0][CollectionExportFlag], Mode=OneWay}"
              ToolTip="{Binding Items[0][ParamExport]}"/>
    <CheckBox Content="Carnet"
              Tag="carnet"
              IsChecked="{Binding Items[0][CollectionCarnetFlag], Mode=OneWay}"
              ToolTip="{Binding Items[0][ParamCarnet]}"/>
    <CheckBox Content="DWG"
              Tag="dwg"
              IsChecked="{Binding Items[0][CollectionDwgFlag], Mode=OneWay}"
              ToolTip="{Binding Items[0][ParamDwg]}"/>
</StackPanel>
```

- `Mode=OneWay` : état initial depuis les données, write-back géré par événement Python
- `ToolTip` : affiche le nom réel du paramètre Revit au survol
- Labels fixes ("Export", "Carnet", "DWG") indépendants de la longueur du nom de param

### Grisage des lignes de feuilles

Ajouter un `DataTrigger` dans le `DataTemplate` des items de feuille :

```xml
<DataTrigger Binding="{Binding [CollectionIsExported]}" Value="False">
    <Setter Property="Opacity" Value="0.4"/>
</DataTrigger>
```

Quand "Export" est décoché, toutes les lignes de feuilles du groupe passent en semi-transparent.

---

## Section 3 — Python (`lib/ui/components/CollectionPreviewComponent.py`)

### 3.1 — Populate

Dans `populate()`, ajouter aux items existants :

```python
items.append(ObservableItem({
    # ... champs existants ...
    'CollectionExportFlag': do_export,
    'CollectionCarnetFlag': carnet_flag,
    'CollectionDwgFlag':    do_dwg,
    'CollectionId':         coll.Id,
    'ParamExport':          pname_export or '',
    'ParamCarnet':          pname_carnet or '',
    'ParamDwg':             pname_dwg or '',
}))
```

### 3.2 — Branchement des événements (routed events)

Après population de la grille, dans `populate()` :

```python
from System.Windows.Controls.Primitives import ToggleButton
from System.Windows import RoutedEventHandler

grid.AddHandler(
    ToggleButton.CheckedEvent,
    RoutedEventHandler(self._on_flag_changed)
)
grid.AddHandler(
    ToggleButton.UncheckedEvent,
    RoutedEventHandler(self._on_flag_changed)
)
```

Les `CheckBox.Checked/Unchecked` remontent (bubble) vers le `ListView` — pas besoin de trouver les contrôles individuellement dans le template.

### 3.3 — Handler `_on_flag_changed`

```python
def _on_flag_changed(self, sender, args):
    from System.Windows.Controls import CheckBox
    cb = args.Source
    if not isinstance(cb, CheckBox):
        return

    flag_type = cb.Tag           # "export", "carnet", "dwg"
    new_val   = bool(cb.IsChecked)
    group     = cb.DataContext   # CollectionViewGroup

    if not group or not group.Items.Count:
        return

    first      = group.Items[0]
    coll_id    = first['CollectionId']
    param_name = first['Param' + flag_type.capitalize()]

    # 1. Écriture Revit dans une transaction
    try:
        with revit.Transaction(u"Modifier flag {}".format(flag_type)):
            coll = revit.doc.GetElement(coll_id)
            p = coll.LookupParameter(param_name)
            if p and not p.IsReadOnly:
                p.Set(1 if new_val else 0)
    except Exception:
        cb.IsChecked = not new_val   # rollback visuel si échec
        return

    # 2. Mise à jour in-place de tous les items du groupe
    flag_key = {
        'export': 'CollectionExportFlag',
        'carnet': 'CollectionCarnetFlag',
        'dwg':    'CollectionDwgFlag',
    }[flag_type]

    for item in group.Items:
        item[flag_key] = new_val
        if flag_type == 'export':
            item['CollectionIsExported'] = new_val   # pilote le grisage

    # 3. Rafraîchissement de la ListCollectionView (pas de re-scan Revit)
    view = getattr(self._grid, 'ItemsSource', None)
    if view:
        view.Refresh()
```

---

## Fichiers modifiés

| Fichier | Nature de la modification |
|---|---|
| `GUI/Controls/CollectionPreview.xaml` | Remplacer `TextBlock CollectionExportInfo` par 3 `CheckBox` + `DataTrigger` grisage |
| `lib/ui/components/CollectionPreviewComponent.py` | Ajouter champs aux items, brancher routed events, implémenter `_on_flag_changed` |

**Aucun nouveau fichier.**

---

## Contraintes et hypothèses

- Les paramètres `ExportationCombo`, `CarnetCombo`, `DWGCombo` sont obligatoirement des paramètres de type `YesNo` sur `SheetCollection` — vérifié par `SheetParameterRepository.is_boolean_param_definition()`
- `param.IsReadOnly` est vérifié avant écriture — pas d'exception silencieuse
- En cas d'échec de transaction, le checkbox est remis visuellement à son état précédent
- Le `view.Refresh()` est un rafraîchissement de vue mémoire uniquement, sans re-scan Revit
- Refactor MVVM différé à une itération ultérieure

---

## Hors scope

- Toggles au niveau des feuilles individuelles
- Migration MVVM / `INotifyPropertyChanged`
- Modification de `ParametersSectionController` ou `SheetParameterRepository`
