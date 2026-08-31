# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

# Où vivent les règles de repérage : dans le DOCUMENT, par Extensible Storage.
# Voir docs/adr/0002-intention-de-reperage-dans-le-modele.md — c'est la seule
# donnée de l'extension qui échappe à `UserConfig`, parce que le repérage est
# une décision de projet et non une préférence personnelle.
#
# Le JSON et la clé de rangement sont des fonctions de module, testables hors
# Revit ; la classe ne porte que l'aller-retour avec le document.

try:
    from lib.services import reperage
except Exception:
    try:
        from services import reperage
    except Exception:
        # Exécution directe du contrôle (`python lib/services/stockage.py`) :
        # seul le dossier du script est sur sys.path.
        import reperage

try:
    from Autodesk.Revit.DB import DataStorage, FilteredElementCollector
    from Autodesk.Revit.DB.ExtensibleStorage import (AccessLevel, Entity,
                                                     Schema, SchemaBuilder)
    from System import Guid
except Exception:
    DataStorage = None
    FilteredElementCollector = None
    AccessLevel = None
    Entity = None
    Schema = None
    SchemaBuilder = None
    Guid = None

#: GUID du schéma. ÉTERNEL : le changer rend illisibles toutes les règles déjà
#: écrites dans les modèles. Une évolution du contenu passe par `VERSION`, pas
#: par un nouveau GUID.
SCHEMA_GUID = '4180d1ae-7c31-4f0a-9b6e-2f5c418ada11'
NOM_SCHEMA = 'Reperage418'
NOM_CHAMP = 'regles'
VENDEUR = 'PDA'

#: Version du CONTENU du champ. Un JSON d'une version supérieure est ignoré
#: plutôt que mal interprété : mieux vaut un outil qui repart de zéro qu'un
#: outil qui écrase les règles d'un collègue mieux équipé.
VERSION = 1


def serialiser(regles):
    """{uid de plan: Regle} -> texte à stocker."""
    return json.dumps({
        'version': VERSION,
        'plans': dict((uid, regle.en_dict())
                      for (uid, regle) in (regles or {}).items()),
    })


def deserialiser(texte):
    """Texte stocké -> {uid de plan: Regle}. Tolère tout : un champ illisible
    donne un dictionnaire vide, jamais une exception qui empêche d'ouvrir
    l'outil."""
    try:
        brut = json.loads(texte or u'{}')
    except Exception:
        return {}
    if not isinstance(brut, dict):
        return {}
    try:
        if int(brut.get('version', 0)) > VERSION:
            return {}
    except Exception:
        return {}
    plans = brut.get('plans')
    if not isinstance(plans, dict):
        return {}
    return dict((uid, reperage.Regle.depuis_dict(d))
                for (uid, d) in plans.items() if isinstance(d, dict))


class StockageReperage(object):
    """L'aller-retour des règles avec le document.

    `lire()` ne demande aucune transaction. `ecrire()` en exige une, OUVERTE PAR
    L'APPELANT : les règles et les filtres qu'elles produisent doivent tomber
    dans la même transaction, sinon l'intention stockée et le modèle divergent —
    exactement ce que le choix du stockage dans le document sert à empêcher.
    """

    def __init__(self, doc=None):
        self._doc = doc

    def disponible(self):
        return self._doc is not None and Schema is not None

    def lire(self):
        """{uid de plan: Regle}. Vide si rien n'a jamais été écrit."""
        if not self.disponible():
            return {}
        entite = self._entite_existante()
        if entite is None:
            return {}
        try:
            return deserialiser(entite.Get[str](NOM_CHAMP))
        except Exception:
            return {}

    def ecrire(self, regles):
        """Range les règles dans le document. À appeler DANS une transaction.

        Retourne un message d'erreur, ou None si tout s'est bien passé — le
        service en fait une ligne de compte rendu plutôt qu'une exception qui
        annulerait les filtres déjà posés.
        """
        if not self.disponible():
            return u'Extensible Storage indisponible : les règles ne sont pas enregistrées.'
        schema = self._schema()
        if schema is None:
            return u'Schéma de stockage introuvable : les règles ne sont pas enregistrées.'
        try:
            support = self._support(creer=True)
            entite = Entity(schema)
            entite.Set[str](NOM_CHAMP, serialiser(regles))
            support.SetEntity(entite)
        except Exception as erreur:
            return u'Règles non enregistrées (%s).' % erreur
        return None

    # -- interne ----------------------------------------------------------

    def _schema(self):
        """Le schéma, retrouvé par son GUID ou construit.

        `Schema.Lookup` d'abord : un schéma déjà chargé dans la session ne peut
        pas être reconstruit, `SchemaBuilder` lèverait.

        ponytail: accès Public en lecture ET en écriture. Un accès Vendor
        empêcherait un autre outil de lire les règles, mais aussi cette
        extension de les relire après un changement d'identifiant vendeur —
        pour de la donnée de projet, la lisibilité vaut mieux que le verrou.
        """
        try:
            existant = Schema.Lookup(Guid(SCHEMA_GUID))
            if existant is not None:
                return existant
        except Exception:
            pass
        try:
            constructeur = SchemaBuilder(Guid(SCHEMA_GUID))
            constructeur.SetReadAccessLevel(AccessLevel.Public)
            constructeur.SetWriteAccessLevel(AccessLevel.Public)
            constructeur.SetSchemaName(NOM_SCHEMA)
            try:
                constructeur.SetVendorId(VENDEUR)
            except Exception:
                pass
            constructeur.AddSimpleField(NOM_CHAMP, str)
            return constructeur.Finish()
        except Exception:
            return None

    def _support(self, creer=False):
        """Le `DataStorage` qui porte l'entité. En crée un si besoin.

        Un `DataStorage` dédié plutôt que `ProjectInformation` : l'élément
        n'appartient qu'à cet outil, personne ne le croisera dans une palette
        de propriétés.
        """
        for element in self._data_storages():
            return element
        if not creer:
            return None
        return DataStorage.Create(self._doc)

    def _entite_existante(self):
        schema = None
        try:
            schema = Schema.Lookup(Guid(SCHEMA_GUID))
        except Exception:
            schema = None
        if schema is None:
            return None
        for element in self._data_storages():
            try:
                entite = element.GetEntity(schema)
                if entite is not None and entite.IsValid():
                    return entite
            except Exception:
                continue
        return None

    def _data_storages(self):
        if self._doc is None or FilteredElementCollector is None:
            return []
        try:
            return list(FilteredElementCollector(self._doc)
                        .OfClass(DataStorage).ToElements())
        except Exception:
            return []


def demo():
    """Contrôle exécutable : python lib/services/stockage.py

    Ne couvre que le JSON — l'aller-retour Revit ne se prouve que dans Revit.
    """
    regles = {
        u'uid-1': reperage.Regle(reperage.MODE_FEUILLE),
        u'uid-2': reperage.Regle(reperage.MODE_JEU, u'PC', [u'Coupe ZZ']),
        u'uid-3': reperage.Regle(reperage.MODE_CHOIX, ajouts=[u'A', u'B']),
    }
    relues = deserialiser(serialiser(regles))
    assert sorted(relues.keys()) == [u'uid-1', u'uid-2', u'uid-3']
    assert relues[u'uid-1'].mode == reperage.MODE_FEUILLE
    assert relues[u'uid-2'].cible == u'PC'
    assert relues[u'uid-2'].ajouts == [u'Coupe ZZ']
    assert relues[u'uid-3'].ajouts == [u'A', u'B']

    # Rien d'écrit, champ illisible, structure inattendue : dictionnaire vide,
    # jamais d'exception.
    for cas in (None, u'', u'{', u'[]', u'{"plans": 3}', u'null'):
        assert deserialiser(cas) == {}

    # Un JSON écrit par une version ultérieure est ignoré, pas mal interprété.
    futur = json.dumps({'version': VERSION + 1, 'plans': {u'uid': {'mode': 'feuille'}}})
    assert deserialiser(futur) == {}

    assert deserialiser(serialiser({})) == {}
    print(u'stockage : OK')


if __name__ == '__main__':
    demo()
