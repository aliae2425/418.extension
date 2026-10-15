// Le choix d'un motif de remplissage : la page de sa fenêtre.
//
// Elle ne décide de rien — ce qu'elle a le droit d'offrir est calculé par
// l'hôte (`services/presentation.proposables`), qui seul connaît la règle :
// un seul des quatre emplacements accepte un motif de MODÈLE. Filtrer en
// amont plutôt que laisser choisir puis récolter un « refusé par Revit » à
// l'enregistrement, où plus rien ne dit pourquoi.

import { $, creer, filtrer, vignette } from './dom.js';
import { fermer, pret } from './hote.js';

const etat = { motifs: [], choix: null };

function rendre() {
  // Le filtre porte sur le nom ET sur le type : taper « modèle » ne laisse
  // que les motifs de modèle, sans case à cocher de plus.
  const visibles = filtrer(etat.motifs, $('#recherche-motif').value,
                           [(m) => m.nom, (m) => m.type]);
  $('#motifs').replaceChildren(...visibles.map((motif) => {
    // `fiche-motif`, et surtout PAS `motif` : cette dernière est la classe
    // de TAILLE d'une vignette, et la fiche en contient une. Les deux règles
    // se superposaient, et le fond de la fiche repeignait le papier de la
    // vignette — invisible en thème clair, où les deux sont blancs.
    const bouton = creer(
      'button', `fiche-motif${motif.id === etat.choix ? ' choisi' : ''}`);
    bouton.append(vignette(motif.svg, 'motif', motif.nom),
                  creer('span', 'nom', motif.nom),
                  creer('span', `genre${motif.modele ? ' modele' : ''}`,
                        motif.type));
    bouton.title = motif.nom;
    bouton.addEventListener('click', () => {
      etat.choix = motif.id;
      rendre();
    });
    // Le double-clic choisit et ferme : c'est le geste attendu dans une
    // grille, et il évite l'aller-retour vers le bouton du pied.
    bouton.addEventListener('dblclick', () => fermer(motif.id));
    return bouton;
  }));
  $('#choisir-motif').disabled = etat.choix == null;
}

$('#recherche-motif').addEventListener('input', rendre);
$('#choisir-motif').addEventListener('click', () => fermer(etat.choix));
$('#annuler').addEventListener('click', () => fermer(null));
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') fermer(null);
  if (e.key === 'Enter' && etat.choix != null) fermer(etat.choix);
});

async function demarrer() {
  const depart = await pret();
  etat.motifs = depart.motifs || [];
  etat.choix = depart.courant;
  $('#titre-motif').textContent = depart.titre || 'Choisir un motif';
  $('#contrainte-motif').textContent = depart.contrainte || '';
  $('#contrainte-motif').hidden = !depart.contrainte;
  rendre();
  $('#recherche-motif').focus();
}

demarrer();
