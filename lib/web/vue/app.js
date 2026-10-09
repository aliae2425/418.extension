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
import { fournisseurChatGPT, MODELE_DEFAUT as MODELE_CHATGPT }
  from '../harnais/fournisseurs/chatgpt.js';
import { TEXTE } from '../harnais/protocole.js';
import { Rendu } from './rendu.js';
import { demanderHote, reponseHote, ligneHote } from './pont.js';
import { analyser, filtrer, completer, CATALOGUE } from './commandes.js';
import { Historique } from './historique.js';

const $ = (id) => document.getElementById(id);
const saisie = $('saisie');
const action = $('action');
const pied = $('pied');

// Ce que le pied de page annonce. Pas de « fictif » : tant qu'aucun
// fournisseur n'est branché, ce qui manque est une CONNEXION — le dire comme
// ça donne le geste à faire, là où « fictif » ne décrivait qu'un état.
let quiRepond = 'non connecté';
let quelsOutils = 'maquette non reliée';
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
  if (evenement === 'ligne') return void ligneHote(charge);
  if (evenement === 'theme') {
    // Les DEUX classes, pas seulement `sombre` : sans `clair` explicite, un
    // Windows sombre et un Revit clair laisseraient le repli de
    // `prefers-color-scheme` gagner, et le volet serait noir à tort.
    const sombre = charge.valeur === 'sombre';
    document.body.classList.toggle('sombre', sombre);
    document.body.classList.toggle('clair', !sombre);
  } else if (evenement === 'config') {
    // L'abonnement d'abord : il ne coûte rien au jeton. L'hôte dit SI une
    // session ou une clé existe, jamais leur valeur.
    if (charge.oauth) brancherChatGPT();
    else if (charge.cle) brancherOpenAI();
    brancherOutils();
    if (!stop) pied.textContent = repos();
  }
});

// Quelle voie répond : 'fictif', 'cle' ou 'abonnement'. Nécessaire parce que
// `/model` doit reconstruire LE BON fournisseur — le reconstruire au hasard
// ferait répondre une clé absente, ou une session fermée.
let voie = 'fictif';

function brancherChatGPT() {
  // L'égress passe par l'hôte : CORS interdit à la page de lire la réponse
  // du backend ChatGPT. Le protocole, lui, reste dans `chatgpt.js`.
  modele = fournisseurChatGPT({
    modele: modeleChoisi(MODELE_CHATGPT),
    diffuser: (corps, opts) => demanderHote(
      'diffuser', { corps }, opts?.signal, opts?.surLigne,
    ),
  });
  quiRepond = `${modeleChoisi(MODELE_CHATGPT)} · abonnement`;
  voie = 'abonnement';
}

function brancherOpenAI() {
  // La clé n'entre jamais dans la page : `fetch` envoie une sentinelle,
  // l'hôte la remplace par interception.
  modele = fournisseurOpenAI({ modele: modeleChoisi() });
  quiRepond = `${modeleChoisi()} · clé`;
  voie = 'cle';
}

// Demande le catalogue de `lib/rvt`. S'il est vide — routes pyRevit éteintes,
// aucun document ouvert — on garde les outils de repli et le pied de page dit
// pourquoi : un volet qui ne sait plus rien faire SANS le dire est pire qu'un
// volet diminué qui l'annonce.
async function brancherOutils() {
  let catalogue = [];
  try {
    catalogue = await demanderHote('outils');
  } catch (erreur) {
    quelsOutils = `maquette injoignable — ${erreur.message}`;
    return;
  }
  if (!catalogue?.length) {
    quelsOutils = 'maquette muette — routes pyRevit éteintes ou projet fermé';
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

// Dérivée du catalogue : une commande ne peut pas s'ajouter sans apparaître
// ici, ni y figurer sans exister.
const AIDE = ['| commande | effet |', '|---|---|',
  ...CATALOGUE.map((c) => `| \`/${c.nom}${c.args ? ` ${c.args}` : ''}\` | ${c.aide} |`),
].join('\n');

const COMMANDES = {
  aide: async () => dire(AIDE),

  connect: async (valeur) => {
    if (valeur) {
      // La clé traverse la page une fois, vers l'hôte, et n'y revient
      // jamais : il ne renvoie que l'état. Rien n'est gardé ici.
      const pose = await demanderHote('connecter', { cle: valeur });
      if (!pose) return dire('Clé refusée — rien n\'a été écrit. Voir `data/418.log`.');
      brancherOpenAI();
      pied.textContent = repos();
      return dire(`Connecté par clé. **${modeleChoisi()}** répond.`);
    }
    // Sans argument : l'abonnement. Le navigateur s'ouvre, l'hôte attend son
    // retour sur sa boucle locale — jusqu'à cinq minutes, hors du fil
    // d'interface pour que Revit reste rendu à la main.
    dire('Navigateur ouvert — connectez-vous à ChatGPT, puis revenez ici.');
    const ouverte = await demanderHote('oauth');
    if (!ouverte) {
      return dire('Connexion abandonnée ou refusée. `/connect` pour réessayer,'
        + ' `/connect sk-…` pour passer par une clé.');
    }
    brancherChatGPT();
    pied.textContent = repos();
    dire(`Session ouverte. **${modeleChoisi(MODELE_CHATGPT)}** répond, sur`
      + ' votre abonnement.');
  },

  model: async (nom) => {
    if (!nom) {
      const defaut = voie === 'abonnement' ? MODELE_CHATGPT : MODELE_DEFAUT;
      return dire(`Modèle : **${modeleChoisi(defaut)}**.`
        + ' `/model <nom>` pour en changer.');
    }
    // Aucune liste en dur : elle vieillirait sans que rien ne le signale, et
    // un nom refusé revient de toute façon en clair dans l'erreur de l'API.
    localStorage.setItem(CLE_MODELE, nom);
    // Reconstruire LA voie active : un fournisseur choisi au hasard ferait
    // répondre une clé absente, ou une session fermée.
    if (voie === 'abonnement') brancherChatGPT();
    else if (voie === 'cle') brancherOpenAI();
    pied.textContent = repos();
    dire(voie === 'fictif'
      ? `Modèle : **${nom}** — retenu, mais il faut d'abord \`/connect\`.`
      : `Modèle : **${nom}**.`);
  },

  logout: async () => {
    const session = await demanderHote('oauth_logout');
    const cle = await demanderHote('deconnecter');
    modele = modeleFactice();
    quiRepond = 'non connecté';
    voie = 'fictif';
    pied.textContent = repos();
    const faits = [session && 'session ChatGPT fermée', cle && 'clé effacée']
      .filter(Boolean);
    dire(faits.length
      ? `${faits.join(', ')}. \`/connect\` pour rouvrir une session.`
      : 'Rien à effacer. Une variable d\'environnement, elle, ne s\'efface '
        + 'pas d\'ici.');
  },
};

// Le modèle choisi à la main l'emporte, quel que soit le fournisseur. Les
// deux backends ne nomment pas leurs modèles pareil — d'où le défaut passé
// par l'appelant plutôt qu'une constante unique.
function modeleChoisi(defaut = MODELE_DEFAUT) {
  return localStorage.getItem(CLE_MODELE) || defaut;
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
const historique = new Historique();

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
  historique.ajouter(texte);
  saisie.value = '';
  fermerListe();
  ajuster();

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
  // Le pied garde l'identité du fournisseur : c'est la bulle d'attente qui
  // dit maintenant que ça réfléchit, et elle le dit avec le temps écoulé.
  rendu.attendre();

  await conduire({
    modele, outils, regles, messages, flux, demander, signal: stop.signal,
  });

  const interrompu = stop.signal.aborted;
  stop = null;
  // Ceinture : `conduire` finit toujours par `tour.fini`, qui fige déjà.
  // Mais une horloge qui survivrait à son tour tournerait pour toujours.
  rendu.figer();
  // Un accord resté en attente quand le tour s'arrête ne doit pas survivre au
  // tour suivant : il répondrait à une question qui n'existe plus.
  repondreAccord = null;
  action.textContent = 'Envoyer';
  action.classList.remove('stop');
  pied.textContent = interrompu ? 'interrompu' : repos();
  saisie.focus();
}

action.onclick = () => (stop ? stop.abort() : envoyer());

// --- propositions de commandes ----------------------------------------------

const liste = $('suggestions');
let proposees = [];
let choisie = 0;

function rafraichirListe() {
  proposees = filtrer(saisie.value);
  choisie = 0;
  dessinerListe();
}

function dessinerListe() {
  liste.hidden = proposees.length === 0;
  if (liste.hidden) { liste.replaceChildren(); return; }
  liste.replaceChildren(...proposees.map((commande, rang) => {
    const el = document.createElement('button');
    el.type = 'button';
    el.className = rang === choisie ? 'choix actif' : 'choix';
    el.innerHTML = '<span class="nom"></span><span class="args"></span>'
      + '<span class="aide"></span>';
    el.querySelector('.nom').textContent = `/${commande.nom}`;
    el.querySelector('.args').textContent = commande.args;
    // L'aide porte du Markdown léger — on ne rend QUE le gras, à la main :
    // passer par le moteur de rendu ferait entrer du HTML là où il n'en faut
    // aucun.
    el.querySelector('.aide').textContent = commande.aide.replace(/\*\*/g, '');
    // `mousedown` et non `click` : le champ perdrait le focus avant le clic,
    // la liste se fermerait, et l'entrée disparaîtrait sous le curseur.
    el.addEventListener('mousedown', (e) => { e.preventDefault(); accepter(rang); });
    return el;
  }));
}

// Remplit le champ au lieu d'exécuter : `/connect` et `/model` prennent des
// arguments, et les exécuter au clic les lancerait sans.
function accepter(rang = choisie) {
  const commande = proposees[rang];
  if (!commande) return false;
  saisie.value = completer(commande);
  fermerListe();
  ajuster();
  saisie.focus();
  saisie.setSelectionRange(saisie.value.length, saisie.value.length);
  return true;
}

function fermerListe() {
  proposees = [];
  dessinerListe();
}

function deplacer(pas) {
  choisie = (choisie + pas + proposees.length) % proposees.length;
  dessinerListe();
}

// --- clavier ------------------------------------------------------------------

// Dans un texte multiligne, ↑ et ↓ doivent déplacer le curseur. On ne prend la
// main que lorsqu'il n'y a pas de ligne au-dessus (pour ↑) ou en dessous
// (pour ↓) — comportement d'un terminal, et il ne gêne jamais l'édition.
const riendessus = () => !saisie.value.slice(0, saisie.selectionStart).includes('\n');
const riendessous = () => !saisie.value.slice(saisie.selectionEnd).includes('\n');

function rappeler(texte) {
  if (texte === null) return;
  saisie.value = texte;
  ajuster();
  saisie.setSelectionRange(texte.length, texte.length);
}

saisie.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && proposees.length) {
    e.preventDefault();
    return fermerListe();
  }
  // Tab complète sur la proposition choisie. Hors liste, on laisse Tab
  // déplacer le focus : insérer une tabulation dans un chat ne sert à rien.
  if (e.key === 'Tab' && proposees.length) {
    e.preventDefault();
    return void accepter();
  }
  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    const bas = e.key === 'ArrowDown';
    if (proposees.length) {
      e.preventDefault();
      return deplacer(bas ? 1 : -1);
    }
    if (!bas && riendessus()) {
      e.preventDefault();
      return rappeler(historique.precedent(saisie.value));
    }
    if (bas && riendessous() && historique.parcourt) {
      e.preventDefault();
      return rappeler(historique.suivant());
    }
    return undefined;
  }
  // Entrée envoie, Maj+Entrée saute une ligne. L'inverse surprend tout le
  // monde, et l'ancien volet faisait déjà comme ça.
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); envoyer(); }
  return undefined;
});

// Le champ grandit avec le texte jusqu'à `max-height`, puis défile. La borne
// vit dans le CSS — la redire ici en ferait deux à tenir d'accord.
function ajuster() {
  saisie.style.height = 'auto';            // sinon `scrollHeight` ne redescend pas
  const style = getComputedStyle(saisie);
  const max = parseFloat(style.maxHeight) || Infinity;
  // `scrollHeight` ignore les bordures, que `box-sizing: border-box` compte
  // dans la hauteur. Sans ce rattrapage, le champ est trop court de deux
  // pixels et affiche une barre pour deux pixels.
  const bordures = parseFloat(style.borderTopWidth)
    + parseFloat(style.borderBottomWidth);
  const voulu = saisie.scrollHeight + bordures;
  saisie.style.height = `${Math.min(voulu, max)}px`;
  // La barre n'apparaît QUE passé la borne : en afficher une tant qu'il reste
  // de la place donne l'impression d'être à l'étroit pour rien.
  saisie.classList.toggle('deborde', voulu > max);
}

saisie.addEventListener('input', () => { ajuster(); rafraichirListe(); });

versHote({ ordre: 'pret' });
pied.textContent = repos();
ajuster();
saisie.focus();
