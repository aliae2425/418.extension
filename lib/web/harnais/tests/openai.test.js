// node --test "lib/web/**/tests/*.test.js"
//
// Aucun réseau : `fetch` est remplacé, et les flux SSE sont fabriqués à la
// main. Ce qu'on éprouve, c'est la traduction de protocole — la seule chose
// dans ce module qui puisse être fausse sans qu'un 200 le dise.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  fournisseurOpenAI, corps, lire, fusionner, evenements, modeles,
  SENTINELLE, SYSTEME, MODELE_DEFAUT,
} from '../fournisseurs/openai.js';

// Un corps de réponse SSE, découpé où l'on veut pour éprouver le tampon.
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
const bout = (delta) => sse({ choices: [{ delta }] });

// --- le corps ---------------------------------------------------------------

test('le prompt système est posé en tête', () => {
  const c = corps([{ role: 'utilisateur', texte: 'salut' }], []);
  assert.equal(c.messages[0].role, 'system');
  assert.equal(c.messages[0].content, SYSTEME);
  assert.equal(c.model, MODELE_DEFAUT);
  assert.equal(c.stream, true);
});

test('nos rôles deviennent les leurs', () => {
  const c = corps([
    { role: 'utilisateur', texte: 'combien de vues' },
    { role: 'assistant', texte: 'quarante-sept' },
  ], []);
  assert.deepEqual(c.messages.slice(1), [
    { role: 'user', content: 'combien de vues' },
    { role: 'assistant', content: 'quarante-sept' },
  ]);
});

test('les arguments d’un appel repartent en CHAÎNE JSON', () => {
  // Les envoyer en objet rend un 400 sur le corps entier, sans dire lequel
  // des messages est en cause.
  const c = corps([{
    role: 'assistant',
    appels: [{ id: 'call_1', nom: 'revit_vues', arguments: { limite: 50 } }],
  }], []);
  const appel = c.messages[1].tool_calls[0];
  assert.equal(appel.function.arguments, '{"limite":50}');
  assert.equal(appel.function.name, 'revit_vues');
  assert.equal(c.messages[1].content, null);
});

test('un resultat d’outil porte son tool_call_id', () => {
  const c = corps([{ role: 'outil', id: 'call_1', nom: 'x', sortie: '{"ok":1}' }], []);
  assert.deepEqual(c.messages[1],
    { role: 'tool', tool_call_id: 'call_1', content: '{"ok":1}' });
});

test('un catalogue vide n’envoie NI tools NI tool_choice', () => {
  // C'est le dernier tour impose par le plafond : annoncer des outils qu'on
  // refusera d'executer ferait boucler la conversation.
  const c = corps([{ role: 'utilisateur', texte: 'x' }], []);
  assert.equal('tools' in c, false);
  assert.equal('tool_choice' in c, false);
});

test('le catalogue devient des fonctions', () => {
  const c = corps([], [{
    nom: 'revit_etat',
    description: 'etat du document',
    parametres: { type: 'object', properties: { a: { type: 'string' } } },
  }]);
  assert.equal(c.tools[0].type, 'function');
  assert.equal(c.tools[0].function.name, 'revit_etat');
  assert.deepEqual(c.tools[0].function.parameters.properties, { a: { type: 'string' } });
  assert.equal(c.tool_choice, 'auto');
});

// --- le flux ----------------------------------------------------------------

test('le texte arrive morceau par morceau', async () => {
  const vus = [];
  const sortie = await lire(flux(bout({ content: 'bon' }), bout({ content: 'jour' })),
    { surTexte: (m) => vus.push(m) });
  assert.deepEqual(vus, ['bon', 'jour']);
  assert.equal(sortie.texte, 'bonjour');
  assert.equal(sortie.appels, undefined);
});

test('une ligne coupee en plein milieu se recolle', async () => {
  // Un `data:` peut etre scinde entre deux morceaux reseau. Sans tampon,
  // l'evenement est perdu et le texte arrive troue.
  const entier = bout({ content: 'coupe' });
  const sortie = await lire(flux(entier.slice(0, 20), entier.slice(20)));
  assert.equal(sortie.texte, 'coupe');
});

test('[DONE] et les lignes vides sont ignores', async () => {
  const sortie = await lire(flux('\n', 'data: [DONE]\n\n', ': ping\n\n',
    bout({ content: 'x' })));
  assert.equal(sortie.texte, 'x');
});

test('un evenement illisible ne fait pas echouer le flux', async () => {
  const sortie = await lire(flux('data: {pas du json\n\n', bout({ content: 'ok' })));
  assert.equal(sortie.texte, 'ok');
});

test('un appel d’outil se reconstitue depuis ses morceaux', async () => {
  // L'id et le nom ne viennent qu'une fois, les arguments se concatenent.
  const sortie = await lire(flux(
    bout({ tool_calls: [{ index: 0, id: 'call_1', function: { name: 'revit_vues', arguments: '' } }] }),
    bout({ tool_calls: [{ index: 0, function: { arguments: '{"lim' } }] }),
    bout({ tool_calls: [{ index: 0, function: { arguments: 'ite":5}' } }] }),
  ));
  assert.deepEqual(sortie.appels, [
    { id: 'call_1', nom: 'revit_vues', arguments: { limite: 5 } },
  ]);
});

test('deux appels en parallele ne se melangent pas', async () => {
  const sortie = await lire(flux(
    bout({ tool_calls: [{ index: 0, id: 'a', function: { name: 'un', arguments: '{}' } }] }),
    bout({ tool_calls: [{ index: 1, id: 'b', function: { name: 'deux', arguments: '{}' } }] }),
  ));
  assert.deepEqual(sortie.appels.map((a) => [a.id, a.nom]), [['a', 'un'], ['b', 'deux']]);
});

test('des arguments illisibles donnent un appel SANS argument', async () => {
  // Un modele qui bafouille son JSON ne doit pas faire echouer le tour :
  // l'outil dira lui-meme ce qui manque.
  const sortie = await lire(flux(
    bout({ tool_calls: [{ index: 0, id: 'a', function: { name: 'x', arguments: '{nawak' } }] }),
  ));
  assert.deepEqual(sortie.appels, [{ id: 'a', nom: 'x', arguments: {} }]);
});

test('fusionner garde l’id et le nom poses une seule fois', () => {
  const appels = new Map();
  fusionner(appels, { index: 0, id: 'a', function: { name: 'nom', arguments: '{' } });
  fusionner(appels, { index: 0, function: { arguments: '}' } });
  assert.deepEqual([...appels.values()], [{ id: 'a', nom: 'nom', arguments: '{}' }]);
});

test('evenements rend des objets, pas des chaines', async () => {
  const lus = [];
  for await (const e of evenements(flux(sse({ a: 1 })))) lus.push(e);
  assert.deepEqual(lus, [{ a: 1 }]);
});

// --- la clé et les erreurs ---------------------------------------------------

test('la page n’envoie qu’une SENTINELLE, jamais une cle', async () => {
  let vu = null;
  const repondre = fournisseurOpenAI({
    recuperer: async (url, options) => {
      vu = options;
      return { ok: true, body: flux(bout({ content: 'x' })) };
    },
  });
  await repondre([{ role: 'utilisateur', texte: 'x' }], []);
  assert.equal(vu.headers.Authorization, SENTINELLE);
  assert.match(SENTINELLE, /418-hote/);
  assert.equal(JSON.stringify(vu).includes('sk-'), false);
});

test('un 401 se dit en clair, avec quoi faire', async () => {
  const repondre = fournisseurOpenAI({
    recuperer: async () => ({ ok: false, status: 401, text: async () => '{}' }),
  });
  await assert.rejects(() => repondre([], []), /OPENAI_API_KEY/);
});

test('une autre erreur rend le message de l’API', async () => {
  const repondre = fournisseurOpenAI({
    recuperer: async () => ({
      ok: false,
      status: 400,
      text: async () => JSON.stringify({ error: { message: 'modele inconnu' } }),
    }),
  });
  await assert.rejects(() => repondre([], []), /400 — modele inconnu/);
});

test('une erreur sans corps lisible ne masque pas le code', async () => {
  const repondre = fournisseurOpenAI({
    recuperer: async () => ({ ok: false, status: 500, text: async () => '<html>' }),
  });
  await assert.rejects(() => repondre([], []), /500 — sans détail/);
});

test('le signal d’interruption est transmis a fetch', async () => {
  let vu = null;
  const stop = new AbortController();
  const repondre = fournisseurOpenAI({
    recuperer: async (url, options) => {
      vu = options.signal;
      return { ok: true, body: flux(bout({ content: 'x' })) };
    },
  });
  await repondre([], [], { signal: stop.signal });
  assert.equal(vu, stop.signal);
});

// --- la liste des modèles ----------------------------------------------------

const catalogue = (...ids) => async () => ({
  ok: true,
  json: async () => ({ data: ids.map((x) => (typeof x === 'string' ? { id: x } : x)) }),
});

test('les modeles sont demandes au fournisseur, pas ecrits en dur', async () => {
  let vu = null;
  const noms = await modeles({
    recuperer: async (url, options) => {
      vu = { url, options };
      return { ok: true, json: async () => ({ data: [{ id: 'gpt-5' }] }) };
    },
  });
  assert.match(vu.url, /\/v1\/models$/);
  assert.equal(vu.options.headers.Authorization, SENTINELLE);
  assert.deepEqual(noms, ['gpt-5']);
});

test('ce qui ne converse pas est ecarte', async () => {
  // Proposer un modele d'embeddings dans un chat n'aide personne.
  const noms = await modeles({
    recuperer: catalogue('gpt-5', 'text-embedding-3-large', 'gpt-4o-audio-preview',
      'dall-e-3', 'o3-mini', 'tts-1', 'omni-moderation-latest'),
  });
  assert.deepEqual(noms, ['gpt-5', 'o3-mini']);
});

test('le plus recent vient en premier', async () => {
  const noms = await modeles({
    recuperer: catalogue({ id: 'gpt-vieux', created: 1 }, { id: 'gpt-neuf', created: 9 }),
  });
  assert.deepEqual(noms, ['gpt-neuf', 'gpt-vieux']);
});

test('une reponse sans data ne leve pas', async () => {
  assert.deepEqual(await modeles({
    recuperer: async () => ({ ok: true, json: async () => ({}) }),
  }), []);
});

test('une cle refusee se dit en clair', async () => {
  await assert.rejects(() => modeles({
    recuperer: async () => ({ ok: false, status: 401, text: async () => '{}' }),
  }), /OPENAI_API_KEY/);
});
