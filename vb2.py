"""CommuTree Video Biodata renderer (repo version).
Usage:  python3 vb2.py profile.json
Expects in the working dir: profile.json, p1.jpg (required),
optional p2.jpg / father.jpg / mother.jpg, fonts/, header.png, music.wav
Output: <id>.mp4  (1080x1920, 30fps, ~21s)
"""
import os, re, sys, json, math, random, subprocess, qrcode
from datetime import date
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops, features

P = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "profile.json", encoding="utf-8"))
HEADER, MUSIC = "header.png", "music.wav"
OUT = f"{P.get('id','out')}.mp4"
FB, FR = "fonts/NotoSerifDevanagari-Bold.ttf", "fonts/NotoSansDevanagari-SemiBold.ttf"
LATIN = {FB: "fonts/NotoSerif-Bold.ttf", FR: "fonts/NotoSans-SemiBold.ttf"}
SAMAJ = "श्री मैढ़ क्षत्रिय स्वर्णकार समाज"

W, H, FPS, XF = 1080, 1920, 30, 0.6            # XF = crossfade seconds
TOP = 335                                       # content starts below header
MAROON, GOLD, GOLD_L, IVORY, INK = (139,1,1), (191,144,56), (236,205,130), (253,249,240), (45,30,25)
assert features.check("raqm"), "libraqm missing: Hindi will break"
random.seed(7)

# ---------- text (Devanagari + Latin fallback) ----------
_fc = {}
def F(p, s):
    if (p, s) not in _fc: _fc[(p, s)] = ImageFont.truetype(p, s, layout_engine=ImageFont.Layout.RAQM)
    return _fc[(p, s)]
RUN = re.compile(r"([A-Za-z][A-Za-z .,&/()-]*[A-Za-z]|[A-Za-z])")
def runs(t, p, s): return [(g, F(LATIN[p] if RUN.fullmatch(g) else p, s)) for g in RUN.split(t) if g]
_m = ImageDraw.Draw(Image.new("L", (1, 1)))
def tlen(t, p, s): return sum(_m.textlength(g, font=f) for g, f in runs(t, p, s))
def fit(t, p, s, maxw, mn=26):
    while s > mn and tlen(t, p, s) > maxw: s -= 2
    return s
def text_sprite(parts, maxw=W-160):
    """parts=[(text,font,size,color)] on one line -> RGBA sprite (auto-shrinks as a group)."""
    scale = 1.0
    while sum(tlen(t, p, int(s*scale)) for t, p, s, _ in parts) > maxw and scale > 0.5: scale -= 0.03
    parts = [(t, p, int(s*scale), c) for t, p, s, c in parts]
    w = int(sum(tlen(t, p, s) for t, p, s, _ in parts)) + 20; h = int(max(s for _, _, s, _ in parts) * 1.8)
    im = Image.new("RGBA", (w, h)); d = ImageDraw.Draw(im); x = 10
    for t, p, s, c in parts:
        for g, f in runs(t, p, s): d.text((x, h*0.12), g, font=f, fill=c); x += d.textlength(g, font=f)
    return im

# ---------- easing / compositing ----------
def ease(t): t = max(0, min(1, t)); return 1 - (1 - t) ** 3            # easeOutCubic
def with_alpha(im, a):
    if a >= 0.999: return im
    r, g, b, al = im.split(); return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))
def put(canvas, spr, x, y, a=1.0):
    if a <= 0.01: return
    canvas.alpha_composite(with_alpha(spr, a), (int(x), int(y)))
def put_center(canvas, spr, y, a=1.0, dy=0): put(canvas, spr, (W - spr.width) / 2, y + dy, a)

# ---------- static background ----------
def build_bg():
    bg = Image.new("RGBA", (W, H), IVORY + (255,)); d = ImageDraw.Draw(bg)
    for y in range(TOP, H):                                  # ivory -> warm cream
        t = (y - TOP) / (H - TOP); d.line([(0, y), (W, y)], fill=(253-int(10*t), 249-int(16*t), 240-int(26*t), 255))
    # faint mandala watermark
    wm = Image.new("RGBA", (W, H)); w = ImageDraw.Draw(wm); cx, cy = W // 2, 1150
    for r in range(120, 620, 70): w.ellipse([cx-r, cy-r, cx+r, cy+r], outline=GOLD + (22,), width=2)
    for k in range(48):
        a = k * math.pi / 24; w.line([cx + 120*math.cos(a), cy + 120*math.sin(a), cx + 600*math.cos(a), cy + 600*math.sin(a)], fill=GOLD + (14,), width=2)
    bg.alpha_composite(wm)
    # double gold frame + corner ornaments
    d.rectangle([24, TOP, W-25, H-25], outline=GOLD, width=4); d.rectangle([38, TOP+14, W-39, H-39], outline=GOLD_L, width=2)
    for (x, y, sx, sy) in [(38, TOP+14, 1, 1), (W-39, TOP+14, -1, 1), (38, H-39, 1, -1), (W-39, H-39, -1, -1)]:
        d.line([x, y+sy*70, x+sx*70, y], fill=GOLD, width=3); d.ellipse([x+sx*18-7, y+sy*18-7, x+sx*18+7, y+sy*18+7], fill=GOLD)
    hdr = Image.open(HEADER).convert("RGBA").crop((0, 0, W, TOP)); bg.alpha_composite(hdr, (0, 0))
    return bg
BG = build_bg()

# gold dust particles (subtle, drift upward)
PARTS = [(random.uniform(60, W-60), random.uniform(TOP, H), random.uniform(2, 5), random.uniform(8, 25), random.uniform(0, 6.28)) for _ in range(40)]
def particles(c, t):
    layer = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(layer)
    for x, y, r, v, ph in PARTS:
        yy = TOP + (y - TOP - v * t) % (H - TOP); a = int(90 + 70 * math.sin(t * 1.5 + ph))
        d.ellipse([x-r, yy-r, x+r, yy+r], fill=GOLD_L + (a,))
    c.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1.5)))

# ---------- photo / placeholder ----------
def placeholder(w=900, h=1100):
    im = Image.new("RGB", (w, h), (244, 234, 214)); d = ImageDraw.Draw(im); cx = w // 2; s = (214, 190, 160)
    d.ellipse([cx-140, 230, cx+140, 510], fill=s); d.rounded_rectangle([cx-290, 540, cx+290, 1100], 230, fill=s)
    return im
PRIVACY = P.get("privacy", "clear")
def load(fn):
    if PRIVACY == "hide" or not os.path.exists(fn): return None
    try: im = ImageOps.exif_transpose(Image.open(fn)).convert("RGB")
    except Exception: return None
    if PRIVACY == "blur": im = im.filter(ImageFilter.GaussianBlur(im.width / 28))
    return im

PHOTO = load("p1.jpg"); PHOTO2 = load("p2.jpg")
# p1 = intro only. Every detail scene uses p2 when it exists, so p1 is not repeated.
DAD, MOM = load("father.jpg"), load("mother.jpg")
HAS_PHOTO = PHOTO is not None
PHOTO = PHOTO or placeholder()

def photo_frame(maxw, maxh, zoom=1.0, rounded=24, src=None):
    """WHOLE photo inside a gold frame — never cropped. The frame takes the photo's own
    aspect ratio (fitted inside maxw x maxh), so tall portraits stay tall and nothing is cut.
    zoom scales the finished frame, so the picture still can't lose edges."""
    im = src or PHOTO
    w, h = maxw, maxh                                  # FIXED frame size for every photo
    sc = min(w / im.width, h / im.height)
    fw, fh = max(80, int(im.width * sc)), max(80, int(im.height * sc))
    fit = im.resize((fw, fh), Image.LANCZOS)
    if fw >= w - 2 and fh >= h - 2:
        p = fit                                        # photo already fills the frame
    else:                                              # fill the gap with the photo's own blur
        p = ImageOps.fit(im, (w, h), centering=(0.5, 0.3)).filter(ImageFilter.GaussianBlur(28))
        p = Image.blend(p, Image.new("RGB", (w, h), (30, 14, 8)), 0.35)
        p.paste(fit, ((w - fw) // 2, (h - fh) // 2))
    im = Image.new("RGBA", (w + 28, h + 28)); m = Image.new("L", (w, h)); ImageDraw.Draw(m).rounded_rectangle([0, 0, w-1, h-1], rounded, fill=255)
    d = ImageDraw.Draw(im); d.rounded_rectangle([0, 0, w+27, h+27], rounded+10, fill=GOLD)
    d.rounded_rectangle([7, 7, w+20, h+20], rounded+6, fill=GOLD_L); im.paste(p, (14, 14), m)
    if not HAS_PHOTO:
        cap = text_sprite([("फोटो देखने के लिए CommuTree एप डाउनलोड करें", FB, 40, MAROON)], maxw=w-40)
        im.alpha_composite(cap, ((im.width - cap.width)//2, im.height - cap.height - 40))
    if zoom != 1.0: im = im.resize((int(im.width * zoom), int(im.height * zoom)), Image.LANCZOS)
    return im
def shadow(spr, blur=18, off=12, a=90):
    s = Image.new("RGBA", (spr.width + 80, spr.height + 80)); s.paste((60, 30, 10, a), (40, 40 + off), spr.split()[3])
    return s.filter(ImageFilter.GaussianBlur(blur))

# ---------- reusable pieces ----------
def divider(width):
    im = Image.new("RGBA", (width, 30)); d = ImageDraw.Draw(im); c = width // 2
    d.line([0, 15, c-22, 15], fill=GOLD, width=3); d.line([c+22, 15, width, 15], fill=GOLD, width=3)
    d.polygon([(c, 3), (c+14, 15), (c, 27), (c-14, 15)], fill=GOLD); return im
def pill(title):
    t = text_sprite([(title, FB, 58, (255, 250, 235))]); w, h = t.width + 110, 108
    im = Image.new("RGBA", (w, h)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w-1, h-1], 54, fill=GOLD); d.rounded_rectangle([5, 5, w-6, h-6], 50, fill=MAROON)
    im.alpha_composite(t, ((w - t.width)//2, (h - t.height)//2 + 4)); return im
def shimmer(spr, t):
    """Diagonal light sweep across a sprite (t 0..1)."""
    if not 0 < t < 1: return spr
    band = Image.new("L", spr.size); d = ImageDraw.Draw(band); x = -200 + (spr.width + 400) * t
    d.polygon([(x, 0), (x+70, 0), (x-30, spr.height), (x-100, spr.height)], fill=120)
    band = ImageChops.multiply(band.filter(ImageFilter.GaussianBlur(12)), spr.split()[3])
    out = spr.copy(); out.alpha_composite(Image.merge("RGBA", (*[Image.new("L", spr.size, 255)]*3, band))); return out

def age(dob):
    try:
        dd, mm, yy = map(int, dob.split("/")); t = date.today(); return f"{t.year - yy - ((t.month, t.day) < (mm, dd))} वर्ष"
    except Exception: return ""

# ---------- scenes: each is (duration, draw_fn(canvas, t)) ----------
TITLE = P["name"] if P.get("show_name") else f"विवाह हेतु {P.get('type','वर')}"
NAME = text_sprite([(TITLE, FB, 118, MAROON)])
CITY = text_sprite([(P.get("city",""), FR, 54, GOLD)]) if P.get("city") else None
DIV = divider(520)

def s_intro(c, t):
    # Frame and photo are FIXED (no zoom, no scale) — a slow light sweep gives the motion
    # instead, so the gold border never breathes.
    fr = photo_frame(780, 940)
    fr = shimmer(fr, (t - 1.8) / 3.0)
    a = ease(t / 0.9)
    put_center(c, shadow(fr), 390 - 40, a * 0.8); put_center(c, fr, 390, a)
    a2 = ease((t - 0.8) / 0.8); put_center(c, shimmer(NAME, (t - 1.6) / 1.2), 1360, a2, dy=40 * (1 - a2))
    k = ease((t - 1.3) / 0.8)
    if k > 0: d = DIV.crop((int(260 * (1 - k)), 0, int(260 + 260 * k), 30)); put_center(c, d, 1560)
    if CITY:
        a3 = ease((t - 1.6) / 0.8); put_center(c, CITY, 1605, a3, dy=25 * (1 - a3))

def s_section(title, rows, photo=None, pair=None):
    photo = photo or PHOTO2 or PHOTO
    rows = [(l, v) for l, v in rows if v]; PL = pill(title)
    if not rows: return None
    # Two-column table: labels left, values all starting at the SAME x, wrapped lines
    # aligned under the value column (never centred, never randomly indented).
    LAB = [text_sprite([(l, FB, 58, MAROON), ("  —", FR, 50, GOLD)], maxw=480) if l else None for l, _ in rows]
    VX = 120 + max([sp.width for sp in LAB if sp] or [0]) + 18
    VW = W - VX - 110

    def wrap(v, size, sub=False):
        words, lines, cur = v.split(" "), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if tlen(t, FB, size) <= VW or not cur: cur = t
            else: lines.append(cur); cur = w
        if cur: lines.append(cur)
        col = (90, 62, 48) if sub else INK
        return [text_sprite([(l, FB, size, col)], maxw=VW) for l in lines]

    RS = []                                  # (label_sprite_or_None, value_sprite, is_first_line)
    MAXL = 3                                 # lines per row; shrink the font instead of truncating
    for i, (l, v) in enumerate(rows):
        for size in ((58, 52, 46, 42, 38) if l else (50, 46, 42, 38, 34)):
            vs = wrap(v, size, sub=not l)
            if len(vs) <= MAXL: break
        for j, sp in enumerate(vs): RS.append((LAB[i] if j == 0 else None, sp, j == 0))
    # Fit the rows between the title pill and the card bottom, whatever the row count.
    ROW_GAP = 0.42                        # seconds between row reveals (reading pace)
    TOP0, BOT = 1090, 1770
    GAP = 150 if len(RS) <= 4 else max(104, int((BOT - TOP0) / len(RS)))
    SUB = int(GAP * 0.62)
    top = TOP0 + max(0, (4 - len(RS))) * 55 - 40
    def fn(c, t):
        # Detail scenes: photo is FIXED (no zoom, no slide). Identical placement in every
        # detail scene means the crossfade leaves it visually static — only text moves.
        fr = photo_frame(470, 560, 1.0, src=photo)
        put_center(c, shadow(fr), 400 - 40, 0.7); put_center(c, fr, 400, 1.0)
        a = ease((t - 0.35) / 0.6); sc = 0.85 + 0.15 * a
        pl = shimmer(PL, (t - 1.0) / 1.0).resize((int(PL.width * sc), int(PL.height * sc))) if a > 0 else PL
        put_center(c, pl, 1005 - pl.height // 2 - 20 + (PL.height - pl.height) // 2 + 0, a)
        y = top + 40
        for i, (lab, val, first) in enumerate(RS):
            a = ease((t - 0.7 - i * ROW_GAP) / 0.75); dx = 60 * (1 - a)
            if lab is not None: put(c, lab, 120 - dx, y, a)
            put(c, val, VX - dx, y, a)
            last = (i + 1 == len(RS)) or RS[i + 1][2]           # underline after the full row
            if last:
                k = ease((t - 0.9 - i * ROW_GAP) / 0.75)
                if k > 0: ImageDraw.Draw(c).line([130, y + val.height + 8, 130 + int(700 * k), y + val.height + 8], fill=GOLD_L + (255,), width=2)
                y += GAP
            else: y += SUB
    return fn

QR = qrcode.make(P.get("profile_url",""), box_size=14, border=2).convert("RGBA").resize((540, 540))
QRT = Image.new("RGBA", (600, 600)); ImageDraw.Draw(QRT).rounded_rectangle([0, 0, 599, 599], 36, fill=(255,255,255,255), outline=GOLD, width=8); QRT.alpha_composite(QR, (30, 30))
CTA = [text_sprite([("अधिक जानकारी के लिए", FB, 60, INK)]), text_sprite([("क्यूआर कोड स्कैन करें", FB, 80, MAROON)]),
       text_sprite([("या समाज की एप में निशुल्क रजिस्टर करें", FB, 48, GOLD)])]
DIS = [text_sprite([("दी गई जानकारी संबंधित व्यक्ति द्वारा प्रदान की गई है,", FR, 32, (110, 90, 80))]), text_sprite([("कृपया सत्यापन कर लें।", FR, 32, (110, 90, 80))])]
def s_qr(c, t):
    a = ease(t / 0.8); sc = 0.8 + 0.2 * a; q = QRT.resize((int(600 * sc), int(600 * sc)))
    put_center(c, shadow(q), 430 - 40 + (600 - q.height) // 2, a * 0.7); put_center(c, q, 430 + (600 - q.height) // 2, a)
    for i, s in enumerate(CTA):
        a = ease((t - 0.7 - i * 0.3) / 0.6); put_center(c, shimmer(s, (t - 2.0) / 1.2) if i == 1 else s, 1100 + i * 115, a, dy=30 * (1 - a))
    a = ease((t - 1.8) / 0.8)
    for i, s in enumerate(DIS): put_center(c, s, 1700 + i * 55, a)

def age(dob):
    try:
        dd, mm, yy = map(int, dob.split("/")); t = date.today()
        return f"{t.year - yy - ((t.month, t.day) < (mm, dd))} वर्ष"
    except Exception: return ""

G = [g for g in P.get("gotra", []) if g]
GL = ["स्वयं", "ननिहाल", "दादी", "नानी"]
def dur(rows, base=3.6):
    """Scene length grows with the number of rows, so nothing flashes past."""
    return round(base + 0.62 * len([1 for l, v in rows if v]), 1)

R_PERSONAL = [("आयु", age(P.get("dob",""))), ("जन्म समय", P.get("birth_time","")),
              ("जन्म स्थान", P.get("birthplace","")), ("ऊंचाई", P.get("height","")),
              ("मांगलिक", P.get("manglik",""))]
R_EDU      = [("शिक्षा", P.get("education","")), ("कार्य", P.get("work","")), ("आय", P.get("income",""))]
R_FAMILY   = [("पिता", P.get("father","")), ("", P.get("father_work","")),
              ("माता", P.get("mother","")), ("", P.get("mother_work",""))]
R_GOTRA    = [(GL[i], g) for i, g in enumerate(G)]

SCENES = [(5.2, s_intro),
          (dur(R_PERSONAL), s_section("व्यक्तिगत विवरण", R_PERSONAL)),
          (dur(R_EDU),      s_section("शिक्षा व कार्य", R_EDU)),
          (dur(R_FAMILY),   s_section("परिवार विवरण", R_FAMILY)),
          (dur(R_GOTRA),    s_section("गोत्र", R_GOTRA)),
          (5.8, s_qr)]
SCENES = [(d, f) for d, f in SCENES if f]

# ---------- render: frame-by-frame -> ffmpeg pipe ----------
starts, t0 = [], 0.0
for d, _ in SCENES: starts.append(t0); t0 += d - XF
TOTAL = t0 + XF
def scene_frame(i, t):
    c = Image.new("RGBA", (W, H)); SCENES[i][1](c, t); return c
audio = ["-i", MUSIC] if os.path.exists(MUSIC) else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       *audio, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "160k", "-af", f"afade=t=in:d=0.8,afade=t=out:st={TOTAL-1.5:.2f}:d=1.5",
                       "-t", f"{TOTAL:.2f}", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
N = int(TOTAL * FPS)
for f in range(N):
    t = f / FPS; frame = BG.copy(); particles(frame, t)
    act = [i for i, s in enumerate(starts) if s <= t < s + SCENES[i][0]]
    if len(act) == 2:                                          # crossfade
        i, j = act; k = ease((t - starts[j]) / XF)
        a, b = scene_frame(i, t - starts[i]), scene_frame(j, t - starts[j])
        frame.alpha_composite(with_alpha(a, 1 - k)); frame.alpha_composite(with_alpha(b, k))
    elif act: frame.alpha_composite(scene_frame(act[0], t - starts[act[0]]))
    ff.stdin.write(frame.convert("RGB").tobytes())
    if f % 90 == 0: print(f"{f}/{N}", flush=True)
ff.stdin.close(); ff.wait(); print("Done:", OUT, f"{TOTAL:.1f}s")
