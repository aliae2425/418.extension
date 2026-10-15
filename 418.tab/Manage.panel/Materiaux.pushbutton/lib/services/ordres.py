# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Ce que la page a le droit de demander. UN ordre = UNE méthode, qui rend du
# JSON pur.
#
# Volontairement sans WebView2, sans JSON et sans WPF : la plomberie du pont
# vit dans `views/MainWindowView.py`, et tout ce qui se décide (qui est coché,
# quelle portée, quel nom obtenu) se teste ici en Python nu avec des doubles —
# cf. `tests/test_ordres.py`. C'est ce que faisaient les ViewModels ; ils ne
# portaient que ça.
#
# Tout tourne sur le fil d'interface, DANS le contexte d'API de la commande
# (la fenêtre est modale) : les transactions partent donc d'ici directement,
# exactement comme les `Click` de l'ancienne fenêtre WPF. Un volet ancré, lui,
# aurait imposé un fil de fond et un ExternalEvent.

try:
    from lib.services import presentation
except Exception:
    from services import presentation

try:
    from core.rename_service import RenameService
except Exception:
    from lib.core.rename_service import RenameService

try:
    from lib.services.journal import log
except Exception:
    try:
        from services.journal import log
    except Exception:
        def log(gabarit, *args):
            pass


class Ordres(object):
    """L'état de l'outil et les réponses aux demandes de la page."""

    def __init__(self, doc=None, service=None, catalogue=None, materiaux=None,
                 cartes=None, sombre=False):
        self._doc = doc
        self._service = service
        self._catalogue = catalogue
        #: entier -> `Material` Revit. La page ne manipule que les entiers.
        self._materiaux = dict(materiaux or {})
        #: les cartes, DANS L'ORDRE d'affichage — c'est lui qui numérote {n}.
        self._cartes = list(cartes or [])
        self._sombre = bool(sombre)

    # -- aiguillage --------------------------------------------------------

    def traiter(self, message):
        """`message` : le dictionnaire reçu de la page. Rend la sortie, ou
        lève — l'hôte transforme l'exception en réponse d'erreur."""
        ordre = (message or {}).get('ordre')
        if ordre == 'pret':
            return self.etat()
        if ordre == 'apercu_renommage':
            return self.apercu_renommage(message)
        if ordre == 'renommer':
            return self.renommer(message)
        if ordre == 'analyser':
            return self.analyser(message)
        if ordre == 'remplacer':
            return self.remplacer(message)
        if ordre == 'editeur':
            return self.editeur(message)
        if ordre == 'selecteur':
            return self.selecteur(message)
        if ordre == 'apercu_face':
            return self.apercu_face(message)
        if ordre == 'rendu':
            return self.rendu(message)
        if ordre == 'enregistrer':
            return self.enregistrer(message)
        raise ValueError(u'ordre inconnu : %s' % ordre)

    # -- l'état de départ --------------------------------------------------

    def etat(self):
        """Tout ce que la page affiche sans rien demander de plus.

        Envoyé d'un bloc : les vignettes sont déjà rendues et une seconde
        demande ne ferait que retarder l'affichage.

        Les catalogues de motifs et d'apparences n'y sont PAS : ils ne
        servent qu'à l'éditeur, qui est une autre fenêtre et donc une autre
        page. Les y mettre ferait voyager cinquante vignettes de motif que la
        fenêtre principale n'affiche jamais.

        ponytail: deux SVG par matériau partent dans UN message — compter
        quelques mégaoctets sur un modèle à plusieurs centaines de matériaux
        très hachurés. C'est un `PostWebMessageAsJson` unique, donc quelques
        centaines de millisecondes à l'ouverture, une fois. Si ça pèse, le
        repli est d'envoyer les cartes sans vignette puis de les demander par
        paquets au défilement.
        """
        return {
            'sombre': self._sombre,
            'cartes': self._cartes,
            'categories': self._catalogue.categories if self._catalogue else [],
            'modifiable': self._modifiable(),
        }

    def _modifiable(self):
        """Faux quand aucune action n'aura d'effet : pas de document, ou
        document en lecture seule. La page le dit AVANT le premier clic."""
        if self._doc is None or self._service is None:
            return False
        try:
            return not self._doc.IsReadOnly
        except Exception:
            return True

    # -- renommage ---------------------------------------------------------

    def _regles(self, message):
        """Le moteur de nommage du socle, en mode regex d'office — c'est ce
        que dit l'aide du champ Rechercher."""
        return RenameService(prefixe=message.get('prefixe') or u'',
                             rechercher=message.get('rechercher') or u'',
                             remplacer=message.get('remplacer') or u'',
                             suffixe=message.get('suffixe') or u'',
                             use_regex=True)

    def _cartes_cochees(self, message):
        """Les cartes cochées, DANS L'ORDRE de la liste.

        C'est cet ordre qui numérote {n} ET celui dans lequel les matériaux
        partent au service : les deux doivent coïncider, sinon l'aperçu
        annonce un numéro et Revit en écrit un autre.
        """
        coches = set(presentation.entier(i) for i in message.get('ids') or [])
        return [carte for carte in self._cartes if carte['id'] in coches]

    def apercu_renommage(self, message):
        """Le nom obtenu pour chaque carte cochée. N'écrit rien.

        Clés en CHAÎNES : un objet JSON n'a pas de clé entière, et la page
        relit par `String(id)`.
        """
        regles = self._regles(message)
        noms = {}
        for index, carte in enumerate(self._cartes_cochees(message), start=1):
            noms[u'%d' % carte['id']] = regles.apply(carte['nom'], index=index)
        return {'noms': noms, 'erreur': regles.regex_error}

    def renommer(self, message):
        """Applique le renommage. Rend les noms que Revit a RÉELLEMENT acceptés.

        Le service assainit et suffixe `*` sur collision : la page reprend ce
        qui est écrit dans la maquette, pas ce que l'aperçu annonçait.
        """
        cartes = self._cartes_cochees(message)
        materiaux = [self._materiaux[carte['id']] for carte in cartes
                     if carte['id'] in self._materiaux]
        if not materiaux or self._service is None:
            return {'changes': 0, 'noms': {}}
        changes = self._service.renommer(materiaux, self._regles(message))
        noms = {}
        for carte in cartes:
            materiau = self._materiaux.get(carte['id'])
            if materiau is None:
                continue
            carte['nom'] = materiau.Name
            noms[u'%d' % carte['id']] = materiau.Name
        return {'changes': changes, 'noms': noms}

    # -- remplacement ------------------------------------------------------

    def _ids_materiaux(self, identifiants):
        """Entiers -> `ElementId` des matériaux. Les inconnus sautent."""
        sortie = []
        for identifiant in identifiants or []:
            materiau = self._materiaux.get(presentation.entier(identifiant))
            if materiau is not None:
                sortie.append(materiau.Id)
        return sortie

    def _portee(self, message):
        """Les catégories à balayer, ou None pour TOUT le modèle.

        None ne veut pas dire « les mêmes catégories sans filtre » : sans
        filtre, le balayage voit aussi ce qui n'a pas de catégorie de modèle.
        C'est bien ce qu'on veut quand l'utilisateur n'a rien restreint, et
        c'est au passage plus rapide qu'un filtre à 200 entrées.
        """
        if self._catalogue is None:
            return None
        cochees = [presentation.entier(i)
                   for i in message.get('categories') or []]
        if len(cochees) >= len(self._catalogue.categories):
            return None
        return [self._catalogue.element_id(i) for i in cochees
                if self._catalogue.element_id(i) is not None]

    def analyser(self, message):
        """Balaye le modèle sans rien modifier."""
        sources = self._ids_materiaux(message.get('sources'))
        if not sources or self._service is None:
            return _rapport_vide(u'Aucune source cochée.')
        rapport = self._service.analyser(sources, self._portee(message))
        if rapport.EstVide:
            etat = u'Aucun élément n\'utilise ces matériaux.'
        else:
            etat = u'%d élément(s) seraient modifiés.' % rapport.Total
        return _rapport_json(rapport, etat, applique=False)

    def remplacer(self, message):
        """Applique le remplacement en une transaction."""
        sources = self._ids_materiaux(message.get('sources'))
        cible = self._materiaux.get(presentation.entier(message.get('cible')))
        if not sources or cible is None or self._service is None:
            log(u'remplacer ignoré : {} source(s), cible={}',
                len(sources), message.get('cible'))
            return _rapport_vide(u'Il faut au moins une source et une cible.')
        rapport = self._service.remplacer(sources, cible.Id,
                                          self._portee(message))
        etat = u'Aucun élément modifié.' if rapport.EstVide \
            else u'%d élément(s) modifié(s).' % rapport.Total
        return _rapport_json(rapport, etat, applique=True)

    # -- éditeur -----------------------------------------------------------

    def _materiau(self, message):
        return self._materiaux.get(presentation.entier(message.get('id')))

    def editeur(self, message):
        """L'état d'édition d'UN matériau : tout ce que sa fenêtre affiche.

        Les huit tuiles et les catalogues partent avec : la fenêtre de
        l'éditeur est une page à elle, elle ne partage rien avec la
        principale, et sans eux elle s'ouvrirait sur des cadres blancs le
        temps d'un second aller-retour.
        """
        materiau = self._materiau(message)
        if materiau is None:
            raise ValueError(u'matériau introuvable')
        etat = presentation.editeur(self._doc, materiau, self._catalogue)
        etat['faces'] = dict(
            (face, self._tuiles(face, etat['emplacements']))
            for face, _ in presentation.LIBELLES_FACE)
        etat['motifs'] = self._catalogue.motifs if self._catalogue else []
        etat['apparences'] = (self._catalogue.apparences
                              if self._catalogue else [])
        etat['modifiable'] = self._modifiable()
        return etat

    def selecteur(self, message):
        """Ce que la fenêtre « choisir un motif » affiche.

        La règle de ce qui est offrable est ici et nulle part ailleurs : un
        seul des quatre emplacements accepte un motif de MODÈLE, et la page
        n'a pas à le savoir.
        """
        face = message.get('face')
        couche = message.get('couche')
        courant = presentation.entier(message.get('motif'))
        return {
            'titre': presentation.titre_emplacement(face, couche),
            'contrainte': presentation.contrainte(face, couche),
            'motifs': presentation.proposables(self._catalogue, face, couche,
                                               courant),
            'courant': courant,
        }

    def _tuiles(self, face, emplacements):
        return presentation.tuiles(
            self._catalogue,
            emplacements.get(presentation.cle(face, u'Background')),
            emplacements.get(presentation.cle(face, u'Foreground')))

    def apercu_face(self, message):
        """Redessine les quatre tuiles d'une face après un changement.

        Appelé à chaque choix de motif ou de couleur : c'est un calcul de
        géométrie, aucune lecture de la maquette.
        """
        return {'face': message.get('face'),
                'tuiles': presentation.tuiles(self._catalogue,
                                              message.get('fond'),
                                              message.get('premier'))}

    def rendu(self, message):
        """La sphère d'un asset d'apparence, choisi mais pas encore écrit.

        Sans ça, changer d'apparence dans la liste laisserait l'aperçu sur
        l'ancienne jusqu'à l'enregistrement — un aperçu qui ment.
        """
        if self._doc is None or self._catalogue is None:
            return presentation.rendu_asset(None)
        element_id = self._catalogue.element_id(message.get('asset'))
        if element_id is None:
            return presentation.rendu_asset(None)
        return presentation.rendu_asset(self._doc.GetElement(element_id))

    def enregistrer(self, message):
        """Écrit ce qui a bougé, puis RELIT le matériau.

        La carte rendue est celle de la maquette, pas celle des champs : elle
        montre le nom réellement accepté (assaini, `*` de collision) et les
        motifs réellement posés.
        """
        materiau = self._materiau(message)
        if materiau is None or self._service is None:
            raise ValueError(u'matériau introuvable')
        changees = presentation.modifiees(message.get('valeurs'), materiau)
        parametres = presentation.identite_modifiee(message.get('identite'),
                                                    materiau)
        if not changees and not parametres:
            return dict(self._relecture(materiau), ok=True,
                        statut=u'Rien à enregistrer.')
        echecs = self._service.enregistrer(
            materiau, presentation.valeurs_revit(changees, self._catalogue),
            parametres)
        statut = u'' if not echecs else u'Refusé par Revit : %s.' % u', '.join(
            presentation.libelles(echecs))
        return dict(self._relecture(materiau), ok=not echecs, statut=statut)

    def _relecture(self, materiau):
        """Ce que la page reprend après une écriture : la carte et l'état
        d'édition, relus dans la maquette et non recopiés des champs."""
        return {'carte': self._rafraichir(materiau),
                'valeurs': presentation.valeurs_lues(materiau),
                'identite': presentation.identite(materiau)}

    def _rafraichir(self, materiau):
        """Relit la carte d'un matériau et la remet en place dans la liste.

        Les usages ne sont PAS recomptés : une édition ne change pas qui
        porte le matériau, et le comptage est un parcours complet du modèle.
        """
        identifiant = presentation.ident(materiau.Id)
        ancienne = self._carte(identifiant) or {}
        neuve = presentation.carte(self._doc, materiau, self._catalogue)
        neuve['usages'] = ancienne.get('usages', neuve['usages'])
        for index, carte in enumerate(self._cartes):
            if carte['id'] == identifiant:
                self._cartes[index] = neuve
                break
        return neuve

    def _carte(self, identifiant):
        for carte in self._cartes:
            if carte['id'] == identifiant:
                return carte
        return None


def _rapport_json(rapport, etat, applique=False):
    """`MaterialService.Rapport` -> ce que la page affiche."""
    return {
        'lignes': [{'categorie': ligne.Categorie, 'detail': ligne.Detail,
                    'total': ligne.Total} for ligne in rapport.Lignes],
        'total': rapport.Total,
        'peints': rapport.Peints,
        'vide': rapport.EstVide,
        'etat': etat,
        'applique': applique,
    }


def _rapport_vide(etat):
    return {'lignes': [], 'total': 0, 'peints': 0, 'vide': True,
            'etat': etat, 'applique': False}
