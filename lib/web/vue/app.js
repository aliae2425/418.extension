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
| \`/connect\` | se connecter à **ChatGPT** dans le navigateur — votre abonnement |
| \`/connect <clé>\` | poser une clé OpenAI, facturée au jeton |
| \`/model <nom>\` | changer de modèle |
| \`/model\` | dire lequel répond |
| \`/logout\` | fermer la session et effacer la clé |
| \`/aide\` | ceci |`;

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
      ? `Modèle : **${nom}** — retenu, mais aucun fournisseur n'est branché.`
      : `Modèle : **${nom}**.`);
  },

  logout: async () => {
    const session = await demanderHote('oauth_logout');
    const cle = await demanderHote('deconnecter');
    modele = modeleFactice();
    quiRepond = 'modèle fictif';
    voie = 'fictif';
    pied.textContent = repos();
    const faits = [session && 'session ChatGPT fermée', cle && 'clé effacée']
      .filter(Boolean);
    dire(faits.length
      ? `${faits.join(', ')}. Le modèle fictif reprend la main.`
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
