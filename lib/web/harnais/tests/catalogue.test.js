// node --test "lib/web/**/tests/*.test.js"
//
// Aucun réseau : `fetch` est remplacé, le stockage est une Map. Ce qu'on
// éprouve, c'est la chaîne de replis — l'ordre entre cache, instantané et
// service, et ce qui se passe quand chacun manque ou ment.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  catalogue, fournisseursServis, modelesServis, resume, VERSION, URL_CATALOGUE,
} from '../catalogue.js';

const charge = (genere, modeles = { 'gpt-x': { nom: 'GPT X', outils: true } }) => ({
  version: VERSION,
  genere,
  fournisseurs: {
    openai: { nom: 'OpenAI', connexion: 'cle', modeles },
  },
});

function magasin(initial = null) {
  const carte = new Map(initial ? [['418.catalogue', JSON.stringify(initial)]] : []);
  return {
    getItem: (c) => carte.get(c) ?? null,
    setItem: (c, v) => carte.set(c, v),
    _carte: carte,
  };
}

const sert = (valeur, ok = true) => async () => ({
  ok, status: ok ? 200 : 503, json: async () => valeur,
});

// --- la chaîne de replis -----------------------------------------------------

test('sans rien, le catalogue est vide mais utilisable', () => {
  const c = catalogue({ stockage: magasin() });
  assert.deepEqual(c.fournisseurs, {});
  assert.equal(c.origine, 'vide');
});

test('l’instantane embarque sert au PREMIER lancement', () => {
  // Sans lui, `/connect` serait vide sur un poste hors ligne.
  const c = catalogue({ stockage: magasin(), embarque: charge('2026-01-01') });
  assert.equal(c.origine, 'embarque');
  assert.ok(c.fournisseurs.openai);
});

test('le cache l’emporte s’il est plus recent', () => {
  const c = catalogue({
    stockage: magasin(charge('2026-06-01')),
    embarque: charge('2026-01-01'),
  });
  assert.equal(c.origine, 'cache');
  assert.equal(c.genere, '2026-06-01');
});

test('l’instantane l’emporte s’il est plus recent que le cache', () => {
  // Une version fraichement livree doit battre un cache de six mois.
  const c = catalogue({
    stockage: magasin(charge('2026-01-01')),
    embarque: charge('2026-06-01'),
  });
  assert.equal(c.origine, 'embarque');
});

test('un cache corrompu est ignore, pas fatal', () => {
  const m = magasin();
  m.setItem('418.catalogue', '{pas du json');
  const c = catalogue({ stockage: m, embarque: charge('2026-01-01') });
  assert.equal(c.origine, 'embarque');
});

test('un cache d’une AUTRE version est ignore', () => {
  const vieux = { ...charge('2030-01-01'), version: 99 };
  const c = catalogue({ stockage: magasin(vieux), embarque: charge('2026-01-01') });
  assert.equal(c.origine, 'embarque');
});

// --- le rafraichissement -----------------------------------------------------

test('rafraichir range au cache et prend la main', async () => {
  const m = magasin();
  const c = catalogue({ stockage: m, embarque: charge('2026-01-01'),
    recuperer: sert(charge('2026-09-09')) });
  assert.equal(await c.rafraichir(), true);
  assert.equal(c.origine, 'service');
  assert.equal(c.genere, '2026-09-09');
  assert.match(m.getItem('418.catalogue'), /2026-09-09/);
});

test('un service en panne ne casse rien', async () => {
  // Un catalogue perime vaut mieux qu'un volet qui refuse de s'ouvrir.
  const c = catalogue({ stockage: magasin(), embarque: charge('2026-01-01'),
    recuperer: sert(null, false) });
  assert.equal(await c.rafraichir(), false);
  assert.equal(c.origine, 'embarque');
});

test('un service injoignable ne leve pas', async () => {
  const c = catalogue({ stockage: magasin(), embarque: charge('2026-01-01'),
    recuperer: async () => { throw new Error('DNS'); } });
  assert.equal(await c.rafraichir(), false);
  assert.equal(c.origine, 'embarque');
});

test('un service qui rend n’importe quoi est refuse', async () => {
  const c = catalogue({ stockage: magasin(), embarque: charge('2026-01-01'),
    recuperer: sert({ version: 99, fournisseurs: {} }) });
  assert.equal(await c.rafraichir(), false);
  assert.equal(c.origine, 'embarque');
});

test('l’URL par defaut est celle du service', () => {
  assert.equal(URL_CATALOGUE, 'https://cloud.418.archi/api.json');
});

// --- ce que l'interface en tire ----------------------------------------------

const DEUX = {
  openai: { nom: 'OpenAI', connexion: 'cle', modeles: {} },
  chatgpt: { nom: 'ChatGPT', connexion: 'abonnement', modeles: {} },
  mistral: { nom: 'Mistral', connexion: 'oauth-maison', modeles: {} },
};

test('un fournisseur qu’aucun adaptateur ne couvre n’est pas propose', () => {
  // Le proposer ouvrirait une voie sans issue.
  const lus = fournisseursServis(DEUX, ['cle', 'abonnement']).map((f) => f.id);
  assert.deepEqual(lus.sort(), ['chatgpt', 'openai']);
});

test('fournisseursServis survit a un catalogue vide', () => {
  assert.deepEqual(fournisseursServis(null, ['cle']), []);
  assert.deepEqual(fournisseursServis({}, ['cle']), []);
});

test('le defaut passe en tete, puis le plus recent', () => {
  const lus = modelesServis({ modeles: {
    vieux: { sorti: '2025-01-01' },
    neuf: { sorti: '2026-09-01' },
    prefere: { sorti: '2024-01-01', defaut: true },
  } }).map((m) => m.id);
  assert.deepEqual(lus, ['prefere', 'neuf', 'vieux']);
});

test('un modele sans outils est ecarte', () => {
  // Dans ce volet, il ne sert a rien.
  const lus = modelesServis({ modeles: {
    bon: { outils: true }, muet: { outils: false },
  } }).map((m) => m.id);
  assert.deepEqual(lus, ['bon']);
});

test('le resume dit ce qui aide a choisir', () => {
  assert.equal(
    resume({ limite: { contexte: 1050000 }, cout: { entree: 2 }, pieces: true,
      raisonnement: true }),
    '1050 k · 2 $/M · pièces · raisonne');
});

test('un cout NUL n’affiche pas « 0 $/M »', () => {
  // C'est un abonnement, pas un modele gratuit — le dire ainsi laisserait
  // croire que l'API ne facture rien.
  assert.equal(resume({ limite: { contexte: 1050000 }, cout: { entree: 0 } }),
    '1050 k');
});

test('le resume d’un modele sans metadonnees est vide, pas casse', () => {
  assert.equal(resume({}), '');
  assert.equal(resume(null), '');
});
