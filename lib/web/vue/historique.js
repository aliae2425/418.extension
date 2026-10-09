// Ce qui a déjà été envoyé, rappelable aux flèches.
//
// Un anneau, pas une pile : on monte dans le passé, on redescend vers le
// présent, et le présent est le brouillon qu'on était en train d'écrire. Le
// perdre parce qu'on a appuyé sur ↑ par curiosité est la faute classique.

const PLAFOND = 50;

export class Historique {
  constructor(plafond = PLAFOND) {
    this._lignes = [];
    this._plafond = plafond;
    // -1 = on est dans le présent. 0 = la dernière envoyée, 1 l'avant-dernière.
    this._rang = -1;
    this._brouillon = '';
  }

  ajouter(texte) {
    const propre = (texte || '').trim();
    this.reinitialiser();
    if (!propre) return this;
    // Répéter la même chose deux fois d'affilée remplit l'anneau de doublons
    // qu'il faut ensuite franchir un par un.
    if (this._lignes[0] === propre) return this;
    this._lignes.unshift(propre);
    if (this._lignes.length > this._plafond) this._lignes.length = this._plafond;
    return this;
  }

  // Remonte d'un cran. `null` quand il n'y a plus rien au-dessus — on reste
  // alors sur la plus ancienne plutôt que de vider le champ.
  precedent(brouillon = '') {
    if (!this._lignes.length) return null;
    if (this._rang === -1) this._brouillon = brouillon;
    if (this._rang >= this._lignes.length - 1) return null;
    this._rang += 1;
    return this._lignes[this._rang];
  }

  // Redescend d'un cran. Au bout, rend le brouillon laissé en partant.
  suivant() {
    if (this._rang < 0) return null;
    this._rang -= 1;
    if (this._rang === -1) return this._brouillon;
    return this._lignes[this._rang];
  }

  // De retour dans le présent : le prochain ↑ repartira du dernier envoyé.
  reinitialiser() {
    this._rang = -1;
    this._brouillon = '';
    return this;
  }

  get parcourt() {
    return this._rang >= 0;
  }

  get lignes() {
    return [...this._lignes];
  }
}
