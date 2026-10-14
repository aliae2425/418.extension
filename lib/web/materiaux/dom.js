// Les quelques gestes de DOM que les trois pages et les deux modales
// partagent. Rien de plus : pas de moteur de gabarits, pas de réactivité.
//
// Règle tenue partout : un nom de matériau, de motif ou de catégorie vient de
// la maquette et passe par `textContent`, JAMAIS par `innerHTML`. Le seul
// balisage injecté tel quel est le SVG des vignettes, fabriqué par
// `services/hatch_svg.py` — c'est nous qui l'écrivons, caractère par
// caractère.

export const $ = (selecteur, racine = document) => racine.querySelector(selecteur);
export const $$ = (selecteur, racine = document) =>
  Array.from(racine.querySelectorAll(selecteur));

/** Un élément, ses classes, son texte. */
export function creer(balise, classes = '', texte = '') {
  const noeud = document.createElement(balise);
  if (classes) noeud.className = classes;
  if (texte) noeud.textContent = texte;
  return noeud;
}

/** Le cadre blanc d'une vignette, avec son SVG dedans.
 *
 * `titre` sert d'infobulle : le nom d'un motif ne tient pas en 64 pixels.
 */
export function vignette(svg, classes = 'motif', titre = '') {
  const cadre = creer('span', `vignette ${classes}`);
  if (titre) cadre.title = titre;
  cadre.innerHTML = svg || '';
  return cadre;
}

/** Une pastille de couleur pleine — le « rendu » des listes. */
export function pastille(couleur, classes = 'rendu', titre = '') {
  const cadre = creer('span', `vignette ${classes}`);
  cadre.style.background = couleur;
  if (titre) cadre.title = titre;
  return cadre;
}

/** Minuscule et sans accents, comme `core/text_filter.normaliser`.
 *
 * Deuxième implémentation du même geste, assumée : filtrer à la frappe par
 * un aller-retour vers l'hôte ferait traverser la liste entière à chaque
 * lettre pour trois lignes de JavaScript.
 */
export function normaliser(valeur) {
  return (valeur == null ? '' : String(valeur))
    .normalize('NFKD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase();
}

/** Les items dont au moins un `getters` contient `texte`. */
export function filtrer(items, texte, getters) {
  const aiguille = normaliser(texte).trim();
  if (!aiguille) return items;
  return items.filter((item) =>
    getters.some((lire) => normaliser(lire(item)).includes(aiguille)));
}

/** Retarde `action` : un aperçu par frappe, pas un par caractère tapé. */
export function differer(action, delai = 120) {
  let minuterie = null;
  return (...args) => {
    clearTimeout(minuterie);
    minuterie = setTimeout(() => action(...args), delai);
  };
}

/** « 3 matériau(x) » sans se demander où mettre le s. */
export function pluriel(nombre, singulier, plur = null) {
  return `${nombre} ${nombre > 1 ? (plur || `${singulier}s`) : singulier}`;
}

/** Une liste de lignes qui se filtre sans rien reconstruire.
 *
 * Les nœuds sont fabriqués UNE fois par matériau et rangés : filtrer ou
 * recocher ne fait que les remettre dans l'ordre. C'est ce qui permet de
 * garder des vignettes SVG dans chaque ligne sans que la recherche ne
 * devienne poussive sur un modèle à plusieurs centaines de matériaux.
 */
export function creerListe(conteneur, gabarit) {
  const noeuds = new Map();
  return {
    noeud: (id) => noeuds.get(id),
    /** Jette le nœud d'un matériau : il sera refait au prochain rendu.
     *
     * Appelé après une édition — le nom, la couleur et les deux vignettes
     * ont changé, et une ligne gardée en cache afficherait l'ancien
     * matériau indéfiniment. */
    oublier: (id) => noeuds.delete(id),
    rendre(cartes) {
      const bloc = document.createDocumentFragment();
      for (const carte of cartes) {
        let noeud = noeuds.get(carte.id);
        if (!noeud) {
          noeud = gabarit(carte);
          noeud.dataset.id = String(carte.id);
          noeuds.set(carte.id, noeud);
        }
        bloc.append(noeud);
      }
      conteneur.replaceChildren(bloc);
    },
  };
}
