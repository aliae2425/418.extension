// La boucle d'outils : tant que le modèle demande des outils, on recommence.
//
// Elle ne connaît ni fournisseur ni Revit. Trois choses lui sont injectées —
// un `modele`, des `outils`, un `demander` — et c'est ce qui permet de la
// faire tourner entièrement en mémoire, en millisecondes, sans Revit ouvert.
// Une boucle infinie, un irréversible qui passe, un dernier tour qui n'arrive
// jamais : tout ça se reproduit ici dans un test.
//
// Le découpage vient d'opencode : ce qui est VRAIMENT commun tient en trois
// choses — le catalogue, l'exécution d'un outil, et la règle du dernier tour.
// La forme du corps, la lecture des appels et le rangement des résultats
// appartiennent au protocole de chaque fournisseur et restent chez lui.
// `/v1/chat/completions` imbrique les outils sous « function », le backend
// Responses les pose à plat, et aucune abstraction ne rendra ces deux-là
// identiques sans mentir.

import * as p from './protocole.js';
import { AUTORISER, REFUSER, appliquerReponse } from './permissions.js';

// Un modèle qui boucle brûle l'abonnement en silence. Le plafond n'est pas
// une précaution, c'est le garde-fou.
export const TOURS_MAX = 5;

export const REFUS = "refusé par l'architecte — ne pas réessayer sans une "
  + 'demande explicite de sa part';
export const SANS_INTERFACE = "aucune interface pour demander l'accord — "
  + 'outil irréversible refusé';

export class Interrompu extends Error {}

// Lance un tour de conversation et le mène jusqu'au texte.
//
//   modele(messages, catalogue, {signal, surTexte, surRaisonnement})
//       → { texte, appels: [{ id, nom, arguments }] }
//   outils : Map nom → { description, parametres, irreversible, executer }
//   demander(nom, args) → 'une_fois' | 'toujours' | 'jamais'
//
// Ne lève jamais : tout finit par un `tour.fini`, sinon l'interface reste
// bloquée sur « réfléchit… ».
export async function conduire({
  modele, outils, flux, regles, demander = null, signal = null,
  toursMax = TOURS_MAX, messages = [],
}) {
  try {
    const texte = await boucler({
      modele, outils, flux, regles, demander, signal, toursMax, messages,
    });
    if (texte) ecrire(flux, p.TEXTE, texte);
    flux.fini();
  } catch (erreur) {
    if (erreur instanceof Interrompu || erreur?.name === 'AbortError') {
      flux.ouvrir(p.ETAPE, { texte: 'interrompu' });
      flux.fini('interrompu');
      return;
    }
    flux.ouvrir(p.ERREUR, { texte: String(erreur?.message || erreur) });
    flux.fini('erreur');
  }
}

async function boucler({
  modele, outils, flux, regles, demander, signal, toursMax, messages,
}) {
  const catalogue = [...outils.values()].map(decrire);
  for (let tour = 0; tour < toursMax; tour += 1) {
    const reponse = await interroger(modele, messages, catalogue, flux, signal);
    if (!reponse.appels?.length) return reponse.texte || '';
    messages.push({ role: 'assistant', appels: reponse.appels });
    for (const appel of reponse.appels) {
      messages.push(await executer({
        appel, outils, flux, regles, demander, signal,
      }));
    }
  }
  // Au plafond, un dernier tour SANS outils plutôt qu'une erreur : le modèle
  // a déjà tout lu, il lui reste à le dire. Lever ici laisserait l'architecte
  // devant une bulle vide après dix secondes d'attente.
  flux.ouvrir(p.ETAPE, { texte: 'je conclus…' });
  const dernier = await interroger(modele, messages, [], flux, signal);
  return dernier.texte || '';
}

async function interroger(modele, messages, catalogue, flux, signal) {
  verifier(signal);
  let bulle = null;
  let pensee = null;
  const reponse = await modele(messages, catalogue, {
    signal,
    // Les deltas arrivent ici et repartent aussitôt : la part ne naît qu'au
    // premier morceau, sinon une bulle vide clignoterait à chaque tour
    // d'outil.
    surTexte: (morceau) => {
      bulle = bulle || flux.ouvrir(p.TEXTE);
      flux.ajouter(bulle, morceau);
    },
    surRaisonnement: (morceau) => {
      pensee = pensee || flux.ouvrir(p.RAISONNEMENT);
      flux.ajouter(pensee, morceau);
    },
  });
  verifier(signal);
  // Le texte déjà poussé en flux ne doit pas repartir en bloc à la fin.
  return bulle ? { ...reponse, texte: '' } : reponse;
}

async function executer({ appel, outils, flux, regles, demander, signal }) {
  const outil = outils.get(appel.nom);
  const part = flux.ouvrir(p.OUTIL, {
    nom: appel.nom,
    arguments: appel.arguments || {},
    etat: p.EN_COURS,
  });

  if (!outil) {
    return echouer(flux, part, appel, `outil inconnu : ${appel.nom}`);
  }

  const verdict = await accorder({ appel, flux, part, regles, demander });
  if (verdict !== null) return verdict;

  try {
    verifier(signal);
    const sortie = await outil.executer(appel.arguments || {}, {
      signal,
      // Le pendant de leur `metadata({title})` : dire ce qui se passe
      // pendant que ça dure.
      etape: (phrase) => flux.ouvrir(p.ETAPE, { texte: phrase }),
    });
    const texte = typeof sortie === 'string' ? sortie : JSON.stringify(sortie);
    flux.changer(part, { etat: p.FAIT, sortie: texte });
    return { role: 'outil', id: appel.id, nom: appel.nom, sortie: texte };
  } catch (erreur) {
    if (erreur instanceof Interrompu || erreur?.name === 'AbortError') throw erreur;
    // Un outil qui casse ne fait pas échouer le tour : le modèle reçoit
    // l'erreur et peut corriger sa demande ou le dire.
    return echouer(flux, part, appel, String(erreur?.message || erreur));
  }
}

// `null` si l'outil peut partir, sinon le message d'outil à rendre au modèle.
async function accorder({ appel, flux, part, regles, demander }) {
  const effet = regles.effet(appel.nom);
  if (effet === AUTORISER) return null;
  if (effet === REFUSER) return refuser(flux, part, appel, REFUS);

  // Pas de `demander` = personne pour répondre. Ouvrir en grand quand
  // personne ne peut répondre serait l'inverse exact de ce que ce verrou
  // existe pour faire.
  if (!demander) return refuser(flux, part, appel, SANS_INTERFACE);

  flux.changer(part, { etat: p.ATTENTE_ACCORD });
  let reponse;
  try {
    reponse = await demander(appel.nom, appel.arguments || {});
  } catch {
    // Une confirmation qui casse vaut un refus, jamais un laissez-passer.
    reponse = null;
  }
  if (!appliquerReponse(regles, appel.nom, reponse)) {
    return refuser(flux, part, appel, REFUS);
  }
  flux.changer(part, { etat: p.EN_COURS });
  return null;
}

function refuser(flux, part, appel, motif) {
  flux.changer(part, { etat: p.REFUSE, sortie: motif });
  return {
    role: 'outil', id: appel.id, nom: appel.nom,
    sortie: JSON.stringify({ erreur: motif }),
  };
}

function echouer(flux, part, appel, motif) {
  flux.changer(part, { etat: p.ECHEC, sortie: motif });
  return {
    role: 'outil', id: appel.id, nom: appel.nom,
    sortie: JSON.stringify({ erreur: motif }),
  };
}

function decrire(outil) {
  return {
    nom: outil.nom,
    description: outil.description,
    parametres: outil.parametres || { type: 'object', properties: {} },
    irreversible: Boolean(outil.irreversible),
  };
}

function ecrire(flux, genre, texte) {
  flux.ajouter(flux.ouvrir(genre), texte);
}

function verifier(signal) {
  if (signal?.aborted) throw new Interrompu('interrompu');
}
