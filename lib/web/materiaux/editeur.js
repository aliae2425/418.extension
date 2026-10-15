// L'éditeur d'UN matériau : la page de sa fenêtre.
//
// Il ne connaît que des valeurs simples — des chaînes, des entiers, des
// couleurs « #RRGGBB » et des identifiants de catalogue. La conversion vers
// l'API Revit (triplets de couleur, `ElementId`) est en Python, dans
// `services/presentation.py`.
//
// Ce qui est envoyé à l'enregistrement : TOUTES les valeurs courantes. C'est
// l'hôte qui RELIT le matériau et n'écrit que ce qui diffère — ce qui a été
// refusé reste ainsi en attente d'une correction, et ce qui est passé n'est
// pas réécrit. L'ancien ViewModel tenait ce ré-ancrage à la main.

import { $, creer, differer, vignette } from './dom.js';
import { demander, ecouter, fermer, poster, pret } from './hote.js';

const FACES = [['Cut', 'Coupe'], ['Surface', 'Surface']];
// Premier plan d'abord : c'est l'ordre de lecture d'un matériau, et celui
// qu'affichait l'éditeur WPF.
const COUCHES = ['Foreground', 'Background'];

const attribut = (face, couche, suffixe) => `${face}${couche}Pattern${suffixe}`;

const etat = {
  id: null,
  valeurs: {},
  // Paramètres d'identité modifiés : {id de définition: texte}. Séparés des
  // valeurs parce qu'ils s'écrivent autrement côté Revit — par `Set`, et non
  // par attribut.
  identite: {},
  emplacements: {},
  motifs: [],
  // La carte relue au dernier enregistrement. Rendue même si l'utilisateur
  // ferme par Annuler ensuite : un enregistrement partiellement refusé a
  // quand même écrit quelque chose, et la fenêtre principale doit le voir.
  carte: null,
  // L'emplacement qui a demandé un motif, le temps que sa fenêtre réponde.
  choix: null,
};

const statut = (texte) => { $('#statut-editeur').textContent = texte || ''; };

/** Un champ a bougé : le message de refus qui traînait n'a plus cours. */
function change(nom, valeur) {
  etat.valeurs[nom] = valeur;
  statut('');
}

// --- les cinq onglets --------------------------------------------------------

// Ceux de l'éditeur de matériaux de Revit, dans le même ordre : c'est le seul
// repère que l'utilisateur a déjà. Une classe sur le corps suffit à basculer,
// rien n'est reconstruit.
for (const onglet of document.querySelectorAll('.onglet-editeur')) {
  onglet.addEventListener('click', () => {
    for (const autre of document.querySelectorAll('.onglet-editeur')) {
      autre.classList.toggle('actif', autre === onglet);
    }
    for (const pan of document.querySelectorAll('.pan-editeur')) {
      pan.classList.toggle('actif',
                           pan.dataset.section === onglet.dataset.section);
    }
  });
}

// --- identité et apparence ---------------------------------------------------

function remplirIdentite(apparences) {
  const { valeurs } = etat;
  $('#e-nom').value = valeurs.Name || '';
  $('#e-classe').value = valeurs.MaterialClass || '';
  $('#e-categorie').value = valeurs.MaterialCategory || '';
  $('#e-rendu-ombrage').checked = Boolean(valeurs.UseRenderAppearanceForShading);
  couleur($('#e-couleur'), $('#e-couleur-pastille'), valeurs.Color,
          (hex) => change('Color', hex));

  const menu = $('#e-apparence');
  menu.replaceChildren(...apparences.map((asset) => {
    const option = creer('option', '', asset.nom);
    option.value = String(asset.id);
    return option;
  }));
  menu.value = String(valeurs.AppearanceAssetId);

  for (const [champ, nom] of CURSEURS) {
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
function couleur(champ, pastille, valeur, surChangement) {
  champ.value = valeur;
  pastille.value = valeur;
  champ.oninput = () => {
    // Une saisie est incomplète à chaque frappe intermédiaire : on ne pousse
    // que ce qui est une couleur complète, le reste attend la lettre
    // suivante au lieu de faire clignoter l'aperçu en noir.
    const hex = champ.value.trim();
    if (!/^#[0-9a-f]{6}$/i.test(hex)) return;
    pastille.value = hex;
    surChangement(hex.toUpperCase());
  };
  pastille.oninput = () => {
    champ.value = pastille.value.toUpperCase();
    surChangement(champ.value);
  };
}

const CURSEURS = [['#e-transparence', 'Transparency'],
                  ['#e-brillance', 'Shininess'],
                  ['#e-lissage', 'Smoothness']];

$('#e-nom').addEventListener('input', (e) => change('Name', e.target.value));
$('#e-classe').addEventListener('input',
                                (e) => change('MaterialClass', e.target.value));
$('#e-categorie').addEventListener(
  'input', (e) => change('MaterialCategory', e.target.value));
$('#e-rendu-ombrage').addEventListener(
  'change', (e) => change('UseRenderAppearanceForShading', e.target.checked));
$('#e-apparence').addEventListener('change', async (e) => {
  const asset = Number(e.target.value);
  change('AppearanceAssetId', asset);
  // La sphère suit le choix AVANT l'enregistrement : un aperçu qui montre
  // l'ancienne apparence est un aperçu qui ment.
  remplirRendu(await demander('rendu', { asset }));
});
for (const [champ, nom] of CURSEURS) {
  $(champ).addEventListener('input', (e) => {
    e.target.nextElementSibling.value = e.target.value;
    change(nom, Number(e.target.value));
  });
}

// --- les paramètres d'identité, tels que Revit les range --------------------

/** Un champ par paramètre : modifiable s'il est du texte, affiché sinon.
 *
 * Un paramètre en lecture n'est pas une case grisée au hasard : c'est un
 * coût, un nombre, une liste — des valeurs qui portent une unité ou une
 * devise, et qu'on ne pose pas avec un champ texte sans se tromper de
 * monnaie. Ils sont là parce qu'on veut les LIRE sans quitter la fenêtre.
 */
function remplirParametres(parametres) {
  const bloc = $('#identite');
  const note = $('#note-identite');
  if (!parametres.length) {
    note.textContent = 'Ce matériau ne porte aucun paramètre d\'identité.';
    bloc.replaceChildren();
    return;
  }
  const figes = parametres.filter((p) => !p.modifiable).length;
  note.textContent = figes
    ? `${figes} paramètre(s) en lecture seule : ils portent une unité ou une `
      + 'devise, et ne se posent pas dans un champ texte.'
    : '';
  bloc.replaceChildren(...parametres.map((parametre) => {
    const etiquette = creer('label', 'parametre', parametre.nom);
    const champ = creer('input');
    champ.type = 'text';
    champ.value = parametre.valeur;
    champ.autocomplete = 'off';
    if (!parametre.modifiable) {
      champ.readOnly = true;
      champ.title = 'Lecture seule';
    } else {
      champ.addEventListener('input', () => {
        etat.identite[parametre.id] = champ.value;
        statut('');
      });
    }
    etiquette.append(champ);
    return etiquette;
  }));
}

// --- l'apparence, sur une sphère ---------------------------------------------

/** La sphère de l'onglet Apparence : ce que l'ASSET donne à voir.
 *
 * Elle ne montre pas la même chose que celle des cartes : la carte rejoue
 * l'ombrage (la couleur que Revit affiche hors vue réaliste), celle-ci
 * rejoue le rendu — couleur diffuse de l'asset, brillant, et la texture
 * quand il y en a une, posée sous les dégradés.
 */
function remplirRendu(rendu) {
  const boule = $('#rendu-sphere');
  const couches = [];
  if (rendu.texture) {
    const texture = creer('span', 'texture');
    // La vignette arrive en data-URI depuis l'hôte : le fichier d'origine
    // vit hors de l'origine servie, et pèse souvent plusieurs mégaoctets.
    texture.style.backgroundImage = `url("${rendu.texture}")`;
    couches.push(texture);
  }
  const matiere = creer('span', 'matiere');
  // Sous une texture, la teinte s'efface : elle la couvrirait.
  matiere.style.setProperty(
    '--teinte',
    rendu.texture ? 'transparent' : (rendu.couleur || etat.valeurs.Color));
  const brillant = (rendu.brillant || 0) / 100;
  matiere.style.setProperty('--eclat', (0.1 + 0.55 * brillant).toFixed(2));
  matiere.style.setProperty('--tache', `${Math.round(34 - 20 * brillant)}%`);
  matiere.style.opacity = (1 - 0.8 * ((rendu.voile || 0) / 100)).toFixed(2);
  couches.push(matiere);
  boule.replaceChildren(...couches);

  const morceaux = [];
  if (rendu.bibliotheque) morceaux.push(rendu.bibliotheque);
  if (rendu.brillant) morceaux.push(`brillant ${rendu.brillant} %`);
  if (rendu.voile) morceaux.push(`transparence ${rendu.voile} %`);
  if (rendu.texture) morceaux.push('texture');
  $('#rendu-detail').textContent = rendu.nom
    ? morceaux.join(' · ')
    : 'Aucune apparence rattachée : la sphère montre la couleur d\'ombrage.';
}

// --- les jeux de propriétés : ossature ---------------------------------------

/** Physique, thermique, carbone : ce qui est rattaché, et rien de plus.
 *
 * En poser un autre demande un navigateur de la bibliothèque de Revit — un
 * outil à lui seul, pas un menu déroulant. Tant qu'il n'existe pas, la page
 * le dit ici plutôt que d'afficher une liste vide qui ferait croire à une
 * panne.
 */
function remplirAssets(liste) {
  const par = (attribut) => liste.find((a) => a.attribut === attribut);
  peindreAssets($('#physique'),
                [par('StructuralAssetId'), par('EmbodiedCarbonAssetId')]);
  peindreAssets($('#thermique'), [par('ThermalAssetId')]);
}

function peindreAssets(conteneur, jeux) {
  conteneur.replaceChildren(...jeux.filter(Boolean).map((jeu) => {
    const ligne = creer('div', 'asset');
    ligne.append(creer('span', 'libelle-asset', jeu.libelle),
                 creer('span', 'nom-asset', jeu.nom || 'Aucun'));
    const bouton = creer('button', 'secondaire', 'Choisir…');
    bouton.disabled = true;
    bouton.title = 'À brancher : choisir un jeu de propriétés demande le '
      + 'navigateur de la bibliothèque Revit.';
    ligne.append(bouton);
    return ligne;
  }));
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
  const emplacement = etat.emplacements[`${face}.${couche}`];
  const bloc = creer('div', 'emplacement');
  bloc.append(creer('div', '', emplacement.libelle));

  const bouton = creer('button', 'bouton-motif');
  bouton.title = 'Choisir un motif de remplissage';
  bouton.dataset.face = face;
  bouton.dataset.couche = couche;
  bouton.addEventListener('click', () => ouvrirSelecteur(face, couche));
  bloc.append(bouton);
  peindreBoutonMotif(bouton, etat.valeurs[attribut(face, couche, 'Id')]);

  const ligne = creer('span', 'couleur');
  const pastille = creer('input');
  pastille.type = 'color';
  pastille.title = 'Choisir une couleur';
  const hex = creer('input', 'hex');
  hex.type = 'text';
  hex.spellcheck = false;
  ligne.append(pastille, hex);
  bloc.append(ligne);
  couleur(hex, pastille, etat.valeurs[attribut(face, couche, 'Color')],
          (valeur) => {
            change(attribut(face, couche, 'Color'), valeur);
            rafraichirFace(face);
          });
  return bloc;
}

function peindreBoutonMotif(bouton, identifiant) {
  const motif = etat.motifs.find((m) => m.id === identifiant) || etat.motifs[0];
  if (!motif) return;
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
  const lire = (couche) => ({
    motif: etat.valeurs[attribut(face, couche, 'Id')],
    couleur: etat.valeurs[attribut(face, couche, 'Color')],
  });
  const sortie = await demander('apercu_face', {
    face, fond: lire('Background'), premier: lire('Foreground'),
  });
  const section = document.querySelector(`#faces [data-face="${face}"]`);
  if (section) peindreTuiles(section.querySelector('.tuiles'), sortie.tuiles);
});

// --- le sélecteur de motif, dans sa fenêtre ---------------------------------

/** Ouvre la fenêtre de choix. On poste sans attendre : elle reste ouverte
 *  aussi longtemps qu'il faut, le choix revient par l'évènement. */
function ouvrirSelecteur(face, couche) {
  etat.choix = { face, couche };
  poster({ ordre: 'ouvrir_motif', face, couche,
           motif: etat.valeurs[attribut(face, couche, 'Id')] });
}

ecouter('ouvrir_motif', ({ resultat }) => {
  const choix = etat.choix;
  etat.choix = null;
  // `null` = la fenêtre a été fermée sans choisir.
  if (!choix || resultat == null) return;
  const { face, couche } = choix;
  change(attribut(face, couche, 'Id'), resultat);
  const bouton = document.querySelector(
    `#faces .bouton-motif[data-face="${face}"][data-couche="${couche}"]`);
  if (bouton) peindreBoutonMotif(bouton, resultat);
  rafraichirFace(face);
});

// --- enregistrement et fermeture ---------------------------------------------

$('#enregistrer').addEventListener('click', async () => {
  const sortie = await demander('enregistrer', {
    id: etat.id, valeurs: etat.valeurs, identite: etat.identite,
  });
  etat.carte = sortie.carte;
  if (!sortie.ok) {
    // On ne ferme PAS : l'utilisateur doit voir ce qui a été refusé et
    // pouvoir le corriger. Les valeurs relues ré-ancrent l'éditeur sur ce que
    // la maquette porte réellement.
    etat.valeurs = { ...sortie.valeurs };
    etat.identite = {};
    $('#e-nom').value = etat.valeurs.Name || '';
    remplirParametres(sortie.identite || []);
    return statut(sortie.statut);
  }
  fermer(etat.carte);
});

// Annuler rend quand même la dernière carte relue : un enregistrement
// partiellement refusé a écrit quelque chose, la fenêtre principale doit le
// voir. Sans sauvegarde, `carte` vaut null et rien n'est rafraîchi.
$('#annuler').addEventListener('click', () => fermer(etat.carte));
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') fermer(etat.carte);
});

// --- démarrage ---------------------------------------------------------------
// En dernier, et pas en tête de module : tout ce qui suit est appelé par le
// démarrage, et une `const` lue avant sa déclaration lève.

async function demarrer() {
  const depart = await pret();
  etat.id = depart.id;
  etat.valeurs = { ...depart.valeurs };
  etat.emplacements = depart.emplacements || {};
  etat.motifs = depart.motifs || [];
  remplirIdentite(depart.apparences || []);
  remplirParametres(depart.identite || []);
  remplirRendu(depart.rendu || {});
  remplirAssets(depart.assets || []);
  construireFaces(depart.faces || {});
  if (depart.modifiable === false) {
    $('#enregistrer').disabled = true;
    statut('Maquette non modifiable : l\'enregistrement resterait sans effet.');
  }
  $('#e-nom').focus();
}

demarrer();
