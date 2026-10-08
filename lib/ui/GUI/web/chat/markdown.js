// Rendu Markdown minimal, sans dépendance.
//
// `marked` + `highlight.js` pèsent 300-400 ko de JS tiers à vendoriser dans un
// dépôt qui n'en contient aucun. Pour ce que les bulles ont réellement besoin
// de rendre — gras, italique, code, listes, titres, tableaux — ça tient ici.
// Le jour où il faut de la coloration syntaxique, c'est le moment de discuter
// d'une dépendance, pas avant.
//
// `lib/core/markdown_simple.py` fait déjà ce travail côté Python, testé par 33
// tests. Le doubler ici est un choix du prototype : on veut voir le rendu
// arriver EN FLUX, donc après chaque delta, et un aller-retour Python par
// jeton coûterait plus que ce parseur.

const ECHAPPE = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' };

// Tout passe par ici d'abord : le texte vient d'un modèle, il n'a aucune
// autorité pour poser du HTML dans la page.
function brut(texte) {
  return String(texte).replace(/[&<>"]/g, (c) => ECHAPPE[c]);
}

function enligne(texte) {
  return brut(texte)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
}

function cellules(ligne) {
  return ligne.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
}

const SEPARATEUR = /^\s*\|?[\s:-]*-[\s:|-]*\|?\s*$/;

export function rendre(texte) {
  const lignes = String(texte).split('\n');
  const sortie = [];
  let liste = null;

  const fermer = () => { if (liste) { sortie.push(`</${liste}>`); liste = null; } };
  const ouvrir = (balise) => {
    if (liste !== balise) { fermer(); sortie.push(`<${balise}>`); liste = balise; }
  };

  for (let i = 0; i < lignes.length; i += 1) {
    const ligne = lignes[i];

    // Tableau : une ligne à barres SUIVIE d'une ligne de tirets. Sans cette
    // seconde condition, un texte qui contient une barre deviendrait un
    // tableau — et ça arrive dès qu'un modèle cite un chemin ou une regex.
    if (ligne.includes('|') && SEPARATEUR.test(lignes[i + 1] || '')) {
      fermer();
      const entetes = cellules(ligne);
      sortie.push('<table><thead><tr>');
      entetes.forEach((c) => sortie.push(`<th>${enligne(c)}</th>`));
      sortie.push('</tr></thead><tbody>');
      i += 1;
      while (i + 1 < lignes.length && lignes[i + 1].includes('|')) {
        i += 1;
        sortie.push('<tr>');
        cellules(lignes[i]).forEach((c) => sortie.push(`<td>${enligne(c)}</td>`));
        sortie.push('</tr>');
      }
      sortie.push('</tbody></table>');
      continue;
    }

    const titre = ligne.match(/^(#{1,4})\s+(.*)$/);
    if (titre) {
      fermer();
      const niveau = Math.min(titre[1].length + 2, 6);
      sortie.push(`<h${niveau}>${enligne(titre[2])}</h${niveau}>`);
      continue;
    }

    const puce = ligne.match(/^\s*[-*]\s+(.*)$/);
    if (puce) { ouvrir('ul'); sortie.push(`<li>${enligne(puce[1])}</li>`); continue; }

    const numero = ligne.match(/^\s*\d+[.)]\s+(.*)$/);
    if (numero) { ouvrir('ol'); sortie.push(`<li>${enligne(numero[1])}</li>`); continue; }

    if (!ligne.trim()) { fermer(); continue; }

    fermer();
    sortie.push(`<p>${enligne(ligne)}</p>`);
  }
  fermer();
  return sortie.join('');
}
