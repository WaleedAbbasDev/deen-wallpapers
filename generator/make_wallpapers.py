"""
Deen Reminders: lock-screen wallpaper generator.

Builds the website into ./site:
  site/w/1.jpg ... site/w/N.jpg   lock-screen wallpapers for iPhone 14 Pro (1179 x 2556)
  site/w/list.json                text of every wallpaper (used by the web app)
  site/index.html + app files     the Home Screen web app

GitHub Actions runs this every few hours, so the wallpapers are shuffled and
new Quran ayahs come in each time.

Run locally:  python generator/make_wallpapers.py
"""

import json
import math
import os
import random
import re
import shutil
import sys
import urllib.request
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "generator", "fonts")
OUT = os.path.join(ROOT, "site")

W, H = 1179, 2556            # iPhone 14 Pro screen in pixels
TEXT_TOP, TEXT_BOTTOM = 930, 2230   # keep clear of the clock (top) and torch/camera buttons (bottom)
MARGIN_X = 105

# English translation of the Quran (Saheeh International), downloaded at build time.
QURAN_SOURCES = [
    "https://raw.githubusercontent.com/fawazahmed0/quran-api/1/editions/eng-ummmuhammad.json",
    "https://cdn.jsdelivr.net/gh/fawazahmed0/quran-api@1/editions/eng-ummmuhammad.json",
]

SURAHS = [
    "Al-Fatihah", "Al-Baqarah", "Ali 'Imran", "An-Nisa", "Al-Ma'idah", "Al-An'am", "Al-A'raf", "Al-Anfal",
    "At-Tawbah", "Yunus", "Hud", "Yusuf", "Ar-Ra'd", "Ibrahim", "Al-Hijr", "An-Nahl", "Al-Isra", "Al-Kahf",
    "Maryam", "Ta-Ha", "Al-Anbiya", "Al-Hajj", "Al-Mu'minun", "An-Nur", "Al-Furqan", "Ash-Shu'ara",
    "An-Naml", "Al-Qasas", "Al-'Ankabut", "Ar-Rum", "Luqman", "As-Sajdah", "Al-Ahzab", "Saba", "Fatir",
    "Ya-Sin", "As-Saffat", "Sad", "Az-Zumar", "Ghafir", "Fussilat", "Ash-Shura", "Az-Zukhruf",
    "Ad-Dukhan", "Al-Jathiyah", "Al-Ahqaf", "Muhammad", "Al-Fath", "Al-Hujurat", "Qaf", "Adh-Dhariyat",
    "At-Tur", "An-Najm", "Al-Qamar", "Ar-Rahman", "Al-Waqi'ah", "Al-Hadid", "Al-Mujadila", "Al-Hashr",
    "Al-Mumtahanah", "As-Saff", "Al-Jumu'ah", "Al-Munafiqun", "At-Taghabun", "At-Talaq", "At-Tahrim",
    "Al-Mulk", "Al-Qalam", "Al-Haqqah", "Al-Ma'arij", "Nuh", "Al-Jinn", "Al-Muzzammil", "Al-Muddaththir",
    "Al-Qiyamah", "Al-Insan", "Al-Mursalat", "An-Naba", "An-Nazi'at", "'Abasa", "At-Takwir", "Al-Infitar",
    "Al-Mutaffifin", "Al-Inshiqaq", "Al-Buruj", "At-Tariq", "Al-A'la", "Al-Ghashiyah", "Al-Fajr",
    "Al-Balad", "Ash-Shams", "Al-Layl", "Ad-Duha", "Ash-Sharh", "At-Tin", "Al-'Alaq", "Al-Qadr",
    "Al-Bayyinah", "Az-Zalzalah", "Al-'Adiyat", "Al-Qari'ah", "At-Takathur", "Al-'Asr", "Al-Humazah",
    "Al-Fil", "Quraysh", "Al-Ma'un", "Al-Kawthar", "Al-Kafirun", "An-Nasr", "Al-Masad", "Al-Ikhlas",
    "Al-Falaq", "An-Nas",
]

LABELS = {
    "quran": "THE HOLY QURAN",
    "hadith": "SAHIH HADITH",
    "ali": "HAZRAT ALI (RA)",
    "iqbal": "ALLAMA IQBAL",
    "rumi": "MAULANA RUMI",
    "scholar": "WORDS OF WISDOM",
}

# Dark themes so the white iPhone clock always stays readable.
THEMES = [
    {"name": "midnight", "top": (8, 14, 32), "bottom": (18, 34, 66), "accent": (214, 180, 110)},
    {"name": "emerald", "top": (4, 26, 22), "bottom": (10, 58, 47), "accent": (222, 192, 120)},
    {"name": "charcoal", "top": (14, 14, 14), "bottom": (36, 32, 27), "accent": (206, 170, 100)},
    {"name": "maroon", "top": (30, 8, 15), "bottom": (66, 20, 36), "accent": (226, 186, 128)},
    {"name": "indigo", "top": (16, 12, 38), "bottom": (40, 30, 82), "accent": (212, 186, 130)},
    {"name": "teal", "top": (4, 22, 30), "bottom": (12, 52, 66), "accent": (220, 196, 140)},
]

# Ayahs that need their story or ruling around them make poor stand-alone reminders,
# so random picks from the whole Quran skip lines containing these words.
NARRATIVE_ONLY = re.compile(
    r"\b(said|says|saying|Pharaoh|Moses|Aaron|Noah|Lot|Abraham|Ishmael|Isaac|Jacob|Joseph|Solomon|David|"
    r"Jonah|Zechariah|Mary|Jesus|Thamud|'Aad|Midian|Shu'ayb|Salih|Hud|Israel|Jews|Christians|Iblees|"
    r"divorce|divorced|menstruation|inheritance|bequest|wives|husband|husbands|slave|slaves|captives|"
    r"booty|spoils|fight|fighting|kill|killed|slay|battle|polytheists|hypocrites|disbelievers|"
    r"Muhammad|Prophet|wife|women)\b",
    re.IGNORECASE,
)
BAD_OPENERS = re.compile(r"^(And|Then|So|But|Or|Except|Until|When|If|Indeed, they|They|He|She|Those|These|That|This|It|"
                         r"Ask|Has|Is it|Perhaps|Do you not consider|You are|We|On the Day|A speaker|Rather|Of|In the|Indeed, he|No!|Have you not|Did they|Allah has set a seal)\b")
# A random ayah must speak about Allah, the soul or the Hereafter to make a good reminder.
GOOD_WORDS = re.compile(r"\b(Allah|your Lord|Lord|Hereafter|mankind|O you who have believed|soul|mercy|merciful|"
                        r"forgiv\w*|patien\w*|remember\w*|remembrance|grateful|worldly life|life of this world|"
                        r"righteous\w*|Paradise|heart|hearts|prayer|repent\w*)\b")


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def dm_sans(size, weight="Medium"):
    f = font("DMSans.ttf", size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


# ---------------------------------------------------------------- Quran data

def load_quran():
    cache = os.path.join(ROOT, ".quran-cache.json")
    for url in QURAN_SOURCES:
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = json.load(r)
            verses = data["quran"]
            with open(cache, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return {(v["chapter"], v["verse"]): v["text"] for v in verses}
        except Exception as e:  # try the next source
            print(f"Could not load {url}: {e}", file=sys.stderr)
    if os.path.exists(cache):
        data = json.load(open(cache, encoding="utf-8"))
        return {(v["chapter"], v["verse"]): v["text"] for v in data["quran"]}
    print("WARNING: no Quran text available; building without Quran wallpapers.", file=sys.stderr)
    return {}


def tidy(text):
    text = text.strip()
    text = re.sub(r"\s+-\s+", " — ", text)
    text = text.replace("  ", " ")
    if text and text[-1] not in ".!?”\"'":
        text += "."
    if text.count('"') % 2:  # close a quotation the ayah leaves open
        text += '"'
    return text


def quran_item(quran, ref):
    surah, verses = ref.split(":")
    surah = int(surah)
    if "-" in verses:
        a, b = (int(x) for x in verses.split("-"))
    else:
        a = b = int(verses)
    parts = [quran.get((surah, v)) for v in range(a, b + 1)]
    if not all(parts):
        return None
    text = " ".join(tidy(p) for p in parts)
    return {"cat": "quran", "text": text, "ref": f"Surah {SURAHS[surah - 1]} · {ref}"}


def random_quran_items(quran, count, used_refs, max_chars, rng):
    candidates = []
    for (s, v), t in quran.items():
        ref = f"{s}:{v}"
        if ref in used_refs or not (55 <= len(t) <= min(max_chars, 260)):
            continue
        if BAD_OPENERS.match(t) or NARRATIVE_ONLY.search(t):
            continue
        if t.count("[") > 2 or '"' in t or not GOOD_WORDS.search(t):
            continue
        candidates.append(ref)
    rng.shuffle(candidates)
    return [quran_item(quran, r) for r in candidates[:count]]


# ---------------------------------------------------------------- drawing

def wrap(draw, text, fnt, max_w):
    lines = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for w in words:
            test = (line + " " + w).strip()
            if draw.textlength(test, font=fnt) <= max_w or not line:
                line = test
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
    # avoid a lonely last word
    if len(lines) >= 2 and len(lines[-1].split()) == 1:
        prev = lines[-2].split()
        if len(prev) > 2:
            moved = prev.pop()
            candidate = moved + " " + lines[-1]
            if draw.textlength(candidate, font=fnt) <= max_w:
                lines[-2], lines[-1] = " ".join(prev), candidate
    return lines


def star_points(cx, cy, r):
    """Eight-pointed star (two overlapping squares) as one outline."""
    pts = []
    inner = r * 0.7654  # where the two squares cross
    for i in range(16):
        ang = math.pi / 8 * i - math.pi / 2
        rad = r if i % 2 == 0 else inner
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


_pattern_cache = None


def pattern_mask():
    """Faint Islamic star lattice, fading out behind the text."""
    global _pattern_cache
    if _pattern_cache is not None:
        return _pattern_cache
    s = 2  # draw at double size for smooth lines
    big = Image.new("L", (W * s, H * s), 0)
    d = ImageDraw.Draw(big)
    step = 168 * s
    r = 62 * s
    for row in range(-1, H * s // step + 2):
        for col in range(-1, W * s // step + 2):
            cx = col * step + (step / 2 if row % 2 else 0)
            cy = row * step
            d.polygon(star_points(cx, cy, r), outline=255, width=2 * s)
            d.line([(cx + r, cy), (cx + step - r, cy)], fill=255, width=2 * s)
    mask = big.resize((W, H), Image.LANCZOS)
    # fade: visible near top and bottom, almost gone behind the quote
    fade = Image.new("L", (1, H))
    for y in range(H):
        mid = (TEXT_TOP + TEXT_BOTTOM) / 2
        dist = abs(y - mid) / (H / 2)
        fade.putpixel((0, y), int(255 * min(1, max(0.08, (dist - 0.12) * 1.6))))
    fade = fade.resize((W, H))
    mask = Image.composite(mask, Image.new("L", (W, H), 0), fade)
    _pattern_cache = mask.point(lambda p: int(p * 0.14))
    return _pattern_cache


def background(theme):
    top, bottom = theme["top"], theme["bottom"]
    grad = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / (H - 1)
        t = t * t * (3 - 2 * t)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    img = grad.resize((W, H))
    # soft glow behind the text
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    cy = (TEXT_TOP + TEXT_BOTTOM) // 2
    gd.ellipse([W * 0.05, cy - 620, W * 0.95, cy + 620], fill=40)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    light = Image.new("RGB", (W, H), tuple(min(255, c + 60) for c in bottom))
    img = Image.composite(light, img, glow)
    accent = Image.new("RGB", (W, H), theme["accent"])
    img = Image.composite(accent, img, pattern_mask())
    return img


def ornament(draw, cx, cy, color, r=13):
    draw.polygon(star_points(cx, cy, r), fill=color)
    draw.line([(cx - 120, cy), (cx - r - 14, cy)], fill=color, width=2)
    draw.line([(cx + r + 14, cy), (cx + 120, cy)], fill=color, width=2)


def render(item, theme, path):
    img = background(theme)
    draw = ImageDraw.Draw(img)
    accent = theme["accent"]
    max_w = W - 2 * MARGIN_X
    max_h = TEXT_BOTTOM - TEXT_TOP

    label_f = dm_sans(31, "SemiBold")
    ref_f = dm_sans(36, "Medium")
    original = item.get("original")

    # find the largest quote size that fits
    for size in range(96, 38, -2):
        q_f = font("CrimsonText-Regular.ttf", size)
        o_lines, o_size = [], 0
        if original:
            # keep each line of the Urdu couplet on one line if possible
            o_size = min(int(size * 0.78), 50)
            while o_size > 30:
                o_f = font("CrimsonText-Italic.ttf", o_size)
                if all(draw.textlength(l, font=o_f) <= max_w for l in original.split("\n")):
                    break
                o_size -= 1
            o_f = font("CrimsonText-Italic.ttf", o_size)
            o_lines = wrap(draw, original, o_f, max_w)
        q_lines = wrap(draw, item["text"], q_f, max_w)
        q_lh, o_lh = int(size * 1.32), int(o_size * 1.35)
        ref_lines = wrap(draw, item["ref"], ref_f, max_w)
        height = 40 + 70 + len(o_lines) * o_lh + (50 if o_lines else 0) + len(q_lines) * q_lh + 70 + len(ref_lines) * 50
        if height <= max_h and len(q_lines) <= 13:
            break

    y = TEXT_TOP + (max_h - height) // 2
    y = max(TEXT_TOP, y - 40)  # sit slightly above centre

    # label with letter spacing
    label = LABELS.get(item["cat"], "REMINDER")
    spacing = 7
    lw = sum(draw.textlength(ch, font=label_f) for ch in label) + spacing * (len(label) - 1)
    x = (W - lw) / 2
    for ch in label:
        draw.text((x, y), ch, font=label_f, fill=accent)
        x += draw.textlength(ch, font=label_f) + spacing
    y += 40
    ornament(draw, W / 2, y + 30, accent)
    y += 70

    if o_lines:
        for line in o_lines:
            draw.text((W / 2, y), line, font=o_f, fill=tuple(int(c * 0.95) for c in accent), anchor="ma")
            y += o_lh
        y += 50

    for line in q_lines:
        draw.text((W / 2, y), line, font=q_f, fill=(246, 242, 234), anchor="ma")
        y += q_lh

    y += 52
    for line in ref_lines:
        draw.text((W / 2, y), line, font=ref_f, fill=tuple(int(c * 0.9) for c in accent), anchor="ma")
        y += 50

    img.save(path, "JPEG", quality=88, optimize=True, progressive=True)


def make_icon(path, size):
    s = 4
    img = Image.new("RGB", (size * s, size * s), (10, 20, 40))
    d = ImageDraw.Draw(img)
    c = size * s / 2
    d.polygon(star_points(c, c, size * s * 0.34), fill=(214, 180, 110))
    d.polygon(star_points(c, c, size * s * 0.2), fill=(10, 20, 40))
    img.resize((size, size), Image.LANCZOS).save(path)


# ---------------------------------------------------------------- main

def main():
    cfg = json.load(open(os.path.join(ROOT, "quotes.json"), encoding="utf-8"))
    settings = cfg.get("settings", {})
    total = int(settings.get("total_wallpapers", 200))
    max_chars = int(settings.get("max_characters", 430))
    share = float(settings.get("random_quran_share", 0.25))

    seed = os.environ.get("SEED") or datetime.now(timezone.utc).strftime("%Y%m%d%H")
    rng = random.Random(seed)

    quran = load_quran()
    items = []
    for ref in cfg.get("quran_refs", []):
        it = quran_item(quran, ref) if quran else None
        if it and len(it["text"]) <= max_chars:
            items.append(it)
    for q in cfg.get("quotes", []):
        if len(q["text"]) <= max_chars:
            items.append(q)

    curated = items[:]
    rng.shuffle(curated)
    n_random = max(0, total - len(curated)) if quran else 0
    n_random = max(n_random, int(total * share)) if quran else 0
    used = set(r for r in cfg.get("quran_refs", []))
    randoms = random_quran_items(quran, n_random, used, max_chars, rng) if quran else []

    pool = curated[: max(0, total - len(randoms))] + randoms
    while len(pool) < total and curated:  # top up by repeating if needed
        pool.append(rng.choice(curated))
    rng.shuffle(pool)

    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "w"))

    listing = []
    for i, item in enumerate(pool, start=1):
        theme = rng.choice(THEMES)
        render(item, theme, os.path.join(OUT, "w", f"{i}.jpg"))
        listing.append({"n": i, "cat": item["cat"], "text": item["text"], "ref": item["ref"],
                        **({"original": item["original"]} if item.get("original") else {})})
        if i % 25 == 0:
            print(f"  {i}/{len(pool)} wallpapers")

    meta = {"generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
            "count": len(pool), "items": listing}
    with open(os.path.join(OUT, "w", "list.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    app = os.path.join(ROOT, "app")
    for name in os.listdir(app):
        shutil.copy(os.path.join(app, name), os.path.join(OUT, name))
    make_icon(os.path.join(OUT, "icon-180.png"), 180)
    make_icon(os.path.join(OUT, "icon-512.png"), 512)
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    print(f"Done: {len(pool)} wallpapers in {OUT}")


if __name__ == "__main__":
    main()
