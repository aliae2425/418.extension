// Anthropic, `/v1/messages`, en direct depuis la page.
//
// **Clé API seulement.** L'abonnement Claude Pro/Max n'est PAS proposé :
// Anthropic l'interdit explicitement, et opencode a retiré ses greffons pour
// cette raison en 1.3.0 — leur doc le dit en toutes lettres. On ne va pas où
// l'éditeur a écrit qu'il ne fallait pas, et on ne bâtit pas sur une porte
// qu'il peut fermer du jour au lendemain.
//
// L'appel direct est **sanctionné**, contrairement à OpenAI qui le tolère :
// `anthropic-dangerous-direct-browser-access` est un opt-in documenté, et
// mesuré ici (préflight 200, `Allow-Origin: *`, `x-api-key` autorisé).
// L'en-tête s'appelle « dangerous » parce qu'il suppose la clé DANS le
// navigateur ; chez nous l'hôte l'injecte, donc on a la voie directe sans le
// danger qui lui vaut son nom.
//
// Le protocole ne ressemble à AUCUN des deux autres, et chaque écart rend un
// 400 sur le corps entier :
//
//   - l'invite système est un paramètre de PREMIER NIVEAU, pas un message ;
//   - `max_tokens` est OBLIGATOIRE — l'omettre est un refus net ;
//   - un outil se décrit par `input_schema`, pas `parameters` ;
//   - un résultat d'outil revient en message `user`, pas dans un rôle à lui.

export const URL_API = 'https://api.anthropic.com/v1/messages';

// La version de l'API, figée. Anthropic date ses ruptures : ne pas la poser
// reviendrait à suivre la dernière, et à casser sans prévenir.
export const VERSION_API = '2023-06-01';

// Ce que l'hôte reconnaît et remplace. Même principe qu'OpenAI, autre
// en-tête : ici c'est `x-api-key`, pas `Authorization`.
export const SENTINELLE = '418-hote';

export const MODELE_DEFAUT = 'claude-fable-5';

// Obligatoire, donc il faut un chiffre. Assez large pour une réponse
// d'architecte, assez borné pour qu'une boucle ne coûte pas une fortune.
export const SORTIE_MAX = 8192;

// Les clés Anthropic commencent par `sk-ant-`. Sert à aiguiller un
// `/connect sk-…` tapé sans passer par l'assistant.
export const PREFIXE_CLE = 'sk-ant-';

// `sk-ant-oat…` n'est PAS une clé API : c'est le jeton OAuth d'un abonnement
// Claude Pro/Max, celui que pose `claude login`. Il se présente en
// `Authorization: Bearer` avec un en-tête `anthropic-beta` dédié, jamais en
// `x-api-key` — donc ici il rend 401, et le 401 ne dit pas pourquoi.
//
// On ne se contente pas de le router : c'est la voie qu'Anthropic interdit
// aux clients tiers, et qu'opencode a retirée pour cette raison. Mieux vaut
// le refuser en le nommant que l'accepter et laisser l'API mentir.
export const PREFIXE_ABONNEMENT = 'sk-ant-oat';

// Une vraie clé de console. Informatif : on n'exige pas ce préfixe, Anthropic
// peut en introduire d'autres.
export const PREFIXE_API = 'sk-ant-api';

export { SYSTEME } from './openai.js';
import { SYSTEME } from './openai.js';

export function fournisseurAnthropic({ modele = MODELE_DEFAUT, url = URL_API,
  recuperer = fetch, sortieMax = SORTIE_MAX } = {}) {
  return async function repondre(messages, catalogue, ctx = {}) {
    const reponse = await recuperer(url, {
      method: 'POST',
      signal: ctx.signal,
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': SENTINELLE,
        'anthropic-version': VERSION_API,
        // Sans lui, le navigateur se fait refuser avant d'avoir rien demandé.
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify(corps(messages, catalogue, modele, sortieMax)),
    });
    if (!reponse.ok) throw new Error(await detail(reponse));
    return lire(reponse.body, ctx);
  };
}

// --- le corps ---------------------------------------------------------------

export function corps(messages, catalogue, modele = MODELE_DEFAUT,
  sortieMax = SORTIE_MAX) {
  const charge = {
    model: modele,
    // PREMIER NIVEAU. L'envoyer en message de rôle « system » est un 400 :
    // Anthropic ne connaît que `user` et `assistant`.
    system: SYSTEME,
    max_tokens: sortieMax,
    messages: fusionner(messages),
    stream: true,
  };
  if (catalogue?.length) {
    charge.tools = catalogue.map((o) => ({
      name: o.nom,
      description: o.description,
      // `input_schema`, pas `parameters`. Même objet, autre nom, et c'est le
      // genre d'écart qu'on ne voit qu'au 400.
      input_schema: o.parametres || { type: 'object', properties: {} },
    }));
  }
  return charge;
}

// Notre forme interne → la leur. Deux règles qui n'ont pas d'équivalent
// ailleurs : un résultat d'outil est un message `user`, et deux messages du
// même rôle à la suite sont refusés — d'où la fusion.
export function fusionner(messages) {
  const sortie = [];
  const pousser = (role, bloc) => {
    const dernier = sortie[sortie.length - 1];
    if (dernier?.role === role) dernier.content.push(bloc);
    else sortie.push({ role, content: [bloc] });
  };

  for (const message of messages || []) {
    if (message.role === 'outil') {
      pousser('user', {
        type: 'tool_result',
        tool_use_id: message.id,
        content: message.sortie || '',
      });
    } else if (message.appels?.length) {
      for (const appel of message.appels) {
        pousser('assistant', {
          type: 'tool_use',
          id: appel.id,
          name: appel.nom,
          // Un OBJET ici, pas une chaîne JSON — l'inverse d'OpenAI.
          input: appel.arguments || {},
        });
      }
    } else {
      pousser(message.role === 'assistant' ? 'assistant' : 'user',
        { type: 'text', text: message.texte || '' });
    }
  }
  return sortie;
}

// --- la lecture du flux ------------------------------------------------------

export async function lire(corpsFlux, ctx = {}) {
  const etat = { texte: '', blocs: new Map() };
  for await (const evenement of evenements(corpsFlux)) {
    avaler(etat, evenement, ctx);
  }
  const appels = [...etat.blocs.values()]
    .filter((b) => b.type === 'tool_use')
    .map((b) => ({ id: b.id, nom: b.nom, arguments: json(b.arguments) }));
  return appels.length ? { texte: etat.texte, appels } : { texte: etat.texte };
}

export function avaler(etat, evenement, ctx = {}) {
  const genre = evenement?.type || '';

  // Un bloc s'OUVRE, puis se remplit par deltas. L'index est sa place : deux
  // outils appelés d'affilée ne se mélangent pas.
  if (genre === 'content_block_start') {
    const bloc = evenement.content_block || {};
    if (bloc.type === 'tool_use') {
      etat.blocs.set(evenement.index, {
        type: 'tool_use', id: bloc.id, nom: bloc.name, arguments: '',
      });
    } else {
      etat.blocs.set(evenement.index, { type: bloc.type });
    }
    return etat;
  }

  if (genre === 'content_block_delta') {
    const delta = evenement.delta || {};
    if (delta.type === 'text_delta' && delta.text) {
      etat.texte += delta.text;
      ctx.surTexte?.(delta.text);
    } else if (delta.type === 'thinking_delta' && delta.thinking) {
      ctx.surRaisonnement?.(delta.thinking);
    } else if (delta.type === 'input_json_delta') {
      // Les arguments arrivent en morceaux de JSON — `partial_json`, pas
      // `arguments`. Les traiter comme complets donne du JSON tronqué.
      const bloc = etat.blocs.get(evenement.index);
      if (bloc) bloc.arguments += delta.partial_json || '';
    }
    return etat;
  }

  if (genre === 'error') {
    const souci = evenement.error?.message;
    if (souci) throw new Error(souci);
  }
  return etat;
}

// Découpe un flux SSE en évènements JSON. Les lignes `event:` sont ignorées :
// le type est déjà dans la charge, et s'en servir éviterait de garder deux
// sources de vérité en accord.
export async function* evenements(corpsFlux) {
  const lecteur = corpsFlux.getReader();
  const decodeur = new TextDecoder();
  let tampon = '';
  try {
    for (;;) {
      const { value, done } = await lecteur.read();
      if (done) break;
      tampon += decodeur.decode(value, { stream: true });
      const lignes = tampon.split('\n');
      tampon = lignes.pop() ?? '';         // la dernière est peut-être tronquée
      for (const ligne of lignes) {
        const charge = utile(ligne);
        if (charge) yield charge;
      }
    }
    const reste = utile(tampon);
    if (reste) yield reste;
  } finally {
    lecteur.releaseLock?.();
  }
}

function utile(ligne) {
  const nu = ligne.trim();
  if (!nu.startsWith('data:')) return null;
  const charge = nu.slice(5).trim();
  if (!charge) return null;
  return json(charge, null);
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

async function detail(reponse) {
  let corpsTexte = '';
  try {
    corpsTexte = await reponse.text();
  } catch {
    corpsTexte = '';
  }
  const lu = json(corpsTexte, null);
  const message = lu?.error?.message || '';
  if (reponse.status === 401) {
    return 'HTTP 401 — clé Anthropic refusée. `/connect sk-ant-…` pour en '
      + 'poser une autre.';
  }
  if (reponse.status === 429) {
    return `HTTP 429 — quota ou cadence dépassés. ${message}`.trim();
  }
  return `HTTP ${reponse.status} — ${message || 'sans détail'}`;
}
