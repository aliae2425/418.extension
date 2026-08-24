# -*- coding: utf-8 -*-
# Base commune aux services d'accès aux réglages d'export (PDF, DWG).
#
# Les deux formats ne diffèrent que par la clé de config du setup mémorisé,
# l'énumération des setups natifs Revit et la construction des options d'API.
# Tout le reste (résolution de la config, get/set du setup, tri des noms)
# était identique à la ligne près dans les deux services.

from __future__ import unicode_literals


class FormatExporterService(object):
    """Réglages d'export d'un format. Sous-classer et définir :

    - `SETUP_KEY`         : clé UserConfig du setup mémorisé.
    - `_list_revit_setups(doc)` : noms des setups natifs du document.
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
        return self._list_revit_setups(doc)

    def _list_revit_setups(self, doc):
        raise NotImplementedError

    @staticmethod
    def _noms_tries(names):
        """Dédoublonne en préservant l'ordre d'apparition, puis trie
        alphabétiquement sans tenir compte de la casse."""
        out = []
        for nm in names:
            if nm and nm not in out:
                out.append(nm)
        try:
            out.sort(key=lambda x: x.lower())
        except Exception:
            out.sort()
        return out

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
