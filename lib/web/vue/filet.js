// Le filet. Script CLASSIQUE, chargé AVANT le module, et ces deux points
// sont la raison d'être du fichier :
//
// - un `try` placé DANS le module ne peut pas attraper l'échec de son propre
//   `import`. Sans filet, un module qui ne charge pas laisse un volet muet, et
//   ça se lit « WebView2 ne marche pas » ;
// - les modules sont différés par défaut, donc ce script tourne en premier
//   même s'il est servi par `src` et non en ligne — ce qui permet à la CSP de
//   rester `script-src 'self'`, sans `unsafe-inline` ni hash à maintenir.

window.addEventListener('error', function (e) {
  var pied = document.getElementById('pied');
  var message = String((e && (e.message || e.type)) || 'erreur inconnue');
  if (pied) pied.textContent = 'interface cassée : ' + message;
  try {
    window.chrome.webview.postMessage(JSON.stringify({
      ordre: 'erreur', message: message,
    }));
  } catch (_) {
    // Hors WebView2 (ouverture dans un navigateur) : le pied suffit.
  }
});

// Une promesse rejetée sans `catch` ne déclenche PAS `error`. Le moteur est
// asynchrone de bout en bout : sans ça, la moitié des pannes seraient muettes.
window.addEventListener('unhandledrejection', function (e) {
  var raison = e && e.reason;
  window.dispatchEvent(new ErrorEvent('error', {
    message: 'promesse rejetée : ' + String((raison && raison.message) || raison),
  }));
});
