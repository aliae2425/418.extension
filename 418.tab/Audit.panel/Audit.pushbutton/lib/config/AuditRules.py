# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import io
import json

# Severity mappé depuis les valeurs texte du JSON. Import gardé (hors Revit OK).
from models import OK, A_REVOIR, CRITIQUE

# ---------------------------------------------------------------------------
# Règles livrées. Aucun audit_rules.json n'est fourni : ces valeurs SONT le
# comportement par défaut du plugin. Le fichier n'existe que si l'utilisateur
# le crée pour surcharger une section (cf. audit_rules.schema.md).
# ---------------------------------------------------------------------------
DEFAULTS = {
    u'version': 1,
    u'score': {
        u'poids_theme': {
            u'warnings': 1.0, u'cad': 1.0, u'vues_feuilles': 1.0,
            u'purge': 0.6, u'nommage': 0.5,
        },
        u'points_critique': 10,
        u'points_a_revoir': 4,
        u'volume_facteur': 0.05,
        u'volume_max': 8,
    },
    u'avertissements': {
        u'mots_critiques': [
            u'dupliqu', u'identical', u'same place',
            u'même endroit', u'meme endroit', u'même place',
        ],
    },
    u'nommage': {
        u'vue_regex': r'^[A-Z]{2,4}_\d{2}_.+',
        u'famille_regex': r'^[A-Z]{2,4}_.+',
    },
    u'vues_feuilles': {
        u'nom_defaut_regex': r'^(Niveau|Level|Quadrillage|Grid)\s*\d+$',
    },
    u'cad': {
        u'gravite_import_explose': u'critique',
        u'gravite_lien': u'a_revoir',
    },
    u'purge': {
        u'gravite': u'a_revoir',
    },
}

# Chemin par défaut : racine du pushbutton (lib/config/ -> lib/ -> pushbutton/).
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_JSON_PATH = os.path.join(_ROOT, 'audit_rules.json')

_GRAVITES = {u'ok': OK, u'a_revoir': A_REVOIR, u'critique': CRITIQUE}


def _map_gravite(valeur, defaut):
    """Mappe une gravité texte ('critique'/'a_revoir'/'ok') vers Severity.
    Valeur inconnue -> defaut."""
    try:
        return _GRAVITES.get((valeur or u'').strip().lower(), defaut)
    except Exception:
        return defaut


class AuditRules(object):
    """Règles d'audit chargées depuis audit_rules.json, avec fallback défauts.

    Remplacement STRICT PAR SECTION : une section présente dans le fichier est
    prise telle quelle ; une section absente retombe sur son défaut en dur.
    Les clés absentes à l'intérieur d'une section présente retombent aussi sur
    le défaut de la clé (via les accesseurs) pour éviter qu'un oubli casse une
    règle. Ne lève jamais : fichier absent / JSON malformé -> défauts.
    """

    def __init__(self, chemin=None, data=None):
        self._data = data if data is not None else self._charger_fichier(chemin)

    # --- Chargement ---------------------------------------------------------
    def _charger_fichier(self, chemin):
        """Contenu brut du JSON, ou `{}` si absent/illisible/non-objet.

        `{}` suffit : `_section` fait déjà retomber CHAQUE section absente sur
        son défaut, donc un fichier manquant et un fichier vide se comportent
        de la même façon."""
        p = chemin or _JSON_PATH
        try:
            if os.path.isfile(p):
                with io.open(p, 'r', encoding='utf-8') as f:
                    charge = json.load(f)
                if isinstance(charge, dict):
                    return charge
                print(u'AuditRules : racine JSON non-objet, défauts utilisés.')
        except Exception as e:
            print(u'AuditRules : JSON illisible ({}), défauts utilisés.'.format(e))
        return {}

    # --- Accesseurs typés ---------------------------------------------------
    def _section(self, cle):
        sec = self._data.get(cle)
        return sec if isinstance(sec, dict) else DEFAULTS.get(cle, {})

    def score_poids(self):
        p = self._section(u'score').get(u'poids_theme')
        if isinstance(p, dict):
            return dict(p)
        return dict(DEFAULTS[u'score'][u'poids_theme'])

    def score_points(self):
        s = self._section(u'score')
        return {
            u'critique': s.get(u'points_critique', DEFAULTS[u'score'][u'points_critique']),
            u'a_revoir': s.get(u'points_a_revoir', DEFAULTS[u'score'][u'points_a_revoir']),
        }

    def score_volume(self):
        s = self._section(u'score')
        return {
            u'facteur': s.get(u'volume_facteur', DEFAULTS[u'score'][u'volume_facteur']),
            u'max': s.get(u'volume_max', DEFAULTS[u'score'][u'volume_max']),
        }

    def mots_critiques(self):
        m = self._section(u'avertissements').get(u'mots_critiques')
        if isinstance(m, (list, tuple)):
            return [(x or u'').lower() for x in m]
        return list(DEFAULTS[u'avertissements'][u'mots_critiques'])

    def vue_regex(self):
        return self._section(u'nommage').get(
            u'vue_regex') or DEFAULTS[u'nommage'][u'vue_regex']

    def famille_regex(self):
        return self._section(u'nommage').get(
            u'famille_regex') or DEFAULTS[u'nommage'][u'famille_regex']

    def nom_defaut_regex(self):
        return self._section(u'vues_feuilles').get(
            u'nom_defaut_regex') or DEFAULTS[u'vues_feuilles'][u'nom_defaut_regex']

    def cad_gravite_import(self):
        return _map_gravite(
            self._section(u'cad').get(u'gravite_import_explose', u'critique'), CRITIQUE)

    def cad_gravite_lien(self):
        return _map_gravite(
            self._section(u'cad').get(u'gravite_lien', u'a_revoir'), A_REVOIR)

    def purge_gravite(self):
        return _map_gravite(
            self._section(u'purge').get(u'gravite', u'a_revoir'), A_REVOIR)


_singleton = None


def charger():
    """Singleton mémoïsé pour l'usage runtime (chargé une fois par session)."""
    global _singleton
    if _singleton is None:
        _singleton = AuditRules()
    return _singleton
