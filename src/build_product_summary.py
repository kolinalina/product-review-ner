
import glob
import html
import json
import re
import sys
from collections import Counter, defaultdict

import pandas as pd

CATALOG_PATH = "data/catalog_products.csv"
OUT_PATH = "data/product_aspects.json"
MIN_REVIEWS = 10          
TOP_PHRASES = 3

# Kamus keluhan sederhana (heuristik, BUKAN model sentimen)
NEG_WORDS = (r"\b(kurang|jelek|buruk|lemot|lambat|lama|boros|panas|rusak|cacat|lecet|penyok|pecah|mati|"
             r"error|bapuk|kecewa|mengecewakan|bocor|retak|tipis|berisik|putus|gagal|bermasalah|"
             r"tidak|gak|nggak|ngga|ga|tak|blm|belum)\b")
# Negasi dari kata negatif = justru positif ("tidak ada lecet", "gak panas")
NEG_OF_NEG = (r"\b(tidak|gak|nggak|ngga|ga|tak|tanpa|bebas)\s+(ada\s+)?"
              r"(cacat|lecet|penyok|rusak|masalah|kendala|panas|lag|lemot|minus|kurang|cepat panas)\b")
# Kata negasi yang berdiri sendiri di depan kata positif ("tidak bagus") ikut dianggap keluhan
POS_AFTER_NEG = r"\b(tidak|gak|nggak|ngga|ga|tak|kurang|belum|blm)\s+(bagus|awet|jernih|cepat|oke|ok|sesuai|rapi|aman|kuat|nyala|berfungsi|jalan|support)\b"


def clean_phrase(p: str) -> str:
    p = re.sub(r"\s+", " ", p.strip(" .,;:!?\"'()[]-_*").lower())
    return p


def is_complaint(phrase: str) -> bool:
    if re.search(NEG_OF_NEG, phrase):
        return False
    if re.search(POS_AFTER_NEG, phrase):
        return True
    # kata "tidak/gak/..." sendirian di depan kata lain tidak dihitung, kecuali pola di atas
    strong = r"\b(kurang|jelek|buruk|lemot|lambat|boros|rusak|cacat|lecet|penyok|pecah|mati|error|bapuk|kecewa|mengecewakan|bocor|retak|berisik|putus|gagal|bermasalah)\b"
    weak_combo = r"\b(cepat|gampang|mudah|agak|sering|jadi|terlalu)\s+(panas|habis|lemot|lag|rusak|drop)\b"
    return bool(re.search(strong, phrase) or re.search(weak_combo, phrase))


def load_reviews(catalog_ids):
    candidates = [p for p in glob.glob("data/*review*.csv")]
    if not candidates:
        sys.exit("CSV review tidak ditemukan di folder data/")
    df = pd.read_csv(candidates[0])
    # dukung dua versi dataset (2025: review_text/product_category, 2019: text/category)
    df = df.rename(columns={"text": "review_text"})
    df["review_text"] = df["review_text"].astype(str).apply(html.unescape).str.strip()
    df = df[df["product_id"].isin(catalog_ids)]
    df = df[df["review_text"].str.len() > 0]
    return df


def summarize(extractor):
    cat = pd.read_csv(CATALOG_PATH)
    cat = cat[cat["n_reviews"] >= MIN_REVIEWS]
    reviews = load_reviews(set(cat["product_id"]))
    print(f"Produk: {len(cat)} | review yang diproses: {len(reviews)}")

    per_prod = defaultdict(lambda: {"reviews_with": defaultdict(int),
                                    "phrases": defaultdict(Counter),
                                    "complaints": Counter(),
                                    "n": 0})
    for i, r in enumerate(reviews.itertuples(), 1):
        info = per_prod[r.product_id]
        info["n"] += 1
        seen_labels = set()
        for label, phrase in extractor(r.review_text):
            phrase = clean_phrase(phrase)
            if not phrase:
                continue
            seen_labels.add(label)
            info["phrases"][label][phrase] += 1
            if is_complaint(phrase):
                info["complaints"][(label, phrase)] += 1
        for l in seen_labels:
            info["reviews_with"][l] += 1
        if i % 200 == 0:
            print(f"  ...{i}/{len(reviews)} review")

    out = []
    for row in cat.itertuples():
        info = per_prod.get(row.product_id)
        if not info or info["n"] == 0:
            continue
        aspects = {}
        for label, n_rev in info["reviews_with"].items():
            aspects[label] = {
                "n_reviews": n_rev,
                "share": round(n_rev / info["n"], 3),
                "top_phrases": [p for p, _ in info["phrases"][label].most_common(TOP_PHRASES)],
            }
        out.append({
            "product_id": int(row.product_id),
            "name": row.product_name,
            "type": row.type,
            "price": None if pd.isna(row.price) else int(row.price),
            "n_reviews": int(info["n"]),
            "avg_rating": round(float(row.avg_rating), 2),
            "url": row.url,
            "aspects": dict(sorted(aspects.items(), key=lambda kv: -kv[1]["n_reviews"])),
            "complaints": [{"aspect": l, "phrase": p, "count": c}
                           for (l, p), c in info["complaints"].most_common(5)],
        })

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Selesai: {len(out)} produk -> {OUT_PATH}")
    return out


if __name__ == "__main__":
    sys.path.insert(0, "src")
    from ner_infer import extract_aspects
    summarize(extract_aspects)