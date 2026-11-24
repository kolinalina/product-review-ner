
import html
import json
import re
import sys

import warnings

import pandas as pd

warnings.filterwarnings("ignore", message="This pattern is interpreted as a regular expression")

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/tokopedia_product_reviews.csv"
SEED = 42
TARGET_PER_TYPE = 75        # 4 type x 75 = 300 reviews
MAX_PER_PRODUCT = 3         # start with 3 review per product
MIN_LEN, MAX_LEN = 50, 400  # length review normal
MIN_LEN_LOW_RATING = 25     # review rating

TYPES = {
    "powerbank": r"power ?bank",
    "tablet": r"ipad|galaxy tab|redmi pad|xiaomi pad|realme pad|oppo pad|lenovo tab|advan x?tab|matepad|xpad|tablet",
    "smartphone": (r"iphone|galaxy [asmz]\d|samsung [asmz]\d|infinix (hot|note|smart|zero|gt)|realme|"
                   r"redmi (note|\d|a\d)|\bpoco|oppo (reno|a\d|find)|\breno|vivo (y|v|t|x)\d|tecno|"
                   r"honor|itel|nokia|aquos|smartphone|hp android"),
    "smart_tv": r"smart tv|android tv|google tv|led tv|oled tv|qled tv|\btv\b",
    # "router": r"router|wifi|repeater|access point",
}

# words for acc
ACC = (r"case|casing|cover|softcase|tempered|anti ?gores|screen ?guard|protector|kabel|cable|holder|stand|"
       r"tripod|pouch|strap|stiker|sticker|skin|hydrogel|sarung|tools?|opening|\blem\b|glass|kaca|\blcd\b|"
       r"touchscreen|baterai|battery|sim ?card|simcard|kartu|esim|perdana|voucher|eshop|keyboard|charger|"
       r"adaptor|adapter|compatible|pelindung|\bpen\b|pencil|stylus|bracket|braket|remote|antena|antenna|"
       r"dongle|\bbox\b|\bstb\b|set ?top|sparepart|spare part|flexi|housing|backdoor|tutup|casan|garskin|"
       r"film|\bring\b|lanyard|bumper|folio|sleeve|\btas\b|\bbag\b|terminal|blok|laptop")

# product aspects
ASPEK_PRODUK = (r"baterai|batre|daya|kapasitas|ngecas|nge-?charge|charging|fast ?charge|cepat (penuh|ngisi|panas)|"
                r"lambat|\blag\b|ngelag|panas|layar|gambar|warna|tampilan|resolusi|jernih|suara|speaker|bass|"
                r"sinyal|wifi|koneksi|bluetooth|kamera|foto|video|performa|kencang|ngebut|"
                r"kualitas|bahan|kokoh|kuat|awet|ringan|berat|mulus|rusak|cacat|lecet|penyok|pecah|mati|error|"
                r"pasang|instal|setting|setup|mudah dipakai|ribet|worth|dus|body|desain|slim|tipis")

# aspect related to service, shipping, and price (for fallback)
ASPEK_LAYANAN = r"packing|kemasan|garansi|pengiriman|kirim|kurir|seller|penjual|respon|harga|murah|mahal"


def load():
    df = pd.read_csv(CSV_PATH)
    df["product_name"] = df["product_name"].astype(str).apply(html.unescape)
    df["review_text"] = df["review_text"].astype(str).str.strip()
    df = df[df["product_category"].isin(["Handphone & Tablet", "Elektronik"])]
    return df


def assign_type(name: str):
    if re.search(ACC, name, flags=re.I):
        return None
    for t, kw in TYPES.items():
        if re.search(kw, name, flags=re.I):
            return t
    return None


def main():
    df = load()

    # set product product_id
    prod = df[["product_id", "product_name"]].drop_duplicates("product_id").copy()
    prod["type"] = prod["product_name"].apply(assign_type)
    prod = prod.dropna(subset=["type"])
    df = df.merge(prod[["product_id", "type"]], on="product_id", how="inner")

    # product catalog
    cat = (df.groupby(["product_id", "product_name", "type"])
             .agg(n_reviews=("review_text", "size"),
                  price=("product_price", "median"),
                  avg_rating=("rating", "mean"),
                  url=("product_url", "first"))
             .reset_index())
    cat = cat[cat["n_reviews"] >= 10].sort_values(["type", "n_reviews"], ascending=[True, False])
    cat.to_csv("data/catalog_products.csv", index=False, encoding="utf-8")

    # cleaning review text
    df = df.drop_duplicates(subset="review_text")
    ln = df["review_text"].str.len()
    good = df[(ln >= MIN_LEN) & (ln <= MAX_LEN)
              & df["review_text"].str.contains(ASPEK_PRODUK, case=False, regex=True)]
    low = df[(df["rating"] <= 3) & (ln >= MIN_LEN_LOW_RATING) & (ln <= MAX_LEN)]

    picked = []
    for t in TYPES:
        g = good[good["type"] == t]
        lo = low[low["type"] == t]

        # low rating , maks 20 per type, random sampling
        part_low = lo.sample(min(len(lo), 20), random_state=SEED)

       
        pool = g[~g.index.isin(part_low.index)].sample(frac=1, random_state=SEED)
        need = max(0, TARGET_PER_TYPE - len(part_low))
        for cap in (MAX_PER_PRODUCT, 4, 5, 6, 8):          # up to 8 review per product, if not enough, fallback to 6,5,4,3
            rest = pool.groupby("product_id").head(cap)
            if len(rest) >= need:
                break
        part_rest = rest.head(need)

        part = pd.concat([part_low, part_rest])

        # Fallback for lenient selection if not enough reviews with product aspects
        if len(part) < TARGET_PER_TYPE:
            lenient = df[(df["type"] == t) & (ln >= 30) & (ln <= MAX_LEN)
                         & (df["review_text"].str.contains(ASPEK_PRODUK + "|" + ASPEK_LAYANAN,
                                                           case=False, regex=True))]
            lenient = lenient[~lenient.index.isin(part.index)].sample(frac=1, random_state=SEED)
            lenient = lenient.groupby("product_id").head(6)
            part = pd.concat([part, lenient.head(TARGET_PER_TYPE - len(part))])

        picked.append(part)
        print(f"{t:11s} produk={g['product_id'].nunique():3d}  kandidat={len(g):4d}  "
              f"terpilih={len(part):3d} (rating<=3: {len(part_low)})")

    out = pd.concat(picked).sample(frac=1, random_state=SEED)   # random shuffle

    tasks = [{
        "data": {
            "text": r.review_text,
            "product_type": r.type,
            "product_id": int(r.product_id),
            "rating": int(r.rating),
        }
    } for r in out.itertuples()]

    with open("data/tasks.json", "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    print(f"\nTotal tasks : {len(tasks)}  -> data/tasks.json")
    print(f"Katalog     : {len(cat)} produk (>=10 review) -> data/catalog_products.csv")
    print("Jumlah produk unik di tasks:", out['product_id'].nunique())


if __name__ == "__main__":
    main()