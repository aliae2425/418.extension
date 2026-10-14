// Le câblage de l'outil Matériaux : l'état de la page, les trois onglets, et
// les ordres envoyés à l'hôte.
//
// Tout ce qui se DÉCIDE est ici (qui est coché, quelle portée, quel onglet) ;
// tout ce qui touche la maquette est en Python. La frontière passe par le
// pont du volet OpenArchi, repris tel quel — une demande, une réponse,
// appariées par référence.
//
// Ce qui ne traverse JAMAIS : le filtre de recherche et la sélection. Les
// faire traverser à chaque frappe ferait voyager la liste entière pour un
// travail de trois lignes.

import {
  $, $$, creer, creerListe, differer, filtrer, pastille, pluriel, vignette,
} from './dom.js';
import { demander, ecouter, poster, pret } from './hote.js';
import { clic } from './selection.js';

// --- l'état -----------------------------------------------------------------

const etat = {
  cartes: [],
  parId: new Map(),
  // Les catalogues de motifs et d'apparences ne sont PAS ici : ils
  // appartiennent à l'éditeur, qui est une autre fenêtre.
  categories: [],
  modifiable: true,
  // Onglet 1 : sélection EXCLUSIVE, il ne mène qu'à l'éditeur.
  choisie: null,
  // Onglets 2 et 3 : deux sélections INDÉPENDANTES sur les mêmes matériaux,
  // comme les trois cases des anciennes cards. Cocher ici ne coche pas là.
  coches: { renommer: new Set(), sources: new Set() },
  ancres: { renommer: null, sources: null },
  cible: null,
  // Portée du remplacement : toutes les catégories cochées au départ, on
  // retire ce qu'on ne veut pas plutôt que de tout désigner.
  portee: new Set(),
  noms: new Map(),        // aperçu de renommage : id -> nom obtenu
  erreurRegex: '',
  rapport: null,
  applique: false,        // un remplacement déjà appliqué ne se rejoue pas
};

// --- onglets ----------------------------------------------------------------

for (const bouton of $$('#rail .onglet')) {
  bouton.addEventListener('click', () => {
    const page = bouton.dataset.page;
    for (const autre of $$('#rail .onglet')) {
      autre.classList.toggle('actif', autre === bouton);
    }
    for (const section of $$('main .page')) {
      section.classList.toggle('actif', section.dataset.page === page);
    }
  });
}

// --- sélection partagée par les onglets 2 et 3 ------------------------------

/** Clic sur une ligne de l'onglet 2 ou 3. La logique est dans
 *  `selection.js` ; ici on ne fait que lui passer ce qui est affiché. */
function cliquer(nom, visibles, id, evenement) {
  etat.ancres[nom] = clic(etat.coches[nom], etat.ancres[nom],
                          visibles.map((carte) => carte.id), id,
                          { shift: evenement.shiftKey });
}

// ╔════════════════════ Onglet 1 — les matériaux ════════════════════╗

const grille = $('#cartes');
const listeCartes = creerListe(grille, gabaritCarte);

function gabaritCarte(carte) {
  const noeud = creer('article', 'carte');
  // La classe et l'apparence ne sont plus écrites sur la carte — elles
  // restent dans l'infobulle, et la recherche continue de porter dessus.
  noeud.title = `${carte.classe} · ${carte.apparence}`;
  noeud.append(apercuCarte(carte));
  noeud.append(creer('div', 'nom', carte.nom));
  noeud.append(creer('div', `usages${carte.usages.total ? '' : ' vide'}`,
                     carte.usages.texte));
  return noeud;
}

/** Les DEUX aperçus sont posés dans la carte ; c'est la grille qui dit lequel
 *  se voit. Basculer ne reconstruit donc rien — ni les sphères, ni les SVG
 *  de hachure, qui sont ce que la page a de plus lourd. */
function apercuCarte(carte) {
  const zone = creer('div', 'apercu');
  zone.append(sphere(carte), motifsCarte(carte));
  return zone;
}

/** La sphère d'aperçu, en CSS pur.
 *
 * Approximation ASSUMÉE : Revit rend une vraie sphère éclairée, on en donne
 * la lecture. Les trois paramètres qui se voient à l'œil y sont — teinte,
 * tache spéculaire, transparence — et ils suffisent à reconnaître un verre
 * d'un plâtre dans une vignette de 88 pixels.
 *
 * ponytail: pas de rendu, pas d'image, pas un octet de plus dans le message.
 * Le jour où l'asset d'apparence doit se voir (bois veiné, carrelage), il
 * faudra une vraie image — et c'est Revit qui devra la fournir.
 */
function sphere(carte) {
  const boule = creer('span', 'sphere');
  boule.title = carte.apparence;
  const matiere = creer('span', 'matiere');
  const brillance = (carte.brillance || 0) / 128;
  const lissage = (carte.lissage || 0) / 100;
  const voile = (carte.transparence || 0) / 100;
  matiere.style.setProperty('--teinte', carte.couleur);
  matiere.style.setProperty('--eclat', (0.12 + 0.6 * brillance).toFixed(2));
  // Plus c'est lisse, plus la tache est SERRÉE : c'est ce qui sépare un
  // verre poli d'un enduit mat, bien plus que l'intensité.
  matiere.style.setProperty('--tache', `${Math.round(34 - 20 * lissage)}%`);
  matiere.style.opacity = (1 - 0.8 * voile).toFixed(2);
  boule.append(matiere);
  return boule;
}

function motifsCarte(carte) {
  const bloc = creer('div', 'motifs-carte');
  for (const face of ['surface', 'coupe']) {
    const figure = creer('figure', 'motif-carte');
    figure.append(vignette(carte[face].svg, 'grande', carte[face].nom),
                  creer('figcaption', '', face));
    bloc.append(figure);
  }
  return bloc;
}

function cartesVisibles() {
  return filtrer(etat.cartes, $('#recherche-cartes').value,
                 [(c) => c.nom, (c) => c.classe]);
}

function rendreCartes() {
  const visibles = cartesVisibles();
  listeCartes.rendre(visibles);
  for (const carte of visibles) {
    listeCartes.noeud(carte.id)
      .classList.toggle('choisie', carte.id === etat.choisie);
  }
  $('#recap-cartes').textContent =
    `${pluriel(etat.cartes.length, 'matériau', 'matériaux')} · `
    + `${visibles.length} affiché${visibles.length > 1 ? 's' : ''}`;
  $('#editer').disabled = etat.choisie == null;
}

for (const bouton of $$('#apercu-cartes .segment')) {
  bouton.addEventListener('click', () => {
    for (const autre of $$('#apercu-cartes .segment')) {
      autre.classList.toggle('actif', autre === bouton);
    }
    grille.classList.toggle('dessin', bouton.dataset.apercu === 'dessin');
  });
}

grille.addEventListener('click', (e) => {
  const noeud = e.target.closest('.carte');
  if (!noeud) return;
  // Sélection exclusive : la carte ne mène qu'à l'éditeur.
  etat.choisie = Number(noeud.dataset.id);
  rendreCartes();
});
grille.addEventListener('dblclick', (e) => {
  const noeud = e.target.closest('.carte');
  if (noeud) editer(Number(noeud.dataset.id));
});
$('#recherche-cartes').addEventListener('input', rendreCartes);
$('#editer').addEventListener('click', () => {
  if (etat.choisie != null) editer(etat.choisie);
});

/** Ouvre l'éditeur dans SA fenêtre.
 *
 * On poste sans attendre : la fenêtre fille bloque l'hôte tant qu'elle est
 * ouverte, et un matériau s'édite en plusieurs minutes. La carte relue
 * revient par l'évènement ci-dessous, à la fermeture.
 */
function editer(id) {
  poster({ ordre: 'ouvrir_editeur', id });
}

ecouter('ouvrir_editeur', ({ resultat }) => {
  // `null` = annulé sans avoir rien écrit : il n'y a rien à rafraîchir.
  if (resultat) majCarte(resultat);
});

/** Une carte relue après édition remplace l'ancienne partout.
 *
 * Les nœuds déjà construits sont jetés dans les TROIS listes : le nom, la
 * couleur et les deux vignettes ont changé, et un nœud gardé en cache
 * afficherait l'ancien matériau indéfiniment.
 */
function majCarte(carte) {
  const index = etat.cartes.findIndex((autre) => autre.id === carte.id);
  if (index < 0) return;
  // Les usages viennent du comptage d'ouverture : l'hôte les reconduit, une
  // édition ne déplace personne.
  etat.cartes[index] = carte;
  etat.parId.set(carte.id, carte);
  for (const liste of [listeCartes, listeRenommer, listeSources, listeCibles]) {
    liste.oublier(carte.id);
  }
  reconstruire();
}

// ╔══════════════════════ Onglet 2 — renommer ═══════════════════════╗

const listeRenommer = creerListe($('#lignes-renommer'), gabaritRenommer);

const PRESETS = {
  tout: () => true,
  aucun: () => false,
  utilises: (carte) => carte.usages.total > 0,
  'non-utilises': (carte) => carte.usages.total === 0,
  // « Sans instance » inclut les non utilisés : c'est la lecture littérale.
  // Le cas intéressant est le matériau déclaré dans les couches d'un type
  // mais jamais posé — il tombe ici aussi.
  'sans-instance': (carte) => carte.usages.instances === 0,
};

function gabaritRenommer(carte) {
  const ligne = creer('div', 'ligne renommer');
  ligne.append(case_a_cocher());
  const titre = creer('span', 'titre', carte.nom);
  titre.title = carte.nom;
  ligne.append(titre);
  ligne.append(creer('span', 'fleche', '→'));
  ligne.append(creer('span', 'nouveau'));
  ligne.append(pastille(carte.couleur, 'rendu', carte.apparence));
  ligne.append(vignette(carte.surface.svg, 'motif', carte.surface.nom));
  ligne.append(vignette(carte.coupe.svg, 'motif', carte.coupe.nom));
  ligne.append(creer('span', `usages${carte.usages.total ? '' : ' vide'}`,
                     carte.usages.texte));
  return ligne;
}

function case_a_cocher(type = 'checkbox') {
  const case_ = creer('input');
  case_.type = type;
  // Affichage seul : TOUS les clics passent par la ligne, sinon la case et
  // la ligne se déclencheraient l'une après l'autre.
  case_.tabIndex = -1;
  return case_;
}

function lignesRenommerVisibles() {
  const visibles = filtrer(etat.cartes, $('#recherche-renommer').value,
                           [(c) => c.nom, (c) => c.classe]);
  if (!$('#masquer-renommer').checked) return visibles;
  // Masque d'affichage, cumulé avec la recherche : il ne touche ni à la
  // sélection ni aux préréglages, qui portent sur la liste complète.
  return visibles.filter((carte) => etat.coches.renommer.has(carte.id));
}

function rendreRenommer() {
  const visibles = lignesRenommerVisibles();
  listeRenommer.rendre(visibles);
  for (const carte of visibles) {
    const ligne = listeRenommer.noeud(carte.id);
    const cochee = etat.coches.renommer.has(carte.id);
    const nouveau = etat.noms.get(carte.id) || '';
    ligne.classList.toggle('cochee', cochee);
    ligne.classList.toggle('change', Boolean(nouveau) && nouveau !== carte.nom);
    ligne.querySelector('input').checked = cochee;
    const cellule = ligne.querySelector('.nouveau');
    cellule.textContent = nouveau;
    cellule.title = nouveau;
    ligne.querySelector('.titre').textContent = carte.nom;
  }
  majPiedRenommer();
}

function majPiedRenommer() {
  const coches = etat.coches.renommer;
  const changes = [...coches].filter((id) => {
    const nom = etat.noms.get(id);
    return nom && nom !== etat.parId.get(id)?.nom;
  }).length;
  $('#recap-renommer').textContent = !coches.size
    ? 'Aucun matériau coché.'
    : (changes
      ? `${pluriel(coches.size, 'matériau', 'matériaux')} coché(s) · `
        + `${pluriel(changes, 'renommage')}.`
      : `${pluriel(coches.size, 'matériau', 'matériaux')} coché(s) · `
        + 'aucun changement de nom.');
  $('#erreur-regex').textContent = etat.erreurRegex;
  $('#erreur-regex').hidden = !etat.erreurRegex;
  $('#renommer').disabled =
    !coches.size || !changes || Boolean(etat.erreurRegex) || !etat.modifiable;
}

const regles = () => ({
  prefixe: $('#prefixe').value,
  rechercher: $('#rechercher').value,
  remplacer: $('#remplacer-par').value,
  suffixe: $('#suffixe').value,
});

/** Demande l'aperçu à l'hôte. Le moteur de nommage (regex, jetons {n},
 *  {date}…) est celui du socle — le porter ici en ferait un second, à tenir
 *  d'accord avec le premier. */
async function rafraichirApercu() {
  const ids = [...etat.coches.renommer];
  if (!ids.length) {
    etat.noms.clear();
    etat.erreurRegex = '';
    return rendreRenommer();
  }
  const sortie = await demander('apercu_renommage', { ids, ...regles() });
  etat.noms = new Map(
    Object.entries(sortie.noms).map(([id, nom]) => [Number(id), nom]));
  etat.erreurRegex = sortie.erreur || '';
  rendreRenommer();
}

const apercuDiffere = differer(rafraichirApercu);

for (const champ of ['#prefixe', '#rechercher', '#remplacer-par', '#suffixe']) {
  $(champ).addEventListener('input', apercuDiffere);
}
$('#recherche-renommer').addEventListener('input', rendreRenommer);
$('#masquer-renommer').addEventListener('change', () => {
  // Les positions affichées changent : l'ancre de plage ne veut plus rien
  // dire, comme après une recherche.
  etat.ancres.renommer = null;
  rendreRenommer();
});
$('#preset-renommer').addEventListener('change', (e) => {
  const predicat = PRESETS[e.target.value];
  // Le menu est une ACTION, pas un état : il retombe sur son libellé neutre,
  // sinon il afficherait un critère qui ne correspond plus dès qu'on coche
  // une ligne à la main.
  e.target.value = '';
  if (!predicat) return;
  etat.coches.renommer = new Set(
    etat.cartes.filter(predicat).map((carte) => carte.id));
  etat.ancres.renommer = null;
  rafraichirApercu();
});

$('#lignes-renommer').addEventListener('click', (e) => {
  const ligne = e.target.closest('.ligne');
  if (!ligne) return;
  cliquer('renommer', lignesRenommerVisibles(), Number(ligne.dataset.id), e);
  // « 3 matériaux renommés » ne vaut plus pour une autre sélection.
  $('#etat-renommer').textContent = '';
  rafraichirApercu();
});

$('#renommer').addEventListener('click', async () => {
  const sortie = await demander('renommer',
                                { ids: [...etat.coches.renommer], ...regles() });
  // Le service assainit et suffixe `*` sur collision : on reprend ce que
  // Revit a réellement écrit, pas ce que l'aperçu annonçait.
  for (const [id, nom] of Object.entries(sortie.noms)) {
    const carte = etat.parId.get(Number(id));
    if (carte) carte.nom = nom;
    // Une carte affiche son nom tel qu'il a été construit : il faut la
    // refaire. Les lignes des onglets 2 et 3, elles, le réécrivent à chaque
    // rendu.
    listeCartes.oublier(Number(id));
  }
  $('#etat-renommer').textContent =
    `${pluriel(sortie.changes, 'matériau', 'matériaux')} renommé(s).`;
  reconstruire();
  rafraichirApercu();
});

// ╔═════════════════════ Onglet 3 — remplacer ═══════════════════════╗

const listeSources = creerListe($('#lignes-sources'), gabaritSource);
const listeCibles = creerListe($('#lignes-cibles'), (carte) =>
  gabaritSource(carte, 'radio'));

function gabaritSource(carte, type = 'checkbox') {
  const ligne = creer('div', 'ligne sources');
  ligne.append(case_a_cocher(type));
  const titre = creer('span', 'titre', carte.nom);
  titre.title = carte.nom;
  ligne.append(titre);
  ligne.append(pastille(carte.couleur, 'rendu', carte.apparence));
  ligne.append(vignette(carte.surface.svg, 'motif', carte.surface.nom));
  ligne.append(vignette(carte.coupe.svg, 'motif', carte.coupe.nom));
  return ligne;
}

const sourcesVisibles = () =>
  filtrer(etat.cartes, $('#recherche-sources').value, [(c) => c.nom]);
const ciblesVisibles = () =>
  filtrer(etat.cartes, $('#recherche-cibles').value, [(c) => c.nom]);

function rendreRemplacer() {
  const sources = sourcesVisibles();
  listeSources.rendre(sources);
  for (const carte of sources) {
    const ligne = listeSources.noeud(carte.id);
    const cochee = etat.coches.sources.has(carte.id);
    ligne.classList.toggle('cochee', cochee);
    ligne.querySelector('input').checked = cochee;
    ligne.querySelector('.titre').textContent = carte.nom;
  }
  const cibles = ciblesVisibles();
  listeCibles.rendre(cibles);
  for (const carte of cibles) {
    const ligne = listeCibles.noeud(carte.id);
    const designee = etat.cible === carte.id;
    ligne.classList.toggle('cible', designee);
    ligne.classList.toggle('cochee', designee);
    ligne.querySelector('input').checked = designee;
    ligne.querySelector('.titre').textContent = carte.nom;
  }
  majPortee();
  majPiedRemplacer();
}

function rendreCategories() {
  const conteneur = $('#categories');
  conteneur.replaceChildren(...etat.categories.map((categorie) => {
    const etiquette = creer('label');
    etiquette.title = categorie.nom;
    const case_ = creer('input');
    case_.type = 'checkbox';
    case_.checked = etat.portee.has(categorie.id);
    case_.dataset.id = String(categorie.id);
    etiquette.append(case_, document.createTextNode(` ${categorie.nom}`));
    return etiquette;
  }));
}

function majPortee() {
  const total = etat.categories.length;
  const cochees = etat.portee.size;
  const resume = $('#resume-portee');
  if (!total || cochees === total) {
    resume.textContent = 'Appliquer à toutes les catégories';
  } else if (!cochees) {
    resume.textContent = 'Aucune catégorie — rien à traiter';
  } else if (cochees === 1) {
    const seule = etat.categories.find((c) => etat.portee.has(c.id));
    resume.textContent = `Appliquer à : ${seule.nom}`;
  } else {
    resume.textContent = `Appliquer à ${cochees} catégories sur ${total}`;
  }
}

function peutAnalyser() {
  // Tout décocher ne veut pas dire « tout le modèle » : ça veut dire qu'il
  // n'y a rien à balayer, donc rien à lancer.
  if (etat.categories.length && !etat.portee.size) return false;
  return Boolean(etat.coches.sources.size) && etat.modifiable;
}

function majPiedRemplacer() {
  const sources = etat.coches.sources.size;
  const cible = etat.cible == null ? null : etat.parId.get(etat.cible);
  const gauche = !sources ? '' : (sources === 1 ? '1 source'
    : `${sources} sources fusionnées`);
  const droite = cible ? cible.nom : 'aucune cible';
  let portee = '';
  if (etat.categories.length && etat.portee.size !== etat.categories.length) {
    portee = !etat.portee.size ? ' · aucune catégorie'
      : (etat.portee.size === 1
        ? ` · ${etat.categories.find((c) => etat.portee.has(c.id)).nom}`
        : ` · ${etat.portee.size} catégories`);
  }
  $('#recap-remplacer').textContent = !sources
    ? 'Aucune source cochée.' : `${gauche} → ${droite}${portee}`;
  $('#analyser').disabled = !peutAnalyser();
  $('#appliquer').disabled =
    !peutAnalyser() || etat.cible == null || etat.applique;
}

function rendreRapport() {
  const rapport = etat.rapport;
  $('#etat-remplacer').textContent = rapport?.etat || '';
  $('#rapport').replaceChildren(...(rapport?.lignes || []).map((ligne) => {
    const pastilleLigne = creer('span', 'pastille', ligne.categorie);
    pastilleLigne.append(creer('em', '', ligne.detail));
    return pastilleLigne;
  }));
  const peints = rapport?.peints || 0;
  $('#peints').hidden = !peints;
  $('#peints').textContent = peints
    ? `${pluriel(peints, 'élément')} avec une face peinte : la peinture n'est `
      + 'pas modifiée, à reprendre à la main.'
    : '';
}

/** Un rapport ne vaut que pour la portée et les sources qui l'ont produit. */
function oublierRapport() {
  etat.rapport = null;
  etat.applique = false;
  rendreRapport();
}

$('#recherche-sources').addEventListener('input', rendreRemplacer);
$('#recherche-cibles').addEventListener('input', rendreRemplacer);
$('#lignes-sources').addEventListener('click', (e) => {
  const ligne = e.target.closest('.ligne');
  if (!ligne) return;
  cliquer('sources', sourcesVisibles(), Number(ligne.dataset.id), e);
  oublierRapport();
  rendreRemplacer();
});
$('#lignes-cibles').addEventListener('click', (e) => {
  const ligne = e.target.closest('.ligne');
  if (!ligne) return;
  etat.cible = Number(ligne.dataset.id);
  oublierRapport();
  rendreRemplacer();
});
$('#tout-sources').addEventListener('click', () => {
  etat.coches.sources = new Set(etat.cartes.map((carte) => carte.id));
  oublierRapport();
  rendreRemplacer();
});
$('#aucun-sources').addEventListener('click', () => {
  etat.coches.sources.clear();
  oublierRapport();
  rendreRemplacer();
});
$('#categories').addEventListener('change', (e) => {
  const id = Number(e.target.dataset.id);
  if (e.target.checked) etat.portee.add(id); else etat.portee.delete(id);
  oublierRapport();
  rendreRemplacer();
});
$('#cocher-portee').addEventListener('click', () => basculerPortee(true));
$('#decocher-portee').addEventListener('click', () => basculerPortee(false));

function basculerPortee(valeur) {
  etat.portee = valeur
    ? new Set(etat.categories.map((categorie) => categorie.id)) : new Set();
  rendreCategories();
  oublierRapport();
  rendreRemplacer();
}

/** Lance un balayage et encaisse l'attente.
 *
 * Le pont rend la main au bout d'une minute. Un balayage complet d'une très
 * grosse maquette peut la dépasser : Python, lui, continue et va au bout —
 * c'est la PAGE qui a cessé d'écouter. On le dit plutôt que de laisser
 * l'onglet figé sur un rapport qui n'arrive jamais.
 *
 * ponytail: le remède propre serait de passer le balayage sur un fil de fond
 * avec un ordre « avancement ». Il coûterait l'ExternalEvent que la fenêtre
 * modale nous épargne — à reprendre si le cas se présente vraiment.
 */
async function balayer(ordre, charge) {
  const bouton = ordre === 'analyser' ? $('#analyser') : $('#appliquer');
  bouton.disabled = true;
  try {
    etat.rapport = await demander(ordre, charge);
    etat.applique = ordre === 'remplacer';
  } catch (erreur) {
    etat.rapport = null;
    rendreRapport();          // avant le message : il réécrit la ligne d'état
    $('#etat-remplacer').textContent =
      `L'hôte n'a pas répondu (${erreur.message}). Le travail peut avoir eu `
      + 'lieu : vérifiez la maquette et data/materiaux.log.';
    return majPiedRemplacer();
  }
  rendreRapport();
  majPiedRemplacer();
}

$('#analyser').addEventListener('click',
                                () => balayer('analyser', demandeRemplacement()));
$('#appliquer').addEventListener('click', () => balayer('remplacer', {
  ...demandeRemplacement(), cible: etat.cible,
}));

const demandeRemplacement = () => ({
  sources: [...etat.coches.sources],
  categories: [...etat.portee],
});

// --- démarrage ---------------------------------------------------------------

function reconstruire() {
  rendreCartes();
  rendreRenommer();
  rendreRemplacer();
}

async function demarrer() {
  const depart = await pret();
  etat.cartes = depart.cartes || [];
  etat.parId = new Map(etat.cartes.map((carte) => [carte.id, carte]));
  etat.categories = depart.categories || [];
  etat.portee = new Set(etat.categories.map((categorie) => categorie.id));
  etat.modifiable = depart.modifiable !== false;

  if (!etat.modifiable) {
    const avertissement = $('#avertissement');
    avertissement.hidden = false;
    avertissement.textContent = 'Maquette non modifiable : les actions de '
      + 'cet outil resteront sans effet.';
  }
  rendreCategories();
  reconstruire();
}

demarrer();
