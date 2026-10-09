// node --test "lib/web/**/tests/*.test.js"

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { analyser, filtrer, completer, CATALOGUE } from '../commandes.js';

test('une commande nue', () => {
  assert.deepEqual(analyser('/aide'), { nom: 'aide', arguments: '' });
});

test('une commande avec argument', () => {
  assert.deepEqual(analyser('/model gpt-5'), { nom: 'model', arguments: 'gpt-5' });
});

test('les espaces autour sont rognes', () => {
  assert.deepEqual(analyser('  /model   gpt-5  '),
    { nom: 'model', arguments: 'gpt-5' });
});

test('le nom est insensible a la casse', () => {
  assert.equal(analyser('/AIDE').nom, 'aide');
});

test('l’argument garde ses espaces internes', () => {
  // Une cle collee n'en a pas, mais un futur /vider "tout sauf X" en aurait.
  assert.equal(analyser('/model  un  deux ').arguments, 'un  deux');
});

test('du texte ordinaire n’est pas une commande', () => {
  assert.equal(analyser('liste mes vues'), null);
  assert.equal(analyser(''), null);
  assert.equal(analyser(null), null);
});

test('une barre seule n’est pas une commande', () => {
  assert.equal(analyser('/'), null);
  assert.equal(analyser('/ aide'), null);
});

test('un chemin colle par megarde n’est pas une commande', () => {
  // `/` interdit dans le nom : sinon « /c/Users/… » deviendrait /c.
  assert.equal(analyser('/c/Users/moi/plan.rvt'), null);
  assert.equal(analyser('/usr/bin'), null);
});

test('une question qui commence par une barre oblique passe au modele', () => {
  assert.equal(analyser('/2 des vues sont-elles vides ?'), null);
});

// --- les propositions --------------------------------------------------------

const noms = (texte) => filtrer(texte).map((c) => c.nom);

test('une barre seule propose tout', () => {
  assert.deepEqual(noms('/'), CATALOGUE.map((c) => c.nom));
});

test('la frappe filtre par prefixe', () => {
  assert.deepEqual(noms('/co'), ['connect']);
  assert.deepEqual(noms('/l'), ['logout']);
});

test('un prefixe sans correspondance ne propose rien', () => {
  assert.deepEqual(noms('/zzz'), []);
});

test('la casse n’empeche pas de proposer', () => {
  assert.deepEqual(noms('/CO'), ['connect']);
});

test('des qu’une espace suit, on n’est plus sur le NOM', () => {
  // On ecrit les arguments : proposer encore des noms serait du bruit.
  assert.deepEqual(noms('/connect '), []);
  assert.deepEqual(noms('/connect sk-abc'), []);
});

test('du texte ordinaire ne propose rien', () => {
  assert.deepEqual(noms('liste mes vues'), []);
  assert.deepEqual(noms(''), []);
  assert.deepEqual(noms('/c/Users'), []);
});

test('completer pose une espace SI la commande prend un argument', () => {
  // L'espace place le curseur la ou l'argument s'ecrit ; son absence dit
  // qu'il n'y a rien a ajouter.
  assert.equal(completer({ nom: 'connect', args: '[clé]' }), '/connect ');
  assert.equal(completer({ nom: 'aide', args: '' }), '/aide');
});

test('chaque commande du catalogue a une aide', () => {
  for (const c of CATALOGUE) {
    assert.ok(c.aide, `${c.nom} sans aide`);
    assert.match(c.nom, /^[a-z]+$/, `${c.nom} : le filtre ne le trouverait pas`);
  }
});
