"""Génère les épures animées des en-têtes, dans gabarits/ :

  chantier-edition.svg    bras robotisé qui referme sa pince (accueil et pages d'édition)
  chantier-editions.svg   robot mobile qui transporte une pile de caisses et balaie au lidar (page Éditions)
  chantier-glossaire.svg  main robotisée dont les capteurs tactiles s'allument (page Glossaire)
  chantier-methode.svg    robot delta au-dessus d'un convoyeur qui lui amène un colis (page Méthode)

Usage : python3 outils/chantier.py
Chaque SVG est inséré tel quel par build.py ; les couleurs et le minutage sont dans static/veille.css
(section « Épures d'ouverture »). Toutes suivent la même grammaire, dans cet ordre d'apparition :
lignes de construction (ch-g), cadres en pointillés (ch-f), pièces tracées (ch-t), articulations (ch-j),
enveloppe de travail (ch-e), axes (ch-a), cote (ch-c), puis un dernier mouvement propre à chaque robot.
Même cadre pour toutes (600 x 520, sol à y = 480) : leur place dans la page reste identique.
"""
import math
from pathlib import Path

GABARITS = Path(__file__).resolve().parent.parent / "gabarits"
L = 'pathLength="1"'


def f(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


def capsule(p0, p1, w):
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]; n = math.hypot(dx, dy)
    ux, uy = dx/n, dy/n; nx, ny = -uy, ux
    a = (p0[0]+nx*w, p0[1]+ny*w); b = (p1[0]+nx*w, p1[1]+ny*w)
    c = (p1[0]-nx*w, p1[1]-ny*w); d = (p0[0]-nx*w, p0[1]-ny*w)
    return (f"M{f(a[0])} {f(a[1])}L{f(b[0])} {f(b[1])}A{w} {w} 0 0 0 {f(c[0])} {f(c[1])}"
            f"L{f(d[0])} {f(d[1])}A{w} {w} 0 0 0 {f(a[0])} {f(a[1])}Z")


def cadre(p0, p1, w, m):
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]; n = math.hypot(dx, dy)
    ux, uy = dx/n, dy/n; nx, ny = -uy, ux
    e = w + m
    pts = [(p0[0]-ux*e+nx*e, p0[1]-uy*e+ny*e), (p1[0]+ux*e+nx*e, p1[1]+uy*e+ny*e),
           (p1[0]+ux*e-nx*e, p1[1]+uy*e-ny*e), (p0[0]-ux*e-nx*e, p0[1]-uy*e-ny*e)]
    return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"


def arc(c, r, a0, a1):
    p = lambda a: (c[0]+r*math.cos(math.radians(a)), c[1]+r*math.sin(math.radians(a)))
    s, e = p(a0), p(a1)
    return f"M{f(s[0])} {f(s[1])}A{r} {r} 0 0 1 {f(e[0])} {f(e[1])}"


def rect(x0, y0, x1, y1, r):
    """Rectangle aux angles arrondis."""
    return (f"M{x0+r} {y0}H{x1-r}Q{x1} {y0} {x1} {y0+r}V{y1-r}Q{x1} {y1} {x1-r} {y1}"
            f"H{x0+r}Q{x0} {y1} {x0} {y1-r}V{y0+r}Q{x0} {y0} {x0+r} {y0}Z")


def cadre_droit(x0, y0, x1, y1):
    return f"M{x0} {y0}H{x1}V{y1}H{x0}Z"


def cote_h(x0, x1, y):
    return f"M{x0} {y}H{x1}M{x0} {y-12}V{y+12}M{x1} {y-12}V{y+12}"


def cote_v(x, y0, y1):
    return f"M{x} {y0}V{y1}M{x-12} {y0}H{x+12}M{x-12} {y1}H{x+12}"


class Epure:
    """Accumule les éléments d'une épure ; chaque méthode correspond à une couche de la grammaire."""

    def __init__(self, nom):
        self.nom = nom
        # width, height, fill et stroke ne servent que de repli si la feuille de style manque : le CSS les remplace.
        self.out = [f'<svg class="chantier chantier-{nom}" viewBox="0 0 600 520" width="240" height="208" '
                    'preserveAspectRatio="xMaxYMax meet" fill="none" stroke="currentColor" stroke-width="1" '
                    'aria-hidden="true" focusable="false">']

    def w(self, s):
        self.out.append(s)

    def guides(self, chemins):
        self.w('<g class="ch-g">')
        for i, d in enumerate(chemins):
            self.w(f'<path {L} d="{d}" style="--d:{0.15 + i*0.12:.2f}s"/>')
        self.w('</g>')

    def cadres(self, chemins):
        self.w('<g class="ch-f">')
        for d, dl in chemins:
            self.w(f'<path d="{d}" style="--d:{dl}s"/>')
        self.w('</g>')

    def enveloppe(self, d):
        self.w(f'<path class="ch-e" d="{d}"/>')

    def axes(self, d):
        self.w(f'<g class="ch-a"><path d="{d}"/></g>')

    def piece(self, d, dl, plein=False, classe=""):
        cl = " ".join(c for c in ("plein" if plein else "", classe) if c)
        attr = f' class="{cl}"' if cl else ""
        self.w(f'<path {L}{attr} d="{d}" style="--d:{dl}s"/>')

    def articulation(self, x, y, r, dl, axe=5, moyeu=None):
        m = f'<circle class="plein" cx="{x}" cy="{y}" r="{moyeu}"/>' if moyeu else ""
        self.w(f'<g style="--d:{dl}s"><circle class="plein" cx="{x}" cy="{y}" r="{r}"/>{m}'
               f'<circle class="axe" cx="{x}" cy="{y}" r="{axe}"/></g>')

    def cote(self, d):
        self.w(f'<path class="ch-c" {L} d="{d}"/>')

    def ecrire(self):
        self.w('</svg>')
        GABARITS.mkdir(exist_ok=True)
        chemin = GABARITS / f"chantier-{self.nom}.svg"
        chemin.write_text("".join(self.out), encoding="utf-8")
        return chemin


def bras():
    """Bras robotisé à trois articulations ; la pince se referme à la fin."""
    e = Epure("edition")
    E = (190, 380); C = (330, 200); P = (480, 240)   # épaule, coude, poignet
    e.guides(["M20 200H590", "M20 380H590", "M190 30V500", "M480 30V500"])
    e.cadres([("M104 378H276V490H104Z", ".55"), (cadre(E, C, 22, 10), ".95"),
              (cadre(C, P, 16, 10), "1.4"), ("M458 238H502V334H458Z", "1.85")])
    e.enveloppe(arc(E, 322, -104, -2))
    e.axes(f"M{E[0]} {E[1]}L{C[0]} {C[1]}L{P[0]} {P[1]}V332")
    e.w('<g class="ch-t">')
    e.piece("M40 480H580", ".35")
    e.piece("M116 480V446Q116 440 122 440H258Q264 440 264 446V480", ".8")
    e.piece("M150 440L164 404Q190 390 216 404L230 440", "1.1")
    e.piece(capsule(E, C, 22), "1.45", plein=True)
    e.piece(capsule(C, P, 16), "1.95", plein=True)
    e.piece("M468 256Q468 252 472 252H488Q492 252 492 256V284H468Z", "2.4", plein=True)
    e.w('</g>')
    e.w('<g class="ch-t ch-mors">')
    e.piece("M466 284V320L473 327", "2.6", classe="mg")
    e.piece("M494 284V320L487 327", "2.6", classe="md")
    e.w('</g>')
    e.w('<g class="ch-j">')
    for (x, y), r, dl in ((E, 28, 1.75), (C, 22, 2.25), (P, 15, 2.7)):
        e.articulation(x, y, r, dl)
    e.w('<circle class="boulon" cx="138" cy="460" r="4" style="--d:1.2s"/>'
        '<circle class="boulon" cx="242" cy="460" r="4" style="--d:1.25s"/>')
    e.w('</g>')
    e.cote(cote_h(190, 480, 120))
    return e.ecrire()


def robot_mobile():
    """Robot mobile autonome : châssis, pile de caisses, lidar ; les roues tournent et le lidar balaie à la fin."""
    e = Epure("editions")
    R1, R2 = (220, 440), (400, 440)          # roues
    LI = (406, 288)                          # centre du lidar
    e.guides(["M20 352H590", "M20 440H590", "M220 40V500", "M400 40V500"])
    e.cadres([(cadre_droit(138, 342, 496, 490), ".55"), (cadre_droit(170, 180, 340, 362), ".95"),
              (cadre_droit(374, 264, 438, 362), "1.4")])
    e.enveloppe(arc(LI, 160, -38, 38))
    e.axes("M178 440H442M406 236V352")
    e.w('<g class="ch-t">')
    e.piece("M40 480H580", ".35")
    e.piece(rect(150, 352, 470, 428, 12), ".8", plein=True)
    e.piece(rect(470, 372, 486, 420, 4), "1.05", plein=True)
    e.piece(rect(180, 290, 330, 352, 4), "1.45", plein=True)
    e.piece("M232 314H278", "1.6")
    e.piece(rect(195, 238, 315, 290, 4), "1.75", plein=True)
    e.piece("M238 260H272", "1.9")
    e.piece(rect(212, 194, 298, 238, 4), "2.0", plein=True)
    e.piece(rect(399, 298, 413, 352, 3), "2.15", plein=True)
    e.piece(rect(384, 276, 428, 300, 7), "2.35", plein=True)
    e.piece("M393 288H419", "2.5")
    e.w('</g>')
    e.w('<g class="ch-j">')
    e.articulation(*R1, 40, "1.2", moyeu=15)
    e.articulation(*R2, 40, "1.3", moyeu=15)
    e.w('</g>')
    # Rayons des roues, tracés par-dessus les roues pleines, qui tournent quand le robot démarre
    e.w('<g class="ch-t">')
    for (x, y), dl in ((R1, "2.7"), (R2, "2.8")):
        rayons = "".join(
            f"M{f(x + 15*math.cos(math.radians(a)))} {f(y + 15*math.sin(math.radians(a)))}"
            f"L{f(x + 34*math.cos(math.radians(a)))} {f(y + 34*math.sin(math.radians(a)))}"
            for a in (45, 135, 225, 315))
        e.w(f'<g class="ch-roue"><path {L} d="{rayons}" style="--d:{dl}s"/></g>')
    e.w('</g>')
    e.cote(cote_h(150, 486, 150))
    # Balayage du lidar : trois ondes vers l'avant
    e.w(f'<g class="ch-ondes" style="--o:{LI[0]}px {LI[1]}px">')
    for r, dl in ((40, "3.9"), (64, "4.15"), (88, "4.4")):
        e.w(f'<path d="{arc(LI, r, -30, 30)}" style="--d:{dl}s"/>')
    e.w('</g>')
    return e.ecrire()


def main_robotisee():
    """Main robotisée sur son support ; les doigts s'écartent et les capteurs tactiles s'allument à la fin."""
    e = Epure("glossaire")
    POIGNET = (330, 384)
    doigts = [  # (x, articulation intermédiaire, bout, rotation finale autour de la base)
        (290, 200, 156, "-4deg"),
        (330, 192, 144, "0deg"),
        (370, 200, 156, "4deg"),
    ]
    PO_B, PO_M, PO_T = (266, 332), (226, 296), (206, 258)   # pouce : base, articulation, bout
    e.guides(["M20 258H590", "M20 384H590", "M290 40V500", "M370 40V500"])
    e.cadres([(cadre_droit(256, 250, 404, 400), ".55"), (cadre_droit(276, 126, 384, 272), ".95"),
              (cadre(PO_B, PO_T, 11, 8), "1.4"), (cadre_droit(252, 400, 408, 490), "1.85")])
    e.enveloppe(arc(POIGNET, 268, -128, -52))
    e.axes(f"M330 118V446M{PO_B[0]} {PO_B[1]}L{PO_T[0]} {PO_T[1]}")
    e.w('<g class="ch-t">')
    e.piece("M40 480H580", ".35")
    e.piece(capsule((330, 446), POIGNET, 26), "1.0", plein=True)
    e.piece("M262 480V454Q262 446 270 446H390Q398 446 398 454V480", ".8", plein=True)
    e.piece(rect(268, 262, 392, 372, 16), "1.45", plein=True)
    e.w('</g>')
    e.w('<g class="ch-j">')
    e.articulation(*POIGNET, 22, "1.75")
    e.w('</g>')
    # Chaque doigt est un groupe qui pivote légèrement autour de sa base à la fin
    capteurs = []
    for i, (x, ym, yb, rot) in enumerate(doigts):
        e.w(f'<g class="ch-ecart" style="--o:{x}px 258px;--r:{rot}">')
        e.w('<g class="ch-t">')
        e.piece(capsule((x, 258), (x, ym), 11), f"{1.75 + i*0.12:.2f}", plein=True)
        e.piece(capsule((x, ym), (x, yb), 10), f"{2.1 + i*0.12:.2f}", plein=True)
        e.w('</g><g class="ch-j">')
        e.articulation(x, 258, 13, f"{2.3 + i*0.1:.2f}", axe=4)
        e.articulation(x, ym, 11, f"{2.55 + i*0.1:.2f}", axe=3.5)
        e.w('</g>')
        e.w(f'<circle class="capteur" cx="{x}" cy="{yb}" r="4.5" style="--d:{4.1 + i*0.12:.2f}s"/>')
        e.w(f'<circle class="ch-anneau" cx="{x}" cy="{yb}" r="11" style="--d:{4.2 + i*0.12:.2f}s"/>')
        e.w('</g>')
    e.w(f'<g class="ch-ecart" style="--o:{PO_B[0]}px {PO_B[1]}px;--r:-6deg">')
    e.w('<g class="ch-t">')
    e.piece(capsule(PO_B, PO_M, 11), "2.2", plein=True)
    e.piece(capsule(PO_M, PO_T, 10), "2.45", plein=True)
    e.w('</g><g class="ch-j">')
    e.articulation(*PO_B, 13, "2.6", axe=4)
    e.articulation(*PO_M, 11, "2.75", axe=3.5)
    e.w('</g>')
    e.w(f'<circle class="capteur" cx="{PO_T[0]}" cy="{PO_T[1]}" r="4.5" style="--d:4.5s"/>')
    e.w(f'<circle class="ch-anneau" cx="{PO_T[0]}" cy="{PO_T[1]}" r="11" style="--d:4.6s"/>')
    e.w('</g>')
    e.cote(cote_v(440, 134, 384))
    return e.ecrire()


def robot_delta():
    """Robot delta suspendu au-dessus d'un convoyeur ; un colis arrive sous la ventouse, qui l'aspire."""
    e = Epure("methode")
    MG, MD, MC = (282, 148), (378, 148), (330, 132)   # moteurs gauche, droit, central (caché par la platine)
    CG, CD, CC = (226, 236), (434, 236), (344, 214)   # coudes
    e.guides(["M20 148H590", "M20 236H590", "M20 369H590", "M330 40V500"])
    e.cadres([(cadre_droit(252, 96, 408, 176), ".55"), (cadre(MG, CG, 10, 8), ".95"),
              (cadre(MD, CD, 10, 8), "1.1"), (cadre_droit(284, 352, 376, 404), "1.4"),
              (cadre_droit(176, 410, 484, 490), "1.85")])
    e.enveloppe(arc((330, 148), 262, 52, 128))
    e.axes("M330 60V480")
    e.w('<g class="ch-t">')
    e.piece("M40 480H580", ".35")
    e.piece("M170 104V480M490 104V480", ".5")
    e.piece(rect(150, 80, 510, 104, 4), ".8", plein=True)
    e.piece(rect(186, 420, 474, 446, 13), "1.2", plein=True)
    e.piece("M214 446V480M446 446V480", "1.3")
    e.piece(capsule(MC, CC, 8), "1.75", plein=True)
    e.piece(rect(262, 104, 398, 132, 6), "1.0", plein=True)
    e.piece(capsule(MG, CG, 10), "1.45", plein=True)
    e.piece(capsule(MD, CD, 10), "1.6", plein=True)
    # Bras inférieurs en parallélogramme, puis effecteur et ventouse
    e.piece("M220 236L300 362M232 236L312 362", "2.0")
    e.piece("M428 236L348 362M440 236L360 362", "2.1")
    e.piece("M338 214L326 358M350 214L338 358", "2.2")
    e.piece(rect(292, 360, 368, 378, 5), "2.4", plein=True)
    e.piece("M330 378V388", "2.55")
    e.piece("M318 388H342L337 396H323Z", "2.65", plein=True)
    e.w('</g>')
    e.w('<g class="ch-j">')
    e.articulation(*MG, 18, "1.7")
    e.articulation(*MD, 18, "1.8")
    e.articulation(*CG, 10, "2.3", axe=3.5)
    e.articulation(*CD, 10, "2.35", axe=3.5)
    e.articulation(*CC, 8, "2.4", axe=3)
    e.articulation(200, 433, 8, "1.5", axe=3)
    e.articulation(460, 433, 8, "1.55", axe=3)
    e.w('</g>')
    e.cote(cote_v(540, 148, 369))
    # Le colis glisse sur le convoyeur jusque sous la ventouse, qui l'aspire
    e.w(f'<g class="ch-colis"><path class="plein" d="{rect(310, 396, 350, 420, 3)}"/><path d="M310 405H350"/></g>')
    e.w('<circle class="ch-anneau" cx="330" cy="394" r="16" style="--d:4.85s"/>')
    return e.ecrire()


if __name__ == "__main__":
    for fabrique in (bras, robot_mobile, main_robotisee, robot_delta):
        chemin = fabrique()
        print(f"{chemin.relative_to(GABARITS.parent)} : {chemin.stat().st_size} octets")
