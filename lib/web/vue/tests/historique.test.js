// node --test "lib/web/**/tests/*.test.js"

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Historique } from '../historique.js';

const rempli = (...lignes) => {
  const h = new Historique();
  for (const l of lignes) h.ajouter(l);
  return h;
};

test('vide, les fleches ne rendent rien', () => {
  const h = new Historique();
  assert.equal(h.precedent('brouillon'), null);
  assert.equal(h.suivant(), null);
});

test('le plus recent vient en premier', () => {
  const h = rempli('un', 'deux', 'trois');
  assert.equal(h.precedent(), 'trois');
  assert.equal(h.precedent(), 'deux');
  assert.equal(h.precedent(), 'un');
});

test('en haut de l’anneau, on RESTE sur la plus ancienne', () => {
  // Rendre null viderait le champ, ce qui se lit comme une perte.
  const h = rempli('un', 'deux');
  h.precedent(); h.precedent();
  assert.equal(h.precedent(), null);
});

test('le brouillon revient quand on redescend', () => {
  // La faute classique : appuyer sur ↑ par curiosite et perdre ce qu'on
  // etait en train d'ecrire.
  const h = rempli('deja envoye');
  assert.equal(h.precedent('ce que j’ecrivais'), 'deja envoye');
  assert.equal(h.suivant(), 'ce que j’ecrivais');
});

test('redescendre depuis le present ne rend rien', () => {
  const h = rempli('un');
  assert.equal(h.suivant(), null);
});

test('monter puis redescendre repasse par les memes', () => {
  const h = rempli('un', 'deux', 'trois');
  h.precedent('x');
  h.precedent();
  assert.equal(h.suivant(), 'trois');
  assert.equal(h.suivant(), 'x');
});

test('envoyer remet au present', () => {
  const h = rempli('un', 'deux');
  h.precedent('x');
  assert.equal(h.parcourt, true);
  h.ajouter('trois');
  assert.equal(h.parcourt, false);
  assert.equal(h.precedent(), 'trois');
});

test('le vide et les espaces ne sont pas retenus', () => {
  const h = rempli('un', '', '   ', '\n');
  assert.deepEqual(h.lignes, ['un']);
});

test('les espaces autour sont rognes', () => {
  assert.deepEqual(rempli('  un  ').lignes, ['un']);
});

test('deux fois la meme d’affilee ne compte qu’une', () => {
  // Sinon l'anneau se remplit de doublons qu'il faut franchir un par un.
  assert.deepEqual(rempli('un', 'un', 'un').lignes, ['un']);
});

test('la meme, plus loin, compte quand meme', () => {
  assert.deepEqual(rempli('un', 'deux', 'un').lignes, ['un', 'deux', 'un']);
});

test('le plafond jette les plus anciennes', () => {
  const h = new Historique(3);
  for (const l of ['a', 'b', 'c', 'd']) h.ajouter(l);
  assert.deepEqual(h.lignes, ['d', 'c', 'b']);
});

test('reinitialiser oublie le brouillon', () => {
  const h = rempli('un');
  h.precedent('x');
  h.reinitialiser();
  assert.equal(h.parcourt, false);
  assert.equal(h.suivant(), null);
});
