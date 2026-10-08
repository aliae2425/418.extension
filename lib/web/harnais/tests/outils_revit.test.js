// node --test "lib/web/**/tests/*.test.js"

import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as p from '../protocole.js';
import * as perm from '../permissions.js';
import { conduire } from '../boucle.js';
import { outilsRevit } from '../outils_revit.js';

const CATALOGUE = [
  {
    nom: 'revit_etat',
    description: 'etat du document',
    parametres: { type: 'object', properties: {} },
    ecrit: false,
    irreversible: false,
  },
  {
    nom: 'revit_synchroniser',
    description: 'DANGER pousse sur le central',
    parametres: { type: 'object', properties: { commentaire: { type: 'string' } } },
    ecrit: true,
    irreversible: true,
  },
];

test('le catalogue devient des outils appelables', () => {
  const carte = outilsRevit(CATALOGUE, async () => '{}');
  assert.deepEqual([...carte.keys()], ['revit_etat', 'revit_synchroniser']);
  assert.equal(carte.get('revit_etat').description, 'etat du document');
  assert.deepEqual(carte.get('revit_synchroniser').parametres.properties,
    { commentaire: { type: 'string' } });
});

test('irreversible vient du CATALOGUE, pas d’une liste en face', () => {
  // Les deux ont diverge deux fois dans l'ancien harnais, et une liste
  // perimee ouvre en grand.
  const carte = outilsRevit(CATALOGUE, async () => '{}');
  assert.equal(carte.get('revit_etat').irreversible, false);
  assert.equal(carte.get('revit_synchroniser').irreversible, true);
});

test('executer recoit le nom, les arguments et le contexte', async () => {
  const vus = [];
  const carte = outilsRevit(CATALOGUE, async (nom, args, ctx) => {
    vus.push([nom, args, ctx?.marque]);
    return '{"ok":1}';
  });
  const sortie = await carte.get('revit_etat').executer({ a: 1 }, { marque: 'ctx' });
  assert.deepEqual(vus, [['revit_etat', { a: 1 }, 'ctx']]);
  assert.equal(sortie, '{"ok":1}');
});

test('une entree sans nom est ignoree', () => {
  const carte = outilsRevit([{ description: 'rien' }, ...CATALOGUE], async () => '');
  assert.equal(carte.size, 2);
});

test('un catalogue absent donne une carte vide, sans lever', () => {
  assert.equal(outilsRevit(null, async () => '').size, 0);
  assert.equal(outilsRevit(undefined, async () => '').size, 0);
});

test('une sortie {"erreur"} est RELEVEE, pas rendue telle quelle', async () => {
  // Le pont rend l'erreur au lieu de lever : c'est le contrat de
  // harnais/outils.py. Mais une part « fait » pour un outil qui a echoue
  // est un mensonge.
  const carte = outilsRevit(CATALOGUE,
    async () => '{"erreur":"aucun document Revit ouvert"}');
  await assert.rejects(() => carte.get('revit_etat').executer({}),
    /aucun document Revit ouvert/);
});

test('une sortie qui n’est pas du JSON passe telle quelle', async () => {
  const carte = outilsRevit(CATALOGUE, async () => 'texte nu');
  assert.equal(await carte.get('revit_etat').executer({}), 'texte nu');
});

test('un JSON legitime qui contient le mot erreur ailleurs passe', async () => {
  const carte = outilsRevit(CATALOGUE, async () => '{"avertissements":["erreur de saisie"]}');
  assert.match(await carte.get('revit_etat').executer({}), /avertissements/);
});

test('bout en bout : un outil Revit en echec marque la part, pas le tour', async () => {
  const recus = [];
  const flux = new p.Flux((e, c) => recus.push([e, c]));
  const outils = outilsRevit(CATALOGUE,
    async () => '{"erreur":"routes pyRevit eteintes"}');
  let tour = 0;
  await conduire({
    flux,
    outils,
    regles: perm.reglesDepuisCatalogue(CATALOGUE),
    messages: [{ role: 'utilisateur', texte: 'etat' }],
    modele: async () => {
      tour += 1;
      return tour === 1
        ? { appels: [{ id: '1', nom: 'revit_etat', arguments: {} }] }
        : { texte: 'les routes sont eteintes' };
    },
  });
  const maj = recus.filter(([e]) => e === p.MAJ).map(([, c]) => c);
  assert.equal(maj.at(-1).etat, p.ECHEC);
  assert.match(maj.at(-1).sortie, /routes pyRevit eteintes/);
  assert.deepEqual(recus.filter(([e]) => e === p.FINI).map(([, c]) => c), [{}]);
});

test('bout en bout : un irreversible Revit passe par l’accord', async () => {
  const recus = [];
  const flux = new p.Flux((e, c) => recus.push([e, c]));
  let lance = false;
  const outils = outilsRevit(CATALOGUE, async () => { lance = true; return '{}'; });
  let tour = 0;
  await conduire({
    flux,
    outils,
    regles: perm.reglesDepuisCatalogue(CATALOGUE),
    messages: [{ role: 'utilisateur', texte: 'synchronise' }],
    demander: async () => perm.JAMAIS,
    modele: async () => {
      tour += 1;
      return tour === 1
        ? { appels: [{ id: '1', nom: 'revit_synchroniser', arguments: {} }] }
        : { texte: 'refuse' };
    },
  });
  assert.equal(lance, false, 'la synchronisation ne doit PAS partir');
  const neuve = recus.filter(([e]) => e === p.NEUVE).map(([, c]) => c)
    .find((c) => c.nom === 'revit_synchroniser');
  assert.equal(neuve.etat, p.ATTENTE_ACCORD);
});
