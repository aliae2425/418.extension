// OpenAI, `/v1/chat/completions`, en direct depuis la page.
//
// **La clé n'entre jamais ici.** La page envoie un en-tête `Authorization`
// qui ne contient qu'une sentinelle ; l'hôte l'intercepte par
// `WebResourceRequested` et remplace sa valeur. Le streaming reste natif —
// `response.body` est lu dans la page — et une XSS dans une bulle ne trouve
// rien à voler.
//
// La sentinelle n'est pas une précaution de plus : sans en-tête `Authorization`
// au départ, le navigateur ne l'annonce pas dans son préflight, et on
// dépendrait de l'ordre entre le contrôle CORS et notre interception. Avec,
// le préflight est exact et l'hôte ne fait que substituer une valeur.
//
// CORS vérifié : `api.openai.com` reflète notre origine `https://418.local`
// et autorise `authorization,content-type`.

export const URL_API = 'https://api.openai.com/v1/chat/completions';

// Ce que l'hôte reconnaît et remplace. Toute autre valeur part telle quelle,
// donc échoue en 401 — ce qui est le bon comportement : on préfère un refus
// franc à un appel anonyme.
export const SENTINELLE = 'Bearer 418-hote';

// Pas de catalogue de modèles en dur : il vieillirait sans que rien ne le
// signale. Un seul défaut, remplaçable par l'appelant.
export const MODELE_DEFAUT = 'gpt-5';

export const SYSTEME = `Tu assistes un architecte dans Autodesk Revit, en français.

Tu disposes d'outils pour lire et modifier la maquette. Appelle-les plutôt que
de supposer : une réponse inventée sur un projet coûte plus cher qu'une
question. Si un outil échoue, dis-le et propose autre chose.

Réponds court. L'architecte lit dans un volet étroit, pas dans un rapport.
Le Markdown est rendu : gras, listes et tableaux passent, emploie-les
sobrement.

Les outils marqués irréversibles ne s'annulent par aucun Ctrl+Z. Ne les
appelle que sur une demande explicite. L'architecte devra donner son accord de
toute façon : le lui demander pour rien l'use.`;

// --- le contrat du harnais --------------------------------------------------

export function fournisseurOpenAI({ modele = MODELE_DEFAUT, url = URL_API,
  recuperer = fetch } = {}) {
  return async function repondre(messages, catalogue, ctx = {}) {
    const reponse = await recuperer(url, {
      method: 'POST',
      signal: ctx.signal,
      headers: {
        'Content-Type': 'application/json',
        Authorization: SENTINELLE,
      },
      body: JSON.stringify(corps(messages, catalogue, modele)),
    });
    if (!reponse.ok) throw new Error(await detail(reponse));
    return lire(reponse.body, ctx);
  };
}

// --- le corps ---------------------------------------------------------------

export function corps(messages, catalogue, modele = MODELE_DEFAUT) {
  const charge = {
    model: modele,
    stream: true,
    messages: [{ role: 'system', content: SYSTEME }, ...messages.map(traduire)],
  };
  if (catalogue?.length) {
    charge.tools = catalogue.map((o) => ({
      type: 'function',
      function: {
        name: o.nom,
        description: o.description,
        parameters: o.parametres || { type: 'object', properties: {} },
      },
    }));
    charge.tool_choice = 'auto';
  }
  return charge;
}

// Notre forme interne → la leur. C'est ici, et nulle part ailleurs, que vit
// la connaissance du protocole OpenAI.
function traduire(message) {
  if (message.role === 'utilisateur') {
    return { role: 'user', content: message.texte || '' };
  }
  if (message.role === 'outil') {
    return { role: 'tool', tool_call_id: message.id, content: message.sortie || '' };
  }
  if (message.appels?.length) {
    return {
      role: 'assistant',
      content: null,
      tool_calls: message.appels.map((a) => ({
        id: a.id,
        type: 'function',
        // Eux attendent une CHAÎNE JSON, pas un objet. L'oublier rend un 400
        // sur le corps entier, sans dire lequel des messages est en cause.
        function: { name: a.nom, arguments: JSON.stringify(a.arguments || {}) },
      })),
    };
  }
  return { role: 'assistant', content: message.texte || '' };
}

// --- la lecture du flux ------------------------------------------------------

export async function lire(corpsFlux, ctx = {}) {
  const appels = new Map();
  let texte = '';
  for await (const evenement of evenements(corpsFlux)) {
    const delta = evenement?.choices?.[0]?.delta;
    if (!delta) continue;
    if (delta.content) {
      texte += delta.content;
      ctx.surTexte?.(delta.content);
    }
    // Certains modèles exposent leur raisonnement ; les autres ignorent
    // simplement cette branche.
    const pensee = delta.reasoning_content || delta.reasoning;
    if (pensee) ctx.surRaisonnement?.(pensee);
    for (const morceau of delta.tool_calls || []) fusionner(appels, morceau);
  }
  const lus = [...appels.values()].map((a) => ({
    id: a.id,
    nom: a.nom,
    arguments: json(a.arguments),
  }));
  return lus.length ? { texte, appels: lus } : { texte };
}

// Un appel d'outil arrive EN MORCEAUX : l'index identifie la place, l'id et
// le nom ne viennent qu'une fois, les arguments se concatènent caractère par
// caractère. Les traiter comme des messages complets donne des noms vides et
// du JSON tronqué.
export function fusionner(appels, morceau) {
  const rang = morceau.index ?? 0;
  const vu = appels.get(rang) || { id: '', nom: '', arguments: '' };
  if (morceau.id) vu.id = morceau.id;
  if (morceau.function?.name) vu.nom += morceau.function.name;
  if (morceau.function?.arguments) vu.arguments += morceau.function.arguments;
  appels.set(rang, vu);
  return appels;
}

// Découpe un flux SSE en évènements JSON. Les lignes arrivent coupées
// n'importe où : un `data:` peut être scindé entre deux morceaux réseau,
// d'où le tampon.
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
      tampon = lignes.pop() ?? '';          // la dernière est peut-être tronquée
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
  if (!charge || charge === '[DONE]') return null;
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

// Le message d'erreur est logé à trois endroits selon l'endpoint. Sans ce
// tri, l'architecte reçoit un corps JSON brut ou juste un code nu.
async function detail(reponse) {
  let corpsTexte = '';
  try {
    corpsTexte = await reponse.text();
  } catch {
    corpsTexte = '';
  }
  const lu = json(corpsTexte, null);
  const message = lu?.error?.message || lu?.error_description
    || (typeof lu?.error === 'string' ? lu.error : '') || lu?.detail || '';
  if (reponse.status === 401) {
    return 'HTTP 401 — clé refusée. Vérifiez OPENAI_API_KEY, puis rouvrez le '
      + 'volet.';
  }
  return `HTTP ${reponse.status} — ${message || 'sans détail'}`;
}
