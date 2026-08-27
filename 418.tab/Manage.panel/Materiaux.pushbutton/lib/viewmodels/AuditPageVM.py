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
    from lib.views import donut_image
except Exception:
    try:
        from views import donut_image
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
    """Un lot de matériaux qui se ressemblent : même apparence, ou noms
    voisins. `Titre` est ce qui les rassemble, `Membres` la liste lisible."""

    def __init__(self, titre, cartes):
        super(GroupeVM, self).__init__()
        self.Titre = titre or u'—'
        self.Cartes = list(cartes)
        self.Nombre = len(self.Cartes)
        self.Membres = u' · '.join(carte.Nom for carte in self.Cartes)


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

    # Les sections de détail se replient quand elles sont vides. Booléens
    # plutôt qu'un binding sur `.Count` : c'est une liste Python, on ne parie
    # pas sur l'IList qu'IronPython en expose.
    @property
    def AApparencesPartagees(self):
        return bool(self.ApparencesPartagees)

    @property
    def ANomsProches(self):
        return bool(self.NomsProches)

    @property
    def ARienASignaler(self):
        return not (self.ApparencesPartagees or self.NomsProches)

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

        self.ApparencesPartagees = self._grouper(
            cartes, lambda carte: carte.Apparence,
            ignorer=(u'', u'Aucune'))
        self.NomsProches = self._grouper(cartes, lambda carte: _cle_nom(carte.Nom),
                                         titre=lambda carte: carte.Nom)
        materiaux_en_double = sum(g.Nombre for g in self.ApparencesPartagees)

        self._repartir(cartes, non_utilises, sans_classe, sans_apparence)

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
            IndicateurVM(len(sans_motif), u'Sans motif',
                         u'ni coupe ni surface', alerte=bool(sans_motif)),
        ]
        log(u'audit : {} matériau(x) · {} non utilisé(s) · {} apparence(s) '
            u'partagée(s) · {} groupe(s) de noms proches',
            total, len(non_utilises), len(self.ApparencesPartagees),
            len(self.NomsProches))
        for nom in ('Indicateurs', 'ApparencesPartagees', 'NomsProches',
                    'Resume', 'ARienASignaler', 'AApparencesPartagees',
                    'ANomsProches', 'Segments', 'Score', 'ScoreDetail',
                    'ScoreMention', 'ScoreNiveau', 'Torus'):
            self.notify_property(nom)

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
    def _grouper(cartes, cle, ignorer=(), titre=None):
        """Groupes de 2 cards ou plus partageant la même clé.

        `titre` : de quoi étiqueter le groupe quand la clé n'est pas lisible
        (le nom normalisé) — on prend celui de la première card.
        """
        par_cle = {}
        for carte in cartes:
            valeur = cle(carte)
            if not valeur or valeur in ignorer:
                continue
            par_cle.setdefault(valeur, []).append(carte)
        groupes = [GroupeVM(titre(membres[0]) if titre else valeur, membres)
                   for (valeur, membres) in par_cle.items() if len(membres) > 1]
        return sorted(groupes, key=lambda g: (-g.Nombre, g.Titre))
