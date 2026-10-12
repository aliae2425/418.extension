// node --test "lib/web/**/tests/*.test.js"
//
// `app.js` est du câblage : il touche le DOM à l'import, donc aucun test ne
// peut le charger sans navigateur. Il n'était donc éprouvé par RIEN — et
// `node --check` ne voit qu'une syntaxe, pas un nom qui n'existe pas.
//
// C'est ainsi qu'ont été livrés trois appels à un `retenirVoie()` jamais
// écrit : la page levait `ReferenceError` à la première connexion, et la
// seule trace était `data/418.log`.
//
// Ce contrôle est grossier et assumé : il lit le fichier comme du texte et
// vérifie que tout ce qui est APPELÉ est déclaré quelque part. Il ne
// remplace pas un vrai analyseur — il attrape la faute qui nous a coûté une
// soirée, et c'est tout ce qu'on lui demande.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ICI = dirname(fileURLToPath(import.meta.url));
const SOURCE = join(ICI, '..', 'app.js');

// Commentaires et chaînes dehors : on n'y cherche pas d'appels, et une
// apostrophe française y ferait dérailler le reste.
function nu(code) {
  return code
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/^\s*\/\/[^\n]*/gm, ' ');
}

// Ce que le langage écrit comme un appel sans en être un.
const MOTS = new Set(['if', 'for', 'while', 'switch', 'catch', 'return',
  'typeof', 'function', 'await', 'new', 'of', 'in', 'do', 'else', 'try',
  'case', 'delete', 'void', 'throw', 'yield', 'instanceof', 'async']);

// Ce que le NAVIGATEUR fournit et que Node n'a pas. La liste est courte
// exprès : y ajouter un nom doit rester un geste conscient, sinon elle
// finirait par tout absoudre.
const NAVIGATEUR = new Set(['getComputedStyle', 'requestAnimationFrame',
  'cancelAnimationFrame', 'alert', 'confirm', 'prompt', 'matchMedia']);

function declarations(code) {
  const vus = new Set();
  const prendre = (motif, groupe = 1) => {
    for (const m of code.matchAll(motif)) vus.add(m[groupe]);
  };
  prendre(/\bfunction\s+([A-Za-z_$][\w$]*)/g);
  prendre(/\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)/g);
  prendre(/\bclass\s+([A-Za-z_$][\w$]*)/g);
  prendre(/\bimport\s+([A-Za-z_$][\w$]*)\s+from/g);
  // Les imports nommés, alias compris.
  for (const bloc of code.matchAll(/import\s*\{([^}]*)\}/g)) {
    for (const brut of bloc[1].split(',')) {
      const nom = brut.trim().split(/\s+as\s+/).pop();
      if (nom) vus.add(nom);
    }
  }
  // Les paramètres : `(a, b) =>` et `function f(a, b)`. Grossier, mais un
  // paramètre déclaré de trop ne fait que taire une alerte, jamais en créer.
  for (const m of code.matchAll(/\(([^()]*)\)\s*(?:=>|\{)/g)) {
    for (const brut of m[1].split(',')) {
      const nom = brut.trim().replace(/^\.\.\./, '').split(/[=:\s]/)[0];
      if (/^[A-Za-z_$][\w$]*$/.test(nom)) vus.add(nom);
    }
  }
  return vus;
}

test('tout ce qu’app.js APPELLE existe quelque part', () => {
  const code = nu(readFileSync(SOURCE, 'utf-8'));
  const connus = declarations(code);
  const manquants = new Set();
  // Le `(?<![.\w$])` écarte les appels de méthode : `x.foo()` n'est pas une
  // fonction libre, et son existence ne se juge pas ici.
  for (const m of code.matchAll(/(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(/g)) {
    const nom = m[1];
    if (MOTS.has(nom) || connus.has(nom) || NAVIGATEUR.has(nom)) continue;
    if (nom in globalThis) continue;
    manquants.add(nom);
  }
  assert.deepEqual([...manquants], [],
    'appelés mais déclarés nulle part — la page lèverait ReferenceError');
});

test('tout id reclame par app.js existe dans index.html', () => {
  // `$('cle-non')` sur un id absent rend `null`, et la faute ne se voit qu'au
  // clic — dans un volet ancré, sans console ouverte, elle ne se voit pas du
  // tout.
  const html = readFileSync(join(ICI, '..', 'index.html'), 'utf-8');
  const poses = new Set([...html.matchAll(/id="([^"]+)"/g)].map((m) => m[1]));
  const code = nu(readFileSync(SOURCE, 'utf-8'));
  const voulus = [...code.matchAll(/\$\('([^']+)'\)/g)].map((m) => m[1]);
  assert.deepEqual(voulus.filter((id) => !poses.has(id)), []);
});

test('le controle attrape bien un nom absent', () => {
  // Sans ce test, le précédent pourrait passer en ne cherchant rien.
  const faux = nu('function a() { retenirVoie(); }');
  const connus = declarations(faux);
  assert.equal(connus.has('retenirVoie'), false);
  assert.equal(connus.has('a'), true);
});
