# -*- coding: utf-8 -*-
# Base commune aux services d'accès aux réglages d'export (PDF, DWG).
#
# Les deux formats ne diffèrent que par la clé de config du setup mémorisé,
# l'énumération des setups natifs Revit et la construction des options d'API.
# Tout le reste (résolution de la config, get/set du setup, tri des noms)
# était identique à la ligne près dans les deux services.

from __future__ import unicode_literals

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

try:
    from core.journal import journal
except Exception:
    try:
        from lib.core.journal import journal
    except Exception:
        journal = None  # type: ignore


# ----------------------------------------------------------------------
# Surcharges d'export
# ----------------------------------------------------------------------
# Valeurs choisies par l'utilisateur, posées PAR-DESSUS les options rendues
# par le setup Revit, au moment de l'export -- la maquette n'est jamais
# modifiée. Triplets (clé UserConfig, propriété des options, énumération DB
# ou None pour un booléen '0'/'1'). Valeur vide = « selon le setup ».

SURCHARGES_PDF = (
    ('pdf_couleur', 'ColorDepth', 'ColorDepthType'),
    ('pdf_qualite', 'RasterQuality', 'RasterQualityType'),
    ('pdf_raster', 'AlwaysUseRaster', None),
    ('pdf_masquer_cadrage', 'HideCropBoundaries', None),
    ('pdf_masquer_zones', 'HideScopeBoxes', None),
    ('pdf_masquer_plans_ref', 'HideReferencePlane', None),
    ('pdf_masquer_etiquettes', 'HideUnreferencedViewTags', None),
    ('pdf_liens_bleu', 'ViewLinksInBlue', None),
)

SURCHARGES_DWG = (
    ('dwg_version', 'FileVersion', 'ACADVersion'),
    ('dwg_coords_partagees', 'SharedCoords', None),
)

_BOOLEENS = {'0': False, '1': True}


def appliquer_surcharges(options, cfg, table, enums=None, log=None):
    """Pose sur `options` les surcharges non vides de `cfg` -> `options`.

    `enums` : espace où chercher les énumérations par nom (défaut : `DB`),
    injectable pour tester hors Revit. Une valeur inconnue ou une propriété
    absente est sautée et journalisée : une surcharge ne fait jamais échouer
    un export.
    """
    if options is None or cfg is None:
        return options
    enums = DB if enums is None else enums
    for cle, propriete, enum in table:
        try:
            brut = cfg.get(cle, '') or ''
        except Exception:
            brut = ''
        if not brut:
            continue
        try:
            if enum is None:
                valeur = _BOOLEENS[brut]
            else:
                valeur = getattr(getattr(enums, enum), brut)
            setattr(options, propriete, valeur)
        except Exception as e:
            _signaler(log, cle, brut, e)
    return options


def _signaler(log, cle, brut, erreur):
    if log is None and journal is not None:
        try:
            log = journal('batch_export')
        except Exception:
            log = None
    if log is not None:
        try:
            log.warning('surcharge ignoree %s=%r : %s', cle, brut, erreur)
        except Exception:
            pass


class FormatExporterService(object):
    """Réglages d'export d'un format. Sous-classer et définir :

    - `SETUP_KEY`         : clé UserConfig du setup mémorisé.
    - `list_all_setups(doc)` : noms des setups natifs du document.
    - `build_options(doc, setup_name=None)` : options d'API Revit.
    """

    SETUP_KEY = None

    def __init__(self, namespace='batch_export', config=None):
        # `config` injecté = on partage la MÊME UserConfig (socle) que le reste
        # de l'app -> les setups persistent dans data/<namespace>.json. Sans
        # injection, le service crée sa propre instance : même fichier, donc
        # mêmes valeurs, mais une lecture de plus par accès.
        if config is not None:
            self._cfg = config
        else:
            try:
                from core.UserConfig import UserConfig
            except Exception:
                try:
                    from lib.core.UserConfig import UserConfig
                except Exception:
                    UserConfig = None  # type: ignore
            self._cfg = UserConfig(namespace) if UserConfig is not None else None

    # ------------------------------------------------------------------
    # Setups disponibles
    # ------------------------------------------------------------------

    def list_all_setups(self, doc):
        """Noms des setups natifs du document. À définir par le format."""
        raise NotImplementedError

    @staticmethod
    def _noms_tries(names):
        """Dédoublonne et trie alphabétiquement, casse ignorée."""
        return sorted(set(n for n in names if n), key=lambda x: x.lower())

    # ------------------------------------------------------------------
    # Setup mémorisé
    # ------------------------------------------------------------------

    def get_saved_setup(self, default=None):
        try:
            val = self._cfg.get(self.SETUP_KEY, '') if self._cfg is not None else None
            return val or default
        except Exception:
            return default

    def set_saved_setup(self, name):
        if not name:
            return False
        try:
            return bool(self._cfg.set(self.SETUP_KEY, name)) if self._cfg is not None else False
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Options d'API
    # ------------------------------------------------------------------

    def build_options(self, doc, setup_name=None):
        raise NotImplementedError
