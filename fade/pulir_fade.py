"""Pulido suave del fade (degradé) de una foto, respetando el corte original.

Uso:
    python fade/pulir_fade.py entrada.jpg salida
Genera salida.png (resultado), salida_cmp.png / salida_full.png (antes-después),
salida_temple.png (sien) y salida_dbg.png (línea de peso y zonas protegidas).

La geometría (ear, sideburn, stripe, carc, Lb, XL/XR, rangos de búsqueda) está
marcada a mano para la foto 2 del modelo: para otra foto hay que volver a ubicarla
(ver fade/PROCESO.md).

Photo 2 - gentle polish of the model's OWN fade.
- weight line: same height, clean shape (removes the step behind the ear), natural hair tips
- tones: levelled to this photo's own median fade profile (patches evened out); real texture kept
- darkening is capped (no painted shade): darkness stays in the real hairs
- black connects a bit softer into the fade
- ear, sideburn, dark stripe untouched; temple edge cleaned into a smooth C
- skin left as it is (no beautifying)"""
import sys, os
import numpy as np, cv2
from scipy import ndimage as nd
from scipy.interpolate import UnivariateSpline, PchipInterpolator

SRC = sys.argv[1]
bgr = cv2.imread(SRC)
img = bgr[:, :, ::-1].astype(np.float32)
H, W = img.shape[:2]
xs = np.arange(W, dtype=np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
tag = sys.argv[2] if len(sys.argv) > 2 else 'resultado'
GAMMA = float(os.environ.get('GAMMA', '1.3'))
DMAX = float(os.environ.get('DMAX', '12'))      # max darkening allowed (lum)

def pchip(pts):
    px, py = zip(*pts)
    return PchipInterpolator(px, py, extrapolate=True)(xs).astype(np.float32)

XL, XR = 262, 752

# ---- weight line ------------------------------------------------------------------------
Ls = nd.uniform_filter(img.mean(2), 5)
raw = np.array([520 + np.argmax(Ls[520:800, x] > 75) for x in range(W)], np.float32)
actual = nd.gaussian_filter1d(nd.median_filter(raw, 9), 1.5)
fx = np.arange(300, 746)
spl = UnivariateSpline(fx, nd.median_filter(raw, 11)[fx], k=3, s=len(fx) * 25)
line = np.empty(W, np.float32)
line[300:746] = spl(np.arange(300, 746))
line_front = pchip([(262, float(actual[262])), (285, float(actual[285])), (300, float(line[300])),
                    (310, float(line[310]))])[:300]
line[:300] = line_front[:300]
line[746:] = line[745] + (xs[746:] - 745) * (line[745] - line[740]) / 5

fw = np.clip((330 - xs) / 30, 0, 1)
line = line * (1 - fw) + np.maximum(line, actual) * fw
# ---- warp hair (and the fade with it) so the edge sits on the clean line -----------------
D = np.zeros(W, np.float32)
D[XL:746] = (line - actual)[XL:746]
D = nd.gaussian_filter1d(D, 1.5)
D *= np.clip((xs - 305) / 25, 0, 1) * np.clip((752 - xs) / 12, 0, 1)      # leave the fringe corner alone
dl = yy - line[None, :]
wv = np.where(dl < 0, np.clip(1 + dl / 50, 0, 1), np.clip(1 - dl / 45, 0, 1))
wv = wv * wv * (3 - 2 * wv)
warped = cv2.remap(img, xx, (yy - D[None, :] * wv).astype(np.float32), cv2.INTER_LINEAR,
                   borderMode=cv2.BORDER_REPLICATE)

# ---- protected areas --------------------------------------------------------------------------
prot = np.zeros((H, W), np.uint8)
ear = np.array([(418, 760), (425, 725), (445, 707), (470, 705), (492, 717), (508, 745), (517, 790),
                (512, 830), (498, 862), (475, 874), (452, 862), (438, 830), (425, 800)], np.int32)
cv2.fillPoly(prot, [ear], 255)
sideburn = np.array([(303, 752), (385, 742), (392, 840), (298, 840)], np.int32)
cv2.fillPoly(prot, [sideburn], 255)
stripe = np.array([(568, 752), (640, 778), (720, 812), (790, 845), (790, 930), (568, 815)], np.int32)
cv2.fillPoly(prot, [stripe], 255)
prot_soft = cv2.GaussianBlur(cv2.dilate(prot, np.ones((5, 5), np.uint8)).astype(np.float32) / 255, (0, 0), 1.8)

# temple: smooth C from the fringe down to the sideburn
y0c = float(line[XL])
carc = np.array([(XL, y0c), (285, y0c + 6), (306, y0c + 18), (324, y0c + 38), (337, y0c + 62),
                 (345, 748)], np.float32)
face = np.zeros((H, W), np.uint8)
cv2.fillPoly(face, [np.vstack([carc, [(345, 900), (0, 900), (0, y0c)]]).astype(np.int32)], 255)
face_soft = cv2.GaussianBlur(face.astype(np.float32) / 255, (0, 0), 0.8)

# ---- distance from line --------------------------------------------------------------------------
below = (yy >= line[None, :]).astype(np.uint8)
dist = cv2.distanceTransform(below, cv2.DIST_L2, 5).astype(np.float32)
above = cv2.distanceTransform(1 - below, cv2.DIST_L2, 5).astype(np.float32)
dsign = np.where(below > 0, dist, -above)

# ---- this photo's own fade profile (median behind the ear, where it is cleanest) --------------
lowW = cv2.GaussianBlur(warped, (0, 0), 3.0)
dg = np.arange(-12, 131, dtype=np.float32)
cols = [x for x in range(525, 700, 2)]
P = np.zeros((len(dg), 3), np.float32)
for i, d in enumerate(dg):
    vals = []
    for x in cols:
        y = int(round(line[x] + d))
        if prot[y, x] == 0:
            vals.append(lowW[y, x])
    P[i] = np.median(np.array(vals), axis=0) if vals else P[i - 1]
P = np.stack([nd.gaussian_filter1d(P[:, c], 2.0, mode='nearest') for c in range(3)], 1)
PL = P.mean(1)
P *= (np.maximum.accumulate(PL) / PL)[:, None]
print('profile', [(int(d), int(v)) for d, v in zip(dg[::10], P.mean(1)[::10])])

# length of the fade per column (to the ear top / stripe / sideburn), in px
Lb = pchip([(262, 105), (330, 100), (400, 92), (450, 92), (520, 100), (600, 110), (680, 112), (752, 100)])
LREF = 100.0                                    # the median profile's natural length
dcl = np.clip(dsign / Lb[None, :] * LREF, -12, 130)
# soften the first stretch so the black connects into the fade
seg = dcl < 45
dcl = np.where(seg, -12 + 57 * np.clip((dcl + 12) / 57, 0, 1) ** GAMMA, dcl)
T = np.stack([np.interp(dcl, dg, P[:, c]) for c in range(3)], -1)

# per-column gain: tail matches this column's real skin
G = np.ones((W, 3), np.float32); valid = np.zeros(W, bool)
skinP = P[(dg >= 95) & (dg <= 120)].mean(0)
for x in range(XL, XR):
    y0 = int(line[x] + Lb[x] - 5)
    ok = (prot[y0:y0 + 20, x] == 0) & (face[y0:y0 + 20, x] == 0)
    if ok.sum() < 6:
        continue
    G[x] = np.median(lowW[y0:y0 + 20, x][ok], axis=0) / skinP; valid[x] = True
for c in range(3):
    G[:, c] = nd.gaussian_filter1d(np.interp(xs, xs[valid], G[valid, c]), 20)
gw = np.clip(dsign / 50, 0, 1)[..., None]
T = T * (1 + (G[None] - 1) * gw)

# ---- level: brighten freely, darken only a little (darkness must come from real hairs) ---------
delta = T - lowW
dmax = np.where(dsign < 25, 30.0, DMAX)[..., None]         # near the line: allow the connection
# never brighten natural shadows next to the ear / sideburn / stripe; elsewhere only a little
dprot = cv2.distanceTransform((255 - prot).astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32)
BMAX = float(os.environ.get('BMAX', '10'))
bmax = (BMAX * np.clip((dprot - 8) / 22, 0, 1))[..., None]
delta = np.clip(delta, -dmax, bmax)
lev = warped + delta

# ---- masks ------------------------------------------------------------------------------------------
rt = np.random.default_rng(17)
tipn = nd.gaussian_filter1d(rt.normal(0, 1, W), 0.8) * 1.0 + \
       nd.gaussian_filter1d((rt.random(W) < 0.35) * rt.uniform(1, 5, W), 0.6) * 1.4
hair_keep = cv2.GaussianBlur((yy < (line + np.clip(tipn, 0, None) - 1)[None, :]).astype(np.float32), (0, 0), 0.7)
band = np.clip(np.minimum((dsign + 1) / 2, (Lb[None, :] * 1.25 - dsign) / 20), 0, 1)
band *= ((xx >= XL) & (xx <= XR)).astype(np.float32)
band = cv2.GaussianBlur(band, (0, 0), 1.5) * np.clip((XR - xx) / 14, 0, 1)
M = band * (1 - face_soft) * (1 - prot_soft) * (1 - hair_keep)

reg = ((xx >= XL) & (xx <= XR + 6)).astype(np.float32)
wp = reg * (1 - face_soft) * (1 - prot_soft)
out = img * (1 - wp[..., None]) + warped * wp[..., None]

# light brown tips right above the line -> a touch more neutral (the black connects)
dd = line[None, :] - yy
tipz = (np.clip(1 - dd / 12, 0, 1) * (dd > -2) * ((xx >= XL) & (xx <= XR))).astype(np.float32)
tipz = cv2.GaussianBlur(tipz, (0, 0), 0.8) * np.clip((XR - xx) / 14, 0, 1) * (1 - face_soft)
Lr = out.mean(2, keepdims=True)
Lrb = cv2.GaussianBlur(Lr[..., 0], (0, 0), 3)[..., None]
neutral = np.array([40, 37, 39], np.float32) * np.clip(Lr / np.maximum(Lrb, 1), 0.6, 1.5)
TIPW = float(os.environ.get('TIPW', '0.35'))
out = out * (1 - TIPW * tipz[..., None]) + neutral * TIPW * tipz[..., None]
out = out * (1 - M[..., None]) + lev * M[..., None]

# temple: stubble left outside the new C (face side, close to the edge) -> remove
k7 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
deh = np.stack([cv2.morphologyEx(img[..., c], cv2.MORPH_CLOSE, k7) for c in range(3)], -1)
deh = cv2.medianBlur(np.clip(deh, 0, 255).astype(np.uint8), 3).astype(np.float32)
det = np.clip(img - cv2.GaussianBlur(img, (0, 0), 1.5), -6, 6)       # keep pores
ring = cv2.dilate(255 - face, np.ones((17, 17), np.uint8)) & face     # face side, near the C
ring[:int(y0c) - 2] = 0
cv2.fillPoly(ring, [sideburn], 0)
ring_soft = cv2.GaussianBlur(ring.astype(np.float32) / 255, (0, 0), 2.0) * face_soft
ring_soft *= (yy < 752).astype(np.float32)
if os.environ.get('RING', '0') == '1':
    out = out * (1 - ring_soft[..., None]) + (deh + det) * ring_soft[..., None]

res = np.clip(out, 0, 255).astype(np.uint8)[:, :, ::-1]
cv2.imwrite(f'{tag}.png', res)
cv2.imwrite(f'{tag}_cmp.png', cv2.resize(np.vstack([bgr[560:880, 200:800], res[560:880, 200:800]]), None, fx=1.2, fy=1.2))
cv2.imwrite(f'{tag}_temple.png', cv2.resize(np.hstack([bgr[600:800, 220:420], res[600:800, 220:420]]), None, fx=2, fy=2))
cv2.imwrite(f'{tag}_full.png', np.hstack([bgr[150:1100, 60:960], res[150:1100, 60:960]]))
dbg = res.copy()
for x in range(240, 790):
    cv2.circle(dbg, (x, int(line[x])), 1, (0, 0, 255), -1)
    cv2.circle(dbg, (x, int(actual[x])), 1, (0, 255, 0), -1)
cv2.polylines(dbg, [ear, sideburn, stripe], True, (255, 0, 0), 1)
cv2.polylines(dbg, [carc.astype(np.int32)], False, (0, 255, 255), 1)
cv2.imwrite(f'{tag}_dbg.png', cv2.resize(dbg[560:900, 200:820], None, fx=1.3, fy=1.3))
