// Le pont vers l'hôte : une question, une réponse, appariées par référence.
//
// `postMessage` est un canal à sens unique sans notion de réponse. On numérote
// donc chaque demande, l'hôte renvoie la même référence, et c'est elle qui
// réveille la bonne promesse. Sans ça, deux appels d'outils en vol se
// répondraient l'un à l'autre.
//
// Mesuré : 0,63 ms l'aller-retour, et l'hôte a le droit de répondre depuis un
// fil de fond. C'est ce qui permet de garder l'appel Revit — bloquant — hors
// du fil d'interface sans geler Revit.

const attentes = new Map();
let rang = 0;

// Au-delà, on rend la main plutôt que de laisser un tour pendu pour
// toujours. Un outil Revit lent met quelques secondes ; une minute veut dire
// que quelque chose est cassé côté hôte.
const DELAI = 60000;

// `surLigne` : l'hôte peut pousser des morceaux AVANT de répondre. C'est ce
// qui porte le streaming d'un fournisseur dont l'égress est en Python —
// chaque ligne du flux arrive ici, la promesse ne se résout qu'à la fin.
export function demanderHote(ordre, charge = {}, signal = null, surLigne = null) {
  const brique = window.chrome?.webview;
  if (!brique) return Promise.reject(new Error('hors WebView2 — aucun hôte'));

  rang += 1;
  const ref = `d${rang}`;
  return new Promise((resoudre, rejeter) => {
    const finir = (fn, valeur) => {
      if (!attentes.delete(ref)) return;    // déjà tranché
      clearTimeout(minuterie);
      signal?.removeEventListener('abort', couper);
      fn(valeur);
    };
    // Le délai se REARME à chaque ligne reçue : un flux qui dure deux minutes
    // est normal, un silence d'une minute ne l'est pas. Sans ça, une longue
    // réponse se ferait couper en plein milieu.
    let minuterie = null;
    const armer = () => {
      clearTimeout(minuterie);
      minuterie = setTimeout(
        () => finir(rejeter, new Error(`l'hôte n'a pas répondu (${ordre})`)),
        DELAI,
      );
    };
    armer();
    // Une interruption ne doit pas attendre la fin de l'outil en cours :
    // l'hôte continuera son travail, mais plus personne ne l'écoute.
    const couper = () => finir(rejeter, new Error('interrompu'));
    signal?.addEventListener('abort', couper, { once: true });

    attentes.set(ref, {
      resoudre: (v) => finir(resoudre, v),
      rejeter: (e) => finir(rejeter, e),
      ligne: (texte) => {
        armer();
        // Une ligne qui fait lever ne doit pas tuer le gestionnaire de
        // messages : elle casse CE tour, et lui seul.
        try {
          surLigne?.(texte);
        } catch (erreur) {
          finir(rejeter, erreur);
        }
      },
    });
    brique.postMessage(JSON.stringify({ ordre, ref, ...charge }));
  });
}

// Appelé par le gestionnaire de messages quand l'hôte répond.
// `true` si la réponse attendait quelqu'un.
export function reponseHote(charge = {}) {
  const attente = attentes.get(charge.ref);
  if (!attente) return false;
  if (charge.erreur) attente.rejeter(new Error(charge.erreur));
  else attente.resoudre(charge.sortie);
  return true;
}

// Un morceau de flux, avant la réponse finale.
export function ligneHote(charge = {}) {
  const attente = attentes.get(charge.ref);
  if (!attente) return false;
  attente.ligne(charge.ligne || '');
  return true;
}
