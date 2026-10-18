# Veille robotique

Veille hebdomadaire publiée chaque lundi sur [nogues.app/robotique](https://nogues.app/robotique/) : ce qui a vraiment avancé en robotique, et ce qui n'est encore qu'une démonstration. Projet personnel de Sébastien Noguès.

## Fonctionnement

Chaque édition est un fichier JSON dans `data/editions/`. Le script `build.py` valide les éditions puis génère un site statique dans `dist/`. Le workflow GitHub Actions lance ce script à chaque push sur `main` et publie `dist/` en SFTP dans `www/robotique` sur l'hébergement OVHcloud.

Une erreur de validation (champ manquant, maturité inconnue, signal hors période, plus de 7 signaux, moins de 3, etc.) arrête le workflow avant tout envoi : rien n'est publié.

```
data/
  editions/AAAA-Sss.json   une édition par semaine ISO couverte (source de vérité)
  index.json               régénéré par build.py --update-data
  historique.json          régénéré : URL des sources des 8 dernières éditions (dédoublonnage)
  glossaire.json           régénéré : mots de la semaine déjà définis
static/                    feuille de style, script, polices (OFL), favicon, image de partage
build.py                   validation et génération, bibliothèque standard Python uniquement
docs/prompt-agent.md       prompt de production de l'agent (Manus.im)
.github/workflows/         validation, génération et publication
```

## Commandes

```bash
python3 build.py               # valide puis génère dist/
python3 build.py --check       # valide seulement
python3 build.py --update-data # régénère index.json, historique.json et glossaire.json
```

Aperçu local : générer, puis servir un dossier qui contient `dist/` sous le nom `robotique` (les liens sont absolus, en `/robotique/`).

```bash
python3 build.py && mkdir -p /tmp/apercu && ln -sfn "$PWD/dist" /tmp/apercu/robotique
python3 -m http.server 8000 --directory /tmp/apercu   # puis http://localhost:8000/robotique/
```

## Pages générées

| Adresse | Contenu |
|---|---|
| `/robotique/` | Édition la plus récente, avec les éditions précédentes |
| `/robotique/AAAA-Sss/` | Une édition, adresse stable |
| `/robotique/editions/` | Toutes les éditions et l'index des signaux, filtrable par rubrique et maturité |
| `/robotique/glossaire/` | Les mots de la semaine, une ancre par mot |
| `/robotique/methode/` | Rubriques, échelle de maturité, sources, production, corrections |
| `/robotique/flux.xml` | Flux RSS des éditions |
| `/robotique/sitemap.xml` | Plan du site |

## Publication : secrets à créer

Les secrets GitHub sont propres à chaque dépôt. Dans **Settings → Secrets and variables → Actions** de ce dépôt, créer les mêmes valeurs que pour `nogues.app` :

| Nom | Type | Valeur |
|---|---|---|
| `OVH_SFTP_HOST` | secret | serveur FTP/SFTP (espace client OVHcloud, onglet « FTP - SSH ») |
| `OVH_SFTP_USER` | secret | login FTP, avec la case SFTP cochée |
| `OVH_SFTP_PASSWORD` | secret | mot de passe FTP |
| `OVH_TARGET_DIR` | variable (facultative) | dossier cible, `www/robotique` par défaut |

Sans ces secrets, le workflow valide et génère le site mais n'envoie rien. Une fois les secrets créés, relancer le workflow depuis l'onglet Actions (« Publier la veille robotique » → Run workflow).

## Corrections

Corriger le signal dans le fichier de l'édition et ajouter une entrée dans `errata`, affichée en bas de l'édition :

```json
{ "date": "2026-10-19", "signal_id": "2026-S42-05", "correction": "Texte de la correction." }
```

Les erreurs peuvent être signalées par [ticket](https://github.com/nogseb/robotique/issues).

## Licences

Polices Bricolage Grotesque et Literata sous licence SIL Open Font License 1.1 (`static/fonts/`).
