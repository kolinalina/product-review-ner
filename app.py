
import json
import math
from pathlib import Path

import pandas as pd
import streamlit as st

from query_parser import parse_query, rupiah

DATA_PATH = Path("data/product_aspects.json")
MAX_COMPARE = 3

TYPE_NAMES = {
    "smartphone": "Smartphone",
    "tablet": "Tablet",
    "powerbank": "Power bank",
    "smart_tv": "Smart TV",
}
ASPECT_NAMES = {
    "BATERAI_DAYA": "Baterai & daya",
    "PERFORMA": "Performa",
    "KUALITAS_FISIK": "Kualitas fisik & desain",
    "LAYAR_TAMPILAN": "Layar & tampilan",
    "SUARA": "Suara",
    "KONEKSI": "Koneksi",
    "KEMUDAHAN": "Kemudahan pakai",
    "HARGA": "Harga (menurut review)",
    "KEASLIAN_KESESUAIAN": "Keaslian & kesesuaian",
    "PENGIRIMAN_LAYANAN": "Pengiriman & layanan",
}
# Aspek yang benar-benar tentang produk (dipakai untuk ringkasan "paling sering dibahas")
PRODUCT_ASPECTS = ["BATERAI_DAYA", "PERFORMA", "KUALITAS_FISIK", "LAYAR_TAMPILAN", "SUARA", "KONEKSI", "KEMUDAHAN"]
TABLE_ORDER = PRODUCT_ASPECTS + ["HARGA", "KEASLIAN_KESESUAIAN", "PENGIRIMAN_LAYANAN"]


# ------------------------------------------------------------------ data & helper
@st.cache_data
def load_products():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def short(name, n=48):
    return name if len(name) <= n else name[: n - 1].rstrip() + "…"


def nice(x):
    """Bulatkan ke angka 'enak dibaca' (187.450 -> 200.000)."""
    if x <= 0:
        return 0
    mag = 10 ** int(math.floor(math.log10(x)))
    step = mag / 2
    return int(round(x / step) * step)


def make_ranges(products):
    """Bikin rentang harga dari sebaran harga produk di jenis itu (bukan angka tetap)."""
    prices = sorted(p["price"] for p in products if p["price"])
    ranges = []
    if len(prices) >= 6:
        cuts = sorted({nice(prices[len(prices) // 3]), nice(prices[2 * len(prices) // 3])})
        lo = 0
        for c in cuts:
            ranges.append((f"Di bawah {rupiah(c)}" if lo == 0 else f"{rupiah(lo)} – {rupiah(c)}", lo, c))
            lo = c
        ranges.append((f"Di atas {rupiah(lo)}", lo, math.inf))
    ranges.append(("Semua harga", 0, math.inf))

    out = []
    for label, lo, hi in ranges:
        is_all = label == "Semua harga"
        n = len(products) if is_all else sum(1 for p in products if p["price"] is not None and lo <= p["price"] < hi)
        if n:
            out.append((f"{label} ({n} produk)", lo, hi, is_all))
    return out


def top_product_aspects(p, k=3):
    items = [(a, p["aspects"][a]["n_reviews"]) for a in PRODUCT_ASPECTS if a in p["aspects"]]
    return sorted(items, key=lambda x: -x[1])[:k]


def priority_score(p, priorities):
    return sum(p["aspects"].get(a, {}).get("share", 0) for a in priorities)


# ------------------------------------------------------------------ state & callbacks
def clear_selection():
    for k in [k for k in st.session_state if str(k).startswith("sel_")]:
        del st.session_state[k]


def pick_type(t):
    st.session_state.type = t
    st.session_state.range = None
    st.session_state.custom = None
    st.session_state.priorities = []
    st.session_state.query_text = None
    st.session_state.note = None
    st.session_state.compare = False
    clear_selection()


def pick_range(i):
    st.session_state.range = i
    st.session_state.custom = None
    st.session_state.compare = False
    clear_selection()


def show_all_prices():
    st.session_state.custom = None
    st.session_state.range = -1          # -1 = "Semua harga" (opsi terakhir)
    st.session_state.compare = False
    clear_selection()


def go_compare():
    st.session_state.compare = True


def back_to_list():
    st.session_state.compare = False


def restart():
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def handle_query(text, types_available):
    """Proses kalimat bebas dari user dan simpan hasilnya ke state."""
    r = parse_query(text, types_available)
    s = st.session_state
    s.query_text = text
    s.compare = False
    s.range = None
    clear_selection()

    s.type = r["type"]
    s.priorities = r["aspects"]
    s.custom = None
    if r["lo"] is not None:
        s.custom = {"lo": r["lo"], "hi": r["hi"], "label": r["budget_label"]}

    parts = []
    if r["type"]:
        parts.append(f"jenis **{TYPE_NAMES[r['type']]}**")
    if r["budget_label"]:
        parts.append(f"budget **{r['budget_label']}**")
    if r["aspects"]:
        parts.append("prioritas **" + ", ".join(ASPECT_NAMES[a].lower() for a in r["aspects"]) + "**")
    note = ("Aku tangkap: " + ", ".join(parts) + ".") if parts else ""
    if r["unsupported"]:
        note += (" Catatan: aspek " + ", ".join(f"'{u}'" for u in r["unsupported"]) +
                 " belum bisa kubandingkan, karena belum ada di data review yang dianalisis.")
    s.note = note or None


# ------------------------------------------------------------------ halaman
st.set_page_config(page_title="Bandingin Elektronik", page_icon="🛒", layout="centered")
st.title("Bandingin Elektronik")
st.caption("Chatbot perbandingan produk berdasarkan review Tokopedia, diringkas oleh model NER IndoBERT hasil fine-tune sendiri.")

if not DATA_PATH.exists():
    st.error("File data/product_aspects.json belum ada. Jalankan dulu: python src/build_product_summary.py")
    st.stop()

products = load_products()
types_available = [t for t in TYPE_NAMES if any(p["type"] == t for p in products)]
state = st.session_state
state.setdefault("type", None)
state.setdefault("range", None)
state.setdefault("custom", None)
state.setdefault("priorities", [])
state.setdefault("query_text", None)
state.setdefault("note", None)
state.setdefault("compare", False)

with st.sidebar:
    st.button("Mulai ulang", on_click=restart, use_container_width=True)
    st.markdown("**Contoh yang bisa diketik**")
    st.caption("power bank 200 ribuan yang awet\n\ntablet 2-3 juta layar jernih\n\nsmart tv di bawah 5 juta suara bagus")
    st.markdown("**Tentang data**")
    st.caption(
        "Review Tokopedia, maksimal 20 review per produk. Aspek (baterai, layar, harga, dll) diekstrak model NER. "
        "Angka seperti 7/20 artinya 7 dari 20 review yang dianalisis menyebut aspek itu. "
        "Keluhan dideteksi dengan kamus kata negatif sederhana, bukan model sentimen."
    )

# kolom ketik ditaruh sebelum st.stop() supaya selalu tampil
typed = st.chat_input("Ketik, misalnya: power bank 200 ribuan yang awet")
if typed:
    handle_query(typed.strip(), types_available)

# --- sapaan + pilih jenis produk
with st.chat_message("assistant"):
    st.write("Halo! Kamu bisa **ketik langsung** apa yang kamu cari, atau pilih jenis produk lewat tombol.")
    if state.type is None and not state.query_text:
        cols = st.columns(len(types_available))
        for col, t in zip(cols, types_available):
            n = sum(1 for p in products if p["type"] == t)
            col.button(f"{TYPE_NAMES[t]}\n({n})", key=f"type_{t}", on_click=pick_type, args=(t,), use_container_width=True)

if state.query_text:
    with st.chat_message("user"):
        st.write(state.query_text)
    with st.chat_message("assistant"):
        if state.note:
            st.write(state.note)
        if state.type is None:
            st.write("Aku belum nangkep jenis produknya. Pilih salah satu ya, atau ketik lagi dengan menyebut jenisnya.")
            cols = st.columns(len(types_available))
            for col, t in zip(cols, types_available):
                col.button(TYPE_NAMES[t], key=f"retype_{t}", on_click=pick_type, args=(t,), use_container_width=True)
        elif not state.note:
            st.write("Aku belum menangkap detailnya, jadi kutampilkan semua produk jenis ini.")
elif state.type:
    with st.chat_message("user"):
        st.write(TYPE_NAMES[state.type])

if state.type is None:
    st.stop()

type_products = [p for p in products if p["type"] == state.type]
ranges = make_ranges(type_products)

# --- tentukan filter harga: dari kalimat user (custom) atau dari tombol
if state.custom is None and state.range is None:
    if state.query_text:
        state.range = -1                      # ketik tanpa budget -> semua harga
    else:
        with st.chat_message("assistant"):
            st.write("Oke. Budget kamu di kisaran berapa?")
            for i, (label, *_rest) in enumerate(ranges):
                st.button(label, key=f"range_{i}", on_click=pick_range, args=(i,), use_container_width=True)
        st.stop()

if state.custom is not None:
    c = state.custom
    lo, hi, is_all, label = c["lo"], c["hi"], False, c["label"]
    candidates = [p for p in type_products if p["price"] is not None and lo <= p["price"] <= hi]
else:
    label, lo, hi, is_all = ranges[state.range]
    candidates = [p for p in type_products if is_all or (p["price"] is not None and lo <= p["price"] < hi)]
    if not state.query_text:
        with st.chat_message("user"):
            st.write(label)

# urutan: kalau ada prioritas aspek, yang paling sering dibahas soal itu di atas
priorities = state.priorities
candidates = sorted(candidates, key=lambda p: (-priority_score(p, priorities), -p["n_reviews"]))

# --- daftar produk, pilih 2-3 untuk dibandingkan
if not state.compare:
    with st.chat_message("assistant"):
        if not candidates:
            st.write(f"Belum ada {TYPE_NAMES[state.type].lower()} di kisaran harga itu.")
            st.button("Tampilkan semua harga", on_click=show_all_prices)
            st.stop()
        msg = f"Ini {len(candidates)} produk yang cocok"
        if priorities:
            msg += ", diurutkan dari yang reviewnya paling sering membahas " + ", ".join(ASPECT_NAMES[a].lower() for a in priorities)
        st.write(msg + f". Centang 2 sampai {MAX_COMPARE} produk, lalu tekan **Bandingkan**.")
        for p in candidates:
            with st.container(border=True):
                st.markdown(f"**{short(p['name'], 70)}**")
                st.caption(f"{rupiah(p['price'])}  ·  rating {p['avg_rating']}  ·  {p['n_reviews']} review dianalisis")
                top = top_product_aspects(p)
                if top:
                    st.write("Paling sering dibahas: " + ", ".join(f"{ASPECT_NAMES[a]} ({n})" for a, n in top))
                else:
                    st.write("Belum ada aspek produk yang terdeteksi di review-nya.")
                for a in priorities:
                    info = p["aspects"].get(a)
                    if info:
                        st.caption(f"{ASPECT_NAMES[a]}: {info['n_reviews']}/{p['n_reviews']} review, mis. " + ", ".join(info["top_phrases"][:2]))
                st.checkbox("Bandingkan", key=f"sel_{p['product_id']}")

        selected = [p for p in candidates if state.get(f"sel_{p['product_id']}")]
        if len(selected) > MAX_COMPARE:
            st.warning(f"Maksimal {MAX_COMPARE} produk. Kurangi dulu pilihannya.")
        elif len(selected) < 2:
            st.info("Pilih minimal 2 produk.")
        st.button("Bandingkan", on_click=go_compare, disabled=not (2 <= len(selected) <= MAX_COMPARE), type="primary")
    st.stop()

# --- tabel perbandingan
selected = [p for p in candidates if state.get(f"sel_{p['product_id']}")]
with st.chat_message("assistant"):
    st.write("Ini perbandingannya:")

    names = [f"{i + 1}. {short(p['name'], 38)}" for i, p in enumerate(selected)]
    rows = {
        "Harga": [rupiah(p["price"]) if p["price"] else "-" for p in selected],
        "Rating rata-rata": [str(p["avg_rating"]) for p in selected],
        "Review dianalisis": [str(p["n_reviews"]) for p in selected],
    }
    for a in TABLE_ORDER:
        if any(a in p["aspects"] for p in selected):
            cells = []
            for p in selected:
                info = p["aspects"].get(a)
                if info:
                    cells.append(f"{info['n_reviews']}/{p['n_reviews']} · " + ", ".join(info["top_phrases"][:2]))
                else:
                    cells.append("-")
            rows[ASPECT_NAMES[a]] = cells
    rows["Keluhan yang muncul"] = [
        "; ".join(f"{c['phrase']} ({c['count']})" for c in p["complaints"][:3]) or "-" for p in selected
    ]
    st.table(pd.DataFrame(rows, index=names).T)

    st.markdown("**Ringkasan singkat**")
    for i, p in enumerate(selected):
        top = top_product_aspects(p, 2)
        if top:
            st.write(f"- Produk {i + 1}: review paling banyak membahas " + " dan ".join(ASPECT_NAMES[a].lower() for a, _ in top) + ".")
        else:
            st.write(f"- Produk {i + 1}: belum ada aspek produk yang terdeteksi dari review-nya.")

    st.caption("Dasar perbandingan: aspek yang paling sering dibahas dan frasa nyata dari review, bukan skor kualitas. "
               "Dengan maksimal 20 review per produk, anggap ini gambaran awal.")
    for i, p in enumerate(selected):
        if p.get("url"):
            st.link_button(f"Buka produk {i + 1} di Tokopedia", p["url"])
    st.button("Kembali ke daftar", on_click=back_to_list)