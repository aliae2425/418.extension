# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Onglet « Repérage des coupes » — maître/détail.
#
# À gauche, TOUS les plans du modèle dans la liste du socle (recherche,
# multi-sélection, sélections préfabriquées). À droite, l'éditeur de règle, qui
# écrit sur TOUTE la sélection.
#
# Aucun plan n'est géré d'office : l'outil ne décide pas à la place de
# l'utilisateur. Ce que ça coûte en clics, les sélections préfabriquées le
# rendent — « du type Plan de repérage » puis « Son jeu », et le projet est
# réglé en deux gestes qui se lisent à voix haute.

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from ui.base.SelectionPageVM import SelectionPageVM
except Exception:
    from lib.ui.base.SelectionPageVM import SelectionPageVM

try:
    from ui.base.SelectionItemVM import SelectionItemVM
except Exception:
    from lib.ui.base.SelectionItemVM import SelectionItemVM

try:
    from ui.helpers.RelayCommand import RelayCommand
except Exception:
    from lib.ui.helpers.RelayCommand import RelayCommand

try:
    from core import text_filter
except Exception:
    from lib.core import text_filter

try:
    from lib.services import reperage
except Exception:
    from services import reperage


class ModeVM(BaseViewModel):
    """Une entrée du menu de mode."""

    def __init__(self, cle, libelle, disponible=True, raison=u''):
        super(ModeVM, self).__init__()
        self.Cle = cle
        self.Libelle = libelle
        self.Disponible = bool(disponible)
        self.Raison = raison


class CoupeItemVM(BaseViewModel):
    """Une coupe dans l'éditeur, avec ses deux forçages.

    `Forcee` et `Exclue` sont exclusifs et pilotés par deux cases : c'est la
    forme la plus courte qui couvre les trois besoins — les ajouts, les
    retraits, et la liste du mode « Coupes choisies », où seul `Forcee` compte.
    Deux cases plutôt qu'un contrôle à trois états : aucun convertisseur WPF à
    écrire.
    """

    def __init__(self, coupe, au_changement):
        super(CoupeItemVM, self).__init__()
        self.Nom = coupe.get('nom')
        feuille = coupe.get('feuille')
        self.Origine = (u'feuille %s · %s' % (feuille, coupe.get('jeu') or u'sans jeu')
                        if feuille else u'sur aucune feuille')
        self._forcee = False
        self._exclue = False
        self._au_changement = au_changement

    @property
    def Forcee(self):
        return self._forcee

    @Forcee.setter
    def Forcee(self, valeur):
        valeur = bool(valeur)
        if valeur == self._forcee:
            return
        self._forcee = valeur
        if valeur and self._exclue:
            self._exclue = False
            self.notify_property('Exclue')
        self.notify_property('Forcee')
        self._au_changement()

    @property
    def Exclue(self):
        return self._exclue

    @Exclue.setter
    def Exclue(self, valeur):
        valeur = bool(valeur)
        if valeur == self._exclue:
            return
        self._exclue = valeur
        if valeur and self._forcee:
            self._forcee = False
            self.notify_property('Forcee')
        self.notify_property('Exclue')
        self._au_changement()

    def regler(self, forcee, exclue):
        """Pose les deux états SANS prévenir l'éditeur : sert quand c'est lui
        qui mène (changement de sélection), il se notifie déjà lui-même."""
        self._forcee = bool(forcee)
        self._exclue = bool(exclue)
        self.notify_property('Forcee')
        self.notify_property('Exclue')


class PlanItemVM(SelectionItemVM):
    """Une ligne de la liste de gauche : un plan, sa règle en toutes lettres."""

    def __init__(self, plan, au_basculement):
        feuille = plan.get('feuille')
        super(PlanItemVM, self).__init__(
            plan['uid'],
            u'%s · %s' % (feuille, plan.get('jeu') or u'sans jeu') if feuille
            else u'hors feuille',
            plan['nom'], False, au_basculement, est_identifiant=False)
        self.Plan = plan
        self._phrase = u''
        self._geree = False
        self._derive = u''

    @property
    def Phrase(self):
        return self._phrase

    @property
    def Geree(self):
        return self._geree

    @property
    def Derive(self):
        return self._derive

    @property
    def ADerive(self):
        return bool(self._derive)

    def poser_regle(self, regle):
        self._geree = regle is not None and regle.mode != reperage.MODE_AUCUN
        self._phrase = reperage.phrase(
            regle if regle is not None else reperage.Regle(), self.Plan)
        for nom in ('Phrase', 'Geree'):
            self.notify_property(nom)

    def poser_derive(self, texte):
        self._derive = texte or u''
        for nom in ('Derive', 'ADerive'):
            self.notify_property(nom)


class ReperagePageVM(BaseViewModel):
    """Le repérage, plan par plan.

    Les règles vivent dans le DOCUMENT (Extensible Storage), rangées par
    `UniqueId` de plan — un plan renommé garde la sienne. Elles ne se relisent
    PAS depuis les filtres posés : une liste de comparaisons ne dit pas de quel
    mode elle vient, l'intention n'y survit pas.

    L'éditeur écrit sur toute la sélection. Quand les plans sélectionnés n'ont
    pas la même règle, il affiche celle du premier et le signale ; toucher un
    contrôle aligne alors tout le monde. C'est le comportement d'un inspecteur
    de propriétés, et il est prévisible — l'alternative (fusionner ce qui est
    commun, garder le reste) produit des règles que personne n'a demandées.
    """

    def __init__(self, plans=None, coupes=None, service=None):
        super(ReperagePageVM, self).__init__()
        self._service = service
        self._plans = list(plans or [])
        self._coupes = list(coupes or [])
        self._regles = self._lire_regles()
        # Vrai pendant que l'éditeur se recharge : les cases préviennent une par
        # une, et sans ce garde-fou chaque rechargement réécrirait la règle
        # qu'il est en train d'afficher.
        self._muet = False
        self._mode = reperage.MODE_AUCUN
        self._jeu = reperage.JEU_DU_PLAN
        self._filtre_coupes = u''
        self._messages = []

        self.Modes = self._construire_modes()
        self.CoupesItems = [CoupeItemVM(c, self._editeur_change)
                            for c in self._coupes]

        # La liste d'abord, VIDE, puis les lignes câblées sur son
        # `_on_item_toggle`, puis les lignes posées dedans : c'est l'ordre de
        # `SelectionPageVM.depuis_descripteurs`, qui ne sert pas ici parce
        # qu'elle fabrique des `SelectionItemVM` et pas nos lignes de plan.
        # Sans ce câblage, cocher une case ne préviendrait personne et
        # l'éditeur resterait sur le plan précédent.
        self.Liste = SelectionPageVM(
            [], id_getter=lambda it: it.Id,
            filter_getters=[lambda it: it.Nom, lambda it: it.ColonneGauche,
                            lambda it: it.Plan.get('type') or u''],
            on_selection_changed=lambda _: self._recharger_editeur(),
            titre=u'Plans du modèle', presets=self._construire_presets())
        self.Items = [PlanItemVM(p, self.Liste._on_item_toggle)
                      for p in self._plans]
        for item in self.Items:
            item.poser_regle(self._regles.get(item.Id))
        self.Liste._all = self.Items
        self.Liste._filtered = list(self.Items)

        self.Reappliquer = RelayCommand(lambda _: self.appliquer())
        self.RetirerTout = RelayCommand(lambda _: self.retirer_tout())
        self._calculer_derives()

    # ------------------------------------------------------------------
    # Chargement
    # ------------------------------------------------------------------

    def _lire_regles(self):
        if self._service is None:
            return {}
        try:
            return self._service.lire_regles()
        except Exception:
            return {}

    def _construire_modes(self):
        """Le menu de mode, un mode indisponible restant VISIBLE mais grisé.

        Un mode absent sans explication laisserait croire à un bug ; grisé avec
        sa raison, il dit ce qui manque au modèle.
        """
        params = {}
        if self._service is not None:
            try:
                params = self._service.parametres()
            except Exception:
                params = {}
        besoins = {reperage.MODE_FEUILLE: reperage.FEUILLE,
                   reperage.MODE_JEU: reperage.JEU,
                   reperage.MODE_CHOIX: reperage.NOM}
        libelles = {reperage.FEUILLE: u'Numéro de feuille',
                    reperage.JEU: u'Jeu de feuilles',
                    reperage.NOM: u'Nom de la vue'}
        modes = []
        for (cle, libelle) in reperage.MODES:
            besoin = besoins.get(cle)
            # Sans service (tests hors Revit), on ne grise rien.
            manque = bool(params) and besoin is not None and besoin not in params
            modes.append(ModeVM(
                cle, libelle, not manque,
                u'« %s » n\'est pas filtrable dans ce modèle'
                % libelles.get(besoin, besoin) if manque else u''))
        return modes

    def _construire_presets(self):
        """Les sélections préfabriquées — ce qui remplace le type de vue
        mémorisé du premier jet.

        Le type redevient un raccourci commode au lieu de DÉFINIR ce qu'est un
        plan de repérage : un plan hors convention reste visible dans la liste,
        au lieu d'y être introuvable.
        """
        presets = []
        for type_vue in sorted(set(p.get('type') for p in self._plans if p.get('type'))):
            presets.append((u'du type %s' % type_vue,
                            lambda it, t=type_vue: it.Plan.get('type') == t))
        for jeu in sorted(set(p.get('jeu') for p in self._plans if p.get('jeu'))):
            presets.append((u'du jeu %s' % jeu,
                            lambda it, j=jeu: it.Plan.get('jeu') == j))
        presets.append((u'sur une feuille', lambda it: bool(it.Plan.get('feuille'))))
        presets.append((u'gérés', lambda it: it.Geree))
        presets.append((u'non gérés', lambda it: not it.Geree))
        presets.append((u'en dérive', lambda it: it.ADerive))
        return presets

    # ------------------------------------------------------------------
    # Dérive
    # ------------------------------------------------------------------

    def _calculer_derives(self):
        """Compare ce que chaque règle produirait à ce qui est réellement posé.

        Deux dérives possibles : le filtre attendu n'est plus sur la vue (feuille
        renumérotée, plan déplacé, filtre supprimé à la main), ou la règle cite
        une coupe qui n'existe plus (renommée). Détecté, jamais réparé
        d'office : ouvrir un outil pour regarder ne doit pas salir le document.
        """
        poses = {}
        if self._service is not None:
            try:
                poses = self._service.filtres_poses()
            except Exception:
                poses = {}
        connus = set(c.get('nom') for c in self._coupes)
        for item in self.Items:
            regle = self._regles.get(item.Id)
            if regle is None:
                item.poser_derive(u'')
                continue
            raisons = []
            attendu = reperage.nom_de_filtre(regle, item.Plan)
            if attendu and attendu not in poses.get(item.Id, []):
                raisons.append(u'filtre absent ou périmé')
            if connus:
                perdues = [n for n in regle.noms_cites() if n not in connus]
                if perdues:
                    raisons.append(u'coupe introuvable : %s' % u', '.join(perdues))
            item.poser_derive(u' · '.join(raisons))
        for nom in ('ADerive', 'DeriveTexte'):
            self.notify_property(nom)

    @property
    def ADerive(self):
        return any(it.ADerive for it in self.Items)

    @property
    def DeriveTexte(self):
        nombre = len([it for it in self.Items if it.ADerive])
        if not nombre:
            return u''
        return (u'%d plan%s a dérivé depuis la dernière application — le modèle '
                u'a bougé sous la règle.' % (nombre, u's' if nombre > 1 else u''))

    # ------------------------------------------------------------------
    # Éditeur : lecture
    # ------------------------------------------------------------------

    def _selectionnes(self):
        return [it for it in self.Items if it.IsSelected]

    @property
    def EditeurActif(self):
        return bool(self._selectionnes())

    @property
    def Entete(self):
        choisis = self._selectionnes()
        if not choisis:
            return u'Sélectionne un ou plusieurs plans à gauche.'
        if len(choisis) == 1:
            return choisis[0].Nom
        return u'%d plans sélectionnés' % len(choisis)

    @property
    def Divergent(self):
        """Vrai si les plans sélectionnés n'ont pas tous la même règle."""
        choisis = self._selectionnes()
        if len(choisis) < 2:
            return False
        premiere = self._regles.get(choisis[0].Id)
        temoin = premiere.en_dict() if premiere else None
        for item in choisis[1:]:
            regle = self._regles.get(item.Id)
            if (regle.en_dict() if regle else None) != temoin:
                return True
        return False

    @property
    def Avertissement(self):
        if self.Divergent:
            return (u'Ces plans n\'ont pas la même règle. Toucher un réglage '
                    u'appliquera celui affiché à tous.')
        mode = self.ModeChoisi
        if mode is not None and not mode.Disponible:
            return mode.Raison
        return u''

    @property
    def AAvertissement(self):
        return bool(self.Avertissement)

    @property
    def ModeChoisi(self):
        for mode in self.Modes:
            if mode.Cle == self._mode:
                return mode
        return None

    @ModeChoisi.setter
    def ModeChoisi(self, valeur):
        cle = getattr(valeur, 'Cle', None)
        if not cle or cle == self._mode:
            return
        self._mode = cle
        for nom in ('ModeChoisi', 'ModeEstJeu', 'ModeEstChoix',
                    'CoupesVisibles', 'TitreCoupes', 'VisibiliteMasquer'):
            self.notify_property(nom)
        self._editeur_change()

    @property
    def ModeEstJeu(self):
        return self._mode == reperage.MODE_JEU

    @property
    def ModeEstChoix(self):
        return self._mode == reperage.MODE_CHOIX

    @property
    def CoupesVisibles(self):
        """La liste des coupes ne sert qu'aux modes qui nomment des coupes —
        soit pour les choisir, soit pour faire exception."""
        return self._mode != reperage.MODE_AUCUN

    @property
    def TitreCoupes(self):
        if self._mode == reperage.MODE_CHOIX:
            return u'Coupes à montrer'
        return u'Exceptions'

    @property
    def VisibiliteMasquer(self):
        """« Masquer » n'a pas de sens quand on choisit les coupes une par une :
        ce qui n'est pas coché est déjà masqué.

        Une chaîne plutôt qu'un booléen : WPF la convertit seul en `Visibility`,
        ce qui évite d'écrire un convertisseur pour trois lignes de XAML.
        """
        return u'Hidden' if self._mode == reperage.MODE_CHOIX else u'Visible'

    @property
    def FiltreCoupes(self):
        return self._filtre_coupes

    @FiltreCoupes.setter
    def FiltreCoupes(self, valeur):
        self._filtre_coupes = valeur or u''
        self.notify_property('FiltreCoupes')
        self.notify_property('CoupesFiltrees')

    @property
    def CoupesFiltrees(self):
        """Les coupes que la recherche laisse voir.

        Une recherche est indispensable ici : sur 200 coupes, désigner celle
        qu'on veut excepter à la molette n'est pas une interface. Même moteur
        que la liste de gauche (`core.text_filter`), mêmes règles d'accents et
        de casse.
        """
        return text_filter.filtrer(self.CoupesItems, self._filtre_coupes,
                                   [lambda it: it.Nom, lambda it: it.Origine])

    @property
    def Jeux(self):
        """Les jeux connus, « celui du plan » en tête.

        Tirés des plans ET des coupes : un jeu sans plan de repérage reste
        proposable, le repérage se règle souvent avant que tout soit posé.
        """
        noms = set(p.get('jeu') for p in self._plans)
        noms.update(c.get('jeu') for c in self._coupes)
        return [reperage.JEU_DU_PLAN] + sorted(n for n in noms if n)

    @property
    def JeuChoisi(self):
        return self._jeu

    @JeuChoisi.setter
    def JeuChoisi(self, valeur):
        valeur = valeur or reperage.JEU_DU_PLAN
        if valeur == self._jeu:
            return
        self._jeu = valeur
        self.notify_property('JeuChoisi')
        self._editeur_change()

    # ------------------------------------------------------------------
    # Éditeur : écriture
    # ------------------------------------------------------------------

    def _recharger_editeur(self):
        """Aligne l'éditeur sur la règle du premier plan sélectionné."""
        self._muet = True
        try:
            choisis = self._selectionnes()
            regle = self._regles.get(choisis[0].Id) if choisis else None
            if regle is None:
                regle = reperage.Regle()
            self._mode = regle.mode
            self._jeu = regle.cible or reperage.JEU_DU_PLAN
            forcees = set(regle.ajouts)
            exclues = set(regle.retraits)
            for coupe in self.CoupesItems:
                coupe.regler(coupe.Nom in forcees, coupe.Nom in exclues)
        finally:
            self._muet = False
        for nom in ('EditeurActif', 'Entete', 'Divergent', 'Avertissement',
                    'AAvertissement', 'ModeChoisi', 'ModeEstJeu',
                    'ModeEstChoix', 'CoupesVisibles', 'TitreCoupes',
                    'VisibiliteMasquer', 'JeuChoisi', 'Resume'):
            self.notify_property(nom)

    def _editeur_change(self):
        """Écrit l'état de l'éditeur sur tous les plans sélectionnés."""
        if self._muet:
            return
        choisis = self._selectionnes()
        if not choisis:
            return
        for item in choisis:
            if self._mode == reperage.MODE_AUCUN:
                self._regles.pop(item.Id, None)
                item.poser_regle(None)
                continue
            regle = reperage.Regle(
                self._mode,
                self._jeu if (self._mode == reperage.MODE_JEU
                              and self._jeu != reperage.JEU_DU_PLAN) else None,
                [c.Nom for c in self.CoupesItems if c.Forcee],
                [c.Nom for c in self.CoupesItems if c.Exclue])
            self._regles[item.Id] = regle
            item.poser_regle(regle)
        for nom in ('Divergent', 'Avertissement', 'AAvertissement', 'Resume'):
            self.notify_property(nom)

    # ------------------------------------------------------------------
    # En-tête et actions
    # ------------------------------------------------------------------

    @property
    def TitrePage(self):
        return u'Repérage des coupes'

    @property
    def Resume(self):
        geres = len([it for it in self.Items if it.Geree])
        return u'%d plan%s · %d géré%s · %d coupe%s' % (
            len(self.Items), u's' if len(self.Items) > 1 else u'',
            geres, u's' if geres > 1 else u'',
            len(self._coupes), u's' if len(self._coupes) > 1 else u'')

    @property
    def Messages(self):
        """Le compte rendu de la dernière action, DANS la page : la fenêtre ne
        se ferme plus sur « Appliquer », la console pyRevit n'est plus le bon
        endroit."""
        return self._messages

    @property
    def AMessages(self):
        return bool(self._messages)

    def appliquer(self):
        """Écrit les filtres et les règles. Retourne les messages du service."""
        if self._service is None:
            self._poser_messages([u'Service indisponible : rien n\'a été écrit.'])
            return self._messages
        cibles = [{'plan': it.Plan,
                   'regle': self._regles.get(it.Id) or reperage.Regle()}
                  for it in self.Items]
        messages = self._service.appliquer(cibles) or []
        self._poser_messages(messages)
        self._calculer_derives()
        return messages

    def retirer_tout(self):
        """Retire du modèle tous les filtres de l'outil, sans toucher aux
        règles : c'est un retour à l'affichage natif, pas un oubli de ce qui
        était décidé."""
        if self._service is None:
            self._poser_messages([u'Service indisponible.'])
            return self._messages
        messages = self._service.retirer_tout() or []
        self._poser_messages(messages)
        self._calculer_derives()
        return messages

    def _poser_messages(self, messages):
        self._messages = [m for m in messages if m]
        for nom in ('Messages', 'AMessages', 'Resume'):
            self.notify_property(nom)

    def plan_selectionne(self):
        """L'`ElementId` du plan à activer pour « Aller au plan », ou None.

        Rendu au script, qui active la vue APRÈS la fermeture de la fenêtre :
        une modale bloque Revit, on ne peut pas changer de vue tant qu'elle est
        ouverte.
        """
        choisis = self._selectionnes()
        return choisis[0].Plan.get('id') if choisis else None
