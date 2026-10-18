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
