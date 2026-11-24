# Aspect-Based Review Chatbot for Indonesian Electronics

Fine-tuned **IndoBERT NER** extracts product aspects (battery, display, sound, price, shipping, etc.) from Indonesian Tokopedia reviews, and powers a **Streamlit chatbot** that helps users compare electronics by what real buyers talk about.

> **Live demo:** `TODO: add Streamlit link`  |  **Model:** `TODO: add Hugging Face Hub link (optional)`

<!-- TODO: add a screenshot or GIF of the chatbot here -->
<!-- ![demo](docs/demo.gif) -->

## Why this project

Marketplace reviews are long, informal, and mostly generic ("barang bagus, pengiriman cepat"). Picking a product from them means reading dozens of reviews. This project turns raw reviews into **aspect profiles per product** (what buyers mention, with real phrases), so two or three products can be compared side by side.

## What I built

1. **Custom NER dataset.** Labeled aspect phrases in Label Studio with 10 labels. 274 reviews in total: 50 labeled manually, 224 pre-labeled by an LLM and then reviewed by me.
2. **Fine-tuned IndoBERT** (`indobenchmark/indobert-base-p1`) for token classification, with a product-level split.
3. **Aspect summaries per product.** The model runs over each product's reviews, producing aspect counts, representative phrases, and a simple complaint list.
4. **Streamlit chatbot** with guided buttons and free-text queries.

## Labels

| Label | Covers |
|---|---|
| `BATERAI_DAYA` | battery, capacity, charging, power output |
| `PERFORMA` | speed, lag, heat |
| `KUALITAS_FISIK` | build, condition, size, design |
| `LAYAR_TAMPILAN` | screen, picture, colors |
| `SUARA` | sound, speaker |
| `KONEKSI` | signal, WiFi, Bluetooth, ports |
| `KEMUDAHAN` | setup, ease of use |
| `HARGA` | price, value for money |
| `KEASLIAN_KESESUAIAN` | authenticity, matches description |
| `PENGIRIMAN_LAYANAN` | packing, shipping, seller service, warranty |

Full rules and edge cases are in [`GUIDELINE.md`](GUIDELINE.md).

## Data

- **Source:** Tokopedia Product Reviews 2025 (Kaggle), 65,543 reviews across 5,521 products, with at most 20 reviews per product. `TODO: add dataset link and check its license`. The raw CSV is not included in this repo.
- **Scope:** four product types: smartphone, tablet, power bank, smart TV. Accessories (cases, cables, screen protectors) are filtered out by name.
- **Sampling for labeling:** reviews that mention at least one product aspect, capped per product, so that labels beyond shipping and seller service get enough examples.

## Model and evaluation

| Setting | Value |
|---|---|
| Base model | `indobenchmark/indobert-base-p1` |
| Task | token classification (BIO tags, word level) |
| Split | train / validation / test, grouped by product (no product appears in two splits) |
| Training | 20 epochs, batch size 8, learning rate 3e-5, best checkpoint by validation F1 |
| Metrics | precision, recall, F1 with `seqeval` |

**Test results**

| Label | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| `TODO` | | | | |

Overall test F1: `TODO`. <!-- paste the classification_report from the notebook -->

## Chatbot

Run it, then either click through the buttons (product type, price range, pick 2-3 products) or type a query:

- `power bank 200 ribuan yang awet`
- `tablet 2-3 juta layar jernih`
- `smart tv di bawah 5 juta suara bagus`

Free-text queries are parsed with rules (product type, budget, aspect priorities), not with the NER model. Short queries are different from long reviews, and rules are more predictable for them. The NER model is used offline to summarize reviews, so the app itself needs no model at runtime.

The comparison table shows, for each product: price, rating, how many reviews mention each aspect (for example `7/20`), example phrases, and complaints.

## Repository structure

```
.
├── app.py                      # Streamlit chatbot
├── query_parser.py             # rule-based parser for typed queries
├── GUIDELINE.md                # labeling guideline
├── notebooks/
│   └── train_ner.ipynb         # IndoBERT fine-tuning (Colab)
├── src/
│   ├── prepare_data.py         # filter reviews, build labeling tasks and catalog
│   ├── prepare_batch2.py       # second labeling batch (product-aspect-rich reviews)
│   ├── ner_infer.py            # inference helper
│   └── build_product_summary.py# per-product aspect summaries
├── data/
│   ├── label_config.xml        # Label Studio config
│   ├── catalog_products.csv    # product catalog
│   └── product_aspects.json    # chatbot data
└── requirements.txt
```

## How to run

```bash
python -m venv .venv
.venv\Scripts\activate           # Windows (use source .venv/bin/activate on Mac/Linux)
pip install -r requirements.txt
streamlit run app.py
```

To reproduce the pipeline:

1. Put the Kaggle CSV in `data/`, then run `python src/prepare_data.py` to create labeling tasks.
2. Label in Label Studio (`label-studio start`, use `data/label_config.xml`) and export as JSON.
3. Train with `notebooks/train_ner.ipynb` (Colab, T4 GPU).
4. Put the model in `models/ner_model/`, then run `python src/build_product_summary.py`.

## Limitations

- **Small dataset.** About 270 labeled reviews. Rare labels (`KONEKSI`, `KEMUDAHAN`, `SUARA`) have few examples and are expected to be weak. F1 varies between runs because the test set is small.
- **LLM-assisted labels.** 224 of the 274 reviews were pre-labeled by an LLM and then checked by me, which may bias the labels toward the pre-labeler's style.
- **Reviews are overwhelmingly positive** (about 94% are 5-star), so "percent positive per aspect" is uninformative. The chatbot compares which aspects are discussed and shows real phrases instead of a quality score.
- **At most 20 reviews per product.** Treat comparisons as a first impression, not a verdict.
- **Complaint detection is a keyword heuristic**, not a sentiment model.
- **Limited coverage.** Only four product types, only a handful of smartphones, and no camera aspect (it is not in the label set).

## Possible next steps

- Label more data, especially for rare aspects, and measure inter-annotator agreement.
- Add aspect-level sentiment.
- Use fresher reviews through scraping to keep the catalog up to date.

## Tech stack

Python, Hugging Face Transformers, IndoBERT, Label Studio, seqeval, pandas, Streamlit

## License

`TODO: choose a license for the code`. The dataset follows its original license.