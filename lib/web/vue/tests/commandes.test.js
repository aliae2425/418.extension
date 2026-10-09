// node --test "lib/web/**/tests/*.test.js"

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { analyser } from '../commandes.js';

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
