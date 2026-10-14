// node --test "lib/web/**/tests/*.test.js"
//
// La sélection et le filtre sont les deux seuls morceaux de la page qui ne
// touchent pas au DOM — et les deux seuls qui ont des cas limites. Le reste
// est du câblage, il se voit à l'écran.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { clic } from '../selection.js';
import { filtrer, normaliser, pluriel } from '../dom.js';

const VISIBLES = [1, 2, 3, 4, 5];

test('un clic coche, un second decoche', () => {
  const coches = new Set();
  let ancre = clic(coches, null, VISIBLES, 3);
  assert.deepEqual([...coches], [3]);
  assert.equal(ancre, 3);
  ancre = clic(coches, ancre, VISIBLES, 3);
  assert.deepEqual([...coches], []);
});

test('Maj etend depuis l’ancre, dans les deux sens', () => {
  const coches = new Set();
  const ancre = clic(coches, null, VISIBLES, 4);
  clic(coches, ancre, VISIBLES, 2, { shift: true });
  assert.deepEqual([...coches].sort(), [2, 3, 4]);
});

test('l’ancre ne bouge pas sous Maj', () => {
  // Deux Maj de suite etendent la MEME plage au lieu de la faire glisser.
  const coches = new Set();
  const ancre = clic(coches, null, VISIBLES, 2);
  const apres = clic(coches, ancre, VISIBLES, 4, { shift: true });
  assert.equal(apres, 2);
  clic(coches, apres, VISIBLES, 5, { shift: true });
  assert.deepEqual([...coches].sort(), [2, 3, 4, 5]);
});

test('Maj sans ancre vaut une simple bascule', () => {
  const coches = new Set();
  const ancre = clic(coches, null, VISIBLES, 3, { shift: true });
  assert.deepEqual([...coches], [3]);
  assert.equal(ancre, 3);
});

test('une ancre sortie du filtre ne fait pas de plage fantome', () => {
  // L'ancre a ete posee avant une recherche qui l'a fait disparaitre : la
  // plage n'a plus de borne, on retombe sur une bascule.
  const coches = new Set();
  const ancre = clic(coches, 99, [3, 4, 5], 5, { shift: true });
  assert.deepEqual([...coches], [5]);
  assert.equal(ancre, 5);
});

test('une ligne qui n’est plus affichee ne change rien', () => {
  const coches = new Set([1]);
  const ancre = clic(coches, 1, [3, 4], 1);
  assert.deepEqual([...coches], [1]);
  assert.equal(ancre, 1);
});

test('la plage ne prend que ce qui est AFFICHE', () => {
  // Avec un filtre actif, Maj saute les lignes masquees : elle prend ce que
  // l'utilisateur voit entre les deux clics, pas la liste complete.
  const coches = new Set();
  const visibles = [1, 4, 5];
  const ancre = clic(coches, null, visibles, 1);
  clic(coches, ancre, visibles, 5, { shift: true });
  assert.deepEqual([...coches].sort(), [1, 4, 5]);
});

test('le filtre ignore la casse et les accents', () => {
  const items = [{ nom: 'Béton coulé' }, { nom: 'BA13' }];
  const trouves = filtrer(items, 'beton', [(i) => i.nom]);
  assert.deepEqual(trouves.map((i) => i.nom), ['Béton coulé']);
  assert.equal(normaliser('Béton'), 'beton');
});

test('un filtre vide rend toute la liste', () => {
  const items = [{ nom: 'a' }, { nom: 'b' }];
  assert.equal(filtrer(items, '   ', [(i) => i.nom]).length, 2);
});

test('le filtre porte sur TOUS les getters', () => {
  const items = [{ nom: 'BA13', type: 'dessin' },
                 { nom: 'Briques', type: 'modèle' }];
  const trouves = filtrer(items, 'modele', [(i) => i.nom, (i) => i.type]);
  assert.deepEqual(trouves.map((i) => i.nom), ['Briques']);
});

test('le pluriel se pose tout seul', () => {
  assert.equal(pluriel(1, 'matériau', 'matériaux'), '1 matériau');
  assert.equal(pluriel(3, 'matériau', 'matériaux'), '3 matériaux');
  assert.equal(pluriel(2, 'élément'), '2 éléments');
});
