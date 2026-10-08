// node --test "lib/web/**/tests/*.test.js"
//
// `pont.js` est le seul module de `vue/` qui porte autre chose que du DOM :
// il apparie des demandes et des réponses. C'est exactement le genre de code
// qui marche à un appel et casse à deux.

import { test, mock } from 'node:test';
import assert from 'node:assert/strict';

// L'hôte, en doublure : on retient ce qui est posté.
const postes = [];
globalThis.window = {
  chrome: { webview: { postMessage: (brut) => postes.push(JSON.parse(brut)) } },
};

const { demanderHote, reponseHote } = await import('../pont.js');

const dernier = () => postes[postes.length - 1];

test('la demande part avec son ordre et une reference', async () => {
  const attente = demanderHote('outils');
  assert.equal(dernier().ordre, 'outils');
  assert.match(dernier().ref, /^d\d+$/);
  reponseHote({ ref: dernier().ref, sortie: [] });
  assert.deepEqual(await attente, []);
});

test('la charge est fusionnee dans le message', async () => {
  const attente = demanderHote('outil', { nom: 'revit_etat', arguments: { a: 1 } });
  assert.equal(dernier().nom, 'revit_etat');
  assert.deepEqual(dernier().arguments, { a: 1 });
  reponseHote({ ref: dernier().ref, sortie: '{}' });
  await attente;
});

test('deux demandes en vol ne se repondent pas l’une a l’autre', async () => {
  // Le defaut que l'appariement existe pour empecher.
  const une = demanderHote('outil', { nom: 'un' });
  const refUne = dernier().ref;
  const deux = demanderHote('outil', { nom: 'deux' });
  const refDeux = dernier().ref;
  assert.notEqual(refUne, refDeux);

  reponseHote({ ref: refDeux, sortie: 'DEUX' });
  reponseHote({ ref: refUne, sortie: 'UNE' });
  assert.equal(await une, 'UNE');
  assert.equal(await deux, 'DEUX');
});

test('une reponse sans demande en vol est ignoree', () => {
  assert.equal(reponseHote({ ref: 'd9999', sortie: 'x' }), false);
});

test('une erreur de l’hote rejette la promesse', async () => {
  const attente = demanderHote('outil', { nom: 'x' });
  reponseHote({ ref: dernier().ref, erreur: 'aucun document Revit ouvert' });
  await assert.rejects(() => attente, /aucun document Revit ouvert/);
});

test('une reponse en double ne rejoue rien', async () => {
  const attente = demanderHote('outil', { nom: 'x' });
  const ref = dernier().ref;
  assert.equal(reponseHote({ ref, sortie: 'premiere' }), true);
  assert.equal(reponseHote({ ref, sortie: 'seconde' }), false);
  assert.equal(await attente, 'premiere');
});

test('couper rejette sans attendre la fin de l’outil', async () => {
  // L'hote continuera son travail, mais plus personne ne l'ecoute.
  const stop = new AbortController();
  const attente = demanderHote('outil', { nom: 'lent' }, stop.signal);
  stop.abort();
  await assert.rejects(() => attente, /interrompu/);
});

test('une reponse arrivee apres l’interruption ne leve pas', async () => {
  const stop = new AbortController();
  const attente = demanderHote('outil', { nom: 'lent' }, stop.signal);
  const ref = dernier().ref;
  stop.abort();
  await assert.rejects(() => attente, /interrompu/);
  assert.equal(reponseHote({ ref, sortie: 'trop tard' }), false);
});

test('un hote muet finit par rendre la main', async () => {
  // Sans delai, un tour reste pendu pour toujours.
  mock.timers.enable({ apis: ['setTimeout'] });
  try {
    const attente = demanderHote('outil', { nom: 'muet' });
    mock.timers.tick(60001);
    await assert.rejects(() => attente, /n'a pas répondu/);
  } finally {
    mock.timers.reset();
  }
});
