// node --test lib/web/harnais/tests/

import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as perm from '../permissions.js';

const CATALOGUE = [
  { nom: 'revit_etat', irreversible: false },
  { nom: 'revit_vues', irreversible: false },
  { nom: 'revit_synchroniser', irreversible: true },
  { nom: 'revit_executer_code', irreversible: true },
];

test('le glob couvre * et ?', () => {
  assert.equal(perm.correspond('revit_etat', 'revit_*'), true);
  assert.equal(perm.correspond('revit_etat', '*'), true);
  assert.equal(perm.correspond('revit_etat', 'revit_eta?'), true);
  assert.equal(perm.correspond('revit_etat', 'revit_vues'), false);
});

test('le glob ancre aux deux bouts', () => {
  // Sans les ancres, « revit_etat » correspondrait à « eta » — et une règle
  // de refus se contournerait en préfixant le nom de l'outil.
  assert.equal(perm.correspond('revit_etat', 'eta'), false);
  assert.equal(perm.correspond('revit_etat', 'revit'), false);
});

test('le glob échappe les métacaractères de regex', () => {
  // Un nom contenant un point ne doit pas se comporter comme un joker.
  assert.equal(perm.correspond('revit_x', 'revit.x'), false);
  assert.equal(perm.correspond('revit.x', 'revit.x'), true);
});

test('la DERNIÈRE règle qui correspond gagne', () => {
  // La précédence d'opencode : on pose un défaut large en tête, et chaque
  // exception s'ajoute à la fin sans réordonner ce qui précède.
  const r = new perm.Regles([
    { motif: '*', effet: perm.AUTORISER },
    { motif: 'revit_*', effet: perm.DEMANDER },
    { motif: 'revit_etat', effet: perm.AUTORISER },
  ]);
  assert.equal(r.effet('revit_etat'), perm.AUTORISER);
  assert.equal(r.effet('revit_vues'), perm.DEMANDER);
  assert.equal(r.effet('autre_chose'), perm.AUTORISER);
});

test('aucune règle qui correspond → le défaut, et il demande', () => {
  // Un outil inconnu ne part PAS tout seul : on demande.
  const r = new perm.Regles();
  assert.equal(r.effet('revit_inconnu'), perm.DEMANDER);
  assert.equal(r.effet('revit_inconnu', perm.REFUSER), perm.REFUSER);
});

test('un effet inconnu est refusé à l’ajout', () => {
  const r = new perm.Regles();
  assert.throws(() => r.ajouter('*', 'peut-etre'), /effet inconnu/);
});

test('le catalogue fait demander les irréversibles, et eux seuls', () => {
  const r = perm.reglesDepuisCatalogue(CATALOGUE);
  assert.equal(r.effet('revit_etat'), perm.AUTORISER);
  assert.equal(r.effet('revit_vues'), perm.AUTORISER);
  assert.equal(r.effet('revit_synchroniser'), perm.DEMANDER);
  assert.equal(r.effet('revit_executer_code'), perm.DEMANDER);
});

test('« une fois » autorise sans rien retenir', () => {
  // Ce qui distingue « vas-y » de « vas-y et ne me redemande plus ».
  const r = perm.reglesDepuisCatalogue(CATALOGUE);
  assert.equal(perm.appliquerReponse(r, 'revit_synchroniser', perm.UNE_FOIS), true);
  assert.equal(r.effet('revit_synchroniser'), perm.DEMANDER);
});

test('« toujours » autorise et retient', () => {
  const r = perm.reglesDepuisCatalogue(CATALOGUE);
  assert.equal(perm.appliquerReponse(r, 'revit_synchroniser', perm.TOUJOURS), true);
  assert.equal(r.effet('revit_synchroniser'), perm.AUTORISER);
});

test('« jamais » refuse et retient', () => {
  const r = perm.reglesDepuisCatalogue(CATALOGUE);
  assert.equal(perm.appliquerReponse(r, 'revit_executer_code', perm.JAMAIS), false);
  assert.equal(r.effet('revit_executer_code'), perm.REFUSER);
});

test('une réponse inconnue vaut refus', () => {
  // Le silence et le charabia ne valent pas accord. Jamais.
  const r = perm.reglesDepuisCatalogue(CATALOGUE);
  assert.equal(perm.appliquerReponse(r, 'revit_synchroniser', undefined), false);
  assert.equal(perm.appliquerReponse(r, 'revit_synchroniser', 'oui'), false);
  assert.equal(r.effet('revit_synchroniser'), perm.DEMANDER);
});

test('« jamais » puis « toujours » : le dernier gagne', () => {
  // La conséquence directe de findLast, et elle est voulue : un refus
  // n'est pas définitif, l'architecte peut revenir dessus.
  const r = perm.reglesDepuisCatalogue(CATALOGUE);
  perm.appliquerReponse(r, 'revit_synchroniser', perm.JAMAIS);
  perm.appliquerReponse(r, 'revit_synchroniser', perm.TOUJOURS);
  assert.equal(r.effet('revit_synchroniser'), perm.AUTORISER);
});
