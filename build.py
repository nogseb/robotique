#!/usr/bin/env python3
"""Génère le site statique de la veille robotique (nogues.app/robotique) à partir de data/.

Usage :
    python3 build.py               valide les éditions puis génère dist/
    python3 build.py --check       valide seulement (code de sortie 1 en cas d'erreur)
    python3 build.py --update-data régénère data/index.json, data/historique.json et data/glossaire.json

Aucune dépendance hors bibliothèque standard Python 3.9+.
Une erreur de validation arrête la génération : rien n'est publié.
"""

import argparse
import html
import json
import re
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
EDITIONS_DIR = DATA / "editions"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

BASE = "/robotique/"
SITE = "https://nogues.app/robotique/"
REPO = "https://github.com/nogseb/robotique"
AUTHOR = "Sébastien Noguès"
AUTHOR_URL = "https://nogues.app/"
SITE_NAME = "Veille robotique"
TAGLINE = "Ce qui a vraiment avancé en robotique, et ce qui n'est encore qu'une démonstration."

# --- Référentiels -----------------------------------------------------------

RUBRIQUES = {
    "materiel": ("Matériel et systèmes", "Qu'est-ce qui rend les robots physiquement plus capables ?", 2),
    "ia": ("IA et autonomie", "Qu'est-ce qui rend les robots plus autonomes ?", 2),
    "usages": ("Usages et marché", "Où les robots créent-ils réellement de la valeur ?", 3),
}

MATURITES = {
    "recherche": (1, "Recherche", "Résultat de laboratoire ou article scientifique."),
    "demo": (2, "Démo", "Vidéo, salon ou prototype, sans client."),
    "pilote": (3, "Pilote", "Testé chez des clients, à petite échelle."),
    "commercialise": (4, "Commercialisé", "En vente ou sous contrat."),
    "deploye": (5, "Déployé", "En service chez un client nommé, en volume."),
}

TYPES = {
    "produit": "Produit",
    "recherche": "Publication scientifique",
    "open-source": "Open source",
    "deploiement": "Déploiement",
    "financement": "Financement ou rachat",
    "partenariat": "Partenariat",
    "reglementation": "Réglementation",
    "etude": "Étude chiffrée",
}

ZONES = {
    "france": "France",
    "europe": "Europe",
    "etats-unis": "États-Unis",
    "chine": "Chine",
    "asie": "Asie",
    "monde": "Monde",
}

HORIZONS = {"moins-1-an", "1-3-ans", "plus-3-ans"}
FIABILITES = {"primaire", "presse", "declaratif"}

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

LIMITES = {"titre": 80, "fait": 160, "portee": 140, "repere": 26}
MOTS_INTERDITS = ["révolutionnaire", "historique", "inédit", "le robot comprend", "le robot pense"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")

# --- Outils de texte ----------------------------------------------------------

NBSP, NNBSP = " ", " "


def typo(s):
    """Typographie française : espaces insécables avant la ponctuation haute, dans les guillemets et les nombres."""
    s = re.sub(r" ([;!?%»])", NNBSP + r"\1", s)
    s = re.sub(r" :", NBSP + ":", s)
    s = re.sub(r"« ", "«" + NNBSP, s)
    s = re.sub(r"(\d) (\d{3})\b", r"\1" + NNBSP + r"\2", s)
    s = re.sub(r"(\d) (kg|mm|M USD|millions|milliards?|véhicules)", r"\1" + NBSP + r"\2", s)
    s = re.sub(r"(\d|1er) (" + "|".join(MOIS) + r")\b", r"\1" + NBSP + r"\2", s)
    s = re.sub(r"\b(" + "|".join(JOURS) + r") (\d)", r"\1" + NBSP + r"\2", s)
    return s


def t(s):
    return html.escape(typo(str(s)), quote=False)


def a(s):
    return html.escape(str(s), quote=True)


def d(iso):
    return date.fromisoformat(iso)


def jour(n):
    return "1er" if n == 1 else str(n)


def date_longue(iso, avec_jour=False):
    x = d(iso)
    txt = f"{jour(x.day)} {MOIS[x.month - 1]} {x.year}"
    return f"{JOURS[x.weekday()]} {txt}" if avec_jour else txt


def date_courte(iso):
    x = d(iso)
    return f"{jour(x.day)} {MOIS[x.month - 1]}"


def periode(debut, fin):
    x, y = d(debut), d(fin)
    if x.year == y.year and x.month == y.month:
        return f"du {jour(x.day)} au {jour(y.day)} {MOIS[y.month - 1]} {y.year}"
    if x.year == y.year:
        return f"du {jour(x.day)} {MOIS[x.month - 1]} au {jour(y.day)} {MOIS[y.month - 1]} {y.year}"
    return f"du {date_longue(debut)} au {date_longue(fin)}"


def plage(debut, fin):
    if not fin or fin == debut:
        return date_courte(debut)
    x, y = d(debut), d(fin)
    if x.month == y.month:
        return f"{jour(x.day)}–{jour(y.day)} {MOIS[y.month - 1]}"
    return f"{date_courte(debut)} – {date_courte(fin)}"


PLURIELS = {"signal": "signaux"}


def pluriel(n, mot):
    return f"{n} {PLURIELS.get(mot, mot + 's') if n > 1 else mot}"


def url_edition(ed):
    return f"{BASE}{ed['semaine_iso']}/"


# --- Validation ---------------------------------------------------------------

class Rapport:
    def __init__(self):
        self.erreurs, self.alertes = [], []

    def err(self, ou, msg):
        self.erreurs.append(f"{ou} : {msg}")

    def alerte(self, ou, msg):
        self.alertes.append(f"{ou} : {msg}")


def champs(obj, noms, ou, r):
    ok = True
    for n in noms:
        if n not in obj or obj[n] in (None, "", []):
            r.err(ou, f"champ obligatoire manquant « {n} »")
            ok = False
    return ok


def verifier_date(v, ou, r):
    try:
        d(v)
        return True
    except (TypeError, ValueError):
        r.err(ou, f"date invalide « {v} » (format attendu AAAA-MM-JJ)")
        return False


def verifier_texte(v, ou, r, limite=None):
    if limite and len(v) > limite:
        r.alerte(ou, f"{len(v)} caractères (limite {limite})")
    if "M$" in v:
        r.err(ou, "écrire « millions de dollars » ou « M USD », jamais « M$ »")
    if EMOJI.search(v):
        r.err(ou, "émoji interdit")
    bas = v.lower()
    for m in MOTS_INTERDITS:
        if m in bas:
            r.alerte(ou, f"mot à éviter « {m} »")
    if "!" in v:
        r.alerte(ou, "point d'exclamation à éviter")


def verifier_sources(sources, ou, r):
    if not isinstance(sources, list) or not sources:
        r.err(ou, "au moins une source est obligatoire")
        return
    for i, s in enumerate(sources, 1):
        o = f"{ou}, source {i}"
        if champs(s, ["titre", "editeur", "url", "date", "fiabilite"], o, r):
            if not str(s["url"]).startswith("https://"):
                r.err(o, "l'URL doit commencer par https://")
            verifier_date(s["date"], o, r)
            if s["fiabilite"] not in FIABILITES:
                r.err(o, f"fiabilité inconnue « {s['fiabilite']} »")


def valider(ed, chemin, r):
    ou = chemin.name
    if not champs(ed, ["semaine_iso", "periode", "date_publication", "essentiel", "signaux",
                       "chiffre", "cas_usage", "agenda", "mot_de_la_semaine"], ou, r):
        return
    if "numero" not in ed or not isinstance(ed["numero"], int):
        r.err(ou, "« numero » doit être un entier")
    if not re.fullmatch(r"\d{4}-S\d{2}", ed["semaine_iso"]):
        r.err(ou, "« semaine_iso » doit suivre le format AAAA-Sss")
    elif chemin.stem != ed["semaine_iso"]:
        r.err(ou, f"le nom du fichier doit être {ed['semaine_iso']}.json")
    p = ed["periode"]
    if not (champs(p, ["debut", "fin"], f"{ou}, période", r)
            and verifier_date(p["debut"], ou, r) and verifier_date(p["fin"], ou, r)):
        return
    verifier_date(ed["date_publication"], ou, r)

    ess = ed["essentiel"]
    if len(ess) != 3:
        r.err(ou, f"« essentiel » doit contenir 3 phrases ({len(ess)} trouvées)")
    for i, phrase in enumerate(ess, 1):
        verifier_texte(phrase, f"{ou}, essentiel {i}", r)
        if len(phrase.split()) > 25:
            r.alerte(f"{ou}, essentiel {i}", f"{len(phrase.split())} mots (limite 25)")

    sig = ed["signaux"]
    if len(sig) < 3:
        r.err(ou, f"seuil de publication non atteint : {len(sig)} signal(s), 3 minimum")
    if len(sig) > 7:
        r.err(ou, f"{len(sig)} signaux, 7 maximum")
    ids, compte = set(), {k: 0 for k in RUBRIQUES}
    for s in sig:
        o = f"{ou}, signal {s.get('id', '?')}"
        if not champs(s, ["id", "rubrique", "titre", "fait", "portee", "type", "maturite",
                          "zone", "date_evenement", "sources"], o, r):
            continue
        if s["id"] in ids:
            r.err(o, "identifiant en double")
        ids.add(s["id"])
        if not s["id"].startswith(ed["semaine_iso"] + "-"):
            r.err(o, f"l'identifiant doit commencer par {ed['semaine_iso']}-")
        if s["rubrique"] not in RUBRIQUES:
            r.err(o, f"rubrique inconnue « {s['rubrique']} »")
        else:
            compte[s["rubrique"]] += 1
        if s.get("rubrique_secondaire") not in (None, *RUBRIQUES):
            r.err(o, f"rubrique secondaire inconnue « {s['rubrique_secondaire']} »")
        if s["type"] not in TYPES:
            r.err(o, f"type inconnu « {s['type']} »")
        if s["maturite"] not in MATURITES:
            r.err(o, f"maturité inconnue « {s['maturite']} »")
        if s["zone"] not in ZONES:
            r.err(o, f"zone inconnue « {s['zone']} »")
        if s.get("horizon") and s["horizon"] not in HORIZONS:
            r.err(o, f"horizon inconnu « {s['horizon']} »")
        for champ in ("titre", "fait", "portee", "repere"):
            if s.get(champ):
                verifier_texte(s[champ], f"{o}, {champ}", r, LIMITES[champ])
        if verifier_date(s["date_evenement"], o, r) and not s.get("rattrapage"):
            if not (p["debut"] <= s["date_evenement"] <= p["fin"]):
                r.err(o, "date hors de la période couverte (ajouter \"rattrapage\": true si c'est voulu)")
        verifier_sources(s["sources"], o, r)
        fiab = {x.get("fiabilite") for x in s["sources"] if isinstance(x, dict)}
        if s["maturite"] == "deploye" and "primaire" not in fiab:
            r.err(o, "un signal « deploye » exige une source primaire")
        if s["type"] == "financement" and not fiab & {"primaire", "presse"}:
            r.err(o, "un financement exige une source primaire ou de presse spécialisée")
    for k, n in compte.items():
        if n > RUBRIQUES[k][2]:
            r.err(ou, f"rubrique {k} : {n} signaux, {RUBRIQUES[k][2]} maximum")

    c = ed["chiffre"]
    if champs(c, ["valeur", "libelle", "contexte", "sources"], f"{ou}, chiffre", r):
        verifier_texte(c["contexte"], f"{ou}, chiffre", r, 300)
        verifier_sources(c["sources"], f"{ou}, chiffre", r)
    cu = ed["cas_usage"]
    if champs(cu, ["titre", "entreprise", "tache_robotisee", "reste_manuel",
                   "resultats_annonces", "a_retenir", "sources"], f"{ou}, cas d'usage", r):
        verifier_sources(cu["sources"], f"{ou}, cas d'usage", r)
    if len(ed["agenda"]) > 3:
        r.err(ou, "agenda : 3 dates maximum")
    for i, ev in enumerate(ed["agenda"], 1):
        o = f"{ou}, agenda {i}"
        if champs(ev, ["debut", "evenement", "lieu", "pourquoi", "url"], o, r):
            verifier_date(ev["debut"], o, r)
            if ev.get("fin"):
                verifier_date(ev["fin"], o, r)
    m = ed["mot_de_la_semaine"]
    if champs(m, ["terme", "slug", "definition"], f"{ou}, mot de la semaine", r):
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", m["slug"]):
            r.err(f"{ou}, mot de la semaine", "slug invalide (minuscules, chiffres, tirets)")
        if m.get("signal_lie") and m["signal_lie"] not in ids:
            r.err(f"{ou}, mot de la semaine", f"signal lié inconnu « {m['signal_lie']} »")
    for i, e in enumerate(ed.get("errata", []), 1):
        o = f"{ou}, erratum {i}"
        if champs(e, ["date", "correction"], o, r):
            verifier_date(e["date"], o, r)


def charger():
    r = Rapport()
    editions = []
    for chemin in sorted(EDITIONS_DIR.glob("*.json")):
        try:
            ed = json.loads(chemin.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            r.err(chemin.name, f"JSON invalide ({e})")
            continue
        valider(ed, chemin, r)
        editions.append(ed)
    if not editions:
        r.err("data/editions", "aucune édition trouvée")
    slugs = {}
    for ed in editions:
        m = ed.get("mot_de_la_semaine") or {}
        if m.get("slug") in slugs:
            r.err(f"{ed.get('semaine_iso')}.json", f"le mot « {m['slug']} » figure déjà dans l'édition {slugs[m['slug']]}")
        elif m.get("slug"):
            slugs[m["slug"]] = ed.get("semaine_iso")
    editions.sort(key=lambda e: e.get("semaine_iso", ""), reverse=True)
    return editions, r


# --- Gabarits -----------------------------------------------------------------

LOGO = ('<svg class="logo" viewBox="0 0 120 120" aria-hidden="true" focusable="false">'
        '<g fill="none" transform="translate(0 2)"><path class="i" stroke-width="18" d="M38 104V38"/>'
        '<path class="i" stroke-width="18" d="M38 66C38 53 48 46 61 46C74 46 84 54 84 68V104"/>'
        '<path class="ac" stroke-width="8" d="M29 16H93M29 6V26M93 6V26"/></g></svg>')

NAV = [("", "Cette semaine"), ("editions/", "Éditions"), ("glossaire/", "Glossaire"), ("methode/", "Méthode")]


def page(titre, description, chemin, corps, actif=None, jsonld=None, indexable=True):
    canon = SITE + chemin
    courant = ' aria-current="page"'
    nav = "".join(
        f'<a href="{BASE}{c}"{courant if c == actif else ""}>{lib}</a>' for c, lib in NAV)
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    robots = "index, follow" if indexable else "noindex"
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t(titre)}</title>
<meta name="description" content="{a(typo(description))}">
<meta name="author" content="{AUTHOR}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canon}">
<meta name="theme-color" content="#EEF1F3" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#12161C" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="{SITE_NAME}, nogues.app">
<meta property="og:url" content="{canon}">
<meta property="og:title" content="{a(titre)}">
<meta property="og:description" content="{a(description)}">
<meta property="og:image" content="{SITE}assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{BASE}assets/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{BASE}flux.xml">
<link rel="preload" href="{BASE}assets/fonts/bricolage-grotesque-latin-800-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{BASE}assets/fonts/literata-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{BASE}assets/veille.css">
{ld}
</head>
<body>
<a class="evitement" href="#contenu">Aller au contenu</a>
<header class="top wrap">
  <div class="marque">
    <a class="maison" href="https://nogues.app/" aria-label="nogues.app, toutes les expériences">{LOGO}<span class="wm">nogues<span>.app</span></span></a>
    <span class="barre" aria-hidden="true">/</span>
    <a class="titre-site" href="{BASE}">Robotique</a>
  </div>
  <nav aria-label="Navigation de la veille">{nav}</nav>
</header>
<main id="contenu">
{corps}
</main>
<footer class="pied wrap ruled">
  <p>Une veille de {AUTHOR}, publiée chaque lundi sur nogues.app. Les éditions sont préparées par un agent d'intelligence artificielle, publiées automatiquement, puis vérifiées par un humain dans la journée ; chaque correction est signalée.</p>
  <p class="liens"><a href="{BASE}methode/">Comment cette veille est faite</a><a href="{BASE}glossaire/">Glossaire</a><a href="{BASE}flux.xml">Flux RSS</a><a href="{REPO}/issues">Signaler une erreur</a><a href="https://nogues.app/">Autres expériences sur nogues.app</a></p>
</footer>
<script src="{BASE}assets/veille.js" defer></script>
</body>
</html>
"""


def html_sources(sources, prefixe="Source"):
    liens = ", ".join(
        f'<a href="{a(s["url"])}" rel="noopener">{t(s["editeur"])}</a>'
        f'<span class="sr-only"> : {t(s["titre"])}, {t(date_longue(s["date"]))}</span>'
        for s in sources)
    lib = prefixe + ("s" if len(sources) > 1 else "")
    return f'<p class="sources">{lib} : {liens}</p>'


def jauge(niveau, libelle):
    segs = "".join('<i class="on"></i>' if k <= niveau else "<i></i>" for k in range(1, 6))
    return f'<span class="jauge" role="img" aria-label="Maturité : {a(libelle)}, niveau {niveau} sur 5">{segs}</span>'


def carte(s):
    niv, lib, _ = MATURITES[s["maturite"]]
    second = ""
    if s.get("rubrique_secondaire"):
        second = f'<span>Aussi : {t(RUBRIQUES[s["rubrique_secondaire"]][0])}</span>'
    return f"""<article class="signal" id="s-{a(s['id'])}">
  <h3>{t(s['titre'])}</h3>
  <p class="fait">{t(s['fait'])}</p>
  <p class="portee">{t(s['portee'])}</p>
  <div class="pied-carte">
    <p class="maturite m{niv}">{jauge(niv, lib)}<a href="{BASE}methode/#maturite" title="{a(MATURITES[s['maturite']][2])}">{t(lib)}</a></p>
    <p class="meta"><span>{t(TYPES[s['type']])}</span><span>{t(ZONES[s['zone']])}</span><time datetime="{s['date_evenement']}">{t(date_courte(s['date_evenement']))}</time>{second}</p>
    {html_sources(s['sources'])}
  </div>
</article>"""


def libelle_repere(s):
    if s.get("repere"):
        return s["repere"]
    if s.get("acteurs"):
        return s["acteurs"][0]
    return s["titre"]


def echelle(ed):
    par = {k: [] for k in MATURITES}
    for s in ed["signaux"]:
        par[s["maturite"]].append(s)
    items = []
    for i, (k, (niv, lib, defi)) in enumerate(MATURITES.items()):
        sig = par[k]
        if sig:
            contenu = '<ul class="pastilles">' + "".join(
                f'<li><a class="pastille" href="#s-{a(s["id"])}" title="{a(typo(s["titre"]))}">'
                f'{t(libelle_repere(s))}'
                f'<span class="sr-only"> : {t(s["titre"])}</span></a></li>' for s in sig) + "</ul>"
        else:
            contenu = '<p class="vide">Aucun signal cette semaine.</p>'
        items.append(f"""<li class="station m{niv}" style="--i:{i}">
      <span class="point" aria-hidden="true"></span>
      <p class="nom">{t(lib)} <span class="sr-only">({pluriel(len(sig), "signal") if sig else "aucun signal"})</span></p>
      <p class="def">{t(defi)}</p>
      {contenu}
    </li>""")
    return f"""<section class="echelle wrap ruled" aria-labelledby="titre-echelle">
  <div class="tete">
    <h2 id="titre-echelle">Où en est chaque annonce</h2>
    <p>Les signaux de la semaine, placés de l'idée de laboratoire au robot en service chez un client. <a href="{BASE}methode/#maturite">Comment ils sont classés</a></p>
  </div>
  <ol class="cote">
    {"".join(items)}
  </ol>
</section>"""


def rubriques(ed):
    blocs = []
    for k, (nom, question, _) in RUBRIQUES.items():
        sig = [s for s in ed["signaux"] if s["rubrique"] == k]
        if sig:
            cartes = "\n".join(carte(s) for s in sig)
            compte = pluriel(len(sig), "signal")
        else:
            cartes = '<p class="vide">Rien de solide cette semaine dans cette rubrique.</p>'
            compte = "aucun signal"
        blocs.append(f"""<div class="rubrique" id="{k}">
    <h2>{t(nom)}</h2>
    <p class="question">{t(question)} <span class="compte">{compte}</span></p>
    <div class="cartes">
{cartes}
    </div>
  </div>""")
    return f'<section class="rubriques wrap ruled" aria-label="Les signaux de la semaine">\n  {"".join(blocs)}\n</section>'


def reperes(ed):
    c, cu, m = ed["chiffre"], ed["cas_usage"], ed["mot_de_la_semaine"]
    agenda = "".join(
        f'<li><p class="quand"><time datetime="{ev["debut"]}">{t(plage(ev["debut"], ev.get("fin")))}</time></p>'
        f'<div><p class="quoi"><a href="{a(ev["url"])}" rel="noopener">{t(ev["evenement"])}</a>, {t(ev["lieu"])}</p>'
        f'<p class="pourquoi">{t(ev["pourquoi"])}</p></div></li>' for ev in ed["agenda"])
    lignes = [("Entreprise", cu["entreprise"]), ("Ce qui est robotisé", cu["tache_robotisee"]),
              ("Ce qui reste manuel", cu["reste_manuel"]), ("Résultats annoncés", cu["resultats_annonces"]),
              ("À retenir", cu["a_retenir"])]
    dl = "".join(f"<dt>{t(x)}</dt><dd>{t(y)}</dd>" for x, y in lignes)
    lie = ""
    if m.get("signal_lie"):
        lie = f' <a href="#s-{a(m["signal_lie"])}">Voir le signal concerné</a>.'
    return f"""<section class="reperes wrap ruled" aria-label="Repères de la semaine">
  <div class="bloc chiffre">
    <h2>Le chiffre</h2>
    <p class="valeur">{t(c['valeur'])}</p>
    <p class="libelle">{t(c['libelle'])}</p>
    <p>{t(c['contexte'])}</p>
    {html_sources(c['sources'])}
  </div>
  <div class="bloc cas">
    <h2>Cas d'usage</h2>
    <h3>{t(cu['titre'])}</h3>
    <dl>{dl}</dl>
    {html_sources(cu['sources'])}
  </div>
  <div class="bloc agenda">
    <h2>À venir</h2>
    <ul>{agenda}</ul>
  </div>
  <div class="bloc mot">
    <h2>Le mot de la semaine</h2>
    <p class="terme"><dfn>{t(m['terme'])}</dfn></p>
    <p>{t(m['definition'])}{lie}</p>
    <p class="suite"><a href="{BASE}glossaire/#{a(m['slug'])}">Tous les mots du glossaire</a></p>
  </div>
</section>"""


def errata(ed):
    if not ed.get("errata"):
        return ""
    items = "".join(
        f'<li><time datetime="{e["date"]}">{t(date_longue(e["date"]))}</time> : {t(e["correction"])}'
        + (f' <a href="#s-{a(e["signal_id"])}">Signal concerné</a>' if e.get("signal_id") else "")
        + "</li>" for e in ed["errata"])
    return f"""<section class="errata wrap ruled" aria-labelledby="titre-errata">
  <h2 id="titre-errata">Corrections apportées à cette édition</h2>
  <ul>{items}</ul>
</section>"""


def ouverture(ed, niveau_titre="h1"):
    ess = "".join(f"<li>{t(p)}</li>" for p in ed["essentiel"])
    return f"""<section class="ouverture wrap">
  <div class="ouverture-titre">
    <p class="numero">Veille robotique, numéro {ed['numero']}</p>
    <{niveau_titre} class="titre-edition">Semaine {t(periode(ed['periode']['debut'], ed['periode']['fin']))}</{niveau_titre}>
    <p class="promesse">{t(TAGLINE)} Publié le {t(date_longue(ed['date_publication'], True))}, à lire en trois minutes.</p>
  </div>
  <div class="ouverture-essentiel">
    <h2 class="titre-essentiel">L'essentiel</h2>
    <ul class="essentiel">{ess}</ul>
  </div>
</section>"""


def jsonld_edition(ed):
    return {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"Veille robotique : semaine {periode(ed['periode']['debut'], ed['periode']['fin'])}",
        "description": " ".join(ed["essentiel"]),
        "datePublished": ed["date_publication"],
        "dateModified": max([ed["date_publication"]] + [e["date"] for e in ed.get("errata", [])]),
        "inLanguage": "fr",
        "url": SITE + ed["semaine_iso"] + "/",
        "image": SITE + "assets/og.png",
        "author": {"@type": "Person", "name": AUTHOR, "url": AUTHOR_URL},
        "publisher": {"@type": "Person", "name": AUTHOR, "url": AUTHOR_URL},
        "isPartOf": {"@type": "CreativeWorkSeries", "name": SITE_NAME, "url": SITE},
        "about": [RUBRIQUES[k][0] for k in RUBRIQUES],
    }


def description_edition(ed):
    txt = ed["essentiel"][0]
    return txt if len(txt) <= 160 else txt[:157].rsplit(" ", 1)[0] + "…"


def page_edition(ed, editions, accueil=False):
    corps = "\n".join([ouverture(ed), echelle(ed), rubriques(ed), reperes(ed), errata(ed)])
    if accueil:
        autres = [e for e in editions if e is not ed]
        if autres:
            items = "".join(
                f'<li><a href="{url_edition(e)}">Semaine {t(periode(e["periode"]["debut"], e["periode"]["fin"]))}</a>'
                f'<span>{t(e["essentiel"][0])}</span></li>' for e in autres[:4])
            corps += f"""
<section class="precedentes wrap ruled" aria-labelledby="titre-precedentes">
  <h2 id="titre-precedentes">Éditions précédentes</h2>
  <ul>{items}</ul>
  <p><a href="{BASE}editions/">Toutes les éditions et tous les signaux</a></p>
</section>"""
        titre = f"{SITE_NAME} : ce qui avance vraiment, chaque lundi"
        return page(titre, description_edition(ed), "", corps, actif="", jsonld=jsonld_edition(ed))
    titre = f"Robotique, semaine {periode(ed['periode']['debut'], ed['periode']['fin'])}"
    return page(titre, description_edition(ed), ed["semaine_iso"] + "/", corps, jsonld=jsonld_edition(ed))


def page_editions(editions):
    liste = "".join(f"""<li class="edition">
    <h3><a href="{url_edition(e)}">Semaine {t(periode(e['periode']['debut'], e['periode']['fin']))}</a></h3>
    <p class="meta">Numéro {e['numero']}, publié le {t(date_longue(e['date_publication']))}, {pluriel(len(e['signaux']), 'signal')}</p>
    <ul>{''.join(f'<li>{t(p)}</li>' for p in e['essentiel'])}</ul>
  </li>""" for e in editions)
    lignes = []
    for e in editions:
        for s in e["signaux"]:
            niv, lib, _ = MATURITES[s["maturite"]]
            lignes.append(f"""<li class="ligne" data-rubrique="{s['rubrique']}" data-maturite="{s['maturite']}">
      <a href="{url_edition(e)}#s-{a(s['id'])}">{t(s['titre'])}</a>
      <span class="r">{t(RUBRIQUES[s['rubrique']][0])}</span>
      <span class="maturite m{niv}">{jauge(niv, lib)}{t(lib)}</span>
      <span class="z">{t(ZONES[s['zone']])}</span>
      <time datetime="{s['date_evenement']}">{t(date_longue(s['date_evenement']))}</time>
    </li>""")
    boutons_r = '<button type="button" data-valeur="" aria-pressed="true">Toutes</button>' + "".join(
        f'<button type="button" data-valeur="{k}" aria-pressed="false">{t(v[0])}</button>' for k, v in RUBRIQUES.items())
    boutons_m = '<button type="button" data-valeur="" aria-pressed="true">Toutes</button>' + "".join(
        f'<button type="button" data-valeur="{k}" aria-pressed="false">{t(v[1])}</button>' for k, v in MATURITES.items())
    corps = f"""<section class="ouverture court wrap">
  <h1 class="titre-edition">Toutes les éditions</h1>
  <p class="promesse">Une édition chaque lundi depuis le {t(date_longue(editions[-1]['date_publication']))}. Les signaux de toutes les semaines peuvent aussi être filtrés plus bas.</p>
</section>
<section class="wrap ruled liste-editions" aria-label="Éditions">
  <ul>{liste}</ul>
</section>
<section class="wrap ruled index-signaux" aria-labelledby="titre-signaux">
  <h2 id="titre-signaux">Tous les signaux</h2>
  <div class="filtres" data-filtres hidden>
    <div role="group" aria-label="Filtrer par rubrique" data-groupe="rubrique"><span class="lib">Rubrique</span>{boutons_r}</div>
    <div role="group" aria-label="Filtrer par maturité" data-groupe="maturite"><span class="lib">Maturité</span>{boutons_m}</div>
  </div>
  <p class="resultat" aria-live="polite" data-resultat></p>
  <ul class="lignes">{''.join(lignes)}</ul>
</section>"""
    return page(f"Toutes les éditions, {SITE_NAME}",
                "Toutes les éditions de la veille robotique hebdomadaire et l'index de leurs signaux, filtrable par rubrique et par maturité.",
                "editions/", corps, actif="editions/")


def glossaire(editions):
    mots = []
    for e in editions:
        m = e["mot_de_la_semaine"]
        mots.append({**m, "semaine": e["semaine_iso"], "periode": periode(e["periode"]["debut"], e["periode"]["fin"]),
                     "url": url_edition(e)})
    return sorted(mots, key=lambda m: m["terme"].lower())


def page_glossaire(editions):
    mots = glossaire(editions)
    entrees = "".join(f"""<div class="entree" id="{a(m['slug'])}">
    <dt>{t(m['terme'])}</dt>
    <dd><p>{t(m['definition'])}</p><p class="origine">Ajouté avec l'édition de la <a href="{m['url']}">semaine {t(m['periode'])}</a>.</p></dd>
  </div>""" for m in mots)
    ld = {
        "@context": "https://schema.org",
        "@type": "DefinedTermSet",
        "name": "Glossaire de la veille robotique",
        "url": SITE + "glossaire/",
        "inLanguage": "fr",
        "hasDefinedTerm": [
            {"@type": "DefinedTerm", "name": m["terme"], "description": m["definition"],
             "url": f"{SITE}glossaire/#{m['slug']}"} for m in mots],
    }
    corps = f"""<section class="ouverture court wrap">
  <h1 class="titre-edition">Glossaire</h1>
  <p class="promesse">Les mots de la robotique expliqués simplement, un par semaine. {pluriel(len(mots), "mot")} pour l'instant.</p>
</section>
<section class="wrap ruled glossaire">
  <dl>{entrees}</dl>
</section>"""
    return page(f"Glossaire de la robotique, {SITE_NAME}",
                "Les termes de la robotique et de l'IA pour robots expliqués simplement, un nouveau mot chaque semaine.",
                "glossaire/", corps, actif="glossaire/", jsonld=ld)


def page_methode():
    niveaux = "".join(
        f'<li class="m{n}"><span class="nom">{jauge(n, lib)}{t(lib)}</span><span>{t(defi)}</span></li>'
        for n, lib, defi in MATURITES.values())
    rubs = "".join(f"<li><strong>{t(n)}.</strong> {t(q)}</li>" for n, q, _ in RUBRIQUES.values())
    corps = f"""<section class="ouverture court wrap">
  <h1 class="titre-edition">Comment cette veille est faite</h1>
  <p class="promesse">La robotique produit beaucoup plus d'annonces que de robots en service. Cette veille trie, vérifie et classe chaque information pour que l'on sache, en trois minutes, ce qui a vraiment avancé.</p>
</section>
<section class="wrap ruled prose">
  <h2>Sept signaux au plus, chaque lundi</h2>
  <p>Chaque édition couvre la semaine écoulée, du lundi au dimanche. Elle retient au plus sept informations, réparties en trois rubriques qui répondent chacune à une question :</p>
  <ul>{rubs}</ul>
  <p>Ces plafonds ne sont jamais des objectifs : une semaine calme donne une édition plus courte. Les véhicules autonomes ne sont pas couverts.</p>

  <h2 id="maturite">L'échelle de maturité</h2>
  <p>Chaque signal reçoit un niveau de maturité, de l'idée de laboratoire au robot en service. C'est la question centrale de cette veille : une vidéo impressionnante n'est pas un déploiement.</p>
  <ol class="niveaux">{niveaux}</ol>
  <p>Le niveau Déployé exige un client nommé et un volume en service, attestés par une source de première main. Un produit en vente ou un contrat signé reste au niveau Commercialisé. Quand un chiffre vient de l'entreprise elle-même, le texte le précise.</p>

  <h2>Les sources</h2>
  <p>Les informations viennent en priorité des sources de première main : communiqués des entreprises, publications scientifiques, statistiques de la Fédération internationale de la robotique, organismes publics. La presse spécialisée complète. Les newsletters de compilation et les sites rédigés par IA servent seulement à repérer un sujet, jamais à le sourcer. Chaque signal renvoie vers ses sources.</p>

  <h2>Qui la produit</h2>
  <p>Chaque lundi matin, un agent d'intelligence artificielle collecte, trie et rédige l'édition selon des règles écrites, puis la publie. Une vérification automatique bloque la publication si une règle n'est pas respectée. {AUTHOR} relit ensuite l'édition dans la journée. Dans le doute, une information est écartée plutôt que publiée.</p>

  <h2>Corrections</h2>
  <p>Une erreur publiée est corrigée et signalée en bas de l'édition concernée, avec sa date. Pour signaler une erreur, <a href="{REPO}/issues">ouvrez un ticket sur GitHub</a>.</p>
</section>"""
    return page(f"Méthode, {SITE_NAME}",
                "Comment la veille robotique est produite : rubriques, échelle de maturité, sources, vérification et corrections.",
                "methode/", corps, actif="methode/")


def page_404():
    corps = f"""<section class="ouverture court wrap">
  <h1 class="titre-edition">Cette page n'existe pas</h1>
  <p class="promesse">L'adresse est peut-être incomplète. <a href="{BASE}">Lire l'édition de la semaine</a> ou <a href="{BASE}editions/">parcourir toutes les éditions</a>.</p>
</section>"""
    return page(f"Page introuvable, {SITE_NAME}", "Cette page n'existe pas.", "404.html", corps, indexable=False)


def flux(editions):
    items = []
    for e in editions:
        pub = datetime.fromisoformat(e["date_publication"] + "T05:00:00").replace(tzinfo=timezone.utc)
        items.append(f"""  <item>
    <title>{html.escape('Semaine ' + periode(e['periode']['debut'], e['periode']['fin']))}</title>
    <link>{SITE}{e['semaine_iso']}/</link>
    <guid isPermaLink="true">{SITE}{e['semaine_iso']}/</guid>
    <pubDate>{format_datetime(pub)}</pubDate>
    <description>{html.escape(' '.join(e['essentiel']))}</description>
  </item>""")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{SITE_NAME}, nogues.app</title>
  <link>{SITE}</link>
  <atom:link href="{SITE}flux.xml" rel="self" type="application/rss+xml"/>
  <description>{html.escape(TAGLINE)} Chaque lundi.</description>
  <language>fr</language>
{chr(10).join(items)}
</channel>
</rss>
"""


def sitemap(editions):
    urls = [("", editions[0]["date_publication"]), ("editions/", editions[0]["date_publication"]),
            ("glossaire/", editions[0]["date_publication"]), ("methode/", None)]
    urls += [(e["semaine_iso"] + "/", e["date_publication"]) for e in editions]
    lignes = "".join(
        f"  <url><loc>{SITE}{u}</loc>{f'<lastmod>{m}</lastmod>' if m else ''}</url>\n" for u, m in urls)
    return f'<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{lignes}</urlset>\n'


HTACCESS = f"""DirectoryIndex index.html
ErrorDocument 404 {BASE}404.html
Options -Indexes
AddType application/rss+xml .xml
<IfModule mod_headers.c>
  <FilesMatch "\\.(woff2|png|svg)$">
    Header set Cache-Control "public, max-age=31536000, immutable"
  </FilesMatch>
  <FilesMatch "\\.(css|js)$">
    Header set Cache-Control "public, max-age=86400"
  </FilesMatch>
</IfModule>
"""


# --- Données dérivées pour l'agent ----------------------------------------------

def mettre_a_jour_donnees(editions):
    index = [{"numero": e["numero"], "semaine_iso": e["semaine_iso"], "date_publication": e["date_publication"],
              "url": SITE + e["semaine_iso"] + "/", "essentiel": e["essentiel"]} for e in editions]
    historique = sorted({s["url"] for e in editions[:8] for x in e["signaux"] for s in x["sources"]})
    gloss = [{"terme": m["terme"], "slug": m["slug"], "definition": m["definition"], "semaine": m["semaine"]}
             for m in glossaire(editions)]
    for nom, contenu in (("index.json", index), ("historique.json", historique), ("glossaire.json", gloss)):
        (DATA / nom).write_text(json.dumps(contenu, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("data/index.json, data/historique.json et data/glossaire.json mis à jour.")


# --- Génération -----------------------------------------------------------------

def ecrire(rel, contenu):
    cible = DIST / rel
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(contenu, encoding="utf-8")


def generer(editions):
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC, DIST / "assets")
    derniere = editions[0]
    ecrire("index.html", page_edition(derniere, editions, accueil=True))
    for e in editions:
        ecrire(f"{e['semaine_iso']}/index.html", page_edition(e, editions))
    ecrire("editions/index.html", page_editions(editions))
    ecrire("glossaire/index.html", page_glossaire(editions))
    ecrire("methode/index.html", page_methode())
    ecrire("404.html", page_404())
    ecrire("flux.xml", flux(editions))
    ecrire("sitemap.xml", sitemap(editions))
    ecrire(".htaccess", HTACCESS)
    n = sum(1 for _ in DIST.rglob("*") if _.is_file())
    print(f"Site généré dans dist/ : {n} fichiers, {len(editions)} édition(s).")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="valider sans générer")
    parser.add_argument("--update-data", action="store_true", help="régénérer les fichiers dérivés de data/")
    args = parser.parse_args()

    editions, r = charger()
    for x in r.alertes:
        print(f"Alerte  {x}")
    for x in r.erreurs:
        print(f"Erreur  {x}", file=sys.stderr)
    if r.erreurs:
        print(f"{len(r.erreurs)} erreur(s) : publication bloquée.", file=sys.stderr)
        sys.exit(1)
    print(f"Validation réussie : {len(editions)} édition(s), {len(r.alertes)} alerte(s).")
    if args.update_data:
        mettre_a_jour_donnees(editions)
    if not args.check:
        generer(editions)


if __name__ == "__main__":
    main()
