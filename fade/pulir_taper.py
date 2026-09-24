"""Pulido de un TAPER fade (degradé solo en patilla y nuca), estilo "más blanco que negro".

Uso:
    python fade/pulir_taper.py entrada.png salida
Genera salida.png, salida_cmp.png (antes/después), salida_full.png, salida_diff.png
(mapa de cambios) y salida_dbg.png (zonas y contornos).

La geometría (ear, face, neck, zonas A/B, cont) está marcada a mano para la foto 4
(1170x2532): para otra foto hay que volver a ubicarla (ver fade/PROCESO.md)."""
import sys, os
import numpy as np, cv2
from scipy import ndimage as nd
from scipy.interpolate import UnivariateSpline, PchipInterpolator

SRC = sys.argv[1]
tag = sys.argv[2] if len(sys.argv) > 2 else 'resultado'
bgr = cv2.imread(SRC)
img = bgr[:, :, ::-1].astype(np.float32)
H, W = img.shape[:2]
xs = np.arange(W, dtype=np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
DMAX = float(os.environ.get('DMAX', '12'))
BMAX = float(os.environ.get('BMAX', '10'))
GAMMA = float(os.environ.get('GAMMA', '1.2'))

def pchip(pts):
    px, py = zip(*pts)
    return PchipInterpolator(px, py, extrapolate=True)(xs).astype(np.float32)

def poly(pts):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 255)
    return m

Ls = nd.uniform_filter(img.mean(2), 5)

# ---------------- geometry -------------------------------------------------------------------
ear = poly([(572, 1470), (585, 1448), (610, 1436), (650, 1438), (690, 1455), (712, 1490), (716, 1550),
            (705, 1610), (685, 1650), (655, 1662), (625, 1640), (600, 1600), (580, 1540)])
bg = ((Ls > 185) & (xx > 860)).astype(np.uint8) * 255                     # wall behind the neck
bg = cv2.dilate(bg, np.ones((15, 15), np.uint8))

# zone A: sideburn taper
AX0, AX1 = 372, 572
rawA = np.array([1360 + np.argmax(Ls[1360:1480, x] > 90) for x in range(W)], np.float32)
fxA = np.arange(AX0 + 10, AX1 - 5)
splA = UnivariateSpline(fxA, nd.median_filter(rawA, 11)[fxA], k=3, s=len(fxA) * 30)
topA = np.full(W, np.nan, np.float32); topA[AX0:AX1] = splA(np.arange(AX0, AX1))
topA[:AX0] = topA[AX0]; topA[AX1:] = topA[AX1 - 1]
botA = pchip([(372, 1525), (420, 1538), (470, 1535), (520, 1515), (572, 1485)])
face = poly([(250, 1380), (345, 1432), (365, 1450), (375, 1475), (380, 1510), (386, 1560), (386, 1640), (250, 1640)])

# zone B: nape taper
BX0, BX1 = 720, 892
topB = pchip([(720, 1470), (760, 1495), (800, 1505), (850, 1510), (892, 1505)])
botB = pchip([(720, 1545), (760, 1592), (800, 1625), (850, 1640), (892, 1640)])
neck = poly([(722, 1462), (750, 1505), (775, 1545), (795, 1585), (815, 1640), (815, 1800),
             (600, 1800), (600, 1462)])                                          # skin left of the nape line

prot = cv2.max(ear, bg)

# ---------------- sideburn: clean top edge (warp the real hair a few px) ---------------------------
actualA = nd.gaussian_filter1d(nd.median_filter(rawA, 9), 1.5)
D = np.zeros(W, np.float32)
D[AX0:AX1] = np.nan_to_num((topA - actualA)[AX0:AX1])
D = np.clip(nd.gaussian_filter1d(D, 1.5), -10, 10)
D *= np.clip((xs - AX0 - 10) / 20, 0, 1) * np.clip((AX1 - 10 - xs) / 20, 0, 1)
tA = np.nan_to_num(topA, nan=0)
dl = yy - tA[None, :]
wv = np.where(dl < 0, np.clip(1 + dl / 40, 0, 1), np.clip(1 - dl / 40, 0, 1))
wv = wv * wv * (3 - 2 * wv) * ((xx >= AX0) & (xx < AX1))
warped = cv2.remap(img, xx, (yy - D[None, :] * wv).astype(np.float32), cv2.INTER_LINEAR,
                   borderMode=cv2.BORDER_REPLICATE)
lowW = cv2.GaussianBlur(warped, (0, 0), 3.0)

# ---------------- contours: keep their slight darkness ------------------------------------------------
# distance to any contour (face edge, ear, nape line, silhouette)
cont = np.zeros((H, W), np.uint8)
cv2.polylines(cont, [np.array([(345, 1432), (365, 1450), (375, 1475), (380, 1510), (386, 1560)], np.int32)], False, 255, 2)   # sideburn front
cv2.polylines(cont, [np.array([(722, 1462), (750, 1505), (775, 1545), (795, 1585), (815, 1640)], np.int32)], False, 255, 2)             # nape side line
cont |= cv2.morphologyEx(cv2.max(ear, bg), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
dcont = cv2.distanceTransform(255 - cont, cv2.DIST_L2, 5).astype(np.float32)

PREF = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'taper_ref_profile.npy'))
if os.environ.get('WHITE', '1') == '1':     # polished taper: short black, short grey, lots of light
    PREF = np.interp(np.linspace(0, 1, 21), [0, 0.1, 0.2, 0.3, 0.45, 0.6, 0.8, 1.0],
                     [0.06, 0.22, 0.42, 0.6, 0.79, 0.9, 0.97, 1.0])
HB = float(os.environ.get('HB', '40'))                      # black level
SKB = float(os.environ.get('SKB', '1.04'))                   # skin brightness factor for the "white"
dEB = cv2.distanceTransform(255 - cv2.max(ear, bg), cv2.DIST_L2, 5).astype(np.float32)

def level_zone(X0, X1, top, bot, excl, out, name):
    t = (yy - top[None, :]) / np.maximum(bot - top, 5)[None, :]
    inzone = (xx >= X0) & (xx < X1) & (t > -0.05) & (t < 1.25) & (excl == 0) & (prot == 0)
    lowO = cv2.GaussianBlur(out, (0, 0), 3.0)
    tb = np.linspace(-0.15, 1.3, 59)
    # own profile of the zone (monotonic) - used to find where each tone lives in the real fade
    core = inzone & (dcont > 10)
    tv = t[core]; lv = lowO[core].mean(1)
    PL = np.array([np.median(lv[np.abs(tv - v) < 0.03]) if (np.abs(tv - v) < 0.03).sum() > 20 else np.nan for v in tb])
    # above the zone (long hair edge) take the column pixels directly
    for i, v in enumerate(tb):
        if np.isnan(PL[i]):
            m = (xx >= X0) & (xx < X1) & (np.abs(t - v) < 0.03) & (excl == 0) & (prot == 0)
            PL[i] = np.median(lowO[m].mean(1)) if m.sum() > 20 else np.nan
    PL = nd.gaussian_filter1d(pd_fill(PL), 1.2)
    PL = np.maximum.accumulate(PL) + np.arange(len(PL)) * 1e-3
    # per-column skin level (the "white")
    SK = np.zeros(W, np.float32); ok = np.zeros(W, bool)
    for x in range(X0, X1):
        ys = np.arange(int(bot[x]), int(bot[x] + 25))
        m = (excl[ys, x] == 0) & (prot[ys, x] == 0)
        if m.sum() > 5:
            SK[x] = np.percentile(lowO[ys, x][m].mean(1), 60); ok[x] = True
    SK = nd.gaussian_filter1d(np.interp(xs, xs[ok], SK[ok]), 15) * SKB
    # target tone at each depth: reference distribution between black and this column's skin
    tq = np.clip(t, 0, 1)
    pr = np.interp(tq, np.linspace(0, 1, len(PREF)), PREF)
    pr = np.where(t < 0, PREF[0] * np.clip(1 + t / 0.05, 0, 1), pr)
    pr = np.where(t > 1, PREF[-1] + (1 - PREF[-1]) * np.clip((t - 1) / 0.25, 0, 1), pr)
    Tl = HB + (SK[None, :] - HB) * pr
    # where in the real fade does that tone live? -> resample the column vertically (real texture)
    # 1-D mapping for the zone (median skin), slope-limited -> no streaks, no hard edges
    skm = float(np.median(SK[X0:X1]))
    tg = np.linspace(-0.15, 1.3, 146)
    prg = np.interp(np.clip(tg, 0, 1), np.linspace(0, 1, len(PREF)), PREF)
    prg = np.where(tg < 0, PREF[0] * np.clip(1 + tg / 0.05, 0, 1), prg)
    prg = np.where(tg > 1, PREF[-1] + (1 - PREF[-1]) * np.clip((tg - 1) / 0.25, 0, 1), prg)
    fs = np.interp(HB + (skm - HB) * prg, PL, tb)
    wedge = np.clip(np.minimum((tg + 0.12) / 0.1, (1.28 - tg) / 0.15), 0, 1)
    fs = tg * (1 - wedge) + fs * wedge
    dt = tg[1] - tg[0]
    for _ in range(3):                                   # slope limits
        d = np.clip(np.diff(fs) / dt, 0.6, 1.7)
        fs = np.concatenate([[fs[0]], fs[0] + np.cumsum(d) * dt])
        fs = fs - np.interp(1.3, tg, fs) + 1.3 if False else fs
    fs = nd.gaussian_filter1d(fs, 2)
    print(name, 'map t->src', [(round(float(a_), 2), round(float(b_), 2)) for a_, b_ in zip(tg[::15], fs[::15])])
    tsrc = np.interp(np.clip(t, -0.15, 1.3), tg, fs)
    tsrc = np.where((t < -0.15) | (t > 1.3), t, tsrc)
    ysrc = top[None, :] + tsrc * (bot - top)[None, :]
    rem = cv2.remap(out, xx, ysrc.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    MODE = os.environ.get('MODE', 'A2')
    if MODE == 'A2':
        # photo-2 style: gentle multiplicative levelling of blotches (texture ratio kept, no colour veil)
        lowR = cv2.GaussianBlur(rem, (0, 0), 4.0)
        lR = lowR.mean(2)
        tgt = cv2.GaussianBlur(Tl.astype(np.float32), (0, 0), 2)
        dd = np.clip(tgt - lR, -float(os.environ.get('DK', '8')), float(os.environ.get('LT', '14')))
        dd = np.where(dd > 0, dd * np.clip((t - 0.15) / 0.25, 0, 1), dd)     # lighten only lower in the fade
        dd = np.where(dd < 0, dd * np.clip((t - 0.1) / 0.3, 0, 1), dd)        # never darken the top band
        dd = cv2.GaussianBlur(dd.astype(np.float32), (0, 0), 2)
        rem = rem * ((lR + dd) / np.maximum(lR, 1))[..., None]
    if MODE == 'C':
        rem = out.copy()
    if MODE in ('B', 'C'):
        # soft: darken mostly the hairs (weighted by how much hair each pixel has), toward the
        # photo's OWN stubble colour; cap the change; lighten only a little
        Lp = rem.mean(2)
        kk = np.ones((7, 7), np.uint8)
        Sk = cv2.GaussianBlur(cv2.dilate(Lp, kk), (0, 0), 3)
        c = np.clip((Sk - Lp) / np.maximum(Sk - 30, 10), 0, 1)
        zone_px = inzone & (dcont > 8)
        dark_px = zone_px & (c > 0.5)
        own_hair = np.median(out[dark_px], axis=0) if dark_px.sum() > 50 else np.array([45, 40, 40], np.float32)
        l0 = cv2.GaussianBlur(Lp, (0, 0), 4.0)
        need = cv2.GaussianBlur((l0 - Tl).astype(np.float32), (0, 0), 3)
        DK = float(os.environ.get('DK', '22')); LT = float(os.environ.get('LT', '8'))
        need = np.clip(need, -LT, DK)
        wgt = 0.35 + 0.65 * np.sqrt(c)                       # hairs take most of it, skin a little
        wgt = wgt / np.maximum(cv2.GaussianBlur(wgt, (0, 0), 4), 0.2)
        dL = need * wgt                                         # >0 darken
        f = np.clip(dL / np.maximum(Lp - own_hair.mean(), 8), -0.6, 0.85)[..., None]
        skin_rgb = cv2.GaussianBlur(np.stack([cv2.dilate(rem[..., k], kk) for k in range(3)], -1), (0, 0), 3)
        rem = np.where(f >= 0, rem * (1 - f) + own_hair * f, rem + (skin_rgb - rem) * (-f))
    # contours / ear / wall: keep as they are
    dex = cv2.distanceTransform((255 - excl).astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32)
    ext = (xx >= X0) & (xx < X1) & (t > -0.4) & (t < 1.25) & (excl == 0) & (prot == 0)
    top_ramp = np.clip((t + 0.4) / 0.4, 0, 1); top_ramp = top_ramp * top_ramp * (3 - 2 * top_ramp)
    Mz = cv2.GaussianBlur(ext.astype(np.float32), (0, 0), 2.0) * top_ramp * np.clip(dex / 14, 0, 1) ** 0.8
    Mz *= np.clip((dEB - 6) / 14, 0, 1)
    Mz *= np.clip((dcont - 3) / 9, 0, 1)            # contours keep their slight darkness
    print(name, 'own', [int(v) for v in PL[::6]], 'target', [int(v) for v in (HB + (np.median(SK[X0:X1]) - HB) * PREF[::4])])
    return out * (1 - Mz[..., None]) + rem * Mz[..., None]

def pd_fill(a):
    a = np.array(a, np.float32); idx = np.arange(len(a)); m = ~np.isnan(a)
    return np.interp(idx, idx[m], a[m]).astype(np.float32)

out = img.copy()
wA = ((xx >= AX0) & (xx < AX1)).astype(np.float32) * (1 - cv2.GaussianBlur(face.astype(np.float32) / 255, (0, 0), 1))
out = out * (1 - wA[..., None]) + warped * wA[..., None]
out = level_zone(AX0, AX1, topA, botA, face, out, 'patilla')
out = level_zone(BX0, BX1, topB, botB, neck, out, 'nuca')

res = np.clip(out, 0, 255).astype(np.uint8)[:, :, ::-1]
cv2.imwrite(f'{tag}.png', res)
cv2.imwrite(f'{tag}_cmp.png', np.vstack([bgr[1330:1700, 300:960], res[1330:1700, 300:960]]))
cv2.imwrite(f'{tag}_full.png', cv2.resize(np.hstack([bgr[700:1900, 100:1170], res[700:1900, 100:1170]]), None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA))
d = cv2.GaussianBlur(res.astype(np.float32).mean(2) - bgr.astype(np.float32).mean(2), (0, 0), 3)
cv2.imwrite(f'{tag}_diff.png', cv2.applyColorMap(np.clip(128 + d * 4, 0, 255).astype(np.uint8), cv2.COLORMAP_JET)[1330:1700, 300:960])
dbg = res.copy()
for x in range(AX0, AX1):
    cv2.circle(dbg, (x, int(topA[x])), 1, (0, 0, 255), -1); cv2.circle(dbg, (x, int(botA[x])), 1, (255, 0, 255), -1)
    cv2.circle(dbg, (x, int(actualA[x])), 1, (0, 255, 0), -1)
for x in range(BX0, BX1):
    cv2.circle(dbg, (x, int(topB[x])), 1, (0, 0, 255), -1); cv2.circle(dbg, (x, int(botB[x])), 1, (255, 0, 255), -1)
cv2.drawContours(dbg, cv2.findContours(cont, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0], -1, (255, 255, 0), 1)
cv2.imwrite(f'{tag}_dbg.png', dbg[1330:1700, 300:960])
print('max brighten', d.max(), 'max darken', d.min())
