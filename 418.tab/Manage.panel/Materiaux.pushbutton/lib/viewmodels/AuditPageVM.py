# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import unicodedata

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.services.journal import log
except Exception:
    try:
        from services.journal import log
    except Exception:
        def log(gabarit, *args):
            pass

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

    « Béton banché », « beton_banche » et « Béton banché (1) » tombent sur la
    même clé — ce sont les doublons que l'audit doit signaler. Les accents
    passent par une décomposition NFKD : sans elle, `[^0-9a-z]` mangerait le
    « é » au lieu de le ramener à « e », et « Béton » ne rejoindrait jamais
    « Beton ».
    """
    cle = _COPIE.sub(u'', (nom or u'').strip().lower())
    try:
        cle = u''.join(c for c in unicodedata.normalize('NFKD', cle)
                       if not unicodedata.combining(c))
    except Exception:
        pass
    return re.sub(r'[^0-9a-z]+', u'', cle)


class IndicateurVM(BaseViewModel):
    """Une tuile de l'onglet Audit : un chiffre, ce qu'il compte, un détail.

    Figée à la construction — l'audit est l'instantané de l'ouverture, comme
    le comptage d'usages. `Alerte` passe le chiffre en teinte
    d'avertissement : c'est ce sur quoi il y a quelque chose à faire.
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
    doit servir au tracé de l'anneau (construit en Python, hors portée d'un
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


class GroupeVM(BaseViewModel):
    """Un lot de matériaux qui se ressemblent : même apparence, même hachure,
    ou noms voisins. `Titre` est ce qui les rassemble, `Membres` la liste
    lisible, `Apercu` la vignette du motif quand le groupe en a un."""

    def __init__(self, titre, cartes, apercu=None):
        super(GroupeVM, self).__init__()
        self.Titre = titre or u'—'
        self.Cartes = list(cartes)
        self.Nombre = len(self.Cartes)
        self.Membres = u' · '.join(carte.Nom for carte in self.Cartes)
        # Toutes les cards du groupe ont le même motif : la première suffit.
        self.Apercu = apercu(self.Cartes[0]) if apercu and self.Cartes else None
        self.AApercu = self.Apercu is not None


class SectionVM(BaseViewModel):
    """Un bloc de détail repliable de l'onglet Audit.

    Les sections sont de la DONNÉE : la page en rend une par entrée de
    `AuditPageVM.Sections`, avec un seul Expander en gabarit. Une section vide
    n'est pas construite du tout — pas de déclencheur de visibilité à écrire,
    et ajouter un critère de doublon ne touche pas au XAML.
    """

    def __init__(self, titre, explication, groupes, deployee=False):
        super(SectionVM, self).__init__()
        self.Titre = titre
        self.Explication = explication
        self.Groupes = list(groupes)
        self.Nombre = len(self.Groupes)
        self.Materiaux = sum(groupe.Nombre for groupe in self.Groupes)
        self.Compteur = u'%d groupe%s · %d matériaux' % (
            self.Nombre, u's' if self.Nombre > 1 else u'', self.Materiaux)
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
    """Onglet 0 — état des lieux des matériaux du modèle.

    Ne lit RIEN dans Revit : tout se déduit des `MaterialCardVM` déjà
    construites par script.py (nom, classe, apparence, motifs) et du comptage
    d'usages déjà fait à l'ouverture. L'audit est donc gratuit, et il est
    figé comme les chiffres d'usages — un remplacement ou un renommage ne le
    recalcule pas.

    ponytail: aucune action (purger, sélectionner les non utilisés) n'est
    câblée — c'est une maquette de lecture. Le jour où on veut agir, le geste
    est de cocher la sélection de l'onglet Matériaux depuis une tuile.
    """

    #: Barème du score : (rôle pénalisé, points perdus si TOUT le modèle est
    #: dans cet état). Un modèle dont la moitié des matériaux ne servent à
    #: rien perd donc 25 points sur les 50 du poste « non utilisés ».
    #:
    #: ponytail: barème arbitraire, calé pour qu'un modèle propre soit à 100 et
    #: qu'un modèle à moitié inutile passe sous 75. À ajuster à l'usage — c'est
    #: la seule constante à toucher, le reste s'en déduit.
    BAREME = (
        (u'non_utilises', 50, u'non utilisés'),
        (u'doublons', 35, u'doublons'),
        (u'incomplets', 15, u'fiches incomplètes'),
    )

    def __init__(self, cartes=None):
        super(AuditPageVM, self).__init__()
        self.Cartes = list(cartes or [])
        self.Indicateurs = []
        self.ApparencesPartagees = []
        self.NomsProches = []
        self.MotifsCoupe = []
        self.MotifsSurface = []
        self.Sections = []
        self.Segments = []
        self.Score = 0
        self.ScoreDetail = u''
        self.Torus = None
        self.calculer()

    @property
    def ScoreNiveau(self):
        """Palier du score, en ASCII : c'est sur LUI que les DataTrigger de la
        page teintent le chiffre. Comparer un libellé accentué dans le XAML
        marcherait, mais ferait dépendre la couleur du texte affiché."""
        if not self.Cartes:
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

    # ------------------------------------------------------------------

    @property
    def TitrePage(self):
        return u'Audit des matériaux'

    @property
    def Resume(self):
        total = len(self.Cartes)
        if not total:
            return u'Aucun matériau dans le modèle.'
        return u'%d matériau%s · instantané à l\'ouverture du modèle' % (
            total, u'x' if total > 1 else u'')

    @property
    def ARienASignaler(self):
        """Aucune section de détail : le message « rien à fusionner » prend
        leur place. Booléen plutôt qu'un binding sur `Sections.Count` : c'est
        une liste Python, on ne parie pas sur l'IList qu'IronPython en expose.
        """
        return not self.Sections

    # ------------------------------------------------------------------

    def calculer(self):
        cartes = self.Cartes
        total = len(cartes)
        utilises = [c for c in cartes if c.EstUtilise]
        non_utilises = [c for c in cartes if not c.EstUtilise]
        # Utilisé (déclaré dans un type) mais posé nulle part : le cas qui ne
        # se voit pas, et qui ne se purge pas non plus.
        sans_instance = [c for c in utilises if c.SansInstance]
        sans_classe = [c for c in cartes if not c.Classe or c.Classe == u'Sans classe']
        sans_apparence = [c for c in cartes if not c.Apparence or c.Apparence == u'Aucune']
        sans_motif = [c for c in cartes
                      if c.MotifCoupeNom == u'Aucun' and c.MotifSurfaceNom == u'Aucun']

        sans_coupe = [c for c in cartes if c.MotifCoupeNom == u'Aucun']
        sans_surface = [c for c in cartes if c.MotifSurfaceNom == u'Aucun']

        self.ApparencesPartagees = self._grouper(
            cartes, lambda carte: carte.Apparence,
            ignorer=(u'', u'Aucune'))
        self.NomsProches = self._grouper(cartes, lambda carte: _cle_nom(carte.Nom),
                                         titre=lambda carte: carte.Nom)
        # Hachures : deux faces, deux regroupements. Deux matériaux qui
        # partagent un motif sont indiscernables sur cette face en vue coupée
        # ou en projection. « Aucun » est écarté — c'est l'absence de motif,
        # comptée par sa propre tuile, pas un motif partagé.
        self.MotifsCoupe = self._grouper(
            cartes, lambda carte: carte.MotifCoupeNom, ignorer=(u'Aucun',),
            apercu=lambda carte: carte.MotifCoupeImage)
        self.MotifsSurface = self._grouper(
            cartes, lambda carte: carte.MotifSurfaceNom, ignorer=(u'Aucun',),
            apercu=lambda carte: carte.MotifSurfaceImage)
        materiaux_en_double = sum(g.Nombre for g in self.ApparencesPartagees)
        motifs_partages = self._ids(self.MotifsCoupe + self.MotifsSurface)

        self._repartir(cartes, non_utilises, sans_classe, sans_apparence)
        self._construire_sections()

        self.Indicateurs = [
            IndicateurVM(total, u'Matériaux', u'dans le modèle'),
            IndicateurVM(len(utilises), u'Utilisés',
                         self._part(len(utilises), total)),
            IndicateurVM(len(non_utilises), u'Non utilisés',
                         u'purgeables', alerte=bool(non_utilises)),
            IndicateurVM(len(sans_instance), u'Sans instance',
                         u'déclarés, jamais posés',
                         alerte=bool(sans_instance)),
            IndicateurVM(materiaux_en_double, u'Apparences dupliquées',
                         u'%d apparence%s partagée%s' % (
                             len(self.ApparencesPartagees),
                             u's' if len(self.ApparencesPartagees) > 1 else u'',
                             u's' if len(self.ApparencesPartagees) > 1 else u''),
                         alerte=bool(self.ApparencesPartagees)),
            IndicateurVM(sum(g.Nombre for g in self.NomsProches),
                         u'Noms proches',
                         u'%d groupe%s à fusionner' % (
                             len(self.NomsProches),
                             u's' if len(self.NomsProches) > 1 else u''),
                         alerte=bool(self.NomsProches)),
            IndicateurVM(len(sans_apparence), u'Sans apparence',
                         u'aucun asset de rendu',
                         alerte=bool(sans_apparence)),
            IndicateurVM(len(sans_classe), u'Sans classe',
                         u'champ « Classe » vide', alerte=bool(sans_classe)),
            IndicateurVM(len(sans_coupe), u'Sans motif de coupe',
                         u'invisibles en vue coupée',
                         alerte=bool(sans_coupe)),
            IndicateurVM(len(sans_surface), u'Sans motif de surface',
                         u'invisibles en projection',
                         alerte=bool(sans_surface)),
            IndicateurVM(len(sans_motif), u'Sans aucun motif',
                         u'ni coupe ni surface', alerte=bool(sans_motif)),
            IndicateurVM(len(motifs_partages), u'Motifs identiques',
                         u'indiscernables sur une face',
                         alerte=bool(motifs_partages)),
        ]
        log(u'audit : {} matériau(x) · {} non utilisé(s) · {} apparence(s) '
            u'partagée(s) · {} groupe(s) de noms proches · {} motif(s) de '
            u'coupe et {} de surface partagés · score {}',
            total, len(non_utilises), len(self.ApparencesPartagees),
            len(self.NomsProches), len(self.MotifsCoupe),
            len(self.MotifsSurface), self.Score)
        for nom in ('Indicateurs', 'ApparencesPartagees', 'NomsProches',
                    'MotifsCoupe', 'MotifsSurface', 'Sections',
                    'Resume', 'ARienASignaler', 'Segments', 'Score',
                    'ScoreDetail', 'ScoreMention', 'ScoreNiveau', 'Torus'):
            self.notify_property(nom)

    # ------------------------------------------------------------------
    # Sections repliables
    # ------------------------------------------------------------------

    #: (titre, explication, nom de l'attribut qui porte les groupes). Les
    #: sections vides ne sont pas construites — l'ordre ici EST l'ordre à
    #: l'écran, et la première section non vide s'ouvre d'office.
    SECTIONS = (
        (u'Apparences partagées',
         u'Même asset de rendu, donc même aspect en vue réaliste. Souvent des '
         u'matériaux à fusionner dans l\'onglet Remplacer.',
         'ApparencesPartagees'),
        (u'Noms proches',
         u'Noms identiques à la casse, aux accents, à la ponctuation ou à un '
         u'« (1) » près.',
         'NomsProches'),
        (u'Motifs de coupe identiques',
         u'Ces matériaux sont indiscernables en vue coupée : même motif de '
         u'coupe, arrière-plan et premier plan compris.',
         'MotifsCoupe'),
        (u'Motifs de surface identiques',
         u'Ces matériaux sont indiscernables en projection : même motif de '
         u'surface.',
         'MotifsSurface'),
    )

    def _construire_sections(self):
        self.Sections = []
        for (titre, explication, attribut) in self.SECTIONS:
            groupes = getattr(self, attribut)
            if not groupes:
                continue
            self.Sections.append(SectionVM(titre, explication, groupes,
                                           deployee=not self.Sections))

    # ------------------------------------------------------------------
    # Anneau de récap + score
    # ------------------------------------------------------------------

    def _repartir(self, cartes, non_utilises, sans_classe, sans_apparence):
        """Range CHAQUE matériau dans une seule part de l'anneau, puis note.

        L'anneau est une partition — sinon les parts ne bouclent pas. Un
        matériau non utilisé QUI EST AUSSI en doublon compte donc comme non
        utilisé : c'est le défaut le plus grave, et c'est celui qui se règle en
        premier (purger avant de fusionner). Les tuiles, elles, comptent chaque
        défaut de son côté — les deux chiffres n'ont pas à coïncider.
        """
        total = len(cartes)
        ids_non_utilises = set(c.Id for c in non_utilises)
        ids_doublons = set(
            c.Id for groupe in (self.ApparencesPartagees + self.NomsProches)
            for c in groupe.Cartes) - ids_non_utilises
        # Fiche incomplète : ni classe ni apparence renseignée. Ne sort pas
        # l'anneau de sa partition (ces matériaux restent « sains » côté
        # usage), c'est un poste de score à part.
        incomplets = set(c.Id for c in sans_classe) | set(c.Id for c in sans_apparence)
        sains = total - len(ids_non_utilises) - len(ids_doublons)

        self.Segments = [
            SegmentVM(u'Sains', sains, total, 'sains',
                      u'utilisés, sans doublon'),
            SegmentVM(u'En doublon', len(ids_doublons), total, 'doublons',
                      u'apparence partagée ou nom voisin'),
            SegmentVM(u'Non utilisés', len(ids_non_utilises), total,
                      'non_utilises', u'purgeables'),
        ]
        self.Torus = (donut_image.torus([(s.Portion, s.Rgb)
                                         for s in self.Segments])
                      if donut_image is not None else None)

        comptes = {u'non_utilises': len(ids_non_utilises),
                   u'doublons': len(ids_doublons),
                   u'incomplets': len(incomplets)}
        perdus = []
        score = 100.0
        for (role, poids, libelle) in self.BAREME:
            if not total or not comptes[role]:
                continue
            perte = poids * comptes[role] / float(total)
            score -= perte
            perdus.append(u'−%d %s' % (round(perte), libelle))
        self.Score = int(round(max(0.0, min(100.0, score)))) if total else 0
        self.ScoreDetail = (u' · '.join(perdus) if perdus
                            else u'aucune pénalité')

    @staticmethod
    def _part(nombre, total):
        return u'%d %%' % round(100.0 * nombre / total) if total else u''

    @staticmethod
    def _ids(groupes):
        """Ids des matériaux figurant dans au moins un de ces groupes."""
        return set(carte.Id for groupe in groupes for carte in groupe.Cartes)

    @staticmethod
    def _grouper(cartes, cle, ignorer=(), titre=None, apercu=None):
        """Groupes de 2 cards ou plus partageant la même clé.

        `titre` : de quoi étiqueter le groupe quand la clé n'est pas lisible
        (le nom normalisé) — on prend celui de la première card.
        `apercu` : vignette à afficher devant le groupe (motif de coupe ou de
        surface), prise sur la première card elle aussi.
        """
        par_cle = {}
        for carte in cartes:
            valeur = cle(carte)
            if not valeur or valeur in ignorer:
                continue
            par_cle.setdefault(valeur, []).append(carte)
        groupes = [GroupeVM(titre(membres[0]) if titre else valeur, membres,
                            apercu=apercu)
                   for (valeur, membres) in par_cle.items() if len(membres) > 1]
        return sorted(groupes, key=lambda g: (-g.Nombre, g.Titre))
