// Ce que les trois pages de l'outil partagent : parler à leur hôte.
//
// Chaque fenêtre a SA page et SON hôte, mais le protocole est le même
// partout — celui du volet OpenArchi, repris tel quel par `../vue/pont.js`.
//
// Deux formes, et il faut choisir la bonne :
//
//   `demander(ordre)`  une question, une réponse, une promesse. Pour tout ce
//                      qui revient tout de suite (lire, écrire, calculer).
//   `poster(ordre)`    on envoie et on n'attend rien ; la réponse arrivera
//                      plus tard, par `ecouter`. C'est la forme des ordres
//                      `ouvrir_*` : une fenêtre fille bloque l'hôte tant
//                      qu'elle est ouverte, et un matériau s'édite en
//                      plusieurs minutes — bien au-delà du délai du pont.

import { demanderHote, reponseHote } from '../vue/pont.js';

const ecouteurs = new Map();

window.chrome?.webview?.addEventListener('message', (e) => {
  const { evenement, charge } = typeof e.data === 'string'
    ? JSON.parse(e.data) : e.data;
  // Une réponse à une demande en vol réveille sa promesse et s'arrête là.
  // Tout le reste est un évènement poussé par l'hôte.
  if (evenement === 'reponse') return void reponseHote(charge);
  const ecouteur = ecouteurs.get(evenement);
  if (ecouteur) ecouteur(charge || {});
});

/** Une fenêtre WebView2 n'a pas de console sous les yeux de l'utilisateur :
 *  l'erreur part dans `data/materiaux.log`, relisible après coup. */
export function signaler(erreur) {
  poster({ ordre: 'erreur', message: String(erreur?.stack || erreur) });
}
window.addEventListener('error', (e) => signaler(e.error || e.message));
window.addEventListener('unhandledrejection', (e) => signaler(e.reason));

export function poster(message) {
  window.chrome?.webview?.postMessage(JSON.stringify(message));
}

export function ecouter(evenement, fonction) {
  ecouteurs.set(evenement, fonction);
}

export async function demander(ordre, charge = {}) {
  try {
    return await demanderHote(ordre, charge);
  } catch (erreur) {
    signaler(erreur);
    throw erreur;
  }
}

/** Le premier mot de toute page : « je suis prête, donne-moi mon état ». */
export async function pret() {
  const contexte = await demander('pret');
  // Les DEUX classes, pas seulement `sombre` : sans `clair` explicite, un
  // Windows sombre et un Revit clair laisseraient le repli de
  // `prefers-color-scheme` gagner, et la fenêtre serait noire à tort.
  document.body.classList.toggle('sombre', Boolean(contexte.sombre));
  document.body.classList.toggle('clair', !contexte.sombre);
  return contexte;
}

/** Le dernier : « voilà ce que je rends », et la fenêtre se retire.
 *
 * `null` veut dire annulé — c'est la seule chose qui distingue « Annuler »
 * d'un choix, côté fenêtre appelante. */
export function fermer(resultat = null) {
  poster({ ordre: 'fermer', resultat });
}
