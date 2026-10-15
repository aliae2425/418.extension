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
  // Ce que l'asset d'apparence donne à voir, et sur quelle forme.
  rendu: {},
  forme: 'sphere',
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

// --- les cinq sections -------------------------------------------------------

// Celles de l'éditeur de matériaux de Revit, dans le même ordre : c'est le
// seul repère que l'utilisateur a déjà. Même rail que la fenêtre principale,
// et rien n'est reconstruit — une classe suffit.
for (const onglet of document.querySelectorAll('.rail .onglet')) {
  onglet.addEventListener('click', () => {
    for (const autre of document.querySelectorAll('.rail .onglet')) {
      autre.classList.toggle('actif', autre === onglet);
    }
    for (const pan of document.querySelectorAll('.pan-editeur')) {
      pan.classList.toggle('actif',
                           pan.dataset.section === onglet.dataset.section);
    }
  });
}

// --- identité et apparence ---------------------------------------------------

function remplirIdentite(depart) {
  const { valeurs } = etat;
  const apparences = depart.apparences || [];
  $('#e-titre').textContent = valeurs.Name || 'Matériau';
  // Les usages viennent du comptage fait à l'ouverture de l'outil : ils
  // disent tout de suite si le matériau est posé quelque part, ou purgeable.
  const usages = depart.usages || {};
  $('#e-usages').textContent = usages.texte || 'Usages non comptés';
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

$('#e-nom').addEventListener('input', (e) => {
  change('Name', e.target.value);
  $('#e-titre').textContent = e.target.value || 'Matériau';
});
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

/** L'aperçu de l'onglet Identité : ce que l'ASSET donne à voir.
 *
 * Il ne montre pas la même chose que la sphère des cartes : la carte rejoue
 * l'ombrage (la couleur que Revit affiche hors vue réaliste), celui-ci
 * rejoue le rendu — couleur diffuse de l'asset, brillant, et la texture
 * quand il y en a une, posée sous les dégradés.
 *
 * Sphère ou cube : la sphère montre mieux le brillant, le cube montre mieux
 * une texture, qui s'y répète sans distorsion sphérique. D'où la bascule.
 */
function remplirRendu(rendu) {
  etat.rendu = rendu;
  peindreApercu();

  const morceaux = [];
  if (rendu.bibliotheque) morceaux.push(rendu.bibliotheque);
  if (rendu.brillant) morceaux.push(`brillant ${rendu.brillant} %`);
  if (rendu.voile) morceaux.push(`transparence ${rendu.voile} %`);
  if (rendu.texture) morceaux.push('texture');
  const detail = rendu.nom
    ? `${rendu.nom} · ${morceaux.join(' · ')}`
    : 'Aucune apparence rattachée : l\'aperçu montre la couleur d\'ombrage.';
  $('#rendu-detail').textContent = detail;
  $('#rendu-proprietes').textContent = detail;
}

/** Les réglages que les deux formes partagent — une seule lecture du rendu. */
function matiereDe(rendu) {
  const brillant = (rendu.brillant || 0) / 100;
  return {
    // Sous une texture, la teinte s'efface : elle la couvrirait.
    teinte: rendu.texture ? 'transparent'
      : (rendu.couleur || etat.valeurs.Color || '#9E9E9E'),
    texture: rendu.texture || '',
    eclat: (0.1 + 0.55 * brillant).toFixed(2),
    tache: `${Math.round(34 - 20 * brillant)}%`,
    opacite: (1 - 0.8 * ((rendu.voile || 0) / 100)).toFixed(2),
  };
}

function peindreApercu() {
  const scene = $('#apercu-materiau');
  const matiere = matiereDe(etat.rendu || {});
  scene.replaceChildren(etat.forme === 'cube' ? cube(matiere)
                                              : sphere(matiere));
}

function sphere(matiere) {
  const boule = creer('span', 'sphere grande');
  if (matiere.texture) boule.append(peau('texture', matiere));
  const galbe = creer('span', 'matiere');
  galbe.style.setProperty('--teinte', matiere.teinte);
  galbe.style.setProperty('--eclat', matiere.eclat);
  galbe.style.setProperty('--tache', matiere.tache);
  galbe.style.opacity = matiere.opacite;
  boule.append(galbe);
  return boule;
}

/** Trois faces en perspective, et c'est tout : les trois autres ne se
 *  voient pas, les dessiner serait du calcul pour personne. L'éclairage est
 *  un filtre par face — dessus plus clair, côté plus sombre. */
function cube(matiere) {
  const scene = creer('span', 'cube');
  const boite = creer('span', 'boite');
  for (const face of ['devant', 'droite', 'dessus']) {
    boite.append(peau(`face ${face}`, matiere));
  }
  scene.append(boite);
  scene.style.opacity = matiere.opacite;
  return scene;
}

function peau(classes, matiere) {
  const surface = creer('span', classes);
  surface.style.background = matiere.teinte;
  if (matiere.texture) {
    // La vignette arrive en data-URI depuis l'hôte : le fichier d'origine
    // vit hors de l'origine servie, et pèse souvent plusieurs mégaoctets.
    surface.style.backgroundImage = `url("${matiere.texture}")`;
  }
  return surface;
}

for (const bouton of document.querySelectorAll('#forme-apercu .segment')) {
  bouton.addEventListener('click', () => {
    for (const autre of document.querySelectorAll('#forme-apercu .segment')) {
      autre.classList.toggle('actif', autre === bouton);
    }
    etat.forme = bouton.dataset.forme;
    peindreApercu();
  });
}

/** Les deux motifs du matériau, en grand, dans l'onglet Identité.
 *
 * Ce sont les tuiles déjà rendues pour la carte : elles ne coûtent rien de
 * plus, et l'éditeur montre ainsi exactement ce que la grille montrait. */
function remplirMotifs(depart) {
  for (const [face, cadre, etiquette] of [
    ['coupe', '#motif-coupe', '#nom-coupe'],
    ['surface', '#motif-surface', '#nom-surface']]) {
    const motif = depart[face] || {};
    $(cadre).innerHTML = motif.svg || '';
    $(cadre).title = motif.nom || '';
    $(etiquette).textContent = motif.nom || 'Aucun';
  }
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
  remplirIdentite(depart);
  remplirParametres(depart.identite || []);
  remplirMotifs(depart);
  remplirAssets(depart.assets || []);
  construireFaces(depart.faces || {});
  if (depart.modifiable === false) {
    $('#enregistrer').disabled = true;
    statut('Maquette non modifiable : l\'enregistrement resterait sans effet.');
  }
  $('#e-nom').focus();

  // La sphère APRÈS le premier affichage, et dans son propre aller-retour :
  // lire un asset et décoder sa texture peut prendre plusieurs secondes sur
  // une bibliothèque posée sur un serveur. Tant qu'elle n'est pas là, le
  // reste de l'éditeur est déjà utilisable — et s'il ne vient jamais, le
  // reste de l'éditeur l'est toujours.
  try {
    remplirRendu(await demander('rendu',
                                { asset: etat.valeurs.AppearanceAssetId }));
  } catch (erreur) {
    remplirRendu({});
  }
}

demarrer();
