// Ce qu'un outil a le droit de faire, et qui en décide.
//
// Remplace `if (nom in irreversibles)` — un test en dur qui ne sait répondre
// qu'une chose et ne retient rien. Le modèle vient d'opencode, transcrit :
//
//   un jeu de règles `{motif, effet}`, effet ∈ autoriser | demander | refuser,
//   et **la DERNIÈRE règle qui correspond gagne**.
//
// La précédence par le dernier est contre-intuitive une seconde, puis évidente :
// on pose un défaut large en tête, et chaque exception s'ajoute à la fin sans
// avoir à réordonner ce qui précède. C'est ce qui permet à « toujours
// autoriser » de s'écrire en une ligne poussée au bout.
//
// Transcrit de opencode (https://github.com/anomalyco/opencode), MIT,
// Copyright (c) 2025 opencode — `core/src/util/wildcard.ts` et
// `core/src/policy.ts`. Voir vendor/opencode-LICENSE.

export const AUTORISER = 'autoriser';
export const DEMANDER = 'demander';
export const REFUSER = 'refuser';

export const EFFETS = [AUTORISER, DEMANDER, REFUSER];

// Réponses possibles à une demande d'accord, reprises telles quelles
// (`once` / `always` / `reject`).
export const UNE_FOIS = 'une_fois';
export const TOUJOURS = 'toujours';
export const JAMAIS = 'jamais';

const ECHAPPE = /[.+^${}()|[\]\\]/g;

// `*` → n'importe quoi, `?` → un caractère. Pas de librairie de glob : une
// regex suffit, et opencode n'en utilise pas non plus.
//
// Sensible à la casse, contrairement à l'original : eux comparent des chemins
// de fichiers sous Windows, nous des noms d'outils, qui sont canoniques.
export function correspond(valeur, motif) {
  const echappe = String(motif).replace(ECHAPPE, '\\$&')
    .replace(/\*/g, '.*')
    .replace(/\?/g, '.');
  return new RegExp(`^${echappe}$`, 's').test(String(valeur));
}

export class Regles {
  constructor(regles = []) {
    this._regles = [];
    for (const r of regles) this.ajouter(r.motif, r.effet);
  }

  // Poussée en FIN de liste, donc prioritaire sur tout ce qui précède.
  ajouter(motif, effet) {
    if (!EFFETS.includes(effet)) throw new Error(`effet inconnu : ${effet}`);
    this._regles.push({ motif, effet });
    return this;
  }

  // La dernière qui correspond gagne. Aucune ne correspond → `defaut`.
  effet(action, defaut = DEMANDER) {
    for (let i = this._regles.length - 1; i >= 0; i -= 1) {
      if (correspond(action, this._regles[i].motif)) return this._regles[i].effet;
    }
    return defaut;
  }

  liste() {
    return this._regles.map((r) => ({ ...r }));
  }
}

// Le jeu de départ, dérivé du catalogue : tout ce qui n'est pas irréversible
// part sans rien demander, le reste demande.
//
// On NE lit pas une configuration sur disque : personne n'en a écrit une, et
// un fichier de réglages pour des valeurs que rien ne change est du décor.
// Les règles vivent en mémoire de session et se modifient par « toujours »
// ou « jamais ».
export function reglesDepuisCatalogue(catalogue) {
  const regles = new Regles([{ motif: '*', effet: AUTORISER }]);
  for (const outil of catalogue) {
    if (outil.irreversible) regles.ajouter(outil.nom, DEMANDER);
  }
  return regles;
}

// Traduit la réponse de l'architecte en décision, et au besoin en règle.
//
// `une_fois` ne retient rien : c'est ce qui distingue « vas-y » de « vas-y et
// ne me redemande plus ». Confondre les deux, c'est ouvrir en grand sur un
// clic distrait.
export function appliquerReponse(regles, action, reponse) {
  if (reponse === TOUJOURS) {
    regles.ajouter(action, AUTORISER);
    return true;
  }
  if (reponse === JAMAIS) {
    regles.ajouter(action, REFUSER);
    return false;
  }
  return reponse === UNE_FOIS;
}
