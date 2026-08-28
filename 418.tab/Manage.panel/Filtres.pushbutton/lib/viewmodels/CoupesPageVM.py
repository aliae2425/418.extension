# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    from lib.ui.helpers.RelayCommand import RelayCommand

try:
    from lib.services import reperage
except Exception:
    from services import reperage

# Libellés d'affichage des `ViewType` listés par l'onglet.
_LIBELLES = {'Section': u'Coupe', 'Elevation': u'Élévation'}


class TypeVM(BaseViewModel):
    """Une entrée du menu « type de vue des plans de repérage »."""

    def __init__(self, ident, nom):
        super(TypeVM, self).__init__()
        self.Id = ident
        self.Nom = nom


class ModeVM(BaseViewModel):
    """Une entrée du menu de mode d'une règle."""

    def __init__(self, cle, libelle):
        super(ModeVM, self).__init__()
        self.Cle = cle
        self.Libelle = libelle


class CibleVM(BaseViewModel):
    """Une case à cocher : un plan de repérage, dans une règle « spécifique »."""

    def __init__(self, nom, coche, au_changement):
        super(CibleVM, self).__init__()
        self.Nom = nom
        self._coche = bool(coche)
        self._au_changement = au_changement

    @property
    def Coche(self):
        return self._coche

    @Coche.setter
    def Coche(self, valeur):
        valeur = bool(valeur)
        if valeur != self._coche:
            self._coche = valeur
            self.notify_property('Coche')
            self._au_changement()

    def regler(self, valeur):
        """Coche ou décoche SANS prévenir la règle : sert quand c'est elle qui
        mène (changement de mode), elle se notifie déjà elle-même."""
        self._coche = bool(valeur)
        self.notify_property('Coche')


class RegleVM(BaseViewModel):
    """Une règle d'une coupe : un mode, et la cible que ce mode demande.

    Enveloppe un `reperage.Regle` et le modifie en place — c'est ce `Regle`
    qui part à la résolution et à la persistance, la vue n'en garde pas de
    copie.

    Les trois éditeurs de cible (menu de jeu, menu de plan, cases) sont
    toujours construits ; c'est un DataTrigger sur `Mode` qui n'en montre
    qu'un. Moins de code qu'un rechargement à chaque changement de mode, et
    l'utilisateur retrouve ses cases s'il fait un aller-retour.
    """

    def __init__(self, regle, ligne):
        super(RegleVM, self).__init__()
        self._regle = regle
        self._ligne = ligne
        self.Modes = [ModeVM(cle, libelle) for (cle, libelle) in reperage.MODES]
        self.Cibles = [CibleVM(nom, nom in regle.cibles, self._change)
                       for nom in ligne.plans()]
        self.Retirer = RelayCommand(lambda _: ligne.retirer(self))

    # -- ce que la résolution consomme ------------------------------------

    def regle(self):
        return self._regle

    # -- mode --------------------------------------------------------------

    @property
    def Mode(self):
        """Clé ASCII du mode : c'est sur ELLE que les DataTrigger de la page
        montrent le bon éditeur, jamais sur le libellé affiché."""
        return self._regle.mode

    @property
    def ModeChoisi(self):
        for mode in self.Modes:
            if mode.Cle == self._regle.mode:
                return mode
        return self.Modes[0]

    @ModeChoisi.setter
    def ModeChoisi(self, valeur):
        cle = getattr(valeur, 'Cle', None)
        if not cle or cle == self._regle.mode:
            return
        # Les cibles d'un mode `jeu` sont des noms de JEUX, celles des deux
        # autres des noms de PLANS : elles ne se transposent pas, on les
        # jette. `plan` -> `specifique` les garde, elles parlent la même
        # langue.
        if u'jeu' in (cle, self._regle.mode):
            self._regle.cibles = []
        self._regle.mode = cle
        # Les cases sont construites une fois pour toutes ; les remettre
        # d'accord avec les cibles AVANT `_change`, qui en mode `specifique`
        # relit les cases et écraserait la cible choisie en mode `plan`.
        for cible in self.Cibles:
            cible.regler(cible.Nom in self._regle.cibles)
        for nom in ('Mode', 'ModeChoisi', 'JeuChoisi', 'PlanChoisi'):
            self.notify_property(nom)
        self._change()

    # -- cible : par jeu ---------------------------------------------------

    @property
    def Jeux(self):
        return self._ligne.jeux()

    @property
    def JeuChoisi(self):
        return self._regle.cibles[0] if self._regle.cibles else reperage.JEU_DE_LA_COUPE

    @JeuChoisi.setter
    def JeuChoisi(self, valeur):
        if not valeur or valeur == reperage.JEU_DE_LA_COUPE:
            self._regle.cibles = []
        else:
            self._regle.cibles = [valeur]
        self.notify_property('JeuChoisi')
        self._change()

    # -- cible : un plan ---------------------------------------------------

    @property
    def Plans(self):
        return self._ligne.plans()

    @property
    def PlanChoisi(self):
        return self._regle.cibles[0] if self._regle.cibles else None

    @PlanChoisi.setter
    def PlanChoisi(self, valeur):
        self._regle.cibles = [valeur] if valeur else []
        self.notify_property('PlanChoisi')
        self._change()

    # -- cible : plusieurs plans ------------------------------------------

    def _relire_cases(self):
        self._regle.cibles = [c.Nom for c in self.Cibles if c.Coche]

    # -- rendu -------------------------------------------------------------

    @property
    def Resume(self):
        vises = reperage.pdr_vises(self._regle, self._ligne.coupe(),
                                   self._ligne.pdrs())
        if not vises:
            return u'ne désigne aucun plan'
        return u'%d plan%s : %s' % (len(vises), u's' if len(vises) > 1 else u'',
                                    u' · '.join(p['nom'] for p in vises))

    def _change(self):
        if self._regle.mode == u'specifique':
            self._relire_cases()
        self.notify_property('Resume')
        self._ligne.change()


class CoupeRowVM(BaseViewModel):
    """Une coupe ou une élévation, et ses règles de repérage."""

    def __init__(self, coupe, page):
        super(CoupeRowVM, self).__init__()
        self.Id = coupe.get('id')
        self._coupe = coupe
        self._page = page
        self.Regles = [RegleVM(regle, self) for regle in page.regles_de(coupe)]
        self.Ajouter = RelayCommand(lambda _: self.ajouter())
        self.Effacer = RelayCommand(lambda _: self.effacer())

    # -- ce que les règles interrogent ------------------------------------

    def coupe(self):
        return self._coupe

    def pdrs(self):
        return self._page.Pdrs

    def plans(self):
        return self._page.Plans

    def jeux(self):
        return self._page.Jeux

    # -- affichage ---------------------------------------------------------

    @property
    def Nom(self):
        return self._coupe.get('nom')

    @property
    def TypeVue(self):
        type_vue = self._coupe.get('type')
        return _LIBELLES.get(type_vue, type_vue)

    @property
    def Origine(self):
        feuille = self._coupe.get('feuille')
        if not feuille:
            return u'sur aucune feuille'
        jeu = self._coupe.get('jeu')
        return u'feuille %s · %s' % (feuille, jeu or u'sans jeu')

    @property
    def Resume(self):
        """Ce que les règles donnent, en une ligne, dans l'en-tête de la vue.

        Sans règle, la coupe n'est pas contrainte : elle reste sur tous les
        plans. Le dire explicitement évite de lire « 0 » comme un oubli.
        """
        if not self.Regles:
            return u'aucune règle · visible sur tous les plans'
        noms = reperage.visibles_sur(self.etat(), self.pdrs())
        if not noms:
            return u'masquée sur tous les plans'
        return u'visible sur %d plan%s' % (len(noms),
                                           u's' if len(noms) > 1 else u'')

    @property
    def ARegles(self):
        return bool(self.Regles)

    # -- édition -----------------------------------------------------------

    def etat(self):
        """La coupe telle que `reperage` l'attend : dict + ses `Regle`."""
        return dict(self._coupe,
                    regles=[vm.regle() for vm in self.Regles])

    def ajouter(self):
        """Nouvelle règle, calée sur le défaut de la coupe.

        Partir du défaut plutôt que d'une règle vide : dans le cas courant
        (« aussi sur le plan de ma feuille ») il n'y a plus rien à régler.
        """
        self.Regles.append(RegleVM(self._page.defaut(self._coupe), self))
        self.change()

    def retirer(self, regle_vm):
        if regle_vm in self.Regles:
            self.Regles.remove(regle_vm)
            self.change()

    def effacer(self):
        self.Regles = []
        self.change()

    def change(self):
        for nom in ('Regles', 'Resume', 'ARegles'):
            self.notify_property(nom)


class CoupesPageVM(BaseViewModel):
    """Onglet Coupes — le repérage, coupe par coupe.

    Un plan de repérage (PDR) est une vue en plan du TYPE mémorisé ici : le
    même réglage que le prototype de `origin/section-filter`, gardé parce
    qu'il désigne d'un coup tous les PDR du projet sans rien cocher.

    Les règles sont persistées (`UserConfig`), rangées par titre de document.
    Elles ne se relisent PAS depuis les filtres posés : une liste de
    `NotEquals` ne dit pas de quel mode elle vient, l'intention n'y survit
    pas.
    """

    CLE_TYPE = 'type_plan_reperage'
    CLE_REGLES = 'reperage'

    def __init__(self, coupes=None, service=None, config=None):
        super(CoupesPageVM, self).__init__()
        self.Coupes = list(coupes or [])
        self._service = service
        self._config = config
        self._regles = {}
        self._type = None
        self.Types = []
        self.Pdrs = []
        self.Lignes = []
        self.charger()

    # ------------------------------------------------------------------
    # Chargement
    # ------------------------------------------------------------------

    def charger(self):
        self.Types = [TypeVM(t['id'], t['nom'])
                      for t in (self._service.types_de_plan()
                                if self._service else [])]
        self._type = self._type_memorise()
        self._regles = self._lire_regles()
        self._recharger_pdr()

    def _recharger_pdr(self):
        self.Pdrs = (self._service.collecter_pdr(self._type)
                     if (self._service and self._type) else [])
        self.Lignes = [CoupeRowVM(coupe, self) for coupe in self.Coupes]
        for nom in ('Types', 'TypeChoisi', 'Pdrs', 'Plans', 'Jeux', 'Lignes',
                    'Resume', 'AucunPlan'):
            self.notify_property(nom)

    def _type_memorise(self):
        """Id du type de vue des PDR, s'il est encore dans le modèle.

        Un id de type ne survit pas au changement de projet : on ne garde le
        réglage que s'il désigne encore quelque chose, sinon le menu repart
        vide plutôt que de filtrer sur un type absent.
        """
        if self._config is None:
            return None
        try:
            memorise = int(self._config.get(self.CLE_TYPE, 0) or 0)
        except Exception:
            return None
        return memorise if memorise in [t.Id for t in self.Types] else None

    # ------------------------------------------------------------------
    # Réglage du type de vue
    # ------------------------------------------------------------------

    @property
    def TypeChoisi(self):
        for type_vm in self.Types:
            if type_vm.Id == self._type:
                return type_vm
        return None

    @TypeChoisi.setter
    def TypeChoisi(self, valeur):
        ident = getattr(valeur, 'Id', None)
        if ident is None or ident == self._type:
            return
        self._type = ident
        if self._config is not None:
            try:
                self._config.set(self.CLE_TYPE, ident)
            except Exception:
                pass
        self._recharger_pdr()

    # ------------------------------------------------------------------
    # Listes de choix
    # ------------------------------------------------------------------

    @property
    def Plans(self):
        return [p['nom'] for p in self.Pdrs]

    @property
    def Jeux(self):
        """Les jeux de feuilles connus, « celui de la coupe » en tête.

        Tirés des coupes ET des plans : un jeu qui n'a pas de PDR reste
        proposable (le repérage se règle souvent avant que les plans soient
        posés sur les feuilles).
        """
        noms = set(c.get('jeu') for c in self.Coupes)
        noms.update(p.get('jeu') for p in self.Pdrs)
        return [reperage.JEU_DE_LA_COUPE] + sorted(n for n in noms if n)

    # ------------------------------------------------------------------
    # Règles
    # ------------------------------------------------------------------

    def regles_de(self, coupe):
        """Les règles persistées de cette coupe, ou son défaut au premier
        passage. Une liste VIDE persistée reste vide — l'utilisateur a
        retiré ses règles, ce n'est pas un « jamais réglé »."""
        nom = coupe.get('nom')
        if nom in self._regles:
            return self._regles[nom]
        defaut = self.defaut(coupe)
        return [defaut] if defaut is not None else []

    def defaut(self, coupe):
        """La règle proposée d'office : le plan de repérage de sa feuille.

        C'est le comportement du prototype — un PDR ne montre que les coupes
        de sa propre feuille — mais posé comme un défaut modifiable, pas
        comme la seule option. Sans PDR sur sa feuille, on retombe sur « par
        jeu », qui ne désigne rien tant qu'aucun plan n'est posé.
        """
        feuille = coupe.get('feuille')
        for pdr in self.Pdrs:
            if feuille and pdr.get('feuille') == feuille:
                return reperage.Regle(u'plan', [pdr['nom']])
        return reperage.Regle(u'jeu')

    def etat(self):
        return [ligne.etat() for ligne in self.Lignes]

    def enregistrer(self):
        """Persiste les règles de TOUTES les coupes listées.

        Y compris les listes vides et les défauts : ce qui est à l'écran est
        ce qui est enregistré, sans quoi un défaut effacé reviendrait à
        l'ouverture suivante.
        """
        if self._config is None:
            return
        brut = self._brut()
        brut[self._titre()] = dict(
            (ligne.Nom, [vm.regle().en_dict() for vm in ligne.Regles])
            for ligne in self.Lignes)
        try:
            self._config.set(self.CLE_REGLES, json.dumps(brut))
        except Exception:
            pass

    def _brut(self):
        if self._config is None:
            return {}
        try:
            charge = json.loads(self._config.get(self.CLE_REGLES, u'{}') or u'{}')
        except Exception:
            return {}
        return charge if isinstance(charge, dict) else {}

    def _lire_regles(self):
        par_coupe = self._brut().get(self._titre()) or {}
        if not isinstance(par_coupe, dict):
            return {}
        return dict((nom, [reperage.Regle.depuis_dict(d) for d in (liste or [])])
                    for (nom, liste) in par_coupe.items())

    def _titre(self):
        try:
            return self._service.titre_document() or u'—'
        except Exception:
            return u'—'

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    def appliquer(self):
        """Écrit le repérage dans le modèle. Retourne les messages du service."""
        self.enregistrer()
        if self._service is None:
            return [u'Service indisponible : rien n\'a été écrit.']
        if not self.Pdrs:
            return [u'Aucun plan de repérage : choisis le type de vue qui '
                    u'les désigne, en haut de l\'onglet.']
        visibles = reperage.resoudre(self.etat(), self.Pdrs)
        cibles = [dict(pdr, visibles=visibles.get(pdr['nom'], []))
                  for pdr in self.Pdrs]
        return self._service.appliquer_reperage(cibles)

    # ------------------------------------------------------------------
    # En-tête
    # ------------------------------------------------------------------

    @property
    def TitrePage(self):
        return u'Repérage des coupes'

    @property
    def Resume(self):
        return u'%d vue%s · %d plan%s de repérage' % (
            len(self.Lignes), u's' if len(self.Lignes) > 1 else u'',
            len(self.Pdrs), u's' if len(self.Pdrs) > 1 else u'')

    @property
    def AucunPlan(self):
        return not self.Pdrs
