// node --test "lib/web/**/tests/*.test.js"
//
// Aucun réseau, aucun hôte : `diffuser` est remplacé. Ce qu'on éprouve, c'est
// la traduction vers le protocole Responses — qui n'est PAS
// /v1/chat/completions, et dont chaque écart rend un 400 sur le corps entier
// sans dire lequel des items est en cause.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  fournisseurChatGPT, corps, entree, avaler, MODELE_DEFAUT,
} from '../fournisseurs/chatgpt.js';
import { SYSTEME } from '../fournisseurs/openai.js';

// Un faux hôte qui rejoue des lignes de flux.
const tuyau = (...lignes) => async (_corps, opts) => {
  for (const ligne of lignes) opts.surLigne(ligne);
};

const ev = (objet) => JSON.stringify(objet);
const delta = (texte) => ev({ type: 'response.output_text.delta', delta: texte });

const etatNeuf = () => ({ texte: '', appels: new Map(), final: [] });

// --- le corps ---------------------------------------------------------------

test('les instructions sont posees a part, pas en message systeme', () => {
  // Responses porte le systeme dans `instructions` ; l'envoyer en message
  // de role « system » le ferait ignorer.
  const c = corps([{ role: 'utilisateur', texte: 'x' }], []);
  assert.equal(c.instructions, SYSTEME);
  assert.equal(c.model, MODELE_DEFAUT);
  assert.equal(c.store, false, 'store:false est EXIGE par le backend');
  assert.equal(c.stream, true);
  assert.equal(c.messages, undefined, 'Responses ne connait pas `messages`');
});

test('l’assistant parle en output_text, l’utilisateur en input_text', () => {
  // Inverser les deux fait repondre un 400 au corps entier.
  const items = entree([
    { role: 'utilisateur', texte: 'combien' },
    { role: 'assistant', texte: 'quarante-sept' },
  ]);
  assert.equal(items[0].content[0].type, 'input_text');
  assert.equal(items[0].role, 'user');
  assert.equal(items[1].content[0].type, 'output_text');
  assert.equal(items[1].role, 'assistant');
});

test('un appel d’outil devient un item function_call a plat', () => {
  const items = entree([{
    role: 'assistant',
    appels: [{ id: 'call_1', nom: 'revit_vues', arguments: { limite: 50 } }],
  }]);
  assert.deepEqual(items[0], {
    type: 'function_call',
    call_id: 'call_1',
    name: 'revit_vues',
    arguments: '{"limite":50}',
  });
});

test('le resultat repart en function_call_output, par call_id', () => {
  const items = entree([{ role: 'outil', id: 'call_1', sortie: '{"ok":1}' }]);
  assert.deepEqual(items[0], {
    type: 'function_call_output', call_id: 'call_1', output: '{"ok":1}',
  });
});

test('l’item d’origine PUIS son resultat — store:false n’en garde aucun', () => {
  const items = entree([
    { role: 'utilisateur', texte: 'etat' },
    { role: 'assistant', appels: [{ id: 'c1', nom: 'revit_etat', arguments: {} }] },
    { role: 'outil', id: 'c1', sortie: '{}' },
  ]);
  assert.deepEqual(items.map((i) => i.type || i.role),
    ['user', 'function_call', 'function_call_output']);
});

test('les outils sont A PLAT, sans niveau « function »', () => {
  // C'est la difference avec /v1/chat/completions, et elle est fatale.
  const c = corps([], [{
    nom: 'revit_etat',
    description: 'etat',
    parametres: { type: 'object', properties: {} },
  }]);
  assert.equal(c.tools[0].name, 'revit_etat');
  assert.equal(c.tools[0].type, 'function');
  assert.equal(c.tools[0].function, undefined);
  assert.equal(c.tools[0].strict, false);
  assert.equal(c.tool_choice, 'auto');
});

test('un catalogue vide n’envoie ni tools ni tool_choice', () => {
  const c = corps([], []);
  assert.equal('tools' in c, false);
  assert.equal('tool_choice' in c, false);
});

// --- le flux ----------------------------------------------------------------

test('le texte arrive par deltas', async () => {
  const vus = [];
  const repondre = fournisseurChatGPT({
    diffuser: tuyau(delta('bon'), delta('jour')),
  });
  const sortie = await repondre([], [], { surTexte: (m) => vus.push(m) });
  assert.deepEqual(vus, ['bon', 'jour']);
  assert.equal(sortie.texte, 'bonjour');
  assert.equal(sortie.appels, undefined);
});

test('le raisonnement passe par son propre rappel', async () => {
  const pensees = [];
  const repondre = fournisseurChatGPT({
    diffuser: tuyau(ev({
      type: 'response.reasoning_summary_text.delta', delta: 'je cherche',
    }), delta('voila')),
  });
  await repondre([], [], { surRaisonnement: (m) => pensees.push(m) });
  assert.deepEqual(pensees, ['je cherche']);
});

test('un appel d’outil est lu depuis output_item.done', async () => {
  const repondre = fournisseurChatGPT({
    diffuser: tuyau(ev({
      type: 'response.output_item.done',
      item: {
        type: 'function_call', call_id: 'c1',
        name: 'revit_vues', arguments: '{"limite":5}',
      },
    })),
  });
  const sortie = await repondre([], []);
  assert.deepEqual(sortie.appels,
    [{ id: 'c1', nom: 'revit_vues', arguments: { limite: 5 } }]);
});

test('l’instantane final n’est lu QUE si les evenements n’ont rien donne', async () => {
  // Les cumuler executerait chaque outil deux fois.
  const item = {
    type: 'function_call', call_id: 'c1', name: 'revit_etat', arguments: '{}',
  };
  const repondre = fournisseurChatGPT({
    diffuser: tuyau(
      ev({ type: 'response.output_item.done', item }),
      ev({ type: 'response.completed', response: { output: [item] } }),
    ),
  });
  const sortie = await repondre([], []);
  assert.equal(sortie.appels.length, 1);
});

test('sans evenement un a un, l’instantane final sert de repli', async () => {
  const item = {
    type: 'function_call', call_id: 'c9', name: 'revit_etat', arguments: '{}',
  };
  const repondre = fournisseurChatGPT({
    diffuser: tuyau(ev({ type: 'response.completed', response: { output: [item] } })),
  });
  const sortie = await repondre([], []);
  assert.deepEqual(sortie.appels.map((a) => a.id), ['c9']);
});

test('un item redit deux fois ne lance qu’un appel', async () => {
  const item = {
    type: 'function_call', call_id: 'c1', name: 'revit_etat', arguments: '{}',
  };
  const repondre = fournisseurChatGPT({
    diffuser: tuyau(
      ev({ type: 'response.output_item.done', item }),
      ev({ type: 'response.output_item.done', item }),
    ),
  });
  assert.equal((await repondre([], [])).appels.length, 1);
});

test('un refus glisse dans l’instantane final est recupere', async () => {
  // Il n'arrive par aucun delta : sans cette branche, la bulle reste vide.
  const repondre = fournisseurChatGPT({
    diffuser: tuyau(ev({
      type: 'response.completed',
      response: {
        output: [{
          type: 'message',
          content: [{ type: 'output_text', text: 'je ne peux pas faire ça' }],
        }],
      },
    })),
  });
  const vus = [];
  const sortie = await repondre([], [], { surTexte: (m) => vus.push(m) });
  assert.match(sortie.texte, /je ne peux pas/);
  assert.deepEqual(vus, ['je ne peux pas faire ça']);
});

test('un flux en echec leve avec le message du backend', async () => {
  const repondre = fournisseurChatGPT({
    diffuser: tuyau(ev({
      type: 'response.failed',
      response: { error: { message: 'quota depasse' } },
    })),
  });
  await assert.rejects(() => repondre([], []), /quota depasse/);
});

test('une ligne illisible n’interrompt pas le flux', () => {
  const etat = etatNeuf();
  avaler(etat, '{pas du json');
  avaler(etat, delta('ok'));
  assert.equal(etat.texte, 'ok');
});

test('des arguments illisibles donnent un appel SANS argument', async () => {
  const repondre = fournisseurChatGPT({
    diffuser: tuyau(ev({
      type: 'response.output_item.done',
      item: {
        type: 'function_call', call_id: 'c1', name: 'x', arguments: '{nawak',
      },
    })),
  });
  assert.deepEqual((await repondre([], [])).appels,
    [{ id: 'c1', nom: 'x', arguments: {} }]);
});

test('le signal d’interruption est transmis au tuyau', async () => {
  let vu = null;
  const stop = new AbortController();
  const repondre = fournisseurChatGPT({
    diffuser: async (_c, opts) => { vu = opts.signal; },
  });
  await repondre([], [], { signal: stop.signal });
  assert.equal(vu, stop.signal);
});

test('le modele impose l’emporte sur le defaut', async () => {
  let envoye = null;
  const repondre = fournisseurChatGPT({
    modele: 'gpt-5.6-terra-mini',
    diffuser: async (c) => { envoye = JSON.parse(c); },
  });
  await repondre([{ role: 'utilisateur', texte: 'x' }], []);
  assert.equal(envoye.model, 'gpt-5.6-terra-mini');
});
