// Ce qui commence par `/` est traité sur place et ne part jamais au modèle.
//
// Analyse seule : la table des commandes vit dans `app.js`, là où est l'état
// qu'elles modifient. Ici il n'y a qu'une règle de reconnaissance, et elle se
// teste sans rien simuler.

// `/` seul, ou `/ quelque chose` : ce n'est pas une commande. Et un chemin
// collé par mégarde (`/c/Users/...`) n'en est pas une non plus — d'où
// l'absence de `/` dans le nom.
const FORME = /^\/([a-z]+)(?:\s+([\s\S]*))?$/i;

export function analyser(texte) {
  const trouve = FORME.exec((texte || '').trim());
  if (!trouve) return null;
  return { nom: trouve[1].toLowerCase(), arguments: (trouve[2] || '').trim() };
}
