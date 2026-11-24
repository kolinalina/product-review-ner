# Labeling Guideline: Aspect NER for Indonesian Electronics Reviews

**Goal:** mark the parts of a review that talk about a specific aspect of the product or the purchase, so a model can later extract them and summarize what buyers say about each product.

**Data:** Tokopedia reviews (Indonesian) for smartphones, tablets, power banks and smart TVs.

---

## 1. General rules

1. **Label short phrases, not whole sentences.** Include the aspect word and its opinion: `suara jernih`, `baterai boros`, `packing rapi`.
2. **Skip filler words** at the edges of a span: `banget`, `sih`, `nih`, `pokoknya`. Do not include punctuation or emojis.
3. **Keep negations inside the span:** `tidak lag`, `gak panas`, `nggak ribet`.
4. **One phrase, one label.** No overlapping spans.
5. **Split different aspects** that are joined by a comma or "dan": `layar jernih` / `baterai awet` are two spans.
6. **Generic praise gets no label:** `barang bagus`, `mantap`, `sesuai pesanan`, `recommended`. If a review has no aspect, leave it empty and click Submit.
7. **Do not label the product name or brand.** There is no product label in this scheme.
8. **When unsure, make a decision, write it down in the "Decisions log" below, and stay consistent.** Consistency matters more than being perfect.

---

## 2. Labels

| Label | Use when the phrase is about... | Examples |
|---|---|---|
| `BATERAI_DAYA` | battery life, capacity, charging speed, power output | `baterai awet`, `ngecas cepat`, `kapasitas sesuai`, `daya kuat` |
| `PERFORMA` | speed, lag, heat, smoothness | `ngebut`, `agak lag`, `gak panas`, `lancar buat main game` |
| `KUALITAS_FISIK` | build, materials, physical condition, defects | `bahan kokoh`, `mulus`, `ada lecet`, `body tipis` |
| `LAYAR_TAMPILAN` | screen, picture, colors, brightness | `gambar tajam`, `warna bagus`, `layar terang` |
| `SUARA` | sound, speaker, volume | `suara jernih`, `speaker kurang kencang` |
| `KONEKSI` | signal, WiFi, Bluetooth, ports | `wifi stabil`, `sinyal kuat`, `bluetooth sering putus` |
| `KEMUDAHAN` | setup, installation, ease of use | `mudah dipasang`, `setting gampang`, `ribet` |
| `HARGA` | price, value for money | `harga terjangkau`, `worth it`, `agak mahal` |
| `PENGIRIMAN_LAYANAN` | packing, shipping, courier, seller service, warranty | `packing aman`, `pengiriman cepat`, `seller responsif`, `garansi resmi` |

---

## 3. Tricky cases (decide by what is being described)

| Phrase | Label | Why |
|---|---|---|
| `cepat ngecas` | `BATERAI_DAYA` | it describes charging |
| `cepat sampai` | `PENGIRIMAN_LAYANAN` | it describes shipping |
| `cepat loading` / `responsif` (device) | `PERFORMA` | it describes device speed |
| `seller responsif` | `PENGIRIMAN_LAYANAN` | it describes service |
| `suara tv jernih` | `SUARA` | sound, not screen |
| `layar tv bagus` | `LAYAR_TAMPILAN` | screen, not build |
| `packing rapi` | `PENGIRIMAN_LAYANAN` | packaging belongs to the purchase |
| `body kokoh` / `tidak mudah lecet` | `KUALITAS_FISIK` | physical build |
| `wifi lancar` | `KONEKSI` | connectivity, not performance |

**Not labeled for now:** authenticity claims like `original`, `segel`, `asli`. If they turn out to be very frequent after the first 50 reviews, we may add a new label.

---

## 4. Worked examples

**Review:** `Layar jernih tapi baterai boros, packing rapi dan pengiriman cepat`

| Span | Label |
|---|---|
| `Layar jernih` | `LAYAR_TAMPILAN` |
| `baterai boros` | `BATERAI_DAYA` |
| `packing rapi` | `PENGIRIMAN_LAYANAN` |
| `pengiriman cepat` | `PENGIRIMAN_LAYANAN` |

**Review:** `Barang bagus, mantap, sesuai pesanan` → **no labels** (generic).

**Review:** `Ngecas cepat banget, gak panas, harga murah` →
`Ngecas cepat` = `BATERAI_DAYA`, `gak panas` = `PERFORMA`, `harga murah` = `HARGA`.

---

## 5. Workflow

1. Open Label Studio, **Label All Tasks**.
2. Pick a label with the number keys (1-9), then select the phrase.
3. Click **Submit**.
4. **First pass: 50 reviews.** Stop, review this guideline, update the log below, then continue to 300.
5. After a few days, **re-label about 30 reviews** without looking at your old answers. Compare them to measure consistency (Cohen's kappa).

---

## 6. Decisions log

Add a line whenever you make a rule for a confusing case.

- _(example)_ `garansi resmi` is labeled `PENGIRIMAN_LAYANAN`.
-
-