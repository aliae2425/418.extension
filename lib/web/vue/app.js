// Le câblage : saisie → boucle → rendu. Rien de plus.
//
// Depuis J4 le moteur tourne ICI, dans la page. Python ne pilote plus rien :
// il monte le WebView2, dit quel thème Revit affiche, et encaisse le journal.
// Ce qui passait par `postMessage` à chaque jeton ne traverse plus rien.

import { Flux } from '../harnais/protocole.js';
import { reglesDepuisCatalogue } from '../harnais/permissions.js';
import { conduire } from '../harnais/boucle.js';
import { modeleFactice, outilsFactices } from '../harnais/modele_factice.js';
import { Rendu } from './rendu.js';

const $ = (id) => document.getElementById(id);
const saisie = $('saisie');
const action = $('action');
const pied = $('pied');

const REPOS = 'modèle fictif — rien n\'est envoyé, rien n\'est modifié';

// --- l'accord ---------------------------------------------------------------

// Un seul accord en vol : la boucle `await` chaque outil l'un après l'autre.
// Ce n'est pas une hypothèse sur l'usage, c'est une propriété de la boucle.
let repondreAccord = null;

const rendu = new Rendu($('fil'), {
  surAccord: (reponse) => {
    const suite = repondreAccord;
    repondreAccord = null;
    suite?.(reponse);
  },
});

function demander() {
  return new Promise((resoudre) => { repondreAccord = resoudre; });
}

// --- l'hôte -----------------------------------------------------------------

function versHote(message) {
  window.chrome?.webview?.postMessage(JSON.stringify(message));
}

window.chrome?.webview?.addEventListener('message', (e) => {
  const { evenement, charge } = typeof e.data === 'string'
    ? JSON.parse(e.data) : e.data;
  if (evenement !== 'theme') return;
  // Les DEUX classes, pas seulement `sombre` : sans `clair` explicite, un
  // Windows sombre et un Revit clair laisseraient le repli de
  // `prefers-color-scheme` gagner, et le volet serait noir à tort.
  const sombre = charge.valeur === 'sombre';
  document.body.classList.toggle('sombre', sombre);
  document.body.classList.toggle('clair', !sombre);
});

// --- le tour ----------------------------------------------------------------

const outils = outilsFactices();
const modele = modeleFactice();
const regles = reglesDepuisCatalogue([...outils.values()]);
const messages = [];

let stop = null;

async function envoyer() {
  const texte = saisie.value.trim();
  if (!texte || stop) return;

  rendu.moi(texte);
  messages.push({ role: 'utilisateur', texte });
  saisie.value = '';
  saisie.style.height = 'auto';

  stop = new AbortController();
  action.textContent = 'Stop';
  action.classList.add('stop');
  pied.textContent = 'réfléchit…';

  await conduire({
    modele,
    outils,
    regles,
    messages,
    flux: new Flux((evenement, charge) => rendu.sur(evenement, charge)),
    demander,
    signal: stop.signal,
  });

  const interrompu = stop.signal.aborted;
  stop = null;
  // Un accord resté en attente quand le tour s'arrête ne doit pas survivre au
  // tour suivant : il répondrait à une question qui n'existe plus.
  repondreAccord = null;
  action.textContent = 'Envoyer';
  action.classList.remove('stop');
  pied.textContent = interrompu ? 'interrompu' : REPOS;
  saisie.focus();
}

action.onclick = () => (stop ? stop.abort() : envoyer());

saisie.addEventListener('keydown', (e) => {
  // Entrée envoie, Maj+Entrée saute une ligne. L'inverse surprend tout le
  // monde, et l'ancien volet faisait déjà comme ça.
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); envoyer(); }
});

saisie.addEventListener('input', () => {
  saisie.style.height = 'auto';
  saisie.style.height = `${Math.min(saisie.scrollHeight, 110)}px`;
});

versHote({ ordre: 'pret' });
pied.textContent = REPOS;
saisie.focus();
