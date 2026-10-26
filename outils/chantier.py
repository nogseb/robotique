"""Génère gabarits/chantier.svg : un bras robotisé qui se construit comme une épure.

Usage : python3 outils/chantier.py > gabarits/chantier.svg
Le SVG est inséré tel quel dans l'en-tête de chaque édition par build.py ;
les couleurs et le minutage de l'animation sont dans static/veille.css (section « Épure d'ouverture »).
"""
import math
import sys

def f(x): return f"{x:.1f}".rstrip("0").rstrip(".")

def capsule(p0, p1, w):
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]; L = math.hypot(dx, dy)
    ux, uy = dx/L, dy/L; nx, ny = -uy, ux
    a = (p0[0]+nx*w, p0[1]+ny*w); b = (p1[0]+nx*w, p1[1]+ny*w)
    c = (p1[0]-nx*w, p1[1]-ny*w); d = (p0[0]-nx*w, p0[1]-ny*w)
    return (f"M{f(a[0])} {f(a[1])}L{f(b[0])} {f(b[1])}A{w} {w} 0 0 0 {f(c[0])} {f(c[1])}"
            f"L{f(d[0])} {f(d[1])}A{w} {w} 0 0 0 {f(a[0])} {f(a[1])}Z")

def cadre(p0, p1, w, m):
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]; L = math.hypot(dx, dy)
    ux, uy = dx/L, dy/L; nx, ny = -uy, ux
    e = w + m
    pts = [(p0[0]-ux*e+nx*e, p0[1]-uy*e+ny*e), (p1[0]+ux*e+nx*e, p1[1]+uy*e+ny*e),
           (p1[0]+ux*e-nx*e, p1[1]+uy*e-ny*e), (p0[0]-ux*e-nx*e, p0[1]-uy*e-ny*e)]
    return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"

def arc(c, r, a0, a1):
    p = lambda a: (c[0]+r*math.cos(math.radians(a)), c[1]+r*math.sin(math.radians(a)))
    s, e = p(a0), p(a1)
    return f"M{f(s[0])} {f(s[1])}A{r} {r} 0 0 1 {f(e[0])} {f(e[1])}"

E = (190, 380); C = (330, 200); P = (480, 240)   # épaule, coude, poignet
L = 'pathLength="1"'
out = []
w = out.append
# Les attributs width, height, fill et stroke ne servent que de repli si la feuille de style manque : le CSS les remplace.
w('<svg class="chantier" viewBox="0 0 600 520" width="240" height="208" preserveAspectRatio="xMaxYMax meet" fill="none" stroke="currentColor" stroke-width="1" aria-hidden="true" focusable="false">')
# 1. Lignes de construction
w('<g class="ch-g">')
for i, d in enumerate(["M20 200H590", "M20 380H590", "M190 30V500", "M480 30V500"]):
    w(f'<path {L} d="{d}" style="--d:{0.15 + i*0.12:.2f}s"/>')
w('</g>')
# 2. Cadres de construction en pointillés
w('<g class="ch-f">')
w(f'<path d="M104 378H276V490H104Z" style="--d:.55s"/>')
w(f'<path d="{cadre(E, C, 22, 10)}" style="--d:.95s"/>')
w(f'<path d="{cadre(C, P, 16, 10)}" style="--d:1.4s"/>')
w(f'<path d="M458 238H502V334H458Z" style="--d:1.85s"/>')
w('</g>')
# 3. Enveloppe de travail et axes
w(f'<path class="ch-e" d="{arc(E, 322, -104, -2)}"/>')
w('<g class="ch-a">')
w(f'<path d="M{E[0]} {E[1]}L{C[0]} {C[1]}L{P[0]} {P[1]}V332"/>')
w('</g>')
# 4. Pièces tracées
w('<g class="ch-t">')
w(f'<path {L} d="M40 480H580" style="--d:.35s"/>')
w(f'<path {L} d="M116 480V446Q116 440 122 440H258Q264 440 264 446V480" style="--d:.8s"/>')
w(f'<path {L} d="M150 440L164 404Q190 390 216 404L230 440" style="--d:1.1s"/>')
w(f'<path {L} class="plein" d="{capsule(E, C, 22)}" style="--d:1.45s"/>')
w(f'<path {L} class="plein" d="{capsule(C, P, 16)}" style="--d:1.95s"/>')
w(f'<path {L} class="plein" d="M468 256Q468 252 472 252H488Q492 252 492 256V284H468Z" style="--d:2.4s"/>')
w('</g>')
# 5. Pince : deux mors qui se referment à la fin
w('<g class="ch-t ch-mors">')
w(f'<path {L} class="mg" d="M466 284V320L473 327" style="--d:2.6s"/>')
w(f'<path {L} class="md" d="M494 284V320L487 327" style="--d:2.6s"/>')
w('</g>')
# 6. Articulations
w('<g class="ch-j">')
for (x, y), r, dl in ((E, 28, 1.75), (C, 22, 2.25), (P, 15, 2.7)):
    w(f'<g style="--d:{dl}s"><circle class="plein" cx="{x}" cy="{y}" r="{r}"/><circle class="axe" cx="{x}" cy="{y}" r="5"/></g>')
w('<circle class="boulon" cx="138" cy="460" r="4" style="--d:1.2s"/><circle class="boulon" cx="242" cy="460" r="4" style="--d:1.25s"/>')
w('</g>')
# 7. Cote horizontale entre l'axe de l'épaule et celui du poignet
w(f'<path class="ch-c" {L} d="M190 120H480M190 108V132M480 108V132"/>')
w('</svg>')
sys.stdout.write("".join(out))
