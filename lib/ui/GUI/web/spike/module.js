// Existe uniquement pour être importé : si cet import aboutit, les modules ES
// fonctionnent, donc le mapping virtuel sert une vraie origine `https://` et
// pas un `file://` sandboxé.
export function marque() {
  return 'import résolu depuis ' + location.origin;
}
