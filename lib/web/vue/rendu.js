// Le dessin, et rien d'autre : ce module ne sait pas qu'un modèle existe.
//
// Il reçoit des parts et des évènements, il produit du DOM. C'est la règle de
// dépendance d'opencode — *Client may depend on Protocol, never Core* — et
// ici elle se vérifie à l'import : `rendu.js` ne connaît que `protocole.js`.

import { rendre } from './markdown.js';
import * as p from '../harnais/protocole.js';
import { UNE_FOIS, TOUJOURS } from '../harnais/permissions.js';

const LIBELLES = {
  [p.EN_COURS]: 'en cours…',
  [p.ATTENTE_ACCORD]: 'votre accord ?',
  [p.FAIT]: 'fait',
  [p.REFUSE]: 'refusé',
  [p.ECHEC]: 'échec',
};

export class Rendu {
  // `surAccord(reponse)` est appelé quand l'architecte tranche. Le moteur
  // n'attend qu'UN accord à la fois — la boucle `await` chaque outil l'un
  // après l'autre — donc un seul rappel en vol suffit, et ce n'est pas une
  // coïncidence heureuse mais une propriété de la boucle.
  constructor(fil, { surAccord } = {}) {
    this._fil = fil;
    this._surAccord = surAccord;
    this._parts = new Map();
    this._textes = new Map();
    this._tour = null;
  }

  tour() {
    this._tour = document.createElement('div');
    this._tour.className = 'tour';
    this._fil.appendChild(this._tour);
    return this._tour;
  }

  moi(texte) {
    this.tour();
    const bulle = document.createElement('div');
    bulle.className = 'bulle moi';
    bulle.textContent = texte;          // jamais de markdown sur sa propre saisie
    this._tour.appendChild(bulle);
    this.tour();                        // le tour de la réponse
    this.bas();
  }

  // --- évènements du moteur ----------------------------------------------

  sur(evenement, charge) {
    if (evenement === p.NEUVE) return this._neuve(charge);
    if (evenement === p.DELTA) return this._delta(charge);
    if (evenement === p.MAJ) return this._maj(charge);
    if (evenement === p.FINI) return this._fini();
    return undefined;
  }

  _neuve(part) {
    const hote = this._tour || this.tour();
    const el = this._fabriquer(part);
    this._parts.set(part.id, el);
    hote.appendChild(el);
    this.bas();
    return el;
  }

  _delta({ id, morceau }) {
    const el = this._parts.get(id);
    if (!el) return;
    const cumul = (this._textes.get(id) || '') + morceau;
    this._textes.set(id, cumul);
    const cible = el.classList.contains('raisonnement')
      ? el.querySelector('.corps') : el;
    // Re-rendre tout le cumul à chaque delta plutôt qu'ajouter du texte : un
    // `**gras` à moitié arrivé n'est pas du HTML valide tant qu'il n'est pas
    // fermé. À l'échelle d'une bulle, le coût ne se voit pas.
    cible.innerHTML = rendre(cumul);
    this.bas();
  }

  _maj(part) {
    const el = this._parts.get(part.id);
    if (el) this._etat(el, part);
    this.bas();
  }

  _fini() {
    this._fil.querySelectorAll('.bulle.ecrit')
      .forEach((b) => b.classList.remove('ecrit'));
  }

  // --- fabrication --------------------------------------------------------

  _fabriquer(part) {
    if (part.genre === p.TEXTE) {
      const el = document.createElement('div');
      el.className = 'bulle lui ecrit';
      return el;
    }
    if (part.genre === p.RAISONNEMENT) {
      const el = document.createElement('details');
      el.className = 'raisonnement';
      const titre = document.createElement('summary');
      titre.textContent = 'raisonnement';
      const corps = document.createElement('div');
      corps.className = 'corps';
      el.append(titre, corps);
      return el;
    }
    if (part.genre === p.OUTIL) return this._outil(part);
    if (part.genre === p.ETAPE) {
      const el = document.createElement('div');
      el.className = 'etape';
      el.textContent = part.texte || '';
      return el;
    }
    const el = document.createElement('div');
    el.className = 'erreur';
    el.textContent = part.texte || 'erreur';
    return el;
  }

  _outil(part) {
    const el = document.createElement('div');
    el.className = 'outil';
    el.innerHTML = '<div class="tete">'
      + '<span class="nom"></span><span class="args"></span>'
      + '<span class="etat"></span></div>';
    el.querySelector('.nom').textContent = part.nom || '';
    el.querySelector('.args').textContent = part.arguments
      ? JSON.stringify(part.arguments) : '';
    this._etat(el, part);
    return el;
  }

  _etat(el, part) {
    el.dataset.etat = part.etat || '';
    const etat = el.querySelector('.etat');
    if (etat) etat.textContent = LIBELLES[part.etat] || part.etat || '';

    // La sortie n'apparaît qu'une fois : un `pre` recréé à chaque mise à jour
    // ferait sauter la sélection en cours.
    let sortie = el.querySelector('pre');
    if (part.sortie) {
      if (!sortie) { sortie = document.createElement('pre'); el.appendChild(sortie); }
      sortie.textContent = part.sortie;
    } else if (sortie) {
      sortie.remove();
    }

    el.querySelector('.accord')?.remove();
    if (part.etat === p.ATTENTE_ACCORD) el.appendChild(this._accord(part));
  }

  // La demande vit DANS le fil, jamais dans une modale : une modale cacherait
  // précisément ce sur quoi on se prononce.
  _accord(part) {
    const boite = document.createElement('div');
    boite.className = 'accord';
    boite.innerHTML = '<span class="avertit">irréversible — aucun Ctrl+Z ne '
      + 'le défait</span>'
      + '<button class="refuser">Refuser</button>'
      + '<button class="accorder">Accorder</button>'
      + '<button class="toujours">Toujours</button>';

    const repondre = (reponse) => {
      boite.remove();
      this._surAccord?.(reponse);
    };
    // « refus » n'est aucune des trois réponses connues, et c'est voulu :
    // tout ce qui n'est pas un accord explicite refuse SANS rien retenir.
    boite.querySelector('.refuser').onclick = () => repondre('refus');
    boite.querySelector('.accorder').onclick = () => repondre(UNE_FOIS);
    boite.querySelector('.toujours').onclick = () => repondre(TOUJOURS);
    // Refuser en tête du DOM, donc premier au Tab, et il prend le focus : le
    // geste sûr doit être le plus facile.
    boite.querySelector('.refuser').focus();
    return boite;
  }

  bas() {
    this._fil.scrollTop = this._fil.scrollHeight;
  }
}
