// La sélection d'une liste cochable : bascule au clic, plage à la Maj.
//
// Isolée du reste parce que c'est le seul morceau de la page qui a des cas
// limites — une ancre qui n'est plus affichée, une plage à l'envers, un Maj
// sans ancre. Même contrat que `SelectionPageVM.handle_row_click` du socle,
// et testable sans DOM (`tests/selection.test.js`).

/** Applique un clic de ligne. Mute `coches`, rend la nouvelle ancre.
 *
 * `visibles` : les identifiants AFFICHÉS, dans l'ordre de l'écran. Une plage
 * se lit à l'écran, pas dans la liste complète : avec un filtre actif, Maj
 * doit prendre ce qu'on voit entre les deux lignes, et rien d'autre.
 *
 * Le clic simple et Ctrl font la même chose — une bascule. La case reste le
 * contrôle, il n'y a rien d'exclusif ici (l'onglet Matériaux, lui, est
 * exclusif, mais il ne passe pas par cette liste).
 */
export function clic(coches, ancre, visibles, id, { shift = false } = {}) {
  const index = visibles.indexOf(id);
  if (index < 0) return ancre;              // ligne plus affichée : rien à faire
  const depuis = ancre == null ? -1 : visibles.indexOf(ancre);
  if (shift && depuis >= 0) {
    const [a, b] = depuis <= index ? [depuis, index] : [index, depuis];
    for (const autre of visibles.slice(a, b + 1)) coches.add(autre);
    // L'ancre NE BOUGE PAS : deux Maj de suite depuis la même ligne étendent
    // la même plage, au lieu de la faire glisser.
    return ancre;
  }
  if (coches.has(id)) coches.delete(id); else coches.add(id);
  return id;
}
