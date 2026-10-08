// Le protocole entre le moteur et l'interface : des *parts* et des évènements.
//
// La leçon d'opencode qu'on retient, et la seule qui coûte peu : **un message
// n'est pas une chaîne**. Il est une suite de parts typées, et un évènement
// porte une part, pas un message. Sans ça, pas de rendu incrémental — on ne
// peint pas au fil de l'eau ce qu'on ne reçoit qu'entier.
//
// opencode en déclare quatorze (`text, reasoning, tool, file, agent, subtask,
// snapshot, patch, compaction, retry, step-start, step-finish`, plus `user` et
// `assistant`). On en prend cinq : on n'a ni fichiers à montrer, ni sous-tâches,
// ni compactage à tracer.
//
// Porté depuis `lib/harnais/parts.py`, qui meurt à J4 avec l'agent factice.
// Les invariants sont les mêmes et les tests aussi — c'est volontaire : si le
// portage avait changé le comportement, les tests l'auraient dit.

// --- genres de parts -------------------------------------------------------

export const TEXTE = 'texte';               // ce que le modèle dit
export const RAISONNEMENT = 'raisonnement'; // ce qu'il se dit, repliable
export const OUTIL = 'outil';               // un appel : nom, args, état, sortie
export const ETAPE = 'etape';               // frontière de tour, comble l'attente
export const ERREUR = 'erreur';             // ce qui a cassé, dit à l'architecte

export const GENRES = [TEXTE, RAISONNEMENT, OUTIL, ETAPE, ERREUR];

// --- états d'une part `outil` ---------------------------------------------

export const EN_COURS = 'en_cours';
export const ATTENTE_ACCORD = 'attente_accord';
export const FAIT = 'fait';
export const REFUSE = 'refuse';
export const ECHEC = 'echec';

// --- évènements ------------------------------------------------------------

export const NEUVE = 'part.neuve';   // une part apparaît
export const DELTA = 'part.delta';   // du texte s'ajoute à une part existante
export const MAJ = 'part.maj';       // l'état d'une part change
export const FINI = 'tour.fini';     // le pendant de `session.idle`

// Les champs qu'une part porte, et les seuls. `changer()` refuse tout le
// reste : sans ça, une faute de frappe poserait un attribut neuf en silence
// et l'interface ne verrait jamais le changement attendu.
const CHAMPS = ['texte', 'nom', 'arguments', 'etat', 'sortie'];

export class Part {
  constructor(id, genre, champs = {}) {
    if (!GENRES.includes(genre)) throw new Error(`genre inconnu : ${genre}`);
    this.id = id;
    this.genre = genre;
    this.texte = champs.texte ?? '';
    this.nom = champs.nom ?? '';              // parts `outil` seulement
    this.arguments = champs.arguments ?? null;
    this.etat = champs.etat ?? '';
    this.sortie = champs.sortie ?? '';
  }

  // La forme qui part à l'interface. Pas de clé vide : ça se lit mal, et
  // chaque clé inutile repart à chaque évènement.
  json() {
    const charge = { id: this.id, genre: this.genre };
    for (const cle of ['texte', 'nom', 'etat', 'sortie']) {
      if (this[cle]) charge[cle] = this[cle];
    }
    if (this.arguments && Object.keys(this.arguments).length) {
      charge.arguments = this.arguments;
    }
    return charge;
  }
}

export class Flux {
  // `sortie(evenement, charge)` est le seul point de contact : le volet y
  // branche un `postMessage`, un test y branche un tableau. Le moteur, lui,
  // ne sait pas qu'une interface existe.
  constructor(sortie) {
    this._sortie = sortie;
    this._rang = 0;
    this._parts = new Map();
  }

  // Déclare une part neuve et la renvoie. L'interface la dessine vide.
  ouvrir(genre, champs = {}) {
    this._rang += 1;
    const part = new Part(`p${this._rang}`, genre, champs);
    this._parts.set(part.id, part);
    this._sortie(NEUVE, part.json());
    return part;
  }

  // Du texte de plus. On n'envoie QUE le morceau, jamais le cumul : renvoyer
  // la part entière à chaque jeton ferait repeindre toute la bulle. C'est la
  // différence entre un flux et un diaporama.
  ajouter(part, morceau) {
    if (!morceau) return part;
    part.texte += morceau;
    this._sortie(DELTA, { id: part.id, morceau });
    return part;
  }

  // Change l'état d'une part — un outil qui finit, échoue, attend l'accord.
  changer(part, champs) {
    for (const [cle, valeur] of Object.entries(champs)) {
      if (!CHAMPS.includes(cle)) throw new Error(`champ inconnu : ${cle}`);
      part[cle] = valeur;
    }
    this._sortie(MAJ, part.json());
    return part;
  }

  // L'interface rend la main à la saisie. Sans lui, elle resterait bloquée
  // sur « réfléchit… ».
  fini(raison = '') {
    this._sortie(FINI, raison ? { raison } : {});
  }

  parts() {
    return [...this._parts.values()];
  }

  // Par où l'interface sait à QUELLE part répondre quand elle accorde un outil.
  dernierId() {
    return this._rang ? `p${this._rang}` : '';
  }
}
