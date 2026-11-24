
import re

TYPE_KEYWORDS = {                      # urutan penting: yang spesifik dulu
    "powerbank": r"power\s*bank|powerbank|\bpb\b",
    "tablet": r"tablet|\bipad\b|\btab\b|galaxy\s*tab|redmi\s*pad|xiaomi\s*pad|matepad",
    "smart_tv": r"smart\s*tv|android\s*tv|google\s*tv|\btv\b|televisi",
    "smartphone": r"smartphone|hand\s*phone|handphone|\bhp\b|ponsel|\bphone\b|iphone|android|"
                  r"\bsamsung\b|\bxiaomi\b|\boppo\b|\bvivo\b|\binfinix\b|\brealme\b|\bpoco\b",
}

ASPECT_KEYWORDS = {
    "BATERAI_DAYA": r"baterai|batre|battery|kapasitas|ngecas|nge-?charge|charging|pengisian|fast\s*charg\w*|\bdaya\b|tahan\s*lama",
    "PERFORMA": r"performa|performance|ngebut|kencang|lancar|\blag\b|ngelag|lemot|adem|gak\s*panas|tidak\s*panas",
    "KUALITAS_FISIK": r"kualitas|kokoh|bahan|desain|design|ringan|tipis|kecil|mungil|compact|portable|tahan\s*banting|mulus",
    "LAYAR_TAMPILAN": r"layar|display|gambar|tampilan|jernih|warna|resolusi|\b4k\b",
    "SUARA": r"suara|speaker|\bbass\b|audio",
    "KONEKSI": r"wifi|sinyal|koneksi|bluetooth|hdmi|\busb\b",
    "KEMUDAHAN": r"mudah|gampang|simpel|simple|praktis|ribet",
}
# Hal yang sering diminta user tapi belum ada di data (label NER kita nggak punya)
UNSUPPORTED = r"kamera|foto|video|\bram\b|memori|storage|penyimpanan|gaming|\bgame\b|chipset|prosesor"

UNIT = {"juta": 1_000_000, "jt": 1_000_000, "ribu": 1_000, "rb": 1_000, "k": 1_000}

_NUM = re.compile(
    r"(?<![\w.])(\d+(?:[.,]\d+)*)\s*(juta|jt|ribu|rb|k)?(an)?(?![a-z0-9])"
    r"(?!\s*(?:mah|watt|w\b|inch|inci|gb|tb|hz|mp\b|ram|rom|kg|cm|mm|\"))",
    flags=re.I,
)
_UPPER = re.compile(r"(di\s*bawah|dibawah|maks\w*|max\w*|kurang\s*dari|paling\s*mahal|budget|sampai|<)\s*(rp\.?\s*)?$", re.I)
_LOWER = re.compile(r"(di\s*atas|diatas|min\w*|lebih\s*dari|>)\s*(rp\.?\s*)?$", re.I)
_RANGE_JOIN = re.compile(r"^\s*(-|–|sampai|s/d|sd|hingga|dan|atau)\s*(rp\.?\s*)?$", re.I)


def rupiah(x):
    return "Rp " + f"{int(round(x)):,}".replace(",", ".")


def _to_float(num, unit):
    if unit:
        s = num.replace(",", ".")
        if s.count(".") > 1:
            s = s.replace(".", "")
        return float(s)
    return float(re.sub(r"[.,]", "", num))


def parse_budget(text):
    """Return (lo, hi, label) atau None."""
    t = text.lower()
    found = []
    for m in _NUM.finditer(t):
        num, unit, an = m.group(1), (m.group(2) or "").lower(), m.group(3)
        value = _to_float(num, unit)
        mult = UNIT.get(unit, 1)
        found.append({"value": value * mult, "raw": value, "unit": unit, "mult": mult, "an": bool(an),
                      "start": m.start(), "end": m.end()})

    # "2 - 3 juta": angka pertama tidak punya satuan, ikut satuan angka kedua
    resolved, i = [], 0
    while i < len(found):
        a = found[i]
        if i + 1 < len(found) and _RANGE_JOIN.match(t[a["end"]:found[i + 1]["start"]]):
            b = found[i + 1]
            if not a["unit"] and b["unit"] and a["raw"] < 1000:
                a["value"], a["unit"], a["mult"] = a["raw"] * b["mult"], b["unit"], b["mult"]
            resolved += [a, b]
            i += 2
        else:
            resolved.append(a)
            i += 1
    # angka tanpa satuan yang kecil (mis. "2" dalam "2 hp") bukan harga
    found = [f for f in resolved if f["unit"] or f["value"] >= 10_000]
    if not found:
        return None

    # rentang: "2 - 3 juta", "antara 200 sampai 300 ribu"
    if len(found) >= 2 and _RANGE_JOIN.match(t[found[0]["end"]:found[1]["start"]]):
        a, b = found[0], found[1]
        lo, hi = sorted([a["value"], b["value"]])
        return lo, hi, f"{rupiah(lo)} – {rupiah(hi)}"

    f = found[0]
    before = t[max(0, f["start"] - 22): f["start"]]
    if _UPPER.search(before):
        return 0, f["value"], f"maksimal {rupiah(f['value'])}"
    if _LOWER.search(before):
        return f["value"], float("inf"), f"minimal {rupiah(f['value'])}"
    # "3 jutaan", "200 ribuan", atau angka biasa -> sekitar
    return f["value"] * 0.75, f["value"] * 1.3, f"sekitar {rupiah(f['value'])}"


def parse_query(text, available_types=None):
    t = text.lower()

    ptype = None
    for name, pat in TYPE_KEYWORDS.items():
        if available_types is not None and name not in available_types:
            continue
        if re.search(pat, t):
            ptype = name
            break

    budget = parse_budget(t)

    aspects = [a for a, pat in ASPECT_KEYWORDS.items() if re.search(pat, t)]
    # "awet": untuk baterai kalau kalimatnya bahas baterai/daya, kalau tidak untuk kualitas
    if re.search(r"\bawet\b", t):
        target = "BATERAI_DAYA" if re.search(r"baterai|batre|daya|charg|ngecas|powerbank|power\s*bank", t) else "KUALITAS_FISIK"
        if target not in aspects:
            aspects.append(target)

    unsupported = sorted(set(re.findall(UNSUPPORTED, t)))
    return {
        "type": ptype,
        "lo": budget[0] if budget else None,
        "hi": budget[1] if budget else None,
        "budget_label": budget[2] if budget else None,
        "aspects": aspects,
        "unsupported": unsupported,
    }