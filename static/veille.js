/* Bascule mode clair / sombre. Par défaut, le site suit le réglage de l'appareil ;
   le choix fait avec le bouton est mémorisé sur cet appareil (clé nogues-theme), puis appliqué dès l'en-tête de page. */
(() => {
  'use strict';
  const bouton = document.querySelector('[data-bascule-theme]');
  if (!bouton) return;
  const racine = document.documentElement;
  const systeme = window.matchMedia('(prefers-color-scheme: dark)');
  const COULEURS = { light: '#EEF1F3', dark: '#12161C' };
  const effectif = () => racine.dataset.theme || (systeme.matches ? 'dark' : 'light');

  const afficher = () => {
    const sombre = effectif() === 'dark';
    const action = sombre ? 'Passer en mode clair' : 'Passer en mode sombre';
    bouton.classList.toggle('sombre', sombre);
    bouton.setAttribute('aria-label', action);
    bouton.title = action;
    // Barre du navigateur mobile : même couleur que le papier du mode choisi
    if (racine.dataset.theme) {
      document.querySelectorAll('meta[name="theme-color"]').forEach((m) => { m.content = COULEURS[racine.dataset.theme]; });
    }
  };

  bouton.addEventListener('click', () => {
    const suivant = effectif() === 'dark' ? 'light' : 'dark';
    racine.dataset.theme = suivant;
    try { localStorage.setItem('nogues-theme', suivant); } catch (e) { /* stockage indisponible : le choix vaut pour cette page */ }
    afficher();
  });
  systeme.addEventListener('change', afficher);
  bouton.hidden = false;
  afficher();
})();

/* Filtres de l'index des signaux (page Éditions). Sans JavaScript, tous les signaux restent affichés. */
(() => {
  'use strict';
  const zone = document.querySelector('[data-filtres]');
  if (!zone) return;
  const lignes = Array.from(document.querySelectorAll('.ligne'));
  const resultat = document.querySelector('[data-resultat]');
  const choix = { rubrique: '', maturite: '' };

  const appliquer = () => {
    let visibles = 0;
    lignes.forEach((ligne) => {
      const ok = Object.entries(choix).every(([cle, val]) => !val || ligne.dataset[cle] === val);
      ligne.hidden = !ok;
      if (ok) visibles += 1;
    });
    if (resultat) {
      resultat.textContent = visibles === 0
        ? 'Aucun signal ne correspond à ces filtres.'
        : `${visibles} ${visibles > 1 ? "signaux" : "signal"} sur ${lignes.length}`;
    }
  };

  zone.querySelectorAll('[data-groupe]').forEach((groupe) => {
    groupe.addEventListener('click', (evt) => {
      const bouton = evt.target.closest('button');
      if (!bouton) return;
      choix[groupe.dataset.groupe] = bouton.dataset.valeur;
      groupe.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b === bouton)));
      appliquer();
    });
  });

  zone.hidden = false;
  appliquer();
})();
