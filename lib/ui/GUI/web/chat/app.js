// L'interface du prototype. Elle ne sait rien du modèle, rien de Revit : elle
// dessine des parts et renvoie des intentions. C'est la règle de dépendance
// d'opencode — le client connaît le protocole, jamais le moteur.

import { rendre } from './markdown.js';

const $ = (id) => document.getElementById(id);
const fil = $('fil');
const saisie = $('saisie');
const action = $('action');
const pied = $('pied');

// id de part → son élément. C'est ce qui permet à un delta de ne porter que
// son morceau : sans ce registre, chaque jeton devrait renvoyer tout le texte.
const elements = new Map();
let tour = null;
let occupe = false;

function vers(message) {
  window.chrome.webview.postMessage(JSON.stringify(message));
}

function au_bas() {
  // `scrollHeight` est lu après la mutation : en flux, suivre le bas est la
  // seule façon de voir ce qui arrive.
  fil.scrollTop = fil.scrollHeight;
}

function nouveau_tour() {
  tour = document.createElement('div');
  tour.className = 'tour';
  fil.appendChild(tour);
  return tour;
}

// --- dessin des parts ------------------------------------------------------

function dessiner(part) {
  const hote = tour || nouveau_tour();
  let el;

  if (part.genre === 'texte') {
    el = document.createElement('div');
    el.className = 'bulle lui ecrit';
  } else if (part.genre === 'raisonnement') {
    el = document.createElement('details');
    el.className = 'raisonnement';
    const titre = document.createElement('summary');
    titre.textContent = 'raisonnement';
    el.appendChild(titre);
    const corps = document.createElement('div');
    corps.className = 'corps';
    el.appendChild(corps);
  } else if (part.genre === 'outil') {
    el = outil(part);
  } else if (part.genre === 'etape') {
    el = document.createElement('div');
    el.className = 'etape';
    el.textContent = part.texte || '';
  } else {
    el = document.createElement('div');
    el.className = 'erreur';
    el.textContent = part.texte || 'erreur';
  }

  elements.set(part.id, el);
  hote.appendChild(el);
  au_bas();
  return el;
}

const LIBELLES = {
  en_cours: 'en cours…',
  attente_accord: 'votre accord ?',
  fait: 'fait',
  refuse: 'refusé',
  echec: 'échec',
};

function outil(part) {
  const el = document.createElement('div');
  el.className = 'outil';
  el.innerHTML = `
    <div class="tete">
      <span class="nom"></span>
      <span class="args"></span>
      <span class="etat"></span>
    </div>`;
  el.querySelector('.nom').textContent = part.nom || '';
  el.querySelector('.args').textContent = part.arguments
    ? JSON.stringify(part.arguments) : '';
  majorer(el, part);
  return el;
}

function majorer(el, part) {
  el.dataset.etat = part.etat || '';
  const etat = el.querySelector('.etat');
  if (etat) etat.textContent = LIBELLES[part.etat] || part.etat || '';

  // La sortie n'apparaît qu'une fois : un `pre` recréé à chaque mise à jour
  // ferait sauter la sélection en cours.
  let sortie = el.querySelector('pre');
  if (part.sortie) {
    if (!sortie) { sortie = document.createElement('pre'); el.appendChild(sortie); }
    sortie.textContent = part.sortie;
  } else if (sortie) {
    sortie.remove();
  }

  const ancien = el.querySelector('.accord');
  if (ancien) ancien.remove();
  if (part.etat === 'attente_accord') el.appendChild(accord(part));
}

function accord(part) {
  const boite = document.createElement('div');
  boite.className = 'accord';
  boite.innerHTML = `
    <span class="avertit">irréversible — aucun Ctrl+Z ne le défait</span>
    <button class="refuser">Refuser</button>
    <button class="accorder">Accorder</button>`;
  // Refuser en tête du DOM, donc premier au Tab : le geste le moins coûteux
  // doit être le plus sûr.
  const repondre = (oui) => {
    boite.remove();
    vers({ ordre: 'accord', id: part.id, oui });
  };
  boite.querySelector('.refuser').onclick = () => repondre(false);
  boite.querySelector('.accorder').onclick = () => repondre(true);
  boite.querySelector('.refuser').focus();
  return boite;
}

// --- évènements du moteur --------------------------------------------------

const textes = new Map();   // id → texte cumulé, pour re-rendre le markdown

function sur_delta({ id, morceau }) {
  const el = elements.get(id);
  if (!el) return;
  const cumul = (textes.get(id) || '') + morceau;
  textes.set(id, cumul);
  const cible = el.classList.contains('raisonnement')
    ? el.querySelector('.corps') : el;
  // Re-rendre tout le cumul à chaque delta, et non ajouter du texte : un
  // `**gras` à moitié arrivé n'est pas du HTML valide tant qu'il n'est pas
  // fermé. À l'échelle d'une bulle, le coût ne se voit pas.
  cible.innerHTML = rendre(cumul);
  au_bas();
}

const GESTES = {
  'part.neuve': (p) => dessiner(p),
  'part.delta': sur_delta,
  'part.maj': (p) => {
    const el = elements.get(p.id);
    if (el) majorer(el, p);
  },
  'tour.fini': ({ raison }) => {
    document.querySelectorAll('.bulle.ecrit')
      .forEach((b) => b.classList.remove('ecrit'));
    rendre_la_main(raison);
  },
};

window.chrome.webview.addEventListener('message', (e) => {
  const { evenement, charge } = typeof e.data === 'string'
    ? JSON.parse(e.data) : e.data;
  if (evenement === 'theme') {
    // Les DEUX classes, pas seulement `sombre` : sans `clair` explicite, un
    // Windows en sombre et un Revit en clair laisseraient le repli de
    // `prefers-color-scheme` gagner, et le volet serait noir à tort.
    const sombre = charge.valeur === 'sombre';
    document.body.classList.toggle('sombre', sombre);
    document.body.classList.toggle('clair', !sombre);
    return;
  }
  const geste = GESTES[evenement];
  if (geste) geste(charge || {});
});

// --- saisie ----------------------------------------------------------------

function rendre_la_main(raison) {
  occupe = false;
  action.textContent = 'Envoyer';
  action.classList.remove('stop');
  pied.textContent = raison === 'interrompu'
    ? 'interrompu' : 'agent fictif — rien n\'est envoyé, rien n\'est modifié';
  saisie.focus();
}

function envoyer() {
  const texte = saisie.value.trim();
  if (!texte || occupe) return;
  nouveau_tour();
  const moi = document.createElement('div');
  moi.className = 'bulle moi';
  moi.textContent = texte;
  tour.appendChild(moi);
  saisie.value = '';
  saisie.style.height = 'auto';
  occupe = true;
  action.textContent = 'Stop';
  action.classList.add('stop');
  pied.textContent = 'réfléchit…';
  nouveau_tour();
  au_bas();
  vers({ ordre: 'envoyer', texte });
}

action.onclick = () => (occupe ? vers({ ordre: 'interrompre' }) : envoyer());

saisie.addEventListener('keydown', (e) => {
  // Entrée envoie, Maj+Entrée saute une ligne. L'inverse surprend tout le
  // monde, et le volet actuel fait déjà comme ça.
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); envoyer(); }
});

saisie.addEventListener('input', () => {
  saisie.style.height = 'auto';
  saisie.style.height = Math.min(saisie.scrollHeight, 110) + 'px';
});

vers({ ordre: 'pret' });
saisie.focus();
