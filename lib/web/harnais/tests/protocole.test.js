// node --test lib/web/harnais/tests/
//
// `node:test` est intégré depuis Node 18 : aucun runner, aucun framework,
// aucune dépendance. C'est la doctrine du dépôt — « scripts unittest nus » —
// transposée au JS.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as p from '../protocole.js';

function flux() {
  const recus = [];
  return [new p.Flux((e, c) => recus.push([e, c])), recus];
}

const de = (recus, evenement) => recus.filter(([e]) => e === evenement).map(([, c]) => c);

test('un genre inconnu est refusé à la construction', () => {
  assert.throws(() => new p.Part('p1', 'chanson'), /genre inconnu/);
});

test('json omet les champs vides', () => {
  // Une part pleine de clés vides se lit mal, et chaque clé inutile repart
  // à chaque évènement.
  const part = new p.Part('p1', p.TEXTE, { texte: 'bonjour' });
  assert.deepEqual(part.json(), { id: 'p1', genre: 'texte', texte: 'bonjour' });
});

test('json garde les arguments d’un outil', () => {
  const part = new p.Part('p1', p.OUTIL, {
    nom: 'revit_etat', arguments: { limite: 5 }, etat: p.EN_COURS,
  });
  const charge = part.json();
  assert.equal(charge.nom, 'revit_etat');
  assert.deepEqual(charge.arguments, { limite: 5 });
});

test('json omet un objet d’arguments vide', () => {
  const part = new p.Part('p1', p.OUTIL, { nom: 'revit_etat', arguments: {} });
  assert.equal('arguments' in part.json(), false);
});

test('les identifiants se suivent', () => {
  const [f, recus] = flux();
  f.ouvrir(p.TEXTE);
  f.ouvrir(p.ETAPE, { texte: 'hop' });
  assert.deepEqual(de(recus, p.NEUVE).map((c) => c.id), ['p1', 'p2']);
});

test('le delta porte le morceau, jamais le cumul', () => {
  // L'invariant qui sépare un flux d'un diaporama.
  const [f, recus] = flux();
  const part = f.ouvrir(p.TEXTE);
  f.ajouter(part, 'bon');
  f.ajouter(part, 'jour');
  assert.deepEqual(de(recus, p.DELTA).map((c) => c.morceau), ['bon', 'jour']);
  assert.equal(part.texte, 'bonjour');
});

test('un delta vide ne part pas', () => {
  const [f, recus] = flux();
  f.ajouter(f.ouvrir(p.TEXTE), '');
  assert.equal(de(recus, p.DELTA).length, 0);
});

test('changer un champ inconnu est refusé', () => {
  // Sans ça, une faute de frappe poserait un attribut neuf en silence et
  // l'interface ne verrait jamais le changement attendu.
  const [f] = flux();
  const part = f.ouvrir(p.OUTIL, { nom: 'revit_etat' });
  assert.throws(() => f.changer(part, { etta: p.FAIT }), /champ inconnu/);
});

test('changer émet la part entière, pas un morceau', () => {
  // Un changement d'état n'est pas incrémental : l'interface redessine.
  const [f, recus] = flux();
  const part = f.ouvrir(p.OUTIL, { nom: 'revit_etat', etat: p.EN_COURS });
  f.changer(part, { etat: p.FAIT, sortie: '{"ok":true}' });
  const [maj] = de(recus, p.MAJ);
  assert.equal(maj.etat, p.FAIT);
  assert.equal(maj.nom, 'revit_etat');
});

test('fini sans raison n’envoie pas de clé vide', () => {
  const [f, recus] = flux();
  f.fini();
  assert.deepEqual(de(recus, p.FINI), [{}]);
});

test('fini avec raison la porte', () => {
  const [f, recus] = flux();
  f.fini('interrompu');
  assert.deepEqual(de(recus, p.FINI), [{ raison: 'interrompu' }]);
});

test('dernierId suit la dernière part ouverte', () => {
  // C'est par lui que l'interface sait à QUELLE part répondre.
  const [f] = flux();
  assert.equal(f.dernierId(), '');
  f.ouvrir(p.TEXTE);
  assert.equal(f.dernierId(), 'p1');
  f.ouvrir(p.OUTIL, { nom: 'revit_synchroniser' });
  assert.equal(f.dernierId(), 'p2');
});
