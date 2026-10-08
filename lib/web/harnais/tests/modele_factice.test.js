// node --test "lib/web/**/tests/*.test.js"
//
// Le faux modèle n'a aucune valeur en soi — il est faux. Ce qu'on vérifie,
// c'est qu'il honore le CONTRAT qu'un vrai fournisseur honorera, et qu'il
// mène la vraie boucle jusqu'au bout. S'il s'en écarte, le jour où on branche
// un vrai modèle on découvrira la différence en production.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as p from '../protocole.js';
import * as perm from '../permissions.js';
import { conduire } from '../boucle.js';
import { modeleFactice, outilsFactices } from '../modele_factice.js';

function jouer(texte, { demander = null, signal = null } = {}) {
  const recus = [];
  const flux = new p.Flux((e, c) => recus.push([e, c]));
  const outils = outilsFactices();
  return conduire({
    flux,
    outils,
    regles: perm.reglesDepuisCatalogue([...outils.values()]),
    // cadence nulle : une suite qui attend 25 ms par mot ne se lance plus.
    modele: modeleFactice({ cadence: 0 }),
    messages: [{ role: 'utilisateur', texte }],
    demander,
    signal,
  }).then(() => recus);
}

const de = (recus, ev) => recus.filter(([e]) => e === ev).map(([, c]) => c);
const texte = (recus, id) => de(recus, p.DELTA)
  .filter((c) => !id || c.id === id).map((c) => c.morceau).join('');
const genres = (recus) => de(recus, p.NEUVE).map((c) => c.genre);
const appels = (recus) => de(recus, p.NEUVE)
  .filter((c) => c.genre === p.OUTIL).map((c) => c.nom);

test('une question simple : du raisonnement, puis du texte, aucun outil', async () => {
  const recus = await jouer('bonjour');
  assert.deepEqual(appels(recus), []);
  assert.ok(genres(recus).includes(p.RAISONNEMENT));
  assert.match(texte(recus), /fictif/);
  assert.deepEqual(de(recus, p.FINI), [{}]);
});

test('la question est renvoyee a l’architecte', async () => {
  // Preuve que les messages traversent bien jusqu'au modele.
  const recus = await jouer('quelle heure est-il');
  assert.match(texte(recus), /quelle heure est-il/);
});

test('« liste mes vues » enchaine deux lectures puis conclut', async () => {
  const recus = await jouer('liste mes vues');
  assert.deepEqual(appels(recus), ['revit_etat', 'revit_vues']);
  assert.match(texte(recus), /MAISON-PDA/);
  assert.deepEqual(de(recus, p.FINI), [{}]);
});

test('un outil qui leve devient une part en echec, le tour finit quand meme', async () => {
  const recus = await jouer('fais une erreur');
  const maj = de(recus, p.MAJ).filter((c) => c.nom === 'revit_nomenclatures');
  assert.equal(maj.at(-1).etat, p.ECHEC);
  assert.match(texte(recus), /Surfaces/);
  assert.deepEqual(de(recus, p.FINI), [{}]);
});

test('la synchronisation demande l’accord et s’arrete sur un refus', async () => {
  const recus = await jouer('synchronise le projet',
    { demander: async () => perm.JAMAIS });
  const neuve = de(recus, p.NEUVE).filter((c) => c.nom === 'revit_synchroniser');
  assert.equal(neuve[0].etat, p.ATTENTE_ACCORD);
  const maj = de(recus, p.MAJ).filter((c) => c.nom === 'revit_synchroniser');
  assert.equal(maj.at(-1).etat, p.REFUSE);
});

test('la synchronisation part si on l’accorde', async () => {
  const recus = await jouer('synchronise le projet',
    { demander: async () => perm.UNE_FOIS });
  const maj = de(recus, p.MAJ).filter((c) => c.nom === 'revit_synchroniser');
  assert.equal(maj.at(-1).etat, p.FAIT);
  assert.match(texte(recus), /synchronisé/);
});

test('l’accord recoit le nom ET les arguments', async () => {
  // L'architecte doit voir CE qu'il autorise, pas seulement qu'on lui demande.
  const vus = [];
  await jouer('synchronise le projet', {
    demander: async (nom, args) => { vus.push([nom, args]); return perm.JAMAIS; },
  });
  assert.equal(vus.length, 1);
  assert.equal(vus[0][0], 'revit_synchroniser');
  assert.equal(vus[0][1].liberer_tout, true);
});

test('couper arrete le scenario sans le marquer en erreur', async () => {
  const stop = new AbortController();
  stop.abort();
  const recus = await jouer('liste mes vues', { signal: stop.signal });
  assert.deepEqual(de(recus, p.FINI), [{ raison: 'interrompu' }]);
  assert.equal(genres(recus).filter((g) => g === p.ERREUR).length, 0);
});

test('un scenario d’outils n’empeche pas le suivant d’en appeler', async () => {
  // Le bug vu en vrai : le faux modele concluait d'emblee des qu'un appel
  // d'outil figurait N'IMPORTE OU dans l'historique. Resultat, apres un
  // premier « liste mes vues », « synchronise le projet » ne demandait
  // plus jamais l'accord — il annoncait la synchronisation sans la faire.
  const recus = [];
  const flux = new p.Flux((e, c) => recus.push([e, c]));
  const outils = outilsFactices();
  const regles = perm.reglesDepuisCatalogue([...outils.values()]);
  const modele = modeleFactice({ cadence: 0 });
  const messages = [];
  const tour = (texte, demander) => {
    messages.push({ role: 'utilisateur', texte });
    return conduire({ flux, outils, regles, modele, messages, demander });
  };

  await tour('liste mes vues');
  const avant = de(recus, p.NEUVE).filter((c) => c.genre === p.OUTIL).length;
  await tour('synchronise le projet', async () => perm.UNE_FOIS);

  const apres = de(recus, p.NEUVE).filter((c) => c.genre === p.OUTIL);
  assert.equal(apres.length, avant + 1);
  assert.equal(apres.at(-1).nom, 'revit_synchroniser');
  assert.equal(apres.at(-1).etat, p.ATTENTE_ACCORD);
});

test('deux tours de suite ne reutilisent aucun id de part', async () => {
  // La cause de l'empilement : des ids qui se telescopent font grossir la
  // bulle du tour precedent au lieu d'en creer une neuve.
  const recus = [];
  const flux = new p.Flux((e, c) => recus.push([e, c]));
  const outils = outilsFactices();
  const commun = {
    flux,
    outils,
    regles: perm.reglesDepuisCatalogue([...outils.values()]),
    modele: modeleFactice({ cadence: 0 }),
    messages: [],
  };
  commun.messages.push({ role: 'utilisateur', texte: 'bonjour' });
  await conduire(commun);
  commun.messages.push({ role: 'utilisateur', texte: 'liste mes vues' });
  await conduire(commun);
  const ids = de(recus, p.NEUVE).map((c) => c.id);
  assert.equal(new Set(ids).size, ids.length, ids.join(','));
});

test('il n’appelle jamais un outil absent du catalogue', async () => {
  // Au dernier tour impose par le plafond, le catalogue est vide : un modele
  // qui appellerait quand meme ferait boucler la conversation sans fin.
  const repondre = modeleFactice({ cadence: 0 });
  const sortie = await repondre(
    [{ role: 'utilisateur', texte: 'liste mes vues' }], [], {});
  assert.equal(sortie.appels, undefined);
});
