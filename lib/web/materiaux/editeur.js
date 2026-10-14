// L'éditeur d'UN matériau, et le sélecteur de motif qu'il ouvre.
//
// Il ne connaît que des valeurs simples : des chaînes, des entiers, des
// couleurs « #RRGGBB » et des identifiants de catalogue. La conversion vers
// l'API Revit (triplets de couleur, `ElementId`) est en Python, dans
// `services/presentation.py`.
//
// Ce qui est envoyé à l'enregistrement : TOUTES les valeurs courantes. C'est
// l'hôte qui RELIT le matériau et n'écrit que ce qui diffère — ce qui a été
// refusé reste ainsi en attente d'une correction, et ce qui est passé n'est
// pas réécrit. L'ancien ViewModel tenait ce ré-ancrage à la main.

import { $, creer, differer, filtrer, vignette } from './dom.js';

const FACES = [['Cut', 'Coupe'], ['Surface', 'Surface']];
// Premier plan d'abord : c'est l'ordre de lecture d'un matériau, et celui
// qu'affichait l'éditeur WPF.
const COUCHES = ['Foreground', 'Background'];

const attribut = (face, couche, suffixe) =>
  `${face}${couche}Pattern${suffixe}`;

let session = null;        // l'édition en cours, ou null

export async function ouvrirEditeur({ id, demander, motifs, apparences,
                                      surEnregistre }) {
  const depart = await demander('editeur', { id });
  session = {
    id,
    demander,
    motifs,
    surEnregistre,
    valeurs: { ...depart.valeurs },
    emplacements: depart.emplacements,
  };

  remplirIdentite(apparences);
  construireFaces(depart.faces);
  statut('');
  $('#modale-editeur').hidden = false;
  $('#e-nom').focus();
}

function fermer() {
  session = null;
  $('#modale-editeur').hidden = true;
}

const statut = (texte) => { $('#statut-editeur').textContent = texte || ''; };

/** Un champ a bougé : le message de refus qui traînait n'a plus cours. */
function change(nom, valeur) {
  session.valeurs[nom] = valeur;
  statut('');
}

// --- identité et apparence ---------------------------------------------------

function remplirIdentite(apparences) {
  const { valeurs } = session;
  $('#e-nom').value = valeurs.Name || '';
  $('#e-classe').value = valeurs.MaterialClass || '';
  couleur($('#e-couleur'), $('#e-couleur-pastille'), valeurs.Color,
          (hex) => change('Color', hex));

  const menu = $('#e-apparence');
  menu.replaceChildren(...apparences.map((asset) => {
    const option = creer('option', '', asset.nom);
    option.value = String(asset.id);
    return option;
  }));
  menu.value = String(valeurs.AppearanceAssetId);

  for (const [champ, nom] of [['#e-transparence', 'Transparency'],
                              ['#e-brillance', 'Shininess'],
                              ['#e-lissage', 'Smoothness']]) {
    const curseur = $(champ);
    curseur.value = String(valeurs[nom] ?? 0);
    curseur.nextElementSibling.value = curseur.value;
  }
}

/** Relie une pastille native et son champ hexadécimal.
 *
 * `<input type="color">` ouvre le sélecteur de Windows — c'est ce que faisait
 * l'ancienne fenêtre, en trente lignes de moins. Le champ texte reste pour
 * coller une valeur de charte.
 */
function couleur(champ, pastilleCouleur, valeur, surChangement) {
  champ.value = valeur;
  pastilleCouleur.value = valeur;
  champ.oninput = () => {
    // Une saisie est incomplète à chaque frappe intermédiaire : on ne pousse
    // que ce qui est une couleur complète, le reste attend la lettre
    // suivante au lieu de faire clignoter l'aperçu en noir.
    const hex = champ.value.trim();
    if (!/^#[0-9a-f]{6}$/i.test(hex)) return;
    pastilleCouleur.value = hex;
    surChangement(hex.toUpperCase());
  };
  pastilleCouleur.oninput = () => {
    champ.value = pastilleCouleur.value.toUpperCase();
    surChangement(champ.value);
  };
}

$('#e-nom').addEventListener('input', (e) => change('Name', e.target.value));
$('#e-classe').addEventListener('input',
                                (e) => change('MaterialClass', e.target.value));
for (const [champ, nom] of [['#e-transparence', 'Transparency'],
                            ['#e-brillance', 'Shininess'],
                            ['#e-lissage', 'Smoothness']]) {
  $(champ).addEventListener('input', (e) => {
    e.target.nextElementSibling.value = e.target.value;
    change(nom, Number(e.target.value));
  });
}

// --- les deux faces ----------------------------------------------------------

function construireFaces(tuilesParFace) {
  $('#faces').replaceChildren(...FACES.map(([face, libelle]) => {
    const section = creer('section', 'carte-section');
    section.dataset.face = face;
    section.append(creer('h3', '', libelle));

    const rangee = creer('div', 'emplacements');
    for (const couche of COUCHES) {
      rangee.append(construireEmplacement(face, couche));
    }
    section.append(rangee);

    const tuiles = creer('div', 'tuiles');
    section.append(tuiles);
    peindreTuiles(tuiles, tuilesParFace[face]);
    return section;
  }));
}

function construireEmplacement(face, couche) {
  const emplacement = session.emplacements[`${face}.${couche}`];
  const bloc = creer('div', 'emplacement');
  bloc.append(creer('div', '', emplacement.libelle));

  const bouton = creer('button', 'bouton-motif');
  bouton.title = 'Choisir un motif de remplissage';
  bouton.addEventListener('click',
                          () => ouvrirSelecteur(face, couche, bouton));
  bloc.append(bouton);
  peindreBoutonMotif(bouton, session.valeurs[attribut(face, couche, 'Id')]);

  const ligne = creer('span', 'couleur');
  const pastilleCouleur = creer('input');
  pastilleCouleur.type = 'color';
  pastilleCouleur.title = 'Choisir une couleur';
  const hex = creer('input', 'hex');
  hex.type = 'text';
  hex.spellcheck = false;
  ligne.append(pastilleCouleur, hex);
  bloc.append(ligne);
  couleur(hex, pastilleCouleur,
          session.valeurs[attribut(face, couche, 'Color')], (valeur) => {
            change(attribut(face, couche, 'Color'), valeur);
            rafraichirFace(face);
          });
  return bloc;
}

function peindreBoutonMotif(bouton, identifiant) {
  const motif = session.motifs.find((m) => m.id === identifiant)
    || session.motifs[0];
  bouton.replaceChildren(
    vignette(motif.svg, 'motif', motif.nom),
    creer('span', 'nom', motif.nom),
    creer('span', `genre${motif.modele ? ' modele' : ''}`, motif.type));
  bouton.title = motif.nom;
}

function peindreTuiles(conteneur, tuiles) {
  conteneur.replaceChildren(...(tuiles || []).map((tuile) => {
    const figure = creer('figure', 'tuile');
    figure.append(vignette(tuile.svg, '', tuile.libelle),
                  creer('figcaption', '', tuile.libelle));
    return figure;
  }));
}

/** Redemande les quatre tuiles d'une face après un changement.
 *
 * Différé : faire glisser un curseur de couleur enverrait sinon une demande
 * par pixel parcouru.
 */
const rafraichirFace = differer(async (face) => {
  if (!session) return;
  const lire = (couche) => ({
    motif: session.valeurs[attribut(face, couche, 'Id')],
    couleur: session.valeurs[attribut(face, couche, 'Color')],
  });
  const sortie = await session.demander('apercu_face', {
    face, fond: lire('Background'), premier: lire('Foreground'),
  });
  const section = document.querySelector(`#faces [data-face="${face}"]`);
  if (section) peindreTuiles(section.querySelector('.tuiles'), sortie.tuiles);
});

// --- le sélecteur de motif ---------------------------------------------------

let choix = null;          // { face, couche, bouton, motif }

function ouvrirSelecteur(face, couche, bouton) {
  const emplacement = session.emplacements[`${face}.${couche}`];
  choix = {
    face, couche, bouton,
    motif: session.valeurs[attribut(face, couche, 'Id')],
  };
  $('#titre-motif').textContent = emplacement.titre;
  $('#contrainte-motif').textContent = emplacement.contrainte;
  $('#contrainte-motif').hidden = !emplacement.contrainte;
  $('#recherche-motif').value = '';
  rendreMotifs();
  $('#modale-motif').hidden = false;
  $('#recherche-motif').focus();
}

/** Les motifs que CET emplacement a le droit d'offrir.
 *
 * Filtrer en amont plutôt que laisser choisir puis récolter un « refusé par
 * Revit » à l'enregistrement, où plus rien ne dit pourquoi. Le motif DÉJÀ en
 * place reste proposé même s'il enfreint la règle (matériau hérité d'un vieux
 * gabarit, fichier lié) : sinon la modale s'ouvre sur du vide et le premier
 * changement de couleur effacerait silencieusement le motif.
 */
function proposables() {
  const emplacement = session.emplacements[`${choix.face}.${choix.couche}`];
  if (emplacement.accepte_modele) return session.motifs;
  const offerts = session.motifs.filter((motif) => !motif.modele);
  const courant = session.motifs.find((motif) => motif.id === choix.motif);
  if (courant && !offerts.includes(courant)) offerts.unshift(courant);
  return offerts;
}

function rendreMotifs() {
  // Le filtre porte sur le nom ET sur le type : taper « modèle » ne laisse
  // que les motifs de modèle, sans case à cocher de plus.
  const visibles = filtrer(proposables(), $('#recherche-motif').value,
                           [(m) => m.nom, (m) => m.type]);
  $('#motifs').replaceChildren(...visibles.map((motif) => {
    const bouton = creer('button', `motif${motif.id === choix.motif ? ' choisi' : ''}`);
    bouton.append(vignette(motif.svg, 'motif', motif.nom),
                  creer('span', 'nom', motif.nom),
                  creer('span', `genre${motif.modele ? ' modele' : ''}`,
                        motif.type));
    bouton.title = motif.nom;
    bouton.addEventListener('click', () => {
      choix.motif = motif.id;
      rendreMotifs();
    });
    return bouton;
  }));
}

$('#recherche-motif').addEventListener('input', rendreMotifs);
$('#choisir-motif').addEventListener('click', () => {
  const { face, couche, bouton, motif } = choix;
  change(attribut(face, couche, 'Id'), motif);
  peindreBoutonMotif(bouton, motif);
  rafraichirFace(face);
  $('#modale-motif').hidden = true;
});

// --- enregistrement et fermeture ---------------------------------------------

$('#enregistrer').addEventListener('click', async () => {
  const sortie = await session.demander('enregistrer', {
    id: session.id, valeurs: session.valeurs,
  });
  session.surEnregistre(sortie.carte);
  if (!sortie.ok) {
    // Ne pas fermer : l'utilisateur doit voir CE qui a été refusé et pouvoir
    // le corriger. Les valeurs relues ré-ancrent l'éditeur sur la maquette.
    session.valeurs = { ...sortie.valeurs };
    $('#e-nom').value = session.valeurs.Name || '';
    return statut(sortie.statut);
  }
  statut(sortie.statut);
  fermer();
});

for (const bouton of document.querySelectorAll('[data-ferme]')) {
  bouton.addEventListener('click', () => {
    if (bouton.dataset.ferme === 'motif') $('#modale-motif').hidden = true;
    else fermer();
  });
}

document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  // La modale du dessus d'abord : Échap ferme le sélecteur, pas l'éditeur
  // qui l'a ouvert.
  if (!$('#modale-motif').hidden) $('#modale-motif').hidden = true;
  else if (!$('#modale-editeur').hidden) fermer();
});
