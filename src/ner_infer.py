import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

MODEL_DIR = "models/ner_model"
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForTokenClassification.from_pretrained(MODEL_DIR).eval()
id2label = {int(k): v for k, v in model.config.id2label.items()}


def bio_to_spans(tokens, tags):
    spans, cur = [], None
    for tok, tag in zip(tokens, tags):
        if tag.startswith("B-"):
            if cur:
                spans.append(cur)
            cur = [tag[2:], [tok]]
        elif tag.startswith("I-") and cur and cur[0] == tag[2:]:
            cur[1].append(tok)
        else:
            if cur:
                spans.append(cur)
            cur = None
    if cur:
        spans.append(cur)
    return [(label, " ".join(words)) for label, words in spans]


def extract_aspects(text):
    words = text.split()
    enc = tokenizer(words, is_split_into_words=True, truncation=True,
                    max_length=128, return_tensors="pt")
    with torch.no_grad():
        pred = model(**enc).logits[0].argmax(-1).tolist()
    tags, prev = [], None
    for idx, w in enumerate(enc.word_ids()):
        if w is not None and w != prev:
            tags.append(id2label[pred[idx]])
        prev = w
    return bio_to_spans(words[:len(tags)], tags)


if __name__ == "__main__":
    for s in ["Baterai awet banget tapi layarnya agak redup, packing rapi dan pengiriman cepat",
              "Suara jernih, harga murah, barang original"]:
        print(s, "->", extract_aspects(s))