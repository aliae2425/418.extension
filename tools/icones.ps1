# icones.ps1 — regenere les icon.png / icon.dark.png du ruban pyRevit depuis
# les geometries Lucide de lib/ui/GUI/resources/Icons.xaml.
#
# CE N'EST PAS UN BUILD STEP. Rien ne l'appelle : on le lance a la main, quand
# une icone du ruban change ou qu'un bouton en gagne une. La source de verite
# reste Icons.xaml — le PNG n'en est qu'un rendu jetable, jamais retouche a la main.
#
# Rendu : viewBox Lucide 24 x 24 a l'echelle 4 (trait 2 unites => 8 px), caps et
# jointures rondes, aucun remplissage, 96 x 96 px. Le dessin est centre sur ses
# bornes reelles (trait compris) : les geometries ne tiennent pas toutes dans
# 2..22, et un decentrage passerait inapercu a la taille du ruban.
# La variante claire est rendue en noir ; la sombre en est derivee pixel a pixel
# (blanc premultiplie = BGR a la valeur de l'alpha), ce qui garantit un masque
# alpha strictement identique entre les deux fichiers.
#
#   .\tools\icones.ps1 -Lister
#   .\tools\icones.ps1 -Cle IconAudit -Destination "418.tab\Audit.panel\Audit.pushbutton"
#   .\tools\icones.ps1 -Verifier
#
# -Verifier rend chaque cle et compare les empreintes aux icon.png du ruban :
# code de sortie 1 des qu'un PNG n'est reproductible par aucune cle. C'est le
# garde-fou de la regle « tout vient de Lucide, via ce script » — sans lui elle
# se redelite en silence, comme elle l'a deja fait pour 18 boutons.

param([string]$Cle, [string]$Destination, [switch]$Lister, [switch]$Verifier)

# Seule icone legitimement hors pipeline : la theiere est le logo du depot
# (HTTP 418, « I'm a teapot ») et n'existe pas chez Lucide.
$exceptions = @('418.panel\Infos.pushbutton')

Add-Type -AssemblyName PresentationCore, PresentationFramework, WindowsBase

# --- lecture des couples (x:Key, Figures) ---------------------------------
$source = Join-Path $PSScriptRoot '..\lib\ui\GUI\resources\Icons.xaml'
[xml]$xaml = Get-Content -LiteralPath $source -Encoding UTF8
$icones = @{}
foreach ($n in $xaml.ResourceDictionary.PathGeometry) { $icones[$n.Key] = $n.Figures }

if ($Verifier) {
    $racine = (Resolve-Path (Join-Path $PSScriptRoot '..\418.tab')).Path
    $tampon = Join-Path ([System.IO.Path]::GetTempPath()) ("icones-" + [System.Guid]::NewGuid().ToString('N'))

    # empreinte de chaque cle, rendue dans un dossier jetable
    $parEmpreinte = @{}
    foreach ($k in $icones.Keys) {
        $d = Join-Path $tampon $k
        New-Item -ItemType Directory -Force $d | Out-Null
        & $PSCommandPath -Cle $k -Destination $d | Out-Null
        $parEmpreinte[(Get-FileHash (Join-Path $d 'icon.png')).Hash] = $k
    }

    $orphelins = @()
    foreach ($png in Get-ChildItem -Recurse -Filter 'icon.png' -Path $racine | Sort-Object FullName) {
        $relatif = $png.DirectoryName.Substring($racine.Length).TrimStart('\')
        if ($exceptions -contains $relatif) { Write-Output ("exception  {0}" -f $relatif); continue }
        $h = (Get-FileHash $png.FullName).Hash
        if ($parEmpreinte.ContainsKey($h)) { Write-Output ("{0,-24} {1}" -f $parEmpreinte[$h], $relatif) }
        else { $orphelins += $relatif; Write-Output ("HORS PIPELINE            {0}" -f $relatif) }
    }
    Remove-Item -Recurse -Force $tampon

    if ($orphelins.Count -gt 0) {
        Write-Output ""
        Write-Output "$($orphelins.Count) icone(s) non reproductible(s) depuis Icons.xaml."
        Write-Output "Ajouter leur geometrie Lucide puis regenerer, ou les declarer en exception."
        exit 1
    }
    Write-Output ""
    Write-Output "Toutes les icones du ruban sortent d'Icons.xaml."
    exit 0
}

if ($Lister -or -not $Cle -or -not $Destination) {
    Write-Output "Cles disponibles dans $((Resolve-Path $source).Path) :"
    $icones.Keys | Sort-Object | ForEach-Object { Write-Output "  $_" }
    return
}
if (-not $icones.ContainsKey($Cle)) { throw "Cle inconnue : $Cle (voir -Lister)" }
if (-not (Test-Path -LiteralPath $Destination)) { throw "Dossier introuvable : $Destination" }

# --- rendu de la geometrie en 96 x 96, trait noir --------------------------
$geometrie = [System.Windows.Media.Geometry]::Parse($icones[$Cle])
$brosse = New-Object System.Windows.Media.SolidColorBrush ([System.Windows.Media.Colors]::Black)
$trait = New-Object System.Windows.Media.Pen -ArgumentList $brosse, 2
$trait.StartLineCap = 'Round'; $trait.EndLineCap = 'Round'; $trait.LineJoin = 'Round'

$bornes = $geometrie.GetRenderBounds($trait)   # bornes trait compris, en unites de viewBox
$transformations = New-Object System.Windows.Media.TransformGroup
foreach ($t in @(
    (New-Object System.Windows.Media.TranslateTransform -ArgumentList (-($bornes.X + $bornes.Width / 2)), (-($bornes.Y + $bornes.Height / 2))),
    (New-Object System.Windows.Media.ScaleTransform -ArgumentList 4, 4),
    (New-Object System.Windows.Media.TranslateTransform -ArgumentList 48, 48))) {
    $transformations.Children.Add($t)
}

$visuel = New-Object System.Windows.Media.DrawingVisual
$ctx = $visuel.RenderOpen()
$ctx.PushTransform($transformations)
$ctx.DrawGeometry($null, $trait, $geometrie)
$ctx.Pop()
$ctx.Close()

$bitmap = New-Object System.Windows.Media.Imaging.RenderTargetBitmap -ArgumentList 96, 96, 96, 96, ([System.Windows.Media.PixelFormats]::Pbgra32)
$bitmap.Render($visuel)
$pixels = New-Object byte[] (96 * 96 * 4)
$bitmap.CopyPixels($pixels, 96 * 4, 0)

# --- ecriture des deux variantes ------------------------------------------
# On ne garde du rendu que le canal alpha, et on recompose en alpha droit
# (Bgra32) : un seul RVB exact par fichier, et le meme masque alpha des deux
# cotes. Repasser par du premultiplie ferait deriver le blanc vers FEFEFE.
function Ecrire-Png($niveau, $chemin) {
    $octets = New-Object byte[] $pixels.Length
    for ($i = 0; $i -lt $pixels.Length; $i += 4) {
        $octets[$i] = $niveau; $octets[$i + 1] = $niveau; $octets[$i + 2] = $niveau
        $octets[$i + 3] = $pixels[$i + 3]
    }
    $img = [System.Windows.Media.Imaging.BitmapSource]::Create(96, 96, 96, 96, [System.Windows.Media.PixelFormats]::Bgra32, $null, $octets, 96 * 4)
    $encodeur = New-Object System.Windows.Media.Imaging.PngBitmapEncoder
    $encodeur.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($img))
    $flux = [System.IO.File]::Create($chemin)
    $encodeur.Save($flux)
    $flux.Close()
    Write-Output "ecrit $chemin"
}

$dossier = (Resolve-Path -LiteralPath $Destination).Path
Ecrire-Png 0 (Join-Path $dossier 'icon.png')
Ecrire-Png 255 (Join-Path $dossier 'icon.dark.png')
