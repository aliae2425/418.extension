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

// Ce que les commandes SONT, séparé de ce qu'elles FONT — les implémentations
// vivent dans `app.js`, là où est l'état qu'elles modifient. Cette table sert
// deux fois : à la liste de propositions, et à `/aide`. Une seule source, donc
// pas de commande qui s'ajoute sans apparaître dans l'aide.
export const CATALOGUE = [
  {
    nom: 'connect',
    args: '[clé]',
    aide: 'se connecter à **ChatGPT** dans le navigateur, ou poser une clé API',
  },
  { nom: 'model', args: '[nom]', aide: 'changer de modèle, ou dire lequel répond' },
  { nom: 'logout', args: '', aide: 'fermer la session et effacer la clé' },
  { nom: 'aide', args: '', aide: 'lister les commandes' },
];

// Une commande en train d'être écrite : `/`, `/mo`, `/model`. Dès qu'une
// espace suit, on écrit les ARGUMENTS — proposer encore des noms de commande
// serait alors du bruit.
const EN_COURS = /^\/([a-z]*)$/i;

// Les propositions pour ce qui est tapé, `[]` s'il n'y a rien à proposer.
export function filtrer(texte) {
  const trouve = EN_COURS.exec(texte || '');
  if (!trouve) return [];
  const debut = trouve[1].toLowerCase();
  return CATALOGUE.filter((c) => c.nom.startsWith(debut));
}

// Ce qu'une proposition met dans le champ. L'espace finale n'est pas
// cosmétique : elle place le curseur là où l'argument s'écrit, et son absence
// sur une commande qui n'en prend pas dit qu'il n'y a rien à ajouter.
export function completer(commande) {
  return commande.args ? `/${commande.nom} ` : `/${commande.nom}`;
}
