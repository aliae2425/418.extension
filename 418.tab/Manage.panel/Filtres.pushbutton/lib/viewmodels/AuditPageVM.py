# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import unicodedata

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from ui.helpers import donut_image
except Exception:
    try:
        from lib.ui.helpers import donut_image
    except Exception:
        donut_image = None


#: Marqueurs de copie en fin de nom, retirés avant comparaison :
#: « Béton (1) », « Béton - copie », « Béton copy ».
_COPIE = re.compile(r'(\s*\(\s*\d+\s*\)|\s*[-_]?\s*copies?|\s*copy)+$',
                    re.IGNORECASE | re.UNICODE)


def _cle_nom(nom):
    """Clé de rapprochement d'un nom : accents translittérés, casse, espaces
    et ponctuation retirés, marqueur de copie final coupé.

    Même geste que l'audit des matériaux : « Murs béton », « murs_beton » et
    « Murs béton (1) » tombent sur la même clé.

    ponytail: fonction recopiée de Materiaux/AuditPageVM plutôt que montée
    dans le socle — deux exemplaires, pas encore trois. Au troisième outil qui
    en a besoin, elle part dans lib/core/.
    """
    cle = _COPIE.sub(u'', (nom or u'').strip().lower())
    try:
        cle = u''.join(c for c in unicodedata.normalize('NFKD', cle)
                       if not unicodedata.combining(c))
    except Exception:
        pass
    return re.sub(r'[^0-9a-z]+', u'', cle)


class IndicateurVM(BaseViewModel):
    """Une tuile : un chiffre, ce qu'il compte, un détail.

    Figée à la construction — l'audit est l'instantané de l'ouverture.
    `Alerte` teinte le chiffre : c'est ce sur quoi il y a à faire.
    """

    def __init__(self, valeur, libelle, detail=u'', alerte=False):
        super(IndicateurVM, self).__init__()
        self.Valeur = u'%s' % valeur
        self.Libelle = libelle
        self.Detail = detail
        self.Alerte = bool(alerte)


class SegmentVM(BaseViewModel):
    """Une part de l'anneau, doublée en légende.

    `Couleur` est un '#RRGGBB' figé, pas un brush de thème : la même teinte
    sert au tracé de l'anneau (construit en Python, hors portée d'un
    DynamicResource) et à la pastille de légende.
    """

    def __init__(self, libelle, nombre, total, role, detail=u''):
        super(SegmentVM, self).__init__()
        self.Libelle = libelle
        self.Role = role
        self.Nombre = nombre
        self.Valeur = u'%d' % nombre
        self.Portion = (float(nombre) / total) if total else 0.0
        self.Part = u'%d %%' % round(100.0 * self.Portion) if total else u'—'
        self.Detail = detail
        self.Rgb = donut_image.couleur(role) if donut_image else (128, 128, 128)
        self.Couleur = (donut_image.hexa(self.Rgb) if donut_image
                        else u'#808080')


class LigneVM(BaseViewModel):
    """Une entrée d'une section de détail : un titre, une explication courte.

    Plus plate que le `GroupeVM` de l'audit des matériaux, parce que les cinq
    sections d'ici n'ont pas la même forme — trois listent des filtres un par
    un, deux listent des groupes. Un seul gabarit XAML couvre les deux.
    """

    def __init__(self, titre, detail=u''):
        super(LigneVM, self).__init__()
        self.Titre = titre or u'—'
        self.Detail = detail


class SectionVM(BaseViewModel):
    """Un bloc de détail repliable.

    Les sections sont de la DONNÉE : la page en rend une par entrée de
    `AuditPageVM.Sections`, avec un seul Expander en gabarit. Une section vide
    n'est pas construite du tout — pas de déclencheur de visibilité à écrire.
    """

    def __init__(self, titre, explication, lignes, unite=u'filtre',
                 deployee=False):
        super(SectionVM, self).__init__()
        self.Titre = titre
        self.Explication = explication
        self.Lignes = list(lignes)
        self.Nombre = len(self.Lignes)
        self.Compteur = u'%d %s%s' % (self.Nombre, unite,
                                      u's' if self.Nombre > 1 else u'')
        self._deployee = bool(deployee)

    @property
    def EstDeployee(self):
        return self._deployee

    @EstDeployee.setter
    def EstDeployee(self, value):
        """Pilotée par l'Expander (binding TwoWay) : l'état de pliage survit à
        un aller-retour vers un autre onglet, la page n'étant montée qu'une
        fois par RailWindow."""
        value = bool(value)
        if value != self._deployee:
            self._deployee = value
            self.notify_property('EstDeployee')


class AuditPageVM(BaseViewModel):
    """Onglet 0 — état des lieux des filtres de vue du modèle.

    Ne lit RIEN dans Revit : tout se déduit des dictionnaires renvoyés par
    `FiltresService.collecter_filtres()`. L'audit est donc figé à l'ouverture,
    comme celui des matériaux.

    ponytail: aucune action (purger, sélectionner) n'est câblée — c'est une
    page de lecture. Le geste viendra quand les onglets Coupes et Repérage
    sauront agir.
    """

    #: Barème du score : (poste, points perdus si TOUT le modèle est dans cet
    #: état, libellé). Même forme que l'audit des matériaux.
    #:
    #: ponytail: barème arbitraire, calé pour qu'un modèle sans filtre mort
    #: soit à 100. À ajuster à l'usage — c'est la seule constante à toucher.
    BAREME = (
        (u'non_utilises', 50, u'non utilisés'),
        (u'sans_effet', 30, u'sans effet'),
        (u'doublons', 20, u'doublons'),
    )

    def __init__(self, filtres=None):
        super(AuditPageVM, self).__init__()
        self.Filtres = list(filtres or [])
        self.Indicateurs = []
        self.NonUtilises = []
        self.SansEffet = []
        self.HorsGabarit = []
        self.NomsProches = []
        self.MemesCategories = []
        self.Sections = []
        self.Segments = []
        self.Score = 0
        self.ScoreDetail = u''
        self.Torus = None
        self.calculer()

    # ------------------------------------------------------------------
    # En-tête
    # ------------------------------------------------------------------

    @property
    def TitrePage(self):
        return u'Audit des filtres'

    @property
    def Resume(self):
        total = len(self.Filtres)
        if not total:
            return u'Aucun filtre dans le modèle.'
        return u'%d filtre%s · instantané à l\'ouverture du modèle' % (
            total, u's' if total > 1 else u'')

    @property
    def ScoreNiveau(self):
        """Palier du score, en ASCII : c'est sur LUI que les DataTrigger de la
        page teintent le chiffre. Comparer un libellé accentué marcherait, mais
        ferait dépendre la couleur du texte affiché."""
        if not self.Filtres:
            return u'vide'
        if self.Score >= 85:
            return u'bon'
        return u'moyen' if self.Score >= 60 else u'critique'

    #: Palier -> mention affichée.
    MENTIONS = {u'vide': u'—', u'bon': u'Bon état',
                u'moyen': u'À nettoyer', u'critique': u'Critique'}

    @property
    def ScoreMention(self):
        return self.MENTIONS[self.ScoreNiveau]

    @property
    def ARienASignaler(self):
        """Aucune section de détail : le message « rien à signaler » prend leur
        place. Booléen plutôt qu'un binding sur `Sections.Count` : c'est une
        liste Python, on ne parie pas sur l'IList qu'IronPython en expose."""
        return not self.Sections

    # ------------------------------------------------------------------
    # Calcul
    # ------------------------------------------------------------------

    def calculer(self):
        filtres = self.Filtres
        total = len(filtres)

        self.NonUtilises = [f for f in filtres if not self._applique(f)]
        # Appliqué quelque part, mais aucune de ces applications ne masque ni
        # ne surcharge : le filtre existe, coûte un aller-retour à chaque
        # ouverture de vue, et ne change rien à l'écran.
        self.SansEffet = [f for f in filtres
                          if self._applique(f) and not f.get('effets')]
        # Posé vue par vue, jamais par un gabarit : le réglage se perdra à la
        # prochaine vue créée.
        self.HorsGabarit = [f for f in filtres
                            if f.get('vues') and not f.get('gabarits')]
        sans_categorie = [f for f in filtres
                          if f.get('genre') == 'parametrique'
                          and not f.get('categories')]
        selection = [f for f in filtres if f.get('genre') == 'selection']

        self.NomsProches = self._grouper(
            filtres, lambda f: _cle_nom(f['nom']), titre=lambda f: f['nom'])
        self.MemesCategories = self._grouper(
            filtres,
            lambda f: u' · '.join(f['categories']) if f['categories'] else u'')

        utilises = total - len(self.NonUtilises)
        vues = self._distinctes(filtres, 'vues')
        gabarits = self._distinctes(filtres, 'gabarits')
        applications = sum(len(f.get('vues', [])) + len(f.get('gabarits', []))
                           for f in filtres)

        self._repartir()
        self._construire_sections()

        self.Indicateurs = [
            IndicateurVM(total, u'Filtres', u'dans le modèle'),
            IndicateurVM(utilises, u'Utilisés', self._part(utilises, total)),
            IndicateurVM(len(self.NonUtilises), u'Non utilisés',
                         u'purgeables', alerte=bool(self.NonUtilises)),
            IndicateurVM(len(self.SansEffet), u'Sans effet',
                         u'appliqués, sans surcharge',
                         alerte=bool(self.SansEffet)),
            IndicateurVM(len(self.HorsGabarit), u'Hors gabarit',
                         u'posés vue par vue',
                         alerte=bool(self.HorsGabarit)),
            IndicateurVM(self._membres(self.NomsProches), u'Noms proches',
                         u'%d groupe%s à fusionner' % (
                             len(self.NomsProches),
                             u's' if len(self.NomsProches) > 1 else u''),
                         alerte=bool(self.NomsProches)),
            IndicateurVM(self._membres(self.MemesCategories),
                         u'Mêmes catégories',
                         u'%d groupe%s de cibles identiques' % (
                             len(self.MemesCategories),
                             u's' if len(self.MemesCategories) > 1 else u''),
                         alerte=bool(self.MemesCategories)),
            IndicateurVM(len(sans_categorie), u'Sans catégorie',
                         u'ne peuvent rien filtrer',
                         alerte=bool(sans_categorie)),
            IndicateurVM(len(selection), u'Filtres de sélection',
                         u'liste figée d\'éléments'),
            IndicateurVM(vues, u'Vues filtrées', u'au moins un filtre'),
            IndicateurVM(gabarits, u'Gabarits filtrés', u'au moins un filtre'),
            IndicateurVM(applications, u'Applications',
                         u'couples filtre / vue'),
        ]
        for nom in ('Indicateurs', 'NonUtilises', 'SansEffet', 'HorsGabarit',
                    'NomsProches', 'MemesCategories', 'Sections', 'Resume',
                    'ARienASignaler', 'Segments', 'Score', 'ScoreDetail',
                    'ScoreMention', 'ScoreNiveau', 'Torus'):
            self.notify_property(nom)

    # ------------------------------------------------------------------
    # Sections repliables
    # ------------------------------------------------------------------

    #: (titre, explication, attribut porteur, constructeur de lignes, unité).
    #: L'ordre ici EST l'ordre à l'écran, et la première section non vide
    #: s'ouvre d'office. Une section vide n'est pas construite.
    SECTIONS = (
        (u'Non utilisés',
         u'Aucune vue ni gabarit ne les applique. Purgeables sans risque.',
         'NonUtilises', '_ligne_filtre', u'filtre'),
        (u'Sans effet',
         u'Appliqués quelque part, mais sans masquage ni remplacement '
         u'graphique : ils ne changent rien à l\'affichage.',
         'SansEffet', '_ligne_filtre', u'filtre'),
        (u'Hors gabarit',
         u'Posés vue par vue, jamais par un gabarit : le réglage ne suivra '
         u'pas les vues créées ensuite.',
         'HorsGabarit', '_ligne_usage', u'filtre'),
        (u'Noms proches',
         u'Noms identiques à la casse, aux accents, à la ponctuation ou à un '
         u'« (1) » près.',
         'NomsProches', '_ligne_groupe', u'groupe'),
        (u'Mêmes catégories',
         u'Ces filtres visent exactement les mêmes catégories : souvent un '
         u'seul suffirait.',
         'MemesCategories', '_ligne_groupe', u'groupe'),
    )

    def _construire_sections(self):
        self.Sections = []
        for (titre, explication, attribut, fabrique, unite) in self.SECTIONS:
            source = getattr(self, attribut)
            if not source:
                continue
            constructeur = getattr(self, fabrique)
            self.Sections.append(SectionVM(
                titre, explication, [constructeur(e) for e in source],
                unite=unite, deployee=not self.Sections))

    @staticmethod
    def _ligne_filtre(filtre):
        categories = filtre.get('categories') or []
        if filtre.get('genre') == 'selection':
            detail = u'filtre de sélection'
        elif categories:
            detail = u' · '.join(categories)
        else:
            detail = u'aucune catégorie'
        return LigneVM(filtre['nom'], detail)

    @staticmethod
    def _ligne_usage(filtre):
        vues = filtre.get('vues') or []
        return LigneVM(filtre['nom'], u'%d vue%s : %s' % (
            len(vues), u's' if len(vues) > 1 else u'', u' · '.join(vues)))

    @staticmethod
    def _ligne_groupe(groupe):
        titre, membres = groupe
        return LigneVM(titre, u'%d filtres : %s' % (
            len(membres), u' · '.join(f['nom'] for f in membres)))

    # ------------------------------------------------------------------
    # Anneau de récap + score
    # ------------------------------------------------------------------

    def _repartir(self):
        """Range CHAQUE filtre dans une seule part de l'anneau, puis note.

        L'anneau est une partition — sinon les parts ne bouclent pas. Un
        filtre non utilisé qui est AUSSI un doublon compte comme non utilisé :
        c'est le défaut le plus grave, et celui qui se règle en premier
        (purger avant de fusionner). Les tuiles, elles, comptent chaque défaut
        de son côté — les deux chiffres n'ont pas à coïncider.
        """
        total = len(self.Filtres)
        morts = set(f['nom'] for f in self.NonUtilises)
        inertes = set(f['nom'] for f in self.SansEffet) - morts
        doublons = set(f['nom']
                       for (_, membres) in (self.NomsProches + self.MemesCategories)
                       for f in membres) - morts - inertes
        sains = total - len(morts) - len(inertes) - len(doublons)

        self.Segments = [
            SegmentVM(u'Sains', sains, total, 'sains',
                      u'appliqués, actifs, sans doublon'),
            SegmentVM(u'En doublon', len(doublons), total, 'doublons',
                      u'nom voisin ou mêmes catégories'),
            SegmentVM(u'Sans effet', len(inertes), total, 'sans_effet',
                      u'appliqués mais inertes'),
            SegmentVM(u'Non utilisés', len(morts), total, 'non_utilises',
                      u'purgeables'),
        ]
        self.Torus = (donut_image.torus([(s.Portion, s.Rgb)
                                         for s in self.Segments])
                      if donut_image is not None else None)

        comptes = {u'non_utilises': len(morts), u'sans_effet': len(inertes),
                   u'doublons': len(doublons)}
        perdus = []
        score = 100.0
        for (poste, poids, libelle) in self.BAREME:
            if not total or not comptes[poste]:
                continue
            perte = poids * comptes[poste] / float(total)
            score -= perte
            perdus.append(u'−%d %s' % (round(perte), libelle))
        self.Score = int(round(max(0.0, min(100.0, score)))) if total else 0
        self.ScoreDetail = u' · '.join(perdus) if perdus else u'aucune pénalité'

    # ------------------------------------------------------------------
    # Outils
    # ------------------------------------------------------------------

    @staticmethod
    def _applique(filtre):
        return bool(filtre.get('vues') or filtre.get('gabarits'))

    @staticmethod
    def _part(nombre, total):
        return u'%d %%' % round(100.0 * nombre / total) if total else u''

    @staticmethod
    def _membres(groupes):
        return sum(len(membres) for (_, membres) in groupes)

    @staticmethod
    def _distinctes(filtres, clef):
        """Nombre de vues (ou de gabarits) distinctes portant un filtre."""
        noms = set()
        for filtre in filtres:
            noms.update(filtre.get(clef) or [])
        return len(noms)

    @staticmethod
    def _grouper(filtres, cle, titre=None):
        """[(titre, [filtres])] pour les clés partagées par 2 filtres ou plus.

        `titre` : de quoi étiqueter le groupe quand la clé n'est pas lisible
        (le nom normalisé) — on prend celui du premier filtre.
        """
        par_cle = {}
        for filtre in filtres:
            valeur = cle(filtre)
            if not valeur:
                continue
            par_cle.setdefault(valeur, []).append(filtre)
        groupes = [(titre(membres[0]) if titre else valeur, membres)
                   for (valeur, membres) in par_cle.items() if len(membres) > 1]
        return sorted(groupes, key=lambda g: (-len(g[1]), g[0]))
