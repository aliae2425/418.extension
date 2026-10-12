// L'arbre de `/model` : les connexions VIVANTES, dépliables, et leurs modèles.
//
// Pas « les modèles de la voie active » : toutes celles auxquelles on est
// branché. Poser une clé Anthropic n'éteint pas la session ChatGPT — l'une et
// l'autre restent là, et `/model` est l'aiguillage. Sans lui, changer de
// maison voudrait dire se déconnecter de la première.
//
// Ici, rien que de la donnée vers de la donnée : ni DOM, ni réseau, ni état
// global. C'est ce qui permet de l'éprouver sans navigateur.

import { fournisseursServis, connexionsServies, modelesServis, resume }
  from './catalogue.js';

export const cleDe = (f, c) => `${f.id}/${c.id}`;

// Ce à quoi l'hôte dit qu'on est branché. Lui seul sait : la page n'a jamais
// vu ni clé ni jeton, elle ne connaît que des booléens.
export function connexionsVivantes(fournisseurs, connexions, branches) {
  const sortie = [];
  for (const f of fournisseursServis(fournisseurs, connexions)) {
    for (const c of connexionsServies(f, connexions)) {
      const vivante = c.id === 'abonnement'
        ? Boolean(branches.oauth) : Boolean(branches.cles?.[f.id]);
      if (vivante) sortie.push({ f, c, cle: cleDe(f, c) });
    }
  }
  return sortie;
}

// DÈS QU'ON FILTRE l'arbre s'aplatit : on cherche un nom de modèle, pas une
// maison, et un en-tête ne porte aucun des mots qu'on tape. Replié il
// cacherait la réponse ; gardé il resterait seul au-dessus de modèles qui ne
// sont plus les siens. À plat, chaque ligne dit d'où elle vient.
export function entreesModeles({
  fournisseurs, connexions, branches, actif = '', ouverts = new Set(),
  listes = new Map(), modeleActif = '', surGroupe = () => {},
  surModele = () => {},
}, q = '') {
  const entrees = [];
  for (const { f, c, cle } of connexionsVivantes(fournisseurs, connexions, branches)) {
    const connus = new Map(modelesServis(c).map((m) => [m.id, m]));
    // Ce que l'API a listé l'emporte sur le catalogue : une clé restreinte ne
    // voit pas tout. À défaut, le catalogue — jamais rien.
    const noms = listes.get(cle) || [...connus.keys()];
    const chez = `${f.nom} · ${c.nom}`;
    const deplie = ouverts.has(cle);
    if (!q) {
      entrees.push({
        titre: `${deplie ? '▾' : '▸'} ${chez}`,
        args: cle === actif ? 'en cours' : '',
        cherche: chez,
        detail: `${noms.length} modèles`,
        groupe: cle,
        prendre: () => surGroupe(cle),
      });
      if (!deplie) continue;
    }
    for (const nom of noms) {
      const fiche = connus.get(nom);
      entrees.push({
        // Pas d'indentation dans le libellé : `white-space: nowrap` replierait
        // les espaces. Le décalage est une marge CSS, posée sur `.sous`.
        titre: fiche?.nom || nom,
        args: fiche && fiche.nom !== nom ? nom : '',
        // La maison fait partie de la recherche : taper « anthropic » doit
        // sortir ses modèles, pas rien du tout.
        cherche: `${nom} ${fiche?.nom || ''} ${chez}`,
        // À plat c'est la maison qu'il faut lire — sans elle, deux modèles
        // homonymes de deux fournisseurs seraient indiscernables.
        detail: q ? chez
          : (cle === actif && nom === modeleActif ? 'en cours' : resume(fiche)),
        sous: cle,
        prendre: () => surModele(f, c, nom),
      });
    }
  }
  return entrees;
}
