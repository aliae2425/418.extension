// node --test "lib/web/**/tests/*.test.js"
//
// L'arbre de `/model`. Ce qu'on éprouve : qu'on reste branché à PLUSIEURS
// fournisseurs à la fois, que choisir ailleurs bascule sans rien fermer, et
// que le filtre ne fasse pas disparaître ce qu'on cherche derrière un groupe
// replié.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { entreesModeles, connexionsVivantes, cleDe } from '../arbre.js';

const CONNEXIONS = ['abonnement', 'cle'];

// Deux maisons, trois portes — exactement la forme qui a motivé l'arbre.
const FOURNISSEURS = {
  openai: {
    nom: 'OpenAI',
    connexions: {
      abonnement: {
        nom: 'ChatGPT Plus / Pro',
        modeles: { 'gpt-5.6': { nom: 'GPT-5.6', defaut: true } },
      },
      cle: {
        nom: 'Clé API',
        modeles: { 'gpt-5.6': { nom: 'GPT-5.6' }, 'gpt-5.6-mini': { nom: 'GPT-5.6 mini' } },
      },
    },
  },
  anthropic: {
    nom: 'Anthropic',
    connexions: {
      cle: {
        nom: 'Clé API',
        modeles: { 'claude-fable-5': { nom: 'Claude Fable 5' } },
      },
    },
  },
};

const base = (extra = {}) => ({
  fournisseurs: FOURNISSEURS, connexions: CONNEXIONS, ...extra,
});

const groupes = (e) => e.filter((x) => x.groupe).map((x) => x.groupe);
const sous = (e) => e.filter((x) => x.sous);

// --- qui est vivant ----------------------------------------------------------

test('rien de branche, rien a montrer', () => {
  assert.deepEqual(
    connexionsVivantes(FOURNISSEURS, CONNEXIONS, { oauth: false, cles: {} }), []);
});

test('DEUX maisons branchees tiennent ensemble', () => {
  // Le cœur de la demande : poser une clé Anthropic n'éteint pas ChatGPT.
  const vus = connexionsVivantes(FOURNISSEURS, CONNEXIONS,
    { oauth: true, cles: { anthropic: true } });
  assert.deepEqual(vus.map((v) => v.cle).sort(),
    ['anthropic/cle', 'openai/abonnement']);
});

test('une cle OpenAI n’allume PAS la porte Anthropic', () => {
  // Les deux partagent l'identifiant de connexion `cle` : s'y tromper
  // proposerait des modèles Claude à une clé OpenAI, qui les refuserait.
  const vus = connexionsVivantes(FOURNISSEURS, CONNEXIONS,
    { oauth: false, cles: { openai: true } });
  assert.deepEqual(vus.map((v) => v.cle), ['openai/cle']);
});

test('l’abonnement ne depend QUE d’oauth, jamais d’une cle', () => {
  const vus = connexionsVivantes(FOURNISSEURS, CONNEXIONS,
    { oauth: false, cles: { openai: true } });
  assert.equal(vus.some((v) => v.c.id === 'abonnement'), false);
});

// --- l'arbre -----------------------------------------------------------------

const BRANCHE = { oauth: true, cles: { anthropic: true } };

test('replie, on ne voit que les en-tetes', () => {
  const e = entreesModeles(base({ branches: BRANCHE, ouverts: new Set() }));
  assert.deepEqual(groupes(e), ['openai/abonnement', 'anthropic/cle']);
  assert.equal(sous(e).length, 0);
});

test('deplier n’ouvre QUE le groupe deplie', () => {
  const e = entreesModeles(base({
    branches: BRANCHE, ouverts: new Set(['anthropic/cle']),
  }));
  assert.deepEqual(groupes(e), ['openai/abonnement', 'anthropic/cle']);
  assert.deepEqual(sous(e).map((x) => x.sous), ['anthropic/cle']);
});

test('le marqueur suit l’etat, et l’en-tete compte ses modeles', () => {
  const e = entreesModeles(base({
    branches: BRANCHE, ouverts: new Set(['anthropic/cle']),
  }));
  const [chatgpt, anthropic] = e.filter((x) => x.groupe);
  assert.ok(chatgpt.titre.startsWith('▸'));
  assert.ok(anthropic.titre.startsWith('▾'));
  assert.equal(anthropic.detail, '1 modèles');
});

test('« en cours » marque la connexion ET le modele actifs', () => {
  const e = entreesModeles(base({
    branches: BRANCHE,
    ouverts: new Set(['openai/abonnement', 'anthropic/cle']),
    actif: 'openai/abonnement',
    modeleActif: 'gpt-5.6',
  }));
  assert.equal(e.find((x) => x.groupe === 'openai/abonnement').args, 'en cours');
  assert.equal(e.find((x) => x.groupe === 'anthropic/cle').args, '');
  // Le MÊME nom de modèle sous une autre connexion ne doit pas être marqué :
  // c'est la paire (connexion, modèle) qui est active, pas le nom seul.
  const marques = e.filter((x) => x.sous && x.detail === 'en cours');
  assert.deepEqual(marques.map((x) => x.sous), ['openai/abonnement']);
});

test('ce que l’API a liste l’emporte sur le catalogue', () => {
  // Une clé restreinte ne voit pas tout : afficher le catalogue entier
  // proposerait des modèles qu'elle refuserait.
  const e = entreesModeles(base({
    branches: { oauth: false, cles: { anthropic: true } },
    ouverts: new Set(['anthropic/cle']),
    listes: new Map([['anthropic/cle', ['claude-haiku-5.5']]]),
  }));
  assert.deepEqual(sous(e).map((x) => x.titre), ['claude-haiku-5.5']);
});

// --- le filtre ---------------------------------------------------------------

test('filtrer APLATIT : plus d’en-tete, et les groupes replies s’ouvrent', () => {
  // Sans ça, chercher « claude » avec Anthropic replié ne rendrait rien.
  const e = entreesModeles(base({
    branches: BRANCHE, ouverts: new Set(),
  }), 'claude');
  assert.deepEqual(groupes(e), []);
  assert.ok(e.some((x) => x.cherche.includes('claude-fable-5')));
});

test('a plat, chaque ligne dit sa maison', () => {
  // Deux fournisseurs peuvent nommer un modèle pareil : sans la maison en
  // détail, les deux lignes seraient indiscernables.
  const e = entreesModeles(base({ branches: BRANCHE }), 'gpt');
  assert.equal(e.find((x) => x.sous === 'openai/abonnement').detail,
    'OpenAI · ChatGPT Plus / Pro');
});

test('la maison entre dans la recherche', () => {
  // L'arbre BÂTIT, il ne filtre pas — c'est la liste qui filtre sur
  // `cherche`. On refait ici ce qu'elle fait.
  const q = 'anthropic';
  const vus = entreesModeles(base({ branches: BRANCHE }), q)
    .filter((x) => x.cherche.toLowerCase().includes(q));
  // Taper le nom d'une maison sort SES modèles, pas rien du tout.
  assert.deepEqual(vus.map((x) => x.titre), ['Claude Fable 5']);
});

// --- les clics ---------------------------------------------------------------

test('un en-tete rappelle surGroupe, un modele rappelle surModele', () => {
  const vus = [];
  const e = entreesModeles(base({
    branches: BRANCHE,
    ouverts: new Set(['anthropic/cle']),
    surGroupe: (cle) => vus.push(['groupe', cle]),
    surModele: (f, c, nom) => vus.push(['modele', cleDe(f, c), nom]),
  }));
  e.find((x) => x.groupe === 'anthropic/cle').prendre();
  e.find((x) => x.sous === 'anthropic/cle').prendre();
  assert.deepEqual(vus, [
    ['groupe', 'anthropic/cle'],
    ['modele', 'anthropic/cle', 'claude-fable-5'],
  ]);
});
