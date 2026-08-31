# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Le repérage des coupes : ce qu'un plan de repérage (PDR) doit MASQUER.
#
# Rien de Revit ici — une règle en entrée, un arbre booléen en sortie.
# `FiltresService` traduit cet arbre en objets Revit ; tout ce qui se DÉCIDE se
# décide ici, donc hors Revit, donc testable.
#
# Une règle est VIVANTE : elle désigne les coupes par leur place (feuille, jeu),
# jamais par leur nom, et Revit la réévalue seul. Voir
# docs/adr/0001-regles-de-reperage-vivantes.md — le mode « Coupes choisies »
# est la seule exception, et il est gelé exprès.
#
# L'arbre est écrit du point de vue du FILTRE, qui sélectionne ce qui disparaît.
# Il faut donc nier ce que l'on veut voir :
#
#     visible = ( base OU pas-encore-posée OU ajouts… ) ET ( pas un retrait… )
#     masqué  = ( ¬base ET posée ET ¬ajouts… )         OU ( c'est un retrait… )
#
# D'où un OU en tête dès qu'il y a un retrait : c'est ce qui oblige le service
# à construire un `LogicalOrFilter` et pas une simple liste de règles.

try:
    from core.sanitize import sanitize_revit_name
except Exception:
    try:
        from lib.core.sanitize import sanitize_revit_name
    except Exception:
        sanitize_revit_name = None

#: Les propriétés du repère sur lesquelles une règle s'exprime. Ce sont des
#: noms abstraits : c'est le service qui les fait correspondre aux paramètres
#: Revit (numéro de feuille, jeu de feuilles, nom de la vue).
FEUILLE = 'feuille'
JEU = 'jeu'
NOM = 'nom'

#: Opérateurs de comparaison d'une feuille de l'arbre.
EGAL = '='
DIFFERENT = '!='
PAS_VIDE = 'pas_vide'

MODE_FEUILLE = 'feuille'
MODE_JEU = 'jeu'
MODE_CHOIX = 'choix'
MODE_AUCUN = 'aucun'

#: `cle` est ce qui se persiste, `libelle` ce qui s'affiche. Le libellé parle
#: du PLAN, pas de l'utilisateur (« Sa feuille », pas « ma feuille ») : c'est
#: une colonne qu'on lit sur 40 lignes, hors contexte.
MODES = (
    (MODE_FEUILLE, u'Sa feuille'),
    (MODE_JEU, u'Son jeu'),
    (MODE_CHOIX, u'Coupes choisies'),
    (MODE_AUCUN, u'Non géré'),
)

#: Entrée de menu du mode `jeu` qui veut dire « celui du plan », par opposition
#: à un jeu nommé. Une règle `jeu` sans cible EST ce cas : le libellé n'est
#: qu'un affichage, il n'est jamais persisté.
JEU_DU_PLAN = u'— le jeu du plan —'

PREFIXE_FILTRE = u'418_PDR_'


class Regle(object):
    """L'intention d'UN plan de repérage.

    - `mode`     : l'une des clés de `MODES`.
    - `cible`    : le jeu visé en mode `jeu`. Vide = le jeu du plan lui-même,
                   ce qui suit le plan s'il change de feuille.
    - `ajouts`   : noms de coupes visibles EN PLUS de la base. En mode `choix`,
                   c'est la liste des coupes retenues — la base ne montre rien.
    - `retraits` : noms de coupes masquées malgré la base. Ce sont eux qui
                   coûtent un OU logique.

    Un ajout ou un retrait est GELÉ : il nomme une coupe, donc il casse si elle
    est renommée. La base, elle, reste vivante.
    """

    def __init__(self, mode=MODE_AUCUN, cible=None, ajouts=None, retraits=None):
        self.mode = mode if mode in dict(MODES) else MODE_AUCUN
        self.cible = cible or None
        self.ajouts = _noms(ajouts)
        self.retraits = _noms(retraits)

    def en_dict(self):
        """Ce qui part en Extensible Storage. Les clés vides sont omises : le
        stockage est un champ texte du document, autant qu'il reste lisible."""
        brut = {'mode': self.mode}
        for (cle, valeur) in (('cible', self.cible), ('ajouts', self.ajouts),
                              ('retraits', self.retraits)):
            if valeur:
                brut[cle] = valeur if isinstance(valeur, list) else valeur
        return brut

    @classmethod
    def depuis_dict(cls, brut):
        brut = brut or {}
        return cls(brut.get('mode'), brut.get('cible'),
                   brut.get('ajouts'), brut.get('retraits'))

    def est_gelee(self):
        """Vrai si la règle nomme au moins une coupe — donc si un renommage la
        casse. Sert à n'avertir que là où il y a un risque."""
        return bool(self.ajouts or self.retraits or self.mode == MODE_CHOIX)

    def noms_cites(self):
        """Les noms de coupes que la règle nomme, dans l'ordre d'affichage.
        C'est là-dessus que la détection de dérive travaille."""
        return list(self.ajouts) + list(self.retraits)


def _noms(valeurs):
    """Liste de noms sans vide ni doublon, ordre d'origine conservé."""
    vus = []
    for valeur in (valeurs or []):
        if valeur and valeur not in vus:
            vus.append(valeur)
    return vus


# ----------------------------------------------------------------------
# L'arbre
# ----------------------------------------------------------------------

def _et(noeuds):
    noeuds = [n for n in noeuds if n]
    if not noeuds:
        return None
    return noeuds[0] if len(noeuds) == 1 else ('et', noeuds)


def _ou(noeuds):
    noeuds = [n for n in noeuds if n]
    if not noeuds:
        return None
    return noeuds[0] if len(noeuds) == 1 else ('ou', noeuds)


def masque(regle, plan):
    """L'arbre de ce que le filtre du plan doit sélectionner (donc masquer).

    `plan` : {'nom', 'feuille', 'jeu'}. `None` en retour = ne rien masquer,
    donc aucun filtre à poser. C'est le retour du mode « Non géré », mais AUSSI
    celui d'un mode inapplicable — un plan hors feuille en mode « Sa feuille »,
    ou sans jeu en mode « Son jeu ». Ne rien masquer est le seul repli sûr :
    faire disparaître tous les repères d'un plan parce qu'une règle ne s'applique
    pas serait un dégât silencieux.
    """
    if regle.mode == MODE_AUCUN:
        return None

    principale = []
    if regle.mode == MODE_FEUILLE:
        feuille = plan.get('feuille')
        if not feuille:
            return None
        principale.append((FEUILLE, DIFFERENT, feuille))
    elif regle.mode == MODE_JEU:
        jeu = regle.cible or plan.get('jeu')
        if not jeu:
            return None
        principale.append((JEU, DIFFERENT, jeu))
    # MODE_CHOIX : pas de base. Tout est masqué, sauf les ajouts.

    # Une coupe pas encore posée sur une feuille reste visible : c'est du
    # travail en cours, la cacher est le bug qu'on découvre à l'impression.
    principale.append((FEUILLE, PAS_VIDE, None))
    for nom in regle.ajouts:
        principale.append((NOM, DIFFERENT, nom))

    branches = [_et(principale)]
    for nom in regle.retraits:
        branches.append((NOM, EGAL, nom))
    return _ou(branches)


def parametres_utilises(arbre):
    """Les propriétés (`FEUILLE`, `JEU`, `NOM`) que cet arbre interroge.

    Le service en a besoin avant d'écrire : si le modèle ne sait pas filtrer
    « Jeu de feuilles », autant le dire avant de tenter la transaction.
    """
    if not arbre:
        return []
    if arbre[0] in ('et', 'ou'):
        vus = []
        for enfant in arbre[1]:
            for param in parametres_utilises(enfant):
                if param not in vus:
                    vus.append(param)
        return vus
    return [arbre[0]]


# ----------------------------------------------------------------------
# Ce qui s'affiche et ce qui se nomme
# ----------------------------------------------------------------------

def phrase(regle, plan):
    """La règle en toutes lettres — l'aperçu de l'outil.

    Aucun compte de repères : une règle vivante change toute seule, un chiffre
    serait vrai à l'affichage et faux le lendemain.
    """
    if regle.mode == MODE_AUCUN:
        return u'affichage natif de Revit'

    if regle.mode == MODE_FEUILLE:
        feuille = plan.get('feuille')
        if not feuille:
            return u'⚠ ce plan n\'est sur aucune feuille'
        base = u'les coupes de la feuille %s' % feuille
    elif regle.mode == MODE_JEU:
        jeu = regle.cible or plan.get('jeu')
        if not jeu:
            return u'⚠ la feuille de ce plan n\'est dans aucun jeu'
        base = u'les coupes du jeu %s' % jeu
    else:
        base = (u'%d coupe%s choisie%s' % (len(regle.ajouts),
                                           _s(regle.ajouts), _s(regle.ajouts))
                if regle.ajouts else u'⚠ aucune coupe choisie')

    morceaux = [base]
    if regle.ajouts and regle.mode != MODE_CHOIX:
        morceaux.append(u'plus %s' % u', '.join(regle.ajouts))
    if regle.retraits:
        morceaux.append(u'sauf %s' % u', '.join(regle.retraits))
    return u', '.join(morceaux)


def _s(liste):
    return u's' if len(liste) > 1 else u''


def nom_de_filtre(regle, plan):
    """Le nom du filtre à poser, DÉDUIT DE SON CONTENU.

    Deux plans d'accord partagent donc le même filtre sans se concerter : 40
    plans du jeu PC laissent un filtre, pas quarante — que l'onglet Audit
    signalerait sinon en doublons, l'outil fabriquant les défauts qu'il dénonce.

    Dès qu'une règle cite des coupes, elle est propre à son plan et le filtre
    prend le nom du plan : mutualiser deux listes de noms qui coïncident
    aujourd'hui ferait qu'éditer un plan modifierait celui du voisin.
    """
    if regle.mode == MODE_AUCUN:
        return None
    if regle.ajouts or regle.retraits or regle.mode == MODE_CHOIX:
        return _nom(u'Plan_%s' % plan.get('nom'))
    if regle.mode == MODE_FEUILLE:
        feuille = plan.get('feuille')
        return _nom(u'Feuille_%s' % feuille) if feuille else None
    jeu = regle.cible or plan.get('jeu')
    return _nom(u'Jeu_%s' % jeu) if jeu else None


def _nom(suffixe):
    brut = PREFIXE_FILTRE + suffixe
    return sanitize_revit_name(brut) if sanitize_revit_name else brut


# ----------------------------------------------------------------------
# Contrôle exécutable : python lib/services/reperage.py
# ----------------------------------------------------------------------

def demo():
    plan = {'nom': u'PDR RDC', 'feuille': u'A01', 'jeu': u'PC'}
    nu = {'nom': u'PDR Détail', 'feuille': u'', 'jeu': u''}

    # Non géré : aucun filtre, donc rien à masquer.
    assert masque(Regle(MODE_AUCUN), plan) is None

    # Sa feuille : une seule comparaison vivante, plus la clause « pas encore
    # posée ». Aucun nom de coupe nulle part — c'est tout l'enjeu.
    assert masque(Regle(MODE_FEUILLE), plan) == (
        'et', [(FEUILLE, DIFFERENT, u'A01'), (FEUILLE, PAS_VIDE, None)])

    # Son jeu, puis un jeu nommé.
    assert masque(Regle(MODE_JEU), plan) == (
        'et', [(JEU, DIFFERENT, u'PC'), (FEUILLE, PAS_VIDE, None)])
    assert masque(Regle(MODE_JEU, u'DCE'), plan) == (
        'et', [(JEU, DIFFERENT, u'DCE'), (FEUILLE, PAS_VIDE, None)])

    # Mode inapplicable -> ne rien masquer, jamais tout masquer.
    assert masque(Regle(MODE_FEUILLE), nu) is None
    assert masque(Regle(MODE_JEU), nu) is None
    assert masque(Regle(MODE_JEU, u'PC'), nu) is not None   # jeu nommé : ok

    # Un ajout reste un ET : il s'empile dans la branche principale.
    assert masque(Regle(MODE_FEUILLE, ajouts=[u'Coupe ZZ']), plan) == (
        'et', [(FEUILLE, DIFFERENT, u'A01'), (FEUILLE, PAS_VIDE, None),
               (NOM, DIFFERENT, u'Coupe ZZ')])

    # Un retrait force le OU en tête — la raison d'être du LogicalOrFilter.
    assert masque(Regle(MODE_FEUILLE, retraits=[u'Coupe AA']), plan) == (
        'ou', [('et', [(FEUILLE, DIFFERENT, u'A01'),
                       (FEUILLE, PAS_VIDE, None)]),
               (NOM, EGAL, u'Coupe AA')])

    # Coupes choisies : pas de base, tout est masqué sauf les coupes nommées
    # (et celles qui ne sont pas encore posées).
    assert masque(Regle(MODE_CHOIX, ajouts=[u'Coupe AA', u'Coupe BB']), plan) == (
        'et', [(FEUILLE, PAS_VIDE, None), (NOM, DIFFERENT, u'Coupe AA'),
               (NOM, DIFFERENT, u'Coupe BB')])
    # Aucune coupe choisie : tout ce qui est posé disparaît. C'est cohérent,
    # et c'est à l'interface de le crier.
    assert masque(Regle(MODE_CHOIX), plan) == (FEUILLE, PAS_VIDE, None)

    # Les paramètres interrogés, pour vérifier la filtrabilité avant d'écrire.
    assert parametres_utilises(masque(Regle(MODE_JEU), plan)) == [JEU, FEUILLE]
    assert parametres_utilises(
        masque(Regle(MODE_FEUILLE, retraits=[u'X']), plan)) == [FEUILLE, NOM]
    assert parametres_utilises(None) == []

    # Aperçu en toutes lettres, jamais un compte.
    assert phrase(Regle(MODE_AUCUN), plan) == u'affichage natif de Revit'
    assert phrase(Regle(MODE_FEUILLE), plan) == u'les coupes de la feuille A01'
    assert phrase(Regle(MODE_JEU), plan) == u'les coupes du jeu PC'
    assert phrase(Regle(MODE_FEUILLE, retraits=[u'Coupe AA']), plan) == (
        u'les coupes de la feuille A01, sauf Coupe AA')
    assert phrase(Regle(MODE_JEU, ajouts=[u'Coupe ZZ'],
                        retraits=[u'Coupe AA']), plan) == (
        u'les coupes du jeu PC, plus Coupe ZZ, sauf Coupe AA')
    assert phrase(Regle(MODE_CHOIX, ajouts=[u'A', u'B']), plan) == u'2 coupes choisies'
    assert phrase(Regle(MODE_CHOIX), plan) == u'⚠ aucune coupe choisie'
    assert phrase(Regle(MODE_FEUILLE), nu) == u'⚠ ce plan n\'est sur aucune feuille'

    # Nommage par contenu : deux plans du même jeu partagent leur filtre, deux
    # plans de feuilles différentes non.
    autre = {'nom': u'PDR R+1', 'feuille': u'A02', 'jeu': u'PC'}
    assert nom_de_filtre(Regle(MODE_JEU), plan) == u'418_PDR_Jeu_PC'
    assert nom_de_filtre(Regle(MODE_JEU), autre) == u'418_PDR_Jeu_PC'
    assert nom_de_filtre(Regle(MODE_FEUILLE), plan) == u'418_PDR_Feuille_A01'
    assert nom_de_filtre(Regle(MODE_FEUILLE), autre) == u'418_PDR_Feuille_A02'
    # Dès qu'une coupe est citée, le filtre est propre au plan.
    assert nom_de_filtre(Regle(MODE_FEUILLE, retraits=[u'Coupe AA']),
                         plan) == u'418_PDR_Plan_PDR RDC'
    assert nom_de_filtre(Regle(MODE_CHOIX, ajouts=[u'A']),
                         plan) == u'418_PDR_Plan_PDR RDC'
    assert nom_de_filtre(Regle(MODE_AUCUN), plan) is None
    assert nom_de_filtre(Regle(MODE_FEUILLE), nu) is None

    # Aller-retour de persistance, et repli sur « Non géré » si le mode est
    # inconnu (une règle écrite par une version ultérieure de l'outil).
    ronde = Regle.depuis_dict(
        Regle(MODE_JEU, u'PC', [u'Z'], [u'A']).en_dict())
    assert (ronde.mode, ronde.cible, ronde.ajouts, ronde.retraits) == (
        MODE_JEU, u'PC', [u'Z'], [u'A'])
    assert Regle.depuis_dict({'mode': 'nawak'}).mode == MODE_AUCUN
    assert Regle(MODE_FEUILLE).en_dict() == {'mode': MODE_FEUILLE}

    # Doublons et vides écartés à la construction.
    assert Regle(MODE_CHOIX, ajouts=[u'A', u'', u'A', None]).ajouts == [u'A']

    assert Regle(MODE_FEUILLE).est_gelee() is False
    assert Regle(MODE_FEUILLE, retraits=[u'A']).est_gelee() is True
    assert Regle(MODE_CHOIX).est_gelee() is True
    assert Regle(MODE_JEU, u'PC', [u'Z'], [u'A']).noms_cites() == [u'Z', u'A']

    print(u'reperage : OK')


if __name__ == '__main__':
    demo()
