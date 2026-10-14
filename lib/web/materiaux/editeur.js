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

// --- identité et apparence ---------------------------------------------------

function remplirIdentite(apparences) {
  const { valeurs } = etat;
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
$('#e-apparence').addEventListener('change',
                                   (e) => change('AppearanceAssetId',
                                                 Number(e.target.value)));
for (const [champ, nom] of CURSEURS) {
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
    id: etat.id, valeurs: etat.valeurs,
  });
  etat.carte = sortie.carte;
  if (!sortie.ok) {
    // On ne ferme PAS : l'utilisateur doit voir ce qui a été refusé et
    // pouvoir le corriger. Les valeurs relues ré-ancrent l'éditeur sur ce que
    // la maquette porte réellement.
    etat.valeurs = { ...sortie.valeurs };
    $('#e-nom').value = etat.valeurs.Name || '';
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
  construireFaces(depart.faces || {});
  if (depart.modifiable === false) {
    $('#enregistrer').disabled = true;
    statut('Maquette non modifiable : l\'enregistrement resterait sans effet.');
  }
  $('#e-nom').focus();
}

demarrer();
