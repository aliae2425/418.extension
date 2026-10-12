// node --test "lib/web/**/tests/*.test.js"
//
// Aucun réseau. Ce qu'on éprouve, c'est la traduction vers le protocole
// Messages — qui ne ressemble à AUCUN des deux autres, et dont chaque écart
// rend un 400 sur le corps entier sans dire lequel des blocs est en cause.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  fournisseurAnthropic, corps, fusionner, lire, avaler,
  SENTINELLE, VERSION_API, MODELE_DEFAUT, SORTIE_MAX, PREFIXE_CLE,
} from '../fournisseurs/anthropic.js';
import { SYSTEME } from '../fournisseurs/openai.js';

function flux(...morceaux) {
  return new ReadableStream({
    start(c) {
      const encodeur = new TextEncoder();
      for (const m of morceaux) c.enqueue(encodeur.encode(m));
      c.close();
    },
  });
}

const sse = (objet) => `data: ${JSON.stringify(objet)}\n\n`;
const txt = (texte, index = 0) => sse({
  type: 'content_block_delta', index, delta: { type: 'text_delta', text: texte },
});

// --- le corps ---------------------------------------------------------------

test('l’invite systeme est un parametre de PREMIER NIVEAU', () => {
  // L'envoyer en message de role « system » est un 400 : Anthropic ne
  // connait que `user` et `assistant`.
  const c = corps([{ role: 'utilisateur', texte: 'salut' }], []);
  assert.equal(c.system, SYSTEME);
  assert.equal(c.messages.some((m) => m.role === 'system'), false);
  assert.equal(c.model, MODELE_DEFAUT);
  assert.equal(c.stream, true);
});

test('max_tokens est TOUJOURS pose', () => {
  // Il est obligatoire chez Anthropic : l'omettre est un refus net.
  assert.equal(corps([], []).max_tokens, SORTIE_MAX);
  assert.equal(corps([], [], 'm', 1234).max_tokens, 1234);
});

test('un outil se decrit par input_schema, pas parameters', () => {
  const c = corps([], [{
    nom: 'revit_etat',
    description: 'etat du document',
    parametres: { type: 'object', properties: { a: { type: 'string' } } },
  }]);
  assert.equal(c.tools[0].name, 'revit_etat');
  assert.deepEqual(c.tools[0].input_schema.properties, { a: { type: 'string' } });
  assert.equal(c.tools[0].parameters, undefined);
  assert.equal(c.tools[0].function, undefined);
});

test('un catalogue vide n’envoie pas de tools', () => {
  assert.equal('tools' in corps([], []), false);
});

// --- les messages ------------------------------------------------------------

test('un resultat d’outil revient en message USER', () => {
  // Il n'y a pas de role `tool` chez Anthropic. C'est l'ecart le plus
  // surprenant des trois protocoles.
  const lus = fusionner([{ role: 'outil', id: 'toolu_1', sortie: '{"ok":1}' }]);
  assert.deepEqual(lus, [{
    role: 'user',
    content: [{ type: 'tool_result', tool_use_id: 'toolu_1', content: '{"ok":1}' }],
  }]);
});

test('les arguments d’un appel partent en OBJET, pas en chaine', () => {
  // L'inverse d'OpenAI, qui les veut serialises.
  const lus = fusionner([{
    role: 'assistant',
    appels: [{ id: 'toolu_1', nom: 'revit_vues', arguments: { limite: 50 } }],
  }]);
  assert.deepEqual(lus[0].content[0].input, { limite: 50 });
});

test('deux messages du MEME role se fusionnent', () => {
  // Anthropic refuse deux `user` d'affilee. Deux outils executes l'un apres
  // l'autre produisent exactement ca.
  const lus = fusionner([
    { role: 'outil', id: 'a', sortie: '1' },
    { role: 'outil', id: 'b', sortie: '2' },
  ]);
  assert.equal(lus.length, 1);
  assert.equal(lus[0].role, 'user');
  assert.equal(lus[0].content.length, 2);
});

test('un tour complet garde l’ordre user, assistant, user', () => {
  const lus = fusionner([
    { role: 'utilisateur', texte: 'etat' },
    { role: 'assistant', appels: [{ id: 'a', nom: 'revit_etat', arguments: {} }] },
    { role: 'outil', id: 'a', sortie: '{}' },
  ]);
  assert.deepEqual(lus.map((m) => m.role), ['user', 'assistant', 'user']);
  assert.equal(lus[1].content[0].type, 'tool_use');
  assert.equal(lus[2].content[0].type, 'tool_result');
});

// --- le flux ----------------------------------------------------------------

test('le texte arrive par deltas', async () => {
  const vus = [];
  const sortie = await lire(flux(txt('bon'), txt('jour')),
    { surTexte: (m) => vus.push(m) });
  assert.deepEqual(vus, ['bon', 'jour']);
  assert.equal(sortie.texte, 'bonjour');
  assert.equal(sortie.appels, undefined);
});

test('le raisonnement passe par son propre rappel', async () => {
  const pensees = [];
  await lire(flux(sse({
    type: 'content_block_delta', index: 0,
    delta: { type: 'thinking_delta', thinking: 'je cherche' },
  })), { surRaisonnement: (m) => pensees.push(m) });
  assert.deepEqual(pensees, ['je cherche']);
});

test('un appel d’outil se reconstitue depuis partial_json', async () => {
  // Les arguments arrivent en morceaux de JSON — `partial_json`, pas
  // `arguments`. Les traiter comme complets donne du JSON tronque.
  const sortie = await lire(flux(
    sse({ type: 'content_block_start', index: 0,
      content_block: { type: 'tool_use', id: 'toolu_1', name: 'revit_vues' } }),
    sse({ type: 'content_block_delta', index: 0,
      delta: { type: 'input_json_delta', partial_json: '{"lim' } }),
    sse({ type: 'content_block_delta', index: 0,
      delta: { type: 'input_json_delta', partial_json: 'ite":5}' } }),
  ));
  assert.deepEqual(sortie.appels,
    [{ id: 'toolu_1', nom: 'revit_vues', arguments: { limite: 5 } }]);
});

test('deux outils a des index differents ne se melangent pas', async () => {
  const sortie = await lire(flux(
    sse({ type: 'content_block_start', index: 0,
      content_block: { type: 'tool_use', id: 'a', name: 'un' } }),
    sse({ type: 'content_block_start', index: 1,
      content_block: { type: 'tool_use', id: 'b', name: 'deux' } }),
    sse({ type: 'content_block_delta', index: 1,
      delta: { type: 'input_json_delta', partial_json: '{}' } }),
    sse({ type: 'content_block_delta', index: 0,
      delta: { type: 'input_json_delta', partial_json: '{}' } }),
  ));
  assert.deepEqual(sortie.appels.map((a) => [a.id, a.nom]), [['a', 'un'], ['b', 'deux']]);
});

test('texte ET outil dans la meme reponse', async () => {
  // Claude commente volontiers avant d'appeler. Perdre l'un des deux est
  // le defaut classique.
  const sortie = await lire(flux(
    sse({ type: 'content_block_start', index: 0, content_block: { type: 'text' } }),
    txt('je regarde'),
    sse({ type: 'content_block_start', index: 1,
      content_block: { type: 'tool_use', id: 'a', name: 'revit_etat' } }),
    sse({ type: 'content_block_delta', index: 1,
      delta: { type: 'input_json_delta', partial_json: '{}' } }),
  ));
  assert.equal(sortie.texte, 'je regarde');
  assert.equal(sortie.appels.length, 1);
});

test('une ligne coupee en plein milieu se recolle', async () => {
  const entier = txt('coupe');
  assert.equal((await lire(flux(entier.slice(0, 18), entier.slice(18)))).texte,
    'coupe');
});

test('une ligne illisible n’interrompt pas le flux', async () => {
  assert.equal((await lire(flux('data: {pas du json\n\n', txt('ok')))).texte, 'ok');
});

test('une erreur dans le flux leve avec son message', async () => {
  await assert.rejects(() => lire(flux(sse({
    type: 'error', error: { message: 'overloaded_error' },
  }))), /overloaded_error/);
});

test('des arguments illisibles donnent un appel SANS argument', async () => {
  const sortie = await lire(flux(
    sse({ type: 'content_block_start', index: 0,
      content_block: { type: 'tool_use', id: 'a', name: 'x' } }),
    sse({ type: 'content_block_delta', index: 0,
      delta: { type: 'input_json_delta', partial_json: '{nawak' } }),
  ));
  assert.deepEqual(sortie.appels, [{ id: 'a', nom: 'x', arguments: {} }]);
});

// --- la clé et les erreurs ---------------------------------------------------

test('la page n’envoie qu’une SENTINELLE, et les trois en-tetes', async () => {
  let vu = null;
  const repondre = fournisseurAnthropic({
    recuperer: async (_url, options) => {
      vu = options;
      return { ok: true, body: flux(txt('x')) };
    },
  });
  await repondre([{ role: 'utilisateur', texte: 'x' }], []);
  assert.equal(vu.headers['x-api-key'], SENTINELLE);
  assert.equal(vu.headers['anthropic-version'], VERSION_API);
  // Sans lui, le navigateur se fait refuser avant d'avoir rien demande.
  assert.equal(vu.headers['anthropic-dangerous-direct-browser-access'], 'true');
  assert.equal(JSON.stringify(vu).includes('sk-ant-'), false);
});

test('l’en-tete d’authentification n’est PAS Authorization', () => {
  // C'est `x-api-key` chez Anthropic. S'y tromper rend un 401 opaque.
  assert.equal(PREFIXE_CLE, 'sk-ant-');
});

test('un 401 dit quoi faire', async () => {
  const repondre = fournisseurAnthropic({
    recuperer: async () => ({ ok: false, status: 401, text: async () => '{}' }),
  });
  await assert.rejects(() => repondre([], []), /sk-ant-/);
});

test('un 429 distingue le quota du reste', async () => {
  const repondre = fournisseurAnthropic({
    recuperer: async () => ({
      ok: false, status: 429,
      text: async () => JSON.stringify({ error: { message: 'rate limit' } }),
    }),
  });
  await assert.rejects(() => repondre([], []), /429 — quota ou cadence/);
});

test('le signal d’interruption est transmis', async () => {
  let vu = null;
  const stop = new AbortController();
  const repondre = fournisseurAnthropic({
    recuperer: async (_u, o) => { vu = o.signal; return { ok: true, body: flux(txt('x')) }; },
  });
  await repondre([], [], { signal: stop.signal });
  assert.equal(vu, stop.signal);
});
