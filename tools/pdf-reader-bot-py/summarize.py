#!/usr/bin/env python3
#
# summarize.py -- builds a lightweight, fully offline extractive summary of
# a PDF's text: scores each sentence by how many frequent, non-stopword
# words it contains, keeps the top-scoring sentences, then re-orders them
# back to their original position in the document. No external services,
# API keys, or ML models -- same offline design as quiz.py.
#
# Usage:
#   python summarize.py <path-to.pdf> [--sentences N] [--ratio F] [--out FILE]

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

_STOPWORDS = set("""
the a an and or but if then else when at by for with about against between
into through during before after above below to from up down in out on off
over under again further once here there all any both each few more most
other some such no nor not only own same so than too very s t can will just
don should now is are was were be been being have has had do does did doing
this that these those of as it its you your yours we our ours they them
their theirs he she his her him himself herself itself which who whom what
where why how also may might must shall would could one two three
""".split())

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']{2,}")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str):
    flat = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in _SENTENCE_RE.split(flat) if s.strip()]


def _words(sentence: str):
    return [w.lower() for w in _WORD_RE.findall(sentence) if w.lower() not in _STOPWORDS]


def _overlap(a_words, b_words) -> float:
    """Jaccard similarity between two word sets, used to skip near-duplicate
    sentences (common with repeated definitions/restatements in notes)."""
    a, b = set(a_words), set(b_words)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def generate_summary(text: str, n_sentences: int = None, ratio: float = 0.15):
    """Extractive summary of `text`: each candidate sentence is scored by
    the frequency-weighted "importance" of the words it contains (a
    classic offline word-frequency/Luhn-style heuristic), the top-scoring,
    non-redundant sentences are kept, and returned back in their original
    document order (not score order) for readability. Returns [] if the
    text is too short/sparse to summarize."""
    sentences = [s for s in _sentences(text) if len(s) >= 30 and len(s.split()) >= 5]
    if len(sentences) < 4:
        return []

    freq = Counter(w for s in sentences for w in _words(s))
    if not freq:
        return []
    top_count = freq.most_common(1)[0][1]
    weight = {w: c / top_count for w, c in freq.items()}

    scored = []
    for i, s in enumerate(sentences):
        ws = _words(s)
        if not ws:
            continue
        # Divide by sqrt(len) rather than len so score isn't dominated by
        # short sentences that happen to be all "important" words.
        score = sum(weight.get(w, 0) for w in ws) / len(ws) ** 0.5
        scored.append((score, i, s, ws))
    if not scored:
        return []

    if n_sentences is None:
        n_sentences = max(3, min(12, round(len(sentences) * ratio)))
    n_sentences = min(n_sentences, len(scored))

    scored.sort(key=lambda t: t[0], reverse=True)

    picked = []
    for score, i, s, ws in scored:
        if len(picked) >= n_sentences:
            break
        if any(_overlap(ws, p_ws) > 0.6 for _, _, _, p_ws in picked):
            continue
        picked.append((score, i, s, ws))

    picked.sort(key=lambda t: t[1])
    return [s for _, _, s, _ in picked]


def summarize_pdf(pdf_path: str, n_sentences: int = None, ratio: float = 0.15):
    import pdf2speech as p2s

    paragraphs = p2s.extract_paragraphs(pdf_path)
    if not paragraphs:
        raise RuntimeError("No extractable text found (the PDF may be scanned images without OCR).")
    return generate_summary(p2s.full_text(paragraphs), n_sentences=n_sentences, ratio=ratio)


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Build an offline extractive summary of a PDF.")
    parser.add_argument("pdf", help="path to the PDF")
    parser.add_argument("--sentences", type=int, default=None,
                         help="number of summary sentences (default: ~15%% of the document, clamped to 3-12)")
    parser.add_argument("--ratio", type=float, default=0.15,
                         help="fraction of sentences to keep when --sentences is not given")
    parser.add_argument("--out", default="", help="also write the summary to this file")
    return parser.parse_args(argv)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    args = parse_args(sys.argv[1:])

    print(f"Extracting text from {args.pdf} ...")
    sentences = summarize_pdf(args.pdf, n_sentences=args.sentences, ratio=args.ratio)
    if not sentences:
        sys.exit("Text too short/sparse to summarize (the PDF may be scanned images without OCR).")

    summary = "\n\n".join(f"- {s}" for s in sentences)
    print(f"\nSummary ({len(sentences)} sentence(s)):\n")
    print(summary)

    if args.out:
        Path(args.out).write_text(summary + "\n", encoding="utf-8")
        print(f"\nWritten to {args.out}")


if __name__ == "__main__":
    main()
