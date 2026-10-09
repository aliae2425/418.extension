// Le câblage : saisie → boucle → rendu. Rien de plus.
//
// Depuis J4 le moteur tourne ICI, dans la page. Python ne pilote plus rien :
// il monte le WebView2, dit quel thème Revit affiche, et encaisse le journal.
// Ce qui passait par `postMessage` à chaque jeton ne traverse plus rien.

import { Flux } from '../harnais/protocole.js';
import { reglesDepuisCatalogue } from '../harnais/permissions.js';
import { conduire } from '../harnais/boucle.js';
import { modeleFactice, outilsFactices } from '../harnais/modele_factice.js';
import { fournisseurOpenAI, MODELE_DEFAUT } from '../harnais/fournisseurs/openai.js';
import { outilsRevit } from '../harnais/outils_revit.js';
import { TEXTE } from '../harnais/protocole.js';
import { Rendu } from './rendu.js';
import { demanderHote, reponseHote } from './pont.js';
import { analyser } from './commandes.js';

const $ = (id) => document.getElementById(id);
const saisie = $('saisie');
const action = $('action');
const pied = $('pied');

let quiRepond = 'modèle fictif';
let quelsOutils = 'outils fictifs, maquette intacte';
const repos = () => `${quiRepond} · ${quelsOutils}`;

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
  // Une réponse à une demande en vol : elle réveille sa promesse et s'arrête
  // là. Tout le reste est un évènement poussé par l'hôte.
  if (evenement === 'reponse') return void reponseHote(charge);
  if (evenement === 'theme') {
    // Les DEUX classes, pas seulement `sombre` : sans `clair` explicite, un
    // Windows sombre et un Revit clair laisseraient le repli de
    // `prefers-color-scheme` gagner, et le volet serait noir à tort.
    const sombre = charge.valeur === 'sombre';
    document.body.classList.toggle('sombre', sombre);
    document.body.classList.toggle('clair', !sombre);
  } else if (evenement === 'config') {
    if (charge.cle) {
      // L'hôte dit SI une clé existe, jamais laquelle. Elle n'entre jamais
      // dans la page : `fetch` envoie une sentinelle, l'hôte la remplace.
      modele = fournisseurOpenAI({ modele: modeleChoisi() });
      quiRepond = modeleChoisi();
    }
    brancherOutils();
    if (!stop) pied.textContent = repos();
  }
});

// Demande le catalogue de `lib/rvt` et remplace les outils fictifs. S'il est
// vide — routes pyRevit éteintes, aucun document ouvert — on GARDE les
// fictifs : un volet qui ne sait plus rien faire serait pire qu'un volet qui
// joue des scénarios et le dit.
async function brancherOutils() {
  let catalogue = [];
  try {
    catalogue = await demanderHote('outils');
  } catch (erreur) {
    quelsOutils = `maquette injoignable (${erreur.message}) — outils fictifs`;
    return;
  }
  if (!catalogue?.length) {
    quelsOutils = 'maquette muette — outils fictifs';
    return;
  }
  outils = outilsRevit(catalogue, (nom, args, ctx) => demanderHote(
    'outil', { nom, arguments: args }, ctx?.signal,
  ));
  regles = reglesDepuisCatalogue([...outils.values()]);
  const dangereux = catalogue.filter((o) => o.irreversible).length;
  quelsOutils = `${catalogue.length} outils Revit, dont ${dangereux} irréversibles`;
}

// --- les commandes ----------------------------------------------------------

// Elles ne partent JAMAIS au modèle et n'entrent pas dans l'historique : ce
// sont des réglages, pas de la conversation. Elles passent quand même par le
// flux, ce qui leur offre le rendu Markdown et le défilement sans rien de neuf.
const CLE_MODELE = '418.modele';

function dire(markdown) {
  flux.ajouter(flux.ouvrir(TEXTE), markdown);
  flux.fini();
}

const AIDE = `| commande | effet |
|---|---|
| \`/connect <clé>\` | poser une clé OpenAI — rangée hors du dépôt |
| \`/connect\` | dire d'où vient la clé en place |
| \`/model <nom>\` | changer de modèle |
| \`/model\` | dire lequel répond |
| \`/logout\` | effacer la clé rangée |
| \`/aide\` | ceci |`;

const COMMANDES = {
  aide: async () => dire(AIDE),

  connect: async (valeur) => {
    if (!valeur) {
      const source = await demanderHote('source');
      return dire(source
        ? `Clé en place, posée par **${source}**.`
        : 'Aucune clé. `/connect sk-…` pour en poser une.');
    }
    // La clé traverse la page une fois, vers l'hôte, et n'y revient jamais :
    // il ne renvoie que l'état. Rien n'est gardé ici, ni en mémoire ni en
    // stockage local.
    const pose = await demanderHote('connecter', { cle: valeur });
    if (!pose) return dire('Clé refusée — rien n\'a été écrit. `/journal`.');
    modele = fournisseurOpenAI({ modele: modeleChoisi() });
    quiRepond = modeleChoisi();
    pied.textContent = repos();
    dire(`Connecté. **${modeleChoisi()}** répond désormais.`);
  },

  model: async (nom) => {
    if (!nom) {
      return dire(`Modèle : **${modeleChoisi()}**.`
        + ' `/model <nom>` pour en changer.');
    }
    // Aucune liste en dur : elle vieillirait sans que rien ne le signale, et
    // un nom refusé revient de toute façon en clair dans l'erreur de l'API.
    localStorage.setItem(CLE_MODELE, nom);
    if (quiRepond !== 'modèle fictif') {
      modele = fournisseurOpenAI({ modele: nom });
      quiRepond = nom;
      pied.textContent = repos();
    }
    dire(`Modèle : **${nom}**.`);
  },

  logout: async () => {
    const efface = await demanderHote('deconnecter');
    modele = modeleFactice();
    quiRepond = 'modèle fictif';
    pied.textContent = repos();
    dire(efface
      ? 'Clé effacée. Le modèle fictif reprend la main.'
      : 'Aucune clé rangée à effacer. Une variable d\'environnement, elle, '
        + 'ne s\'efface pas d\'ici.');
  },
};

function modeleChoisi() {
  return localStorage.getItem(CLE_MODELE) || MODELE_DEFAUT;
}

async function executer(commande) {
  const faire = COMMANDES[commande.nom];
  if (!faire) {
    return dire(`Commande inconnue : \`/${commande.nom}\`. \`/aide\` les liste.`);
  }
  try {
    await faire(commande.arguments);
  } catch (erreur) {
    dire(`\`/${commande.nom}\` a échoué : ${erreur.message}`);
  }
}

// --- le tour ----------------------------------------------------------------

let outils = outilsFactices();
// Remplacé par le vrai fournisseur si l'hôte annonce une clé — voir le
// gestionnaire de `config` plus haut. Fictif tant qu'il n'y en a pas : un
// volet qui ne répond rien serait pire qu'un volet qui répond faux et le dit.
let modele = modeleFactice();
let regles = reglesDepuisCatalogue([...outils.values()]);
const messages = [];

// UN flux pour toute la session, pas un par tour. Les ids de parts doivent
// être uniques dans la conversation : un flux neuf repartirait à `p1`, et le
// `p1` du tour 2 irait réveiller la bulle du tour 1, qui se remettrait à
// grossir. C'est exactement ce qui empilait les réponses les unes sur les
// autres.
const flux = new Flux((evenement, charge) => rendu.sur(evenement, charge));

let stop = null;

async function envoyer() {
  const texte = saisie.value.trim();
  if (!texte || stop) return;

  rendu.moi(texte);
  saisie.value = '';
  saisie.style.height = 'auto';

  // Une commande est traitée SUR PLACE et n'entre pas dans l'historique :
  // c'est un réglage, pas un tour de conversation. Elle ne part jamais en
  // fond non plus — elle touche l'état de la page.
  const commande = analyser(texte);
  if (commande) {
    await executer(commande);
    saisie.focus();
    return;
  }

  messages.push({ role: 'utilisateur', texte });
  stop = new AbortController();
  action.textContent = 'Stop';
  action.classList.add('stop');
  pied.textContent = 'réfléchit…';

  await conduire({
    modele, outils, regles, messages, flux, demander, signal: stop.signal,
  });

  const interrompu = stop.signal.aborted;
  stop = null;
  // Un accord resté en attente quand le tour s'arrête ne doit pas survivre au
  // tour suivant : il répondrait à une question qui n'existe plus.
  repondreAccord = null;
  action.textContent = 'Envoyer';
  action.classList.remove('stop');
  pied.textContent = interrompu ? 'interrompu' : repos();
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
pied.textContent = repos();
saisie.focus();
