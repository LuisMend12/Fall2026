#!/usr/bin/env python3
#
# pdf2speech.py -- turn a PDF into spoken-word audio tracks for offline listening.
#
# Pipeline: PyMuPDF (extract, page-aware) -> text cleanup -> chunk into tracks
#           -> pyttsx3 / Windows SAPI -> .wav files
#
# Requires: pymupdf, pyttsx3, pywin32 (Windows SAPI voices) -- see requirements.txt
#
# Usage:
#   python pdf2speech.py <path-to.pdf> [options]
#
# Options:
#   --outdir DIR      output directory (default: ./audio/<pdf-basename>)
#   --voice ID        SAPI voice id/token -- see --list-voices for the list
#   --rate N          speech rate, -10 (slow) to 10 (fast), default 0
#   --max-chars N     characters per track before splitting, default 4000
#   --workers N       parallel SAPI worker processes, default: half the CPU count (max 4)
#   --list-voices     print installed voices (id + name) and exit
#
# Example:
#   python pdf2speech.py notes/week1/intro.pdf --rate 1

import argparse
import multiprocessing as mp
import os
import queue
import re
import sys
from pathlib import Path


def extract_paragraphs(pdf_path: str):
    """Paragraphs across the whole document as (page_number, text), 1-based
    pages, so playback can later be synced back to a page in a PDF viewer."""
    import pymupdf as fitz

    if not Path(pdf_path).is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        paragraphs = []
        for pnum, page in enumerate(doc, start=1):
            cleaned = clean_page_text(page.get_text())
            for p in cleaned.split("\n\n"):
                p = p.strip()
                if p:
                    paragraphs.append((pnum, p))
        return paragraphs
    finally:
        doc.close()


def clean_page_text(raw: str) -> str:
    text = re.sub(r"-\n(?=[a-z])", "", raw)           # de-hyphenate words split across lines
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)       # join wrapped lines within a paragraph
    text = re.sub(r"[ \t]{2,}", " ", text)             # collapse repeated spaces
    text = re.sub(r"\n{3,}", "\n\n", text)             # collapse excess blank lines
    return text.strip()


def full_text(paragraphs) -> str:
    return "\n\n".join(p for _, p in paragraphs)


def chunk_paragraphs(paragraphs, max_chars: int = 4000):
    """Groups paragraphs into <=max_chars chunks. Returns (chunks, chunk_pages)
    where chunk_pages[i] is the PDF page the i-th chunk's text starts on."""
    chunks, chunk_pages = [], []
    buf, length, start_page = [], 0, 0
    for pnum, p in paragraphs:
        if length > 0 and length + len(p) > max_chars:
            chunks.append("\n\n".join(buf) + "\n\n")
            chunk_pages.append(start_page)
            buf, length = [], 0
        if length == 0:
            start_page = pnum
        buf.append(p)
        length += len(p)
    if length > 0:
        chunks.append("\n\n".join(buf) + "\n\n")
        chunk_pages.append(start_page)
    return chunks, chunk_pages


def list_voices():
    import pyttsx3

    engine = pyttsx3.init()
    for v in engine.getProperty("voices"):
        print(f"{v.id}\t{v.name}")


def get_voices():
    import pyttsx3

    engine = pyttsx3.init()
    return [{"id": v.id, "name": v.name} for v in engine.getProperty("voices")]


def default_worker_count(n_chunks: int) -> int:
    cpu = os.cpu_count() or 4
    return max(1, min(4, cpu // 2, n_chunks))


def split_into_groups(n_items: int, n_groups: int):
    n_groups = max(1, min(n_groups, n_items))
    base, rem = divmod(n_items, n_groups)
    groups, start = [], 0
    for g in range(n_groups):
        size = base + (1 if g < rem else 0)
        if size == 0:
            continue
        groups.append(range(start, start + size))
        start += size
    return groups


def _rate_to_wpm(rate: int) -> int:
    # pyttsx3's `rate` property is words-per-minute (default ~200); our UI/CLI
    # keeps the old SAPI-style -10..10 scale, so map it onto wpm here.
    return max(60, 200 + rate * 15)


def _worker(items, voice: str, rate: int, progress_q):
    import pyttsx3

    engine = pyttsx3.init()
    if voice:
        engine.setProperty("voice", voice)
    engine.setProperty("rate", _rate_to_wpm(rate))
    for text, out_wav in items:
        engine.save_to_file(text, out_wav)
        engine.runAndWait()
        progress_q.put(1)


def synthesize_many(chunks, out_paths, voice: str = "", rate: int = 0, workers=None, on_progress=None):
    """Synthesizes chunks[i] -> out_paths[i] (same length, same order) using
    up to `workers` SAPI worker processes running concurrently. Two
    independent wins over one process per chunk: (1) the fixed cost of
    starting Python and initializing a pyttsx3/SAPI engine is paid `workers`
    times instead of once per chunk, since each worker owns one engine for
    its whole slice, and (2) multiple engine processes can render in
    parallel since SAPI synthesis-to-file isn't limited by real-time
    playback and each writes its own wav file. `on_progress(done_count)`,
    if given, is called as tracks complete."""
    assert len(chunks) == len(out_paths)
    n = len(chunks)
    if n == 0:
        return
    if workers is None:
        workers = default_worker_count(n)

    groups = split_into_groups(n, workers)
    progress_q = mp.Queue()
    procs = []
    for rng in groups:
        items = [(chunks[i], out_paths[i]) for i in rng]
        p = mp.Process(target=_worker, args=(items, voice, rate, progress_q))
        p.start()
        procs.append(p)

    done = 0
    while done < n:
        try:
            progress_q.get(timeout=0.5)
            done += 1
            if on_progress:
                on_progress(done)
        except queue.Empty:
            if not any(p.is_alive() for p in procs):
                break

    # A worker can exit right after its last put() before the item is fully
    # flushed through the queue's pipe -- give it a brief grace window.
    while done < n:
        try:
            progress_q.get(timeout=0.5)
            done += 1
        except queue.Empty:
            break
    if on_progress:
        on_progress(done)

    for p in procs:
        p.join()

    for p in procs:
        if p.exitcode not in (0, None):
            raise RuntimeError(f"Speech synthesis worker failed (exit code {p.exitcode})")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Turn a PDF into spoken-word audio tracks.")
    parser.add_argument("pdf", nargs="?", help="path to the PDF")
    parser.add_argument("--outdir", default="")
    parser.add_argument("--voice", default="", help="SAPI voice id (see --list-voices)")
    parser.add_argument("--rate", type=int, default=0)
    parser.add_argument("--max-chars", dest="max_chars", type=int, default=4000)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--list-voices", dest="list_voices", action="store_true")
    return parser.parse_args(argv)


def main():
    args = parse_args(sys.argv[1:])

    if args.list_voices:
        list_voices()
        return

    if not args.pdf:
        sys.exit("Usage: python pdf2speech.py <path-to.pdf> [--voice ID] [--rate N] "
                  "[--outdir DIR] [--max-chars N] [--workers N] | --list-voices")

    print(f"Extracting text from {args.pdf} ...")
    paragraphs = extract_paragraphs(args.pdf)
    if not paragraphs:
        sys.exit("No extractable text found (the PDF may be scanned images without OCR).")

    outdir = Path(args.outdir) if args.outdir else Path("audio") / Path(args.pdf).stem
    outdir.mkdir(parents=True, exist_ok=True)

    (outdir / "transcript.txt").write_text(full_text(paragraphs), encoding="utf-8")

    chunks, chunk_pages = chunk_paragraphs(paragraphs, max_chars=args.max_chars)
    n = len(chunks)
    workers = args.workers if args.workers > 0 else default_worker_count(n)
    print(f"Split into {n} track(s). Synthesizing with SAPI ({workers} worker(s) in parallel)...")

    track_names = [f"track_{i + 1:03d}.wav" for i in range(n)]
    out_paths = [str(outdir / name) for name in track_names]

    def progress(d):
        print(f"\r  [{d}/{n}] tracks done", end="", flush=True)

    synthesize_many(chunks, out_paths, voice=args.voice, rate=args.rate, workers=workers, on_progress=progress)
    print()

    (outdir / "playlist.m3u").write_text("\n".join(track_names) + "\n", encoding="utf-8")

    print(f"\nDone. Audio tracks + playlist.m3u written to: {outdir}")
    print("Copy that folder to your phone and queue playlist.m3u for the commute.")


if __name__ == "__main__":
    main()
