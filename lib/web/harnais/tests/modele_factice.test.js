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
  const maj = de(recus, p.MAJ).filter((c) => c.nom === 'revit_synchroniser');
  assert.equal(maj[0].etat, p.ATTENTE_ACCORD);
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

test('il n’appelle jamais un outil absent du catalogue', async () => {
  // Au dernier tour impose par le plafond, le catalogue est vide : un modele
  // qui appellerait quand meme ferait boucler la conversation sans fin.
  const repondre = modeleFactice({ cadence: 0 });
  const sortie = await repondre(
    [{ role: 'utilisateur', texte: 'liste mes vues' }], [], {});
  assert.equal(sortie.appels, undefined);
});
