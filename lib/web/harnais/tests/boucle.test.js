// node --test "lib/web/**/tests/*.test.js"
//
// Tout ce qui peut mal tourner dans un agent se reproduit ici en
// millisecondes : plafond de tours, irréversible qui passe, outil qui casse,
// interruption. Aucun Revit, aucun réseau, aucun secret.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as p from '../protocole.js';
import * as perm from '../permissions.js';
import { conduire, TOURS_MAX, REFUS, SANS_INTERFACE } from '../boucle.js';

function banc({ tours = [], outils = [], regles = null } = {}) {
  const recus = [];
  const flux = new p.Flux((e, c) => recus.push([e, c]));
  const vus = [];
  let rang = 0;

  // Chaque entrée de `tours` est ce que le modèle répond à ce tour-là.
  const modele = async (messages, catalogue, ctx) => {
    vus.push({ catalogue, messages: messages.slice() });
    const reponse = tours[Math.min(rang, tours.length - 1)] || { texte: '' };
    rang += 1;
    for (const morceau of reponse.flux || []) ctx.surTexte(morceau);
    return reponse;
  };

  const carte = new Map();
  for (const o of outils) carte.set(o.nom, o);

  return {
    flux,
    recus,
    vus,
    modele,
    outils: carte,
    regles: regles || perm.reglesDepuisCatalogue(outils),
    get tours() { return rang; },
  };
}

const de = (recus, ev) => recus.filter(([e]) => e === ev).map(([, c]) => c);
const majs = (recus, nom) => de(recus, p.MAJ).filter((c) => c.nom === nom);
const texte = (recus) => de(recus, p.DELTA).map((c) => c.morceau).join('');

const LECTURE = {
  nom: 'revit_etat',
  description: 'etat du document',
  irreversible: false,
  executer: async () => '{"document":"MAISON.rvt"}',
};

const DANGER = {
  nom: 'revit_synchroniser',
  description: 'DANGER pousse sur le central',
  irreversible: true,
  executer: async () => '{"synchronise":true}',
};

// --- le cas nominal --------------------------------------------------------

test('sans appel d’outil, un seul tour', async () => {
  const b = banc({ tours: [{ texte: 'bonjour' }] });
  await conduire(b);
  assert.equal(b.tours, 1);
  assert.equal(de(b.recus, p.FINI).length, 1);
});

test('le texte deja pousse en flux ne repart pas en bloc', async () => {
  // Sinon la bulle s'affiche deux fois : une fois mot a mot, une fois entiere.
  const b = banc({ tours: [{ flux: ['bon', 'jour'], texte: 'bonjour' }] });
  await conduire(b);
  assert.equal(texte(b.recus), 'bonjour');
  assert.equal(de(b.recus, p.NEUVE).filter((c) => c.genre === p.TEXTE).length, 1);
});

test('une part de texte ne naît qu’au premier morceau', async () => {
  // Sinon une bulle vide clignote a chaque tour d'outil.
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_etat' }] }, { texte: 'fini' }],
    outils: [LECTURE],
  });
  await conduire(b);
  const bulles = de(b.recus, p.NEUVE).filter((c) => c.genre === p.TEXTE);
  assert.equal(bulles.length, 1);
});

test('un appel d’outil relance un tour', async () => {
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_etat' }] }, { texte: 'voila' }],
    outils: [LECTURE],
  });
  await conduire(b);
  assert.equal(b.tours, 2);
  assert.deepEqual(majs(b.recus, 'revit_etat').map((c) => c.etat), [p.FAIT]);
});

test('le resultat de l’outil repart au modele', async () => {
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_etat' }] }, { texte: 'ok' }],
    outils: [LECTURE],
  });
  await conduire(b);
  const second = b.vus[1].messages;
  assert.equal(second.at(-1).role, 'outil');
  assert.match(second.at(-1).sortie, /MAISON/);
});

test('la reponse du modele entre dans l’historique', async () => {
  // Sans elle, le modele ne voit aucune de ses propres reponses au tour
  // suivant et repete ce qu'il vient de dire. Invisible avec un faux
  // modele, fatal avec un vrai.
  const messages = [{ role: 'utilisateur', texte: 'combien de vues' }];
  const b = banc({ tours: [{ texte: 'quarante-sept' }] });
  await conduire({ ...b, messages });
  assert.deepEqual(messages.at(-1), { role: 'assistant', texte: 'quarante-sept' });
});

test('le modele revoit sa propre reponse au tour suivant', async () => {
  const messages = [{ role: 'utilisateur', texte: 'un' }];
  const b = banc({ tours: [{ texte: 'premiere' }] });
  await conduire({ ...b, messages });
  messages.push({ role: 'utilisateur', texte: 'deux' });
  await conduire({ ...b, messages });
  const roles = b.vus.at(-1).messages.map((m) => m.role);
  assert.deepEqual(roles, ['utilisateur', 'assistant', 'utilisateur']);
});

test('le texte STREAME entre aussi dans l’historique', async () => {
  // Le piege : il n'est pas dans la valeur de retour du modele, seulement
  // dans les deltas. L'oublier laisse un historique troue.
  const messages = [{ role: 'utilisateur', texte: 'bonjour' }];
  const b = banc({ tours: [{ flux: ['bon', 'jour'] }] });
  await conduire({ ...b, messages });
  assert.deepEqual(messages.at(-1), { role: 'assistant', texte: 'bonjour' });
});

test('deux tours de suite gardent des ids de parts distincts', async () => {
  // Le flux vit a l'echelle de la SESSION. Un flux par tour repartirait a
  // `p1`, et le `p1` du tour 2 irait reveiller la bulle du tour 1 — c'est
  // ce qui empilait les reponses les unes sur les autres.
  const b = banc({ tours: [{ flux: ['un'] }] });
  await conduire(b);
  await conduire(b);
  const ids = de(b.recus, p.NEUVE).map((c) => c.id);
  assert.equal(new Set(ids).size, ids.length, ids.join(','));
});

// --- le plafond ------------------------------------------------------------

test('au plafond, un dernier tour SANS outils', async () => {
  // Lever ici laisserait l'architecte devant une bulle vide.
  const b = banc({
    tours: [{ appels: [{ id: 'x', nom: 'revit_etat' }] }],
    outils: [LECTURE],
  });
  await conduire(b);
  assert.equal(b.tours, TOURS_MAX + 1);
  assert.deepEqual(b.vus.at(-1).catalogue, []);
  assert.equal(de(b.recus, p.FINI).length, 1);
});

test('le catalogue est servi tant qu’il reste des tours', async () => {
  const b = banc({ tours: [{ texte: 'x' }], outils: [LECTURE, DANGER] });
  await conduire(b);
  assert.deepEqual(b.vus[0].catalogue.map((o) => o.nom),
    ['revit_etat', 'revit_synchroniser']);
  assert.equal(b.vus[0].catalogue[1].irreversible, true);
});

// --- l'accord --------------------------------------------------------------

test('un irreversible sans interface pour demander est REFUSE', async () => {
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_synchroniser' }] }, { texte: 'ok' }],
    outils: [DANGER],
  });
  await conduire({ ...b, demander: null });
  // Refusé d'emblée : pas d'`attente_accord`, puisque personne n'est là pour
  // répondre. La page ne doit surtout pas dessiner des boutons sans suite.
  assert.deepEqual(majs(b.recus, 'revit_synchroniser').map((c) => c.etat),
    [p.REFUSE]);
  assert.equal(majs(b.recus, 'revit_synchroniser')[0].sortie, SANS_INTERFACE);
  assert.match(b.vus[1].messages.at(-1).sortie, /irréversible refusé/);
});

test('un refus explicite n’execute pas l’outil', async () => {
  let lance = false;
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_synchroniser' }] }, { texte: 'ok' }],
    outils: [{ ...DANGER, executer: async () => { lance = true; return 'x'; } }],
  });
  await conduire({ ...b, demander: async () => perm.JAMAIS });
  assert.equal(lance, false);
  assert.equal(majs(b.recus, 'revit_synchroniser').at(-1).etat, p.REFUSE);
  assert.match(b.vus[1].messages.at(-1).sortie, /refusé par l'architecte/);
});

test('un accord « une fois » execute et ne retient rien', async () => {
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_synchroniser' }] }, { texte: 'ok' }],
    outils: [DANGER],
  });
  await conduire({ ...b, demander: async () => perm.UNE_FOIS });
  assert.equal(majs(b.recus, 'revit_synchroniser').at(-1).etat, p.FAIT);
  assert.equal(b.regles.effet('revit_synchroniser'), perm.DEMANDER);
});

test('un accord « toujours » ne redemande pas', async () => {
  let demandes = 0;
  const b = banc({
    tours: [
      { appels: [{ id: '1', nom: 'revit_synchroniser' }] },
      { appels: [{ id: '2', nom: 'revit_synchroniser' }] },
      { texte: 'ok' },
    ],
    outils: [DANGER],
  });
  await conduire({
    ...b,
    demander: async () => { demandes += 1; return perm.TOUJOURS; },
  });
  assert.equal(demandes, 1);
  assert.equal(b.regles.effet('revit_synchroniser'), perm.AUTORISER);
});

test('une demande d’accord qui casse vaut un refus', async () => {
  // Jamais un laissez-passer.
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_synchroniser' }] }, { texte: 'ok' }],
    outils: [DANGER],
  });
  await conduire({ ...b, demander: async () => { throw new Error('boum'); } });
  assert.equal(majs(b.recus, 'revit_synchroniser').at(-1).etat, p.REFUSE);
});

test('la part NAÎT en attente_accord — c’est ce qui dessine les boutons', async () => {
  // Et elle naît dans cet etat, elle n'y bascule pas : sinon « en cours… »
  // clignote une fraction de seconde sur un outil qui n'a rien lance.
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_synchroniser' }] }, { texte: 'ok' }],
    outils: [DANGER],
  });
  await conduire({ ...b, demander: async () => perm.UNE_FOIS });
  const neuve = de(b.recus, p.NEUVE)
    .filter((c) => c.nom === 'revit_synchroniser');
  assert.equal(neuve[0].etat, p.ATTENTE_ACCORD);
  assert.deepEqual(majs(b.recus, 'revit_synchroniser').map((c) => c.etat),
    [p.EN_COURS, p.FAIT]);
});

test('une lecture naît en en_cours, sans detour', async () => {
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_etat' }] }, { texte: 'ok' }],
    outils: [LECTURE],
  });
  await conduire({ ...b, demander: async () => perm.UNE_FOIS });
  const neuve = de(b.recus, p.NEUVE).filter((c) => c.nom === 'revit_etat');
  assert.equal(neuve[0].etat, p.EN_COURS);
});

test('une lecture ne demande jamais rien', async () => {
  let demande = false;
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_etat' }] }, { texte: 'ok' }],
    outils: [LECTURE],
  });
  await conduire({ ...b, demander: async () => { demande = true; return perm.UNE_FOIS; } });
  assert.equal(demande, false);
});

// --- les pannes ------------------------------------------------------------

test('un outil inconnu ne fait pas echouer le tour', async () => {
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_fantome' }] }, { texte: 'ok' }],
    outils: [LECTURE],
  });
  await conduire(b);
  assert.equal(majs(b.recus, 'revit_fantome').at(-1).etat, p.ECHEC);
  assert.match(b.vus[1].messages.at(-1).sortie, /outil inconnu/);
  assert.equal(de(b.recus, p.FINI).length, 1);
});

test('un outil qui leve rend l’erreur au modele', async () => {
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_etat' }] }, { texte: 'ok' }],
    outils: [{ ...LECTURE, executer: async () => { throw new Error('plus de place'); } }],
  });
  await conduire(b);
  assert.equal(majs(b.recus, 'revit_etat').at(-1).etat, p.ECHEC);
  assert.match(b.vus[1].messages.at(-1).sortie, /plus de place/);
});

test('un modele qui leve devient une part erreur, et le tour finit', async () => {
  const recus = [];
  const flux = new p.Flux((e, c) => recus.push([e, c]));
  await conduire({
    flux,
    outils: new Map(),
    regles: perm.reglesDepuisCatalogue([]),
    modele: async () => { throw new Error('401'); },
  });
  assert.equal(de(recus, p.NEUVE).filter((c) => c.genre === p.ERREUR).length, 1);
  assert.deepEqual(de(recus, p.FINI), [{ raison: 'erreur' }]);
});

test('le tour finit TOUJOURS, exactement une fois', async () => {
  // Sans ça l'interface reste bloquee sur « reflechit… ».
  const cas = [
    { tours: [{ texte: 'a' }] },
    { tours: [{ appels: [{ id: '1', nom: 'revit_fantome' }] }, { texte: 'b' }] },
    { tours: [{ appels: [{ id: '1', nom: 'revit_synchroniser' }] }], outils: [DANGER] },
  ];
  for (const c of cas) {
    const b = banc(c);
    await conduire(b);
    assert.equal(de(b.recus, p.FINI).length, 1, JSON.stringify(c));
  }
});

// --- l'interruption --------------------------------------------------------

test('couper avant le depart arrete tout de suite', async () => {
  const stop = new AbortController();
  stop.abort();
  const b = banc({ tours: [{ texte: 'jamais' }] });
  await conduire({ ...b, signal: stop.signal });
  assert.equal(b.tours, 0);
  assert.deepEqual(de(b.recus, p.FINI), [{ raison: 'interrompu' }]);
});

test('couper pendant un outil arrete la boucle', async () => {
  const stop = new AbortController();
  const b = banc({
    tours: [{ appels: [{ id: '1', nom: 'revit_etat' }] }, { texte: 'jamais' }],
    outils: [{ ...LECTURE, executer: async () => { stop.abort(); return 'x'; } }],
  });
  await conduire({ ...b, signal: stop.signal });
  assert.equal(b.tours, 1);
  assert.deepEqual(de(b.recus, p.FINI), [{ raison: 'interrompu' }]);
});

test('une interruption n’est pas une erreur', async () => {
  // L'afficher en rouge ferait croire a un echec.
  const stop = new AbortController();
  stop.abort();
  const b = banc({ tours: [{ texte: 'x' }] });
  await conduire({ ...b, signal: stop.signal });
  assert.equal(de(b.recus, p.NEUVE).filter((c) => c.genre === p.ERREUR).length, 0);
});
