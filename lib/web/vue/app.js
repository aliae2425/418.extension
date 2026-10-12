// Le câblage : saisie → boucle → rendu. Rien de plus.
//
// Depuis J4 le moteur tourne ICI, dans la page. Python ne pilote plus rien :
// il monte le WebView2, dit quel thème Revit affiche, et encaisse le journal.
// Ce qui passait par `postMessage` à chaque jeton ne traverse plus rien.

import { Flux } from '../harnais/protocole.js';
import { reglesDepuisCatalogue } from '../harnais/permissions.js';
import { conduire } from '../harnais/boucle.js';
import { modeleFactice, outilsFactices } from '../harnais/modele_factice.js';
import { fournisseurOpenAI, MODELE_DEFAUT, modeles as modelesOpenAI }
  from '../harnais/fournisseurs/openai.js';
import { outilsRevit } from '../harnais/outils_revit.js';
import { fournisseurChatGPT, MODELE_DEFAUT as MODELE_CHATGPT }
  from '../harnais/fournisseurs/chatgpt.js';
import { fournisseurAnthropic, MODELE_DEFAUT as MODELE_ANTHROPIC,
  PREFIXE_CLE as PREFIXE_ANTHROPIC }
  from '../harnais/fournisseurs/anthropic.js';
import { TEXTE } from '../harnais/protocole.js';
import { Rendu } from './rendu.js';
import { demanderHote, reponseHote, ligneHote } from './pont.js';
import { analyser, filtrer, completer, CATALOGUE } from './commandes.js';
import { Historique } from './historique.js';
import { catalogue, fournisseursServis, connexionsServies, modelesServis }
  from '../harnais/catalogue.js';
import { entreesModeles as arbreModeles, connexionsVivantes }
  from '../harnais/arbre.js';
// L'instantané embarqué : il fait que `/connect` n'est jamais vide, même au
// tout premier lancement et sur un poste sans Internet.
import embarque from '../catalogue.json' with { type: 'json' };

const $ = (id) => document.getElementById(id);
const saisie = $('saisie');
const action = $('action');
const pied = $('pied');

// Ce que le pied de page annonce. Pas de « fictif » : tant qu'aucun
// fournisseur n'est branché, ce qui manque est une CONNEXION — le dire comme
// ça donne le geste à faire, là où « fictif » ne décrivait qu'un état.
// « vérification… » au départ, et non « non connecté » : on ne sait pas
// encore. Annoncer une absence qu'on n'a pas constatée ferait taper /connect
// à quelqu'un qui est déjà connecté.
let quiRepond = 'vérification…';
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
    // session ou une clé existe, jamais leur valeur — et il a VERIFIE que la
    // session tient, pas seulement qu'un jeton traîne.
    branches = { oauth: Boolean(charge.oauth), cles: charge.cles || {} };
    const { cles } = branches;
    // La voie du dernier coup d'abord : on peut être branché à trois
    // fournisseurs à la fois, et repartir sur le premier venu à chaque
    // ouverture du volet serait une surprise quotidienne.
    if (reprendreVoie()) { /* rien de plus */ }
    else if (charge.oauth) brancherChatGPT();
    else if (cles.openai) brancherOpenAI();
    else if (cles.anthropic) brancherAnthropic();
    else quiRepond = 'non connecté';
    // Une session morte ne se découvre pas au premier message : on le dit
    // maintenant, avec le geste à faire.
    if (charge.raison) dire(`${charge.raison}`);
    brancherOutils();
    if (!stop) pied.textContent = repos();
  }
});

// Qui répond, et par où. Deux fournisseurs partagent la connexion `cle` :
// la voie seule ne suffit plus à savoir lequel reconstruire, et le
// reconstruire au hasard ferait répondre une clé absente.
let voie = 'fictif';
let maison = '';

// Ce à quoi on est branché, d'après l'hôte. Plusieurs à la fois : poser une
// clé Anthropic n'enlève rien à la session ChatGPT, et `/model` sert alors
// d'aiguillage entre les deux.
let branches = { oauth: false, cles: {} };

// Reprend la voie du dernier coup, si elle tient encore. Débranchée depuis
// (clé effacée, session expirée), on retombe sur l'ordre par défaut plutôt
// que de brancher dans le vide.
function reprendreVoie() {
  let lu = null;
  try {
    lu = JSON.parse(localStorage.getItem(CLE_VOIE) || 'null');
  } catch { return false; }
  if (!lu?.voie) return false;
  const vivante = lu.voie === 'abonnement'
    ? branches.oauth : Boolean(branches.cles[lu.maison]);
  if (!vivante) return false;
  maison = lu.maison;
  voie = lu.voie;
  rebrancher();
  return true;
}

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
  maison = 'openai';
  retenirVoie();
}

function brancherOpenAI() {
  // La clé n'entre jamais dans la page : `fetch` envoie une sentinelle,
  // l'hôte la remplace par interception.
  modele = fournisseurOpenAI({ modele: modeleChoisi(MODELE_DEFAUT) });
  quiRepond = `${modeleChoisi(MODELE_DEFAUT)} · clé`;
  voie = 'cle';
  maison = 'openai';
  retenirVoie();
}

function brancherAnthropic() {
  // Appel DIRECT, et sanctionné : `anthropic-dangerous-direct-browser-access`
  // est un opt-in documenté. L'en-tête d'authentification est `x-api-key`,
  // pas `Authorization` — l'hôte y pose sa propre sentinelle.
  modele = fournisseurAnthropic({ modele: modeleChoisi(MODELE_ANTHROPIC) });
  quiRepond = `${modeleChoisi(MODELE_ANTHROPIC)} · clé`;
  voie = 'cle';
  maison = 'anthropic';
  retenirVoie();
}

// Reconstruit le fournisseur ACTIF. Appelé par `/model` : en choisir un au
// hasard ferait répondre une clé absente, ou une session fermée.
function rebrancher() {
  if (voie === 'abonnement') return brancherChatGPT();
  if (voie !== 'cle') return undefined;
  return maison === 'anthropic' ? brancherAnthropic() : brancherOpenAI();
}

// Le modèle par défaut de la voie active — les trois ne nomment pas leurs
// modèles pareil.
function defautCourant() {
  if (voie === 'abonnement') return MODELE_CHATGPT;
  return maison === 'anthropic' ? MODELE_ANTHROPIC : MODELE_DEFAUT;
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
// Le modèle est retenu PAR CONNEXION, pas globalement : passer chez
// Anthropic en gardant `gpt-5.6` ferait répondre un 404 au premier message.
const CLE_MODELE = '418.modele';
// La connexion active, retenue pour survivre à un rechargement. Rester
// branché à trois fournisseurs et redémarrer sur le premier venu serait une
// surprise à chaque ouverture du volet.
const CLE_VOIE = '418.voie';

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
    if (valeur) return poserCle(valeur);
    etapeFournisseur();
  },

  model: async (nom) => {
    if (!nom) return choisirModele();
    // Aucune liste en dur : elle vieillirait sans que rien ne le signale, et
    // un nom refusé revient de toute façon en clair dans l'erreur de l'API.
    retenirModele(nom);
    rebrancher();
    pied.textContent = repos();
    dire(voie === 'fictif'
      ? `Modèle : **${nom}** — retenu, mais il faut d'abord \`/connect\`.`
      : `Modèle : **${nom}**.`);
  },

  // Sans argument, TOUT : « me déconnecter » qui laisserait une clé derrière
  // serait une déconnexion qui n'en est pas une. Avec, on n'en débranche
  // qu'un — on peut tenir trois voies, et en fermer une n'est pas les fermer
  // toutes.
  logout: async (qui) => {
    const chez = (qui || '').trim().toLowerCase();
    if (chez && chez !== 'chatgpt' && !(chez in branches.cles)) {
      return dire(`\`${chez}\` n'est pas un fournisseur connu. `
        + '`/logout` sans argument ferme tout.');
    }
    const session = (!chez || chez === 'chatgpt')
      ? await demanderHote('oauth_logout') : false;
    const cle = chez === 'chatgpt'
      ? false : await demanderHote('deconnecter', { fournisseur: chez || null });
    if (session) branches.oauth = false;
    if (cle) branches.cles = chez ? { ...branches.cles, [chez]: false } : {};
    // Rebrancher sur ce qui RESTE : avoir fermé ChatGPT ne doit pas rendre
    // muette une clé Anthropic posée juste avant.
    const reste = vivantes()[0];
    if (reste) {
      maison = reste.f.id;
      voie = reste.c.id;
      rebrancher();
    } else {
      modele = modeleFactice();
      quiRepond = 'non connecté';
      voie = 'fictif';
      maison = '';
      localStorage.removeItem(CLE_VOIE);
    }
    pied.textContent = repos();
    const faits = [session && 'session ChatGPT fermée',
      cle && (chez ? `clé ${chez} effacée` : 'clés effacées')].filter(Boolean);
    if (!faits.length) {
      return dire('Rien à effacer. Une variable d\'environnement, elle, ne '
        + 's\'efface pas d\'ici.');
    }
    return dire(reste
      ? `${faits.join(', ')}. Reste **${reste.f.nom} · ${reste.c.nom}**.`
      : `${faits.join(', ')}. \`/connect\` pour rouvrir une session.`);
  },
};

// Le modèle choisi à la main l'emporte, quel que soit le fournisseur. Les
// deux backends ne nomment pas leurs modèles pareil — d'où le défaut passé
// par l'appelant plutôt qu'une constante unique.
// --- /connect : fournisseur → connexion → modèle ----------------------------
//
// Trois étapes dans la MÊME liste, et Échap remonte d'un cran plutôt que de
// tout refermer : se tromper de porte ne doit pas obliger à retaper la
// commande. `/model` ouvre directement la troisième.

function etapeFournisseur() {
  const servis = fournisseursServis(cat.fournisseurs, CONNEXIONS);
  if (!servis.length) {
    return dire('Aucun fournisseur au catalogue. `/connect sk-…` pour poser '
      + 'une clé OpenAI directement.');
  }
  // On montre cette étape MÊME avec un seul fournisseur. Elle paraît un clic
  // pour rien, et c'est faux : elle dit chez qui on va, et elle rend la
  // structure lisible — maison, puis porte, puis modèle. La sauter donnait
  // un `/connect` qui s'ouvrait sur « ChatGPT / Clé API » sans qu'on sache
  // que les deux sont la même maison.
  ouvrirMenu(servis.map((f) => ({
    titre: f.nom,
    args: `${connexionsServies(f, CONNEXIONS).length} voies`,
    cherche: f.nom,
    detail: connexionsServies(f, CONNEXIONS).map((c) => c.nom).join(' · '),
    prendre: () => etapeConnexion(f),
  })));
}

function etapeConnexion(fournisseur) {
  const voies = connexionsServies(fournisseur, CONNEXIONS);
  if (!voies.length) return dire(`${fournisseur.nom} : aucune voie branchée.`);
  ouvrirMenu(voies.map((c) => ({
    titre: c.nom,
    args: `${modelesServis(c).length} modèles`,
    cherche: `${c.nom} ${c.id}`,
    detail: c.detail || '',
    prendre: () => (c.id === 'abonnement'
      ? void connecterChatGPT(fournisseur, c)
      : void saisirCle(fournisseur)),
  })), { retour: etapeFournisseur });
}

// La clé se tape dans une MODALE, pas dans le fil. Dans le fil elle resterait
// affichée en clair, `↑` la rappellerait, et elle traînerait dans l'historique
// de la session. `<dialog>` fait le reste tout seul : fond bloqué, focus
// piégé, Échap qui annule.
function demanderCle(fournisseur) {
  const modale = $('modale-cle');
  const champ = $('cle-valeur');
  $('cle-titre').textContent = `Clé API — ${fournisseur.nom}`;
  $('cle-aide').textContent = fournisseur.doc
    ? `À créer sur ${fournisseur.doc}. Elle est rangée hors du dépôt, et `
      + 'la page ne la reverra jamais.'
    : 'Elle est rangée hors du dépôt, et la page ne la reverra jamais.';
  champ.placeholder = fournisseur.id === 'anthropic' ? 'sk-ant-…' : 'sk-…';
  champ.value = '';
  // Annuler n'est pas un bouton de soumission (sinon Entrée l'aurait
  // déclenché) : il ferme à la main, avec la même valeur vide qu'Échap.
  $('cle-non').onclick = () => modale.close('');
  modale.showModal();
  champ.focus();
  return new Promise((resoudre) => {
    modale.addEventListener('close', () => {
      const valeur = champ.value.trim();
      // Le champ est vidé AVANT de rendre : la clé ne doit pas rester dans le
      // DOM après coup, où un simple inspecteur la relirait.
      champ.value = '';
      resoudre(modale.returnValue === 'ok' ? valeur : '');
    }, { once: true });
  });
}

async function saisirCle(fournisseur) {
  const valeur = await demanderCle(fournisseur);
  if (!valeur) return dire('Rien posé. `/connect` pour reprendre.');
  cleAttendue = fournisseur.id;
  return poserCle(valeur);
}

async function poserCle(valeur) {
  // La clé traverse la page une fois, vers l'hôte, et n'y revient jamais :
  // il ne renvoie que l'état. Rien n'est gardé ici.
  const pose = await demanderHote('connecter', { cle: valeur });
  if (!pose) return dire('Clé refusée — rien n\'a été écrit. Voir `data/418.log`.');
  brancherOpenAI();
  pied.textContent = repos();
  dire('Connecté par clé.');
  return choisirModele();
}

async function connecterChatGPT(_fournisseur = null, _connexion = null) {
  // Le navigateur s'ouvre, l'hôte attend son retour sur sa boucle locale —
  // jusqu'à cinq minutes, hors du fil d'interface pour que Revit reste rendu
  // à la main.
  dire('Navigateur ouvert — connectez-vous à ChatGPT, puis revenez ici.');
  const ouverte = await demanderHote('oauth');
  if (!ouverte) {
    return dire('Connexion abandonnée ou refusée. `/connect` pour réessayer.');
  }
  branches.oauth = true;
  brancherChatGPT();
  pied.textContent = repos();
  dire('Session ouverte, sur votre abonnement.');
  // Troisième étape, enchaînée : l'ancien assistant faisait déjà ça, et
  // s'arrêter juste avant le choix du modèle laisse le travail à moitié.
  return choisirModele();
}

// --- /model : un arbre des connexions VIVANTES ------------------------------
//
// Pas « les modèles de la voie active » : TOUTES celles auxquelles on est
// branché, dépliables. Poser une clé Anthropic n'éteint pas la session
// ChatGPT — l'une et l'autre restent là, et `/model` est l'aiguillage. Sans
// lui, changer de maison voudrait dire se déconnecter de la première.

const ouverts = new Set();     // les connexions dépliées, par `maison/voie`
const listes = new Map();      // ce que l'API a répondu, une fois demandé

// L'arbre lui-même vit dans `harnais/arbre.js` : il ne touche ni au DOM ni au
// réseau, et s'éprouve donc sans navigateur. Ici on ne fait que lui donner
// l'état de la page et recevoir ses clics.
const vivantes = () => connexionsVivantes(cat.fournisseurs, CONNEXIONS, branches);

function entreesModeles(q = '') {
  return arbreModeles({
    fournisseurs: cat.fournisseurs,
    connexions: CONNEXIONS,
    branches,
    actif: `${maison}/${voie}`,
    ouverts,
    listes,
    modeleActif: modeleChoisi(defautCourant()),
    surGroupe: basculer,
    surModele: basculerVers,
  }, q);
}

async function choisirModele() {
  if (!vivantes().length) {
    return dire('Aucun fournisseur branché. `/connect` d\'abord.');
  }
  // Le groupe actif déplié d'office : on ouvre `/model` pour changer DE
  // modèle neuf fois sur dix, pas pour changer de maison.
  ouverts.add(`${maison}/${voie}`);
  ouvrirMenu(entreesModeles);
  return undefined;
}


function basculer(cle, force = null) {
  const ouvrir = force === null ? !ouverts.has(cle) : force;
  if (ouvrir) ouverts.add(cle); else ouverts.delete(cle);
  rafraichirListe(choisie);
  if (ouvrir && !listes.has(cle)) remplir(cle);
}

async function remplir(cle) {
  // Seule une clé OpenAI sait dire ce qu'elle peut appeler. Le backend Codex
  // n'expose aucun catalogue, Anthropic non plus derrière une clé : pour eux
  // 418.cloud EST la source, et c'est le trou qu'il existe pour boucher.
  if (cle !== 'openai/cle') return;
  try {
    const noms = await modelesOpenAI();
    if (noms.length) listes.set(cle, noms);
  } catch {
    // Le catalogue reste affiché — une liste datée vaut mieux qu'une liste
    // vide, et `/model <nom>` marche de toute façon.
    return;
  }
  if (menu === entreesModeles) rafraichirListe(choisie);
}

// Choisir un modèle d'une AUTRE maison, c'est y basculer. Les deux
// connexions restent ouvertes : on change d'aiguillage, pas de session.
function basculerVers(f, c, nom) {
  maison = f.id;
  voie = c.id;
  retenirModele(nom, f.id, c.id);
  rebrancher();
  pied.textContent = repos();
  dire(`**${f.nom} · ${c.nom}** — modèle **${nom}**.`);
}

// Le modèle retenu POUR CETTE connexion. Les trois voies ne nomment pas
// leurs modèles pareil, d'où le défaut passé par l'appelant.
function modeleChoisi(defaut = MODELE_DEFAUT, chez = maison, par = voie) {
  return localStorage.getItem(`${CLE_MODELE}.${chez}.${par}`) || defaut;
}

function retenirModele(nom, chez = maison, par = voie) {
  localStorage.setItem(`${CLE_MODELE}.${chez}.${par}`, nom);
}

function retenirVoie() {
  localStorage.setItem(CLE_VOIE, JSON.stringify({ maison, voie }));
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

// Les deux voies qu'on sait VRAIMENT brancher. Un fournisseur du catalogue
// dont la `connexion` n'est pas là-dedans n'apparaît pas : le proposer
// ouvrirait une voie sans issue.
const CONNEXIONS = ['abonnement', 'cle'];
const cat = catalogue({ embarque });

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

  // Une clé tapée à la main ne doit pas finir affichée dans le fil ni
  // rappelable par `↑`. La modale est la voie normale ; celle-ci reste
  // ouverte, et on la masque des deux endroits où elle traînerait.
  const commande = analyser(texte);
  const secret = commande?.nom === 'connect' && commande.arguments;
  rendu.moi(secret ? '/connect ••••••••' : texte);
  if (!secret) historique.ajouter(texte);
  saisie.value = '';
  fermerListe();
  ajuster();

  // Une commande est traitée SUR PLACE et n'entre pas dans l'historique :
  // c'est un réglage, pas un tour de conversation. Elle ne part jamais en
  // fond non plus — elle touche l'état de la page.
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

// La MÊME liste sert deux choses : les propositions de commandes pendant la
// frappe, et les menus ouverts par `/connect` et `/model`. Une entrée a la
// même forme dans les deux cas — titre, détail, et ce qu'elle fait — donc une
// seule navigation au clavier à écrire, et une seule à apprendre.
const liste = $('suggestions');
let proposees = [];
let choisie = 0;
// Un menu ne se referme pas à la frappe, il s'y FILTRE. Les propositions de
// commandes, elles, se recalculent à chaque touche.
let menu = null;
// L'étape précédente d'un assistant. Échap y remonte au lieu de tout
// refermer : se tromper de porte ne doit pas obliger à retaper la commande.
let menuRetour = null;
// Chez qui la prochaine `/connect <clé>` doit aller. Posé par l'assistant ;
// sans lui on devine au préfixe, qui est stable mais pas garanti.
let cleAttendue = '';

function depuisCommande(c) {
  return {
    titre: `/${c.nom}`,
    args: c.args,
    detail: c.aide.replace(/\*\*/g, ''),
    cherche: c.nom,
    // Remplit le champ au lieu d'exécuter : `/connect` et `/model` prennent
    // des arguments, et les lancer au clic les lancerait sans.
    prendre: () => {
      poser(completer(c));
      return false;
    },
  };
}

function rafraichirListe(rang = 0) {
  if (menu) {
    const q = saisie.value.trim().toLowerCase();
    // Une FONCTION quand les entrées dépendent de ce qui est tapé — c'est le
    // cas de l'arbre de `/model`, qui se déplie entièrement dès qu'on filtre.
    const entrees = typeof menu === 'function' ? menu(q) : menu;
    proposees = entrees
      .map((e) => ({ ...e, cherche: e.cherche ?? e.titre }))
      .filter((e) => !q || e.cherche.toLowerCase().includes(q));
  } else {
    proposees = filtrer(saisie.value).map(depuisCommande);
  }
  // Borné, pas remis à zéro : déplier un groupe ne doit pas ramener le
  // curseur en haut de la liste, sinon on perd sa place à chaque →.
  choisie = Math.max(0, Math.min(rang, proposees.length - 1));
  dessinerListe();
}

// Ouvre un menu. `entrees` : un tableau de
// `{titre, detail?, args?, cherche?, groupe?, prendre()}`, ou une fonction
// `(filtre) => tableau` quand il se reconstruit — `/model` s'en sert pour
// déplier ses groupes. `retour` : l'étape précédente, rappelée par Échap.
function ouvrirMenu(entrees, { retour = null } = {}) {
  menu = entrees;
  menuRetour = retour;
  saisie.value = '';
  ajuster();
  rafraichirListe();
  saisie.focus();
}

function dessinerListe() {
  liste.hidden = proposees.length === 0;
  liste.classList.toggle('menu', Boolean(menu));
  if (liste.hidden) { liste.replaceChildren(); return; }
  liste.replaceChildren(...proposees.map((entree, rang) => {
    const el = document.createElement('button');
    el.type = 'button';
    el.className = `choix${rang === choisie ? ' actif' : ''}`
      + `${entree.groupe ? ' groupe' : ''}${entree.sous ? ' sous' : ''}`;
    el.innerHTML = '<span class="nom"></span><span class="args"></span>'
      + '<span class="aide"></span>';
    el.querySelector('.nom').textContent = entree.titre;
    el.querySelector('.args').textContent = entree.args || '';
    // `textContent` et non `innerHTML` : ces libellés viennent parfois d'un
    // fournisseur, et rien d'extérieur n'a le droit de poser du HTML ici.
    el.querySelector('.aide').textContent = entree.detail || '';
    // `mousedown` et non `click` : le champ perdrait le focus avant le clic,
    // la liste se fermerait, et l'entrée disparaîtrait sous le curseur.
    el.addEventListener('mousedown', (e) => { e.preventDefault(); accepter(rang); });
    return el;
  }));
}

function accepter(rang = choisie) {
  const entree = proposees[rang];
  if (!entree) return false;
  // Un en-tête de groupe se déplie : il ne choisit rien. Refermer la liste
  // obligerait à retaper `/model` pour voir ce qu'on vient d'ouvrir.
  if (entree.groupe) { entree.prendre(); return true; }
  fermerListe();
  entree.prendre();
  return true;
}

// Remplit le champ et pose le curseur au bout. Sert à la complétion des
// commandes : `/connect`, `/model` prennent un argument, les lancer au clic
// les lancerait sans.
function poser(texte) {
  saisie.value = texte;
  ajuster();
  saisie.focus();
  saisie.setSelectionRange(texte.length, texte.length);
}

function fermerListe() {
  menu = null;
  menuRetour = null;
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
  if (e.key === 'Escape' && (proposees.length || menu)) {
    e.preventDefault();
    const precedente = menuRetour;
    fermerListe();
    // Remonter d'un cran plutôt que tout refermer, quand il y a un cran.
    if (precedente) precedente();
    return undefined;
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
  // → déplie, ← replie. Sur un modèle, ← remonte à son en-tête et le ferme :
  // c'est le geste d'un arbre, et il évite de chercher la ligne du groupe.
  if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && menu) {
    const entree = proposees[choisie];
    const cle = entree?.groupe || entree?.sous;
    if (!cle || saisie.value) return undefined;   // on édite : le curseur prime
    e.preventDefault();
    if (e.key === 'ArrowRight') return void basculer(cle, true);
    const rang = proposees.findIndex((x) => x.groupe === cle);
    if (rang >= 0) choisie = rang;
    return void basculer(cle, false);
  }
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    // Dans un MENU, Entrée choisit : il n'y a rien à envoyer pendant qu'on
    // choisit. Sur les propositions de commandes, elle envoie — Tab complète,
    // et c'est la règle documentée du volet.
    if (menu && proposees.length) return void accepter();
    return void envoyer();
  }
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

// Le catalogue part en FOND, et n'est jamais attendu : une requête qui
// traîne ne doit pas retarder l'ouverture du volet. Ce qui est déjà en
// cache ou embarqué suffit à dessiner `/connect` tout de suite ; ce qui
// arrive sert au prochain coup.
cat.rafraichir();

versHote({ ordre: 'pret' });
pied.textContent = repos();
ajuster();
saisie.focus();
