// Abonnement ChatGPT — le backend Responses, par le tuyau de l'hôte.
//
// Mesuré : `chatgpt.com/backend-api` ne renvoie aucun
// `Access-Control-Allow-Origin`, et `allow-credentials` interdit le `*`. Une
// page ne peut pas lire la réponse. L'égress passe donc par Python — c'est la
// seule différence avec `openai.js`, qui appelle en direct.
//
// **Le protocole reste ici.** `harnais/oauth.py` ne sait pas ce qu'est un item
// Responses : il poste un corps déjà formé et renvoie les lignes du flux une à
// une. Un fournisseur, un module, comme pour la clé API.
//
// Et ce n'est PAS `/v1/chat/completions` : les outils sont à plat (pas de
// niveau `function`), l'entrée est une liste d'items typés, et `store: false`
// est exigé par le backend. Les deux protocoles ne se confondent pas.

import { SYSTEME } from './openai.js';

// Le backend Codex a son propre nommage de modèles. Pas de liste en dur :
// elle vieillirait sans que rien ne le signale, et `/model` existe pour ça.
export const MODELE_DEFAUT = 'gpt-5.6-terra';

// `diffuser(corps, {signal, surLigne})` → promesse résolue en fin de flux.
// C'est le pont vers l'hôte, injecté pour que tout ici se teste sans WebView2.
export function fournisseurChatGPT({ modele = MODELE_DEFAUT, diffuser } = {}) {
  return async function repondre(messages, catalogue, ctx = {}) {
    const etat = { texte: '', appels: new Map(), final: [] };
    await diffuser(JSON.stringify(corps(messages, catalogue, modele)), {
      signal: ctx.signal,
      surLigne: (ligne) => avaler(etat, ligne, ctx),
    });
    // L'instantané final porte les MÊMES items que les évènements un à un :
    // on ne le lit que si le premier n'a rien donné. Les cumuler exécuterait
    // chaque outil deux fois.
    const lus = etat.appels.size ? [...etat.appels.values()] : etat.final;
    const appels = lus.map((a) => ({
      id: a.call_id || a.id,
      nom: a.name,
      arguments: json(a.arguments),
    }));
    return appels.length ? { texte: etat.texte, appels } : { texte: etat.texte };
  };
}

// --- le corps ---------------------------------------------------------------

export function corps(messages, catalogue, modele = MODELE_DEFAUT) {
  const charge = {
    model: modele,
    instructions: SYSTEME,
    input: entree(messages),
    // Exigé par le backend, ce n'est pas une préférence.
    store: false,
    stream: true,
  };
  if (catalogue?.length) {
    // Forme À PLAT : pas de niveau « function » intermédiaire, contrairement
    // à /v1/chat/completions. S'y tromper rend un 400 sur le corps entier.
    charge.tools = catalogue.map((o) => ({
      type: 'function',
      name: o.nom,
      description: o.description,
      strict: false,
      parameters: o.parametres || { type: 'object', properties: {} },
    }));
    charge.tool_choice = 'auto';
  }
  return charge;
}

export function entree(messages) {
  const items = [];
  for (const message of messages || []) {
    if (message.role === 'outil') {
      items.push({
        type: 'function_call_output',
        call_id: message.id,
        output: message.sortie || '',
      });
    } else if (message.appels?.length) {
      // L'item d'origine PUIS son résultat : le backend ne garde rien d'un
      // appel à l'autre (`store: false`), il faut lui rendre les deux.
      for (const appel of message.appels) {
        items.push({
          type: 'function_call',
          call_id: appel.id,
          name: appel.nom,
          arguments: JSON.stringify(appel.arguments || {}),
        });
      }
    } else {
      // L'assistant parle en `output_text`, l'utilisateur en `input_text` :
      // inverser les deux fait répondre un 400 au corps entier.
      const assistant = message.role === 'assistant';
      items.push({
        role: assistant ? 'assistant' : 'user',
        content: [{
          type: assistant ? 'output_text' : 'input_text',
          text: message.texte || '',
        }],
      });
    }
  }
  return items;
}

// --- la lecture du flux ------------------------------------------------------

export function avaler(etat, ligne, ctx = {}) {
  const evenement = json(ligne, null);
  const genre = evenement?.type || '';

  if (genre === 'response.output_text.delta' && evenement.delta) {
    etat.texte += evenement.delta;
    ctx.surTexte?.(evenement.delta);
    return etat;
  }
  if (genre === 'response.reasoning_summary_text.delta' && evenement.delta) {
    ctx.surRaisonnement?.(evenement.delta);
    return etat;
  }
  if (genre === 'response.output_item.done') {
    const item = evenement.item || {};
    // Clé par `call_id` : un item redit deux fois ne doit pas lancer deux
    // appels. Le backend répète parfois le dernier item avant de conclure.
    if (item.type === 'function_call') etat.appels.set(item.call_id, item);
    return etat;
  }
  if (genre === 'response.completed' || genre === 'response.done') {
    const sortie = evenement.response?.output || [];
    etat.final = sortie.filter((i) => i.type === 'function_call');
    // Un refus se glisse dans le flux sans jamais passer par un delta.
    const texteFinal = sortie
      .filter((i) => i.type === 'message')
      .flatMap((i) => i.content || [])
      .filter((c) => c.type === 'output_text' || c.type === 'text')
      .map((c) => c.text || '').join('');
    if (!etat.texte && texteFinal) {
      etat.texte = texteFinal;
      ctx.surTexte?.(texteFinal);
    }
    return etat;
  }
  if (genre === 'response.failed' || genre === 'error') {
    const souci = evenement.response?.error?.message
      || evenement.error?.message || evenement.message;
    if (souci) throw new Error(souci);
  }
  return etat;
}

function json(brut, defaut = {}) {
  try {
    const lu = JSON.parse(brut || '');
    return lu ?? defaut;
  } catch {
    // Un modèle qui bafouille son JSON ne doit pas faire échouer le tour :
    // l'outil est appelé sans argument et dira lui-même ce qui manque.
    return defaut;
  }
}
