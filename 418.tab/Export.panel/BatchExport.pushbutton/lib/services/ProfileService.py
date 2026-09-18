# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import io
import json
import os

# Double forme d'import (régime pyRevit vs tests standalone), cf. convention
# du projet -- JAMAIS d'import relatif profond (cf. CLAUDE.md).
try:
    from core.UserConfig import _config_dir
except Exception:
    try:
        from lib.core.UserConfig import _config_dir
    except Exception:
        _config_dir = None  # type: ignore

try:
    from core.sanitize import sanitize
except Exception:
    try:
        from lib.core.sanitize import sanitize
    except Exception:
        sanitize = None  # type: ignore


def _nom_fichier(nom):
    """Nom de profil -> nom de fichier Windows valide (sans extension)."""
    nom = (nom or u'').strip()
    if sanitize is not None:
        try:
            return sanitize(nom, fallback=u'profil')
        except Exception:
            pass
    return nom or u'profil'


NOM_DEFAUT = u'Défaut'

# Profil « Défaut » : le plus neutre possible. Nommage réduit à l'essentiel
# (feuille = numéro_nom, carnet = titre du jeu), setups d'impression VIDES
# -> `build_options(doc, setup_name=None)` prend les réglages par défaut de
# Revit, et aucune option d'organisation activée.
#
# Intégré au code, PAS écrit sur disque : c'est un repli toujours présent,
# indésinstallable et non corruptible (cf. `delete`/`save`).
DEFAUT = {
    'pattern_sheet': u'{numero}_{nom}',
    'pattern_set': u'{titre}',
    'pattern_sheet_rows': u'[]',
    'pattern_set_rows': u'[]',
    'pdf_setup_name': u'',
    'dwg_setup_name': u'',
    'create_subfolders': u'0',
    'separate_format_folders': u'0',
    'manual_combine_pdf': u'0',
}


class ProfileService(object):
    """Profils d'export : un fichier JSON par profil dans `data/profils/`.

    Un profil est un SOUS-ENSEMBLE de la config `batch_export` (cf. `CLES`) :
    conventions de nommage, setups d'impression PDF/DWG et options
    d'organisation. Appliquer un profil = réécrire ces clés dans la config
    courante ; l'exporter = les vider dans un fichier partageable.

    Trois clés sont volontairement EXCLUES :
      - `PathDossier` (destination) : propre au poste, un profil partagé ne
        doit pas trimballer le chemin local de quelqu'un d'autre ;
      - `jeux_badges` : propre au projet ouvert, pas au réglage d'export ;
      - `manual_pdf_combine_title` : titre d'UN export combiné précis, pas
        un réglage durable.

    `_config_dir()` (UserConfig) est réutilisé comme racine : les profils
    suivent donc l'override `PY418_CONFIG_DIR` des tests.
    """

    CLES = (
        'pattern_sheet', 'pattern_set',
        'pattern_sheet_rows', 'pattern_set_rows',
        'pdf_setup_name', 'dwg_setup_name',
        'create_subfolders', 'separate_format_folders',
        'manual_combine_pdf',
    )

    def __init__(self, config=None, dossier=None):
        self._cfg = config
        self._dossier = dossier

    def dossier(self):
        if self._dossier:
            return self._dossier
        base = _config_dir() if _config_dir is not None else os.getcwd()
        return os.path.join(base, 'profils')

    def _chemin(self, nom):
        return os.path.join(self.dossier(), _nom_fichier(nom) + '.json')

    # ------------------------------------------------------------------
    # Lecture / écriture de fichiers
    # ------------------------------------------------------------------

    def lire(self, chemin):
        """Lit un fichier de profil -> dict filtré sur `CLES`.

        Frontière de confiance (fichier venant d'un autre poste) : tout ce
        qui n'est pas une clé connue est IGNORÉ, et un JSON illisible ou qui
        n'est pas un objet LÈVE -- l'appelant doit pouvoir le signaler plutôt
        que d'appliquer un profil vide en silence.
        """
        with io.open(chemin, 'r', encoding='utf-8') as f:
            brut = json.load(f)
        if not isinstance(brut, dict):
            raise ValueError(u'Profil invalide (le JSON n\'est pas un objet).')
        return dict((k, v) for k, v in brut.items() if k in self.CLES)

    def ecrire(self, chemin, donnees=None):
        """Écrit `donnees` (défaut : les réglages courants) en JSON UTF-8.

        `ensure_ascii=False` est OBLIGATOIRE : sous IronPython 2.7 l'encodeur
        ASCII de `json` lève sur le moindre accent (cf. UserConfig).
        """
        donnees = self.snapshot() if donnees is None else donnees
        d = os.path.dirname(chemin)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with io.open(chemin, 'w', encoding='utf-8') as f:
            f.write(json.dumps(donnees, ensure_ascii=False, indent=2))
        return chemin

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def list(self):
        """Noms des profils disponibles. « Défaut » d'abord (il est intégré,
        donc toujours là), puis les profils de l'utilisateur triés (casse
        ignorée). Un fichier qui usurperait le nom réservé est masqué."""
        try:
            noms = [f[:-5] for f in os.listdir(self.dossier())
                    if f.lower().endswith('.json')]
        except Exception:
            noms = []
        noms = [n for n in noms if n != NOM_DEFAUT]
        return [NOM_DEFAUT] + sorted(noms, key=lambda n: n.lower())

    def snapshot(self):
        """Réglages courants -> dict. Les clés absentes de la config sont
        omises (un profil ne fabrique pas de valeur par défaut)."""
        out = {}
        if self._cfg is None:
            return out
        for cle in self.CLES:
            try:
                val = self._cfg.get(cle, None)
            except Exception:
                val = None
            if val is not None:
                out[cle] = val
        return out

    def save(self, nom):
        """Enregistre les réglages courants sous le profil `nom`."""
        if (nom or u'').strip() == NOM_DEFAUT:
            raise ValueError(
                u'« {} » est un nom réservé : choisissez-en un autre.'.format(
                    NOM_DEFAUT))
        return self.ecrire(self._chemin(nom))

    def delete(self, nom):
        if nom == NOM_DEFAUT:
            raise ValueError(
                u'Le profil « {} » ne peut pas être supprimé.'.format(NOM_DEFAUT))
        chemin = self._chemin(nom)
        if os.path.exists(chemin):
            os.remove(chemin)

    def apply(self, nom):
        """Écrit les réglages du profil `nom` dans la config -> nb de clés."""
        donnees = (dict(DEFAUT) if nom == NOM_DEFAUT
                   else self.lire(self._chemin(nom)))
        if self._cfg is None:
            return 0
        for cle, val in donnees.items():
            self._cfg.set(cle, val)
        return len(donnees)

    def importer(self, chemin):
        """Copie un fichier de profil externe dans `data/profils/` -> nom.

        Le nom du profil est celui du fichier. Un fichier qui ne contient
        aucune clé connue lève : l'utilisateur s'est trompé de fichier.
        """
        donnees = self.lire(chemin)
        if not donnees:
            raise ValueError(u'Aucun réglage reconnu dans ce fichier.')
        nom = os.path.splitext(os.path.basename(chemin))[0]
        # Le nom vient de l'expéditeur : s'il heurte le nom réservé, on le
        # décale plutôt que de refuser un import que l'utilisateur ne
        # maîtrise pas (`list()` masquerait un fichier « Défaut.json »).
        if nom == NOM_DEFAUT:
            nom = nom + u' (importé)'
        self.ecrire(self._chemin(nom), donnees)
        return nom
