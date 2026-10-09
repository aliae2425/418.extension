// Le catalogue des fournisseurs et des modèles, servi par 418.cloud.
//
// Trois sources, et l'ordre compte — c'est la chaîne d'opencode, pour les
// mêmes raisons :
//
//   1. le CACHE local        instantané, et c'est ce qui fait que le volet
//                            s'ouvre sans attendre le réseau ;
//   2. l'INSTANTANÉ embarqué  pour le tout premier lancement, et pour un
//                            poste hors ligne — sans lui, `/connect` serait
//                            vide sur une machine d'agence sans Internet ;
//   3. le SERVICE            tiré en fond, rangé au cache, servi au prochain
//                            coup. Jamais attendu : une requête qui traîne
//                            ne doit pas retarder l'ouverture du volet.
//
// Le plus RÉCENT des deux premiers gagne : un instantané fraîchement livré
// doit l'emporter sur un cache de six mois, et un cache à jour sur un
// instantané que personne n'a régénéré depuis.

export const URL_CATALOGUE = 'https://cloud.418.archi/api.json';

// Le client refuse un format qu'il ne sait pas lire plutôt que d'en tirer
// n'importe quoi. Le service pose le même numéro.
export const VERSION = 1;

const CLE = '418.catalogue';

export function catalogue({
  url = URL_CATALOGUE, recuperer = fetch, stockage = null, embarque = null,
} = {}) {
  const magasin = stockage ?? (typeof localStorage === 'undefined' ? null : localStorage);
  let courant = meilleur(depuisCache(magasin), valide(embarque) ? embarque : null);

  return {
    get fournisseurs() { return courant.charge?.fournisseurs || {}; },
    // D'où vient ce qu'on affiche. Le dire permet au volet d'être honnête
    // quand il montre une liste vieille de trois mois.
    get origine() { return courant.origine; },
    get genere() { return courant.charge?.genere || ''; },

    // Tire le service et range. Ne lève jamais : un catalogue périmé vaut
    // mieux qu'un volet qui refuse de s'ouvrir parce qu'un serveur tousse.
    async rafraichir(signal = null) {
      try {
        const reponse = await recuperer(url, { signal });
        if (!reponse.ok) throw new Error(`HTTP ${reponse.status}`);
        const charge = await reponse.json();
        if (!valide(charge)) throw new Error('catalogue illisible ou version inconnue');
        ranger(magasin, charge);
        courant = { charge, origine: 'service' };
        return true;
      } catch {
        return false;
      }
    },
  };
}

// --- la forme ---------------------------------------------------------------

function valide(charge) {
  return Boolean(charge)
    && charge.version === VERSION
    && charge.fournisseurs
    && typeof charge.fournisseurs === 'object';
}

// Le plus récent des deux, `{charge: null}` s'il n'y en a aucun.
function meilleur(cache, embarque) {
  if (!cache) return embarque ? { charge: embarque, origine: 'embarque' } : { charge: null, origine: 'vide' };
  if (!embarque) return { charge: cache, origine: 'cache' };
  return (embarque.genere || '') > (cache.genere || '')
    ? { charge: embarque, origine: 'embarque' }
    : { charge: cache, origine: 'cache' };
}

function depuisCache(magasin) {
  try {
    const charge = JSON.parse(magasin?.getItem(CLE) || 'null');
    return valide(charge) ? charge : null;
  } catch {
    // Un cache corrompu se remplace, il ne fait pas tomber le volet.
    return null;
  }
}

function ranger(magasin, charge) {
  try {
    magasin?.setItem(CLE, JSON.stringify(charge));
  } catch {
    // Quota plein, mode privé : tant pis, on retombera sur l'embarqué.
  }
}

// --- ce que l'interface en tire ---------------------------------------------

// Les fournisseurs qu'on sait VRAIMENT brancher. Le catalogue décrit, le
// volet implémente : une `connexion` qu'aucun adaptateur ne couvre ne doit
// pas apparaître dans `/connect`, sinon on propose une voie sans issue.
export function fournisseursServis(fournisseurs, connexionsSues) {
  return Object.entries(fournisseurs || {})
    .filter(([, f]) => connexionsSues.includes(f.connexion))
    .map(([id, f]) => ({ id, ...f }));
}

// Les modèles d'un fournisseur, triés : le défaut en tête, puis du plus
// récent au plus ancien. Ceux qui ne savent pas appeler d'outils sont
// écartés — dans ce volet, un modèle sans outils ne sert à rien.
export function modelesServis(fournisseur) {
  return Object.entries(fournisseur?.modeles || {})
    .filter(([, m]) => m.outils !== false)
    .map(([id, m]) => ({ id, ...m }))
    .sort((a, b) => {
      if (Boolean(b.defaut) !== Boolean(a.defaut)) return b.defaut ? 1 : -1;
      return (b.sorti || '').localeCompare(a.sorti || '');
    });
}

// « 1 050 k · 2 $/M · pièces » — ce qui aide à choisir, en une ligne étroite.
export function resume(modele) {
  const bouts = [];
  const contexte = modele?.limite?.contexte;
  if (contexte) bouts.push(`${Math.round(contexte / 1000)} k`);
  // Un coût nul est un abonnement, pas un modèle gratuit : l'afficher
  // « 0 $/M » laisserait croire que l'API ne facture rien.
  if (modele?.cout?.entree) bouts.push(`${modele.cout.entree} $/M`);
  if (modele?.pieces) bouts.push('pièces');
  if (modele?.raisonnement) bouts.push('raisonne');
  return bouts.join(' · ');
}
