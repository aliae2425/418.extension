// Le catalogue de `lib/rvt` transformé en outils que la boucle sait appeler.
//
// Ce module ne sait pas COMMENT on atteint Revit — il reçoit un `executer`
// et s'en sert. C'est ce qui le rend testable sans WebView2, sans Revit et
// sans serveur : le pont postMessage vit dans `vue/`, où sont les choses
// propres à l'hôte.

// `catalogue` : ce que sert `GET /418/outils/` — des objets
// `{nom, description, parametres, ecrit, irreversible}`.
// `executer(nom, arguments, ctx)` → texte de sortie, ou lève.
export function outilsRevit(catalogue, executer) {
  const carte = new Map();
  for (const outil of catalogue || []) {
    if (!outil?.nom) continue;
    carte.set(outil.nom, {
      nom: outil.nom,
      description: outil.description || '',
      parametres: outil.parametres || { type: 'object', properties: {} },
      // `irreversible` pilote l'accord. Le lire du catalogue plutôt que
      // d'en tenir une liste en face : les deux ont divergé deux fois dans
      // l'ancien harnais, et une liste périmée ouvre en grand.
      irreversible: Boolean(outil.irreversible),
      executer: async (args, ctx) => verdict(await executer(outil.nom, args, ctx)),
    });
  }
  return carte;
}

// Le pont rend `{"erreur": …}` au lieu de lever : c'est le contrat de
// `harnais/outils.py`, qui préfère rendre l'échec au modèle plutôt que de
// faire tomber le tour. Mais une part affichée « fait » pour un outil qui a
// échoué est un mensonge. On relève l'erreur ici — la boucle la remettra au
// modèle de toute façon, en marquant la part en échec.
function verdict(sortie) {
  if (typeof sortie !== 'string') return sortie;
  let lu;
  try {
    lu = JSON.parse(sortie);
  } catch {
    return sortie;                         // pas du JSON : c'est une sortie
  }
  const souci = lu?.erreur || lu?.error;
  if (souci) throw new Error(typeof souci === 'string' ? souci : sortie);
  return sortie;
}
