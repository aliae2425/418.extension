// Un modèle FICTIF, qui n'appelle rien et ne touche à rien.
//
// Il honore le contrat qu'un vrai fournisseur honorera — mêmes arguments,
// même forme de retour, mêmes rappels de flux — pour que la boucle, elle, ne
// sache jamais qu'elle parle à un faux. C'est ce qui permet de l'éprouver
// sans abonnement, sans réseau et sans maquette ouverte.
//
// Remplace `lib/harnais/agent_factice.py`, qui meurt avec lui. La différence
// est que celui-ci ne pilote plus la conversation : il ne fait que répondre.
// La boucle décide, l'accord se demande, les outils s'exécutent — comme en vrai.

// Un mot toutes les 25 ms : assez lent pour qu'on VOIE le flux, assez rapide
// pour ne pas rendre l'essai pénible. Un vrai modèle est plus irrégulier.
export const CADENCE = 25;

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

const BIENVENUE = `Je suis un modèle **fictif** : rien ne m'interroge et je ne
touche pas à la maquette. Je sers à éprouver la boucle — catalogue, tours,
accord, interruption — sans abonnement ni projet ouvert.

Essayez **« liste mes vues »** pour des appels d'outils, **« synchronise le
projet »** pour l'accord sur un irréversible, ou **« fais une erreur »**.`;

const VUES = `Le projet **MAISON-PDA.rvt** contient **47 vues en plan**, dont
31 exportables.

| type | nombre |
|---|---|
| plans | 47 |
| exportables | 31 |

Les 16 restantes n'ont pas de cartouche associé.`;

// Rejoue un scénario selon la dernière chose écrite par l'architecte.
// La signature est celle qu'un vrai fournisseur devra présenter.
export function modeleFactice({ cadence = CADENCE } = {}) {
  return async function repondre(messages, catalogue, ctx = {}) {
    // Le TOUR en cours, pas toute la conversation : un vrai modèle relit son
    // historique entier et décide, celui-ci n'a qu'un scénario à rejouer.
    // Regarder tout l'historique le faisait conclure d'emblée dès le premier
    // appel d'outil de la session — donc plus jamais d'accord demandé.
    const tour = depuisLaDemande(messages);
    const demande = tour.length ? tour[0].texte || '' : '';
    const outils = new Set(catalogue.map((o) => o.nom));
    const scene = choisir(demande);

    // Deuxième passage : les outils de CE tour ont répondu, il reste à conclure.
    if (tour.some((m) => m.role === 'outil')) {
      await ecrire(ctx, scene.conclusion, cadence);
      return { texte: '' };
    }

    if (scene.pensee) await penser(ctx, scene.pensee, cadence);

    // Un catalogue vide, c'est le dernier tour imposé par le plafond : on
    // n'a plus le droit d'appeler quoi que ce soit, seulement de parler.
    const appels = (scene.appels || []).filter((a) => outils.has(a.nom));
    if (appels.length) return { texte: '', appels };

    await ecrire(ctx, scene.conclusion, cadence);
    return { texte: '' };
  };
}

function choisir(demande) {
  const texte = demande.toLowerCase();
  if (texte.includes('synchronis')) {
    return {
      pensee: "La synchronisation pousse sur le central : elle est visible par "
        + "toute l'équipe et aucun Ctrl+Z ne la défait. Je demande l'accord.",
      appels: [{
        id: 'a1',
        nom: 'revit_synchroniser',
        arguments: { commentaire: 'mise à jour des niveaux', liberer_tout: true },
      }],
      conclusion: 'Projet synchronisé. Les emprunts ont été libérés.',
    };
  }
  if (texte.includes('erreur') || texte.includes('casse')) {
    return {
      appels: [{
        id: 'a1',
        nom: 'revit_nomenclatures',
        arguments: { nom: 'Surfaces' },
      }],
      conclusion: "La nomenclature « Surfaces » n'existe pas dans ce projet. "
        + 'Voulez-vous que je liste celles qui existent ?',
    };
  }
  if (texte.includes('vue') || texte.includes('feuille')) {
    return {
      pensee: "Il me faut l'état du document avant de lister quoi que ce soit — "
        + 'inutile d\'interroger un projet fermé.',
      appels: [
        { id: 'a1', nom: 'revit_etat', arguments: {} },
        { id: 'a2', nom: 'revit_vues', arguments: { type: 'FloorPlan', limite: 50 } },
      ],
      conclusion: VUES,
    };
  }
  return {
    pensee: "La demande ne porte sur aucun élément du modèle. Je réponds de "
      + 'mémoire, sans ouvrir le document.',
    conclusion: `${BIENVENUE}\n\nVotre question était : « ${demande.trim()} »`,
  };
}

// Les messages depuis la dernière demande de l'architecte, celle-ci comprise.
// `[]` s'il n'y en a aucune.
function depuisLaDemande(messages) {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i].role === 'utilisateur') return messages.slice(i);
  }
  return [];
}

async function penser(ctx, texte, cadence) {
  await pousser(ctx.surRaisonnement, texte, cadence, ctx.signal);
}

async function ecrire(ctx, texte, cadence) {
  await pousser(ctx.surTexte, texte, cadence, ctx.signal);
}

// Mot à mot. L'espace se recolle au mot suivant : un delta vide est ignoré
// par le flux, et on perdrait les espaces à l'émettre seul.
async function pousser(rappel, texte, cadence, signal) {
  if (!rappel || !texte) return;
  let premier = true;
  for (const mot of String(texte).split(' ')) {
    if (signal?.aborted) return;
    rappel(premier ? mot : ` ${mot}`);
    premier = false;
    if (cadence) await dormir(cadence);
  }
}

// Les outils que ce faux modèle sait appeler. Ils ne touchent pas Revit : ils
// rendent une réponse plausible, de la forme que `lib/rvt` rend vraiment.
export function outilsFactices() {
  return new Map([
    ['revit_etat', {
      nom: 'revit_etat',
      description: 'document ouvert, état du lien',
      irreversible: false,
      executer: async () => '{"document":"MAISON-PDA.rvt","revit_disponible":true}',
    }],
    ['revit_vues', {
      nom: 'revit_vues',
      description: 'vues du projet, filtrables par type',
      irreversible: false,
      executer: async () => '{"vues":47,"exportables":31}',
    }],
    ['revit_nomenclatures', {
      nom: 'revit_nomenclatures',
      description: 'nomenclatures du projet',
      irreversible: false,
      executer: async () => {
        throw new Error('nomenclature introuvable : « Surfaces »');
      },
    }],
    ['revit_synchroniser', {
      nom: 'revit_synchroniser',
      description: 'DANGER — pousse sur le central, visible par toute l\'équipe',
      irreversible: true,
      executer: async () => '{"synchronise":true,"emprunts":0}',
    }],
  ]);
}
