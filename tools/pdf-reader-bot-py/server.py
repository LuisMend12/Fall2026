#!/usr/bin/env python3
#
# server.py -- local web front end for pdf2speech (Python port of server.jl).
#
# Scans the repo for PDFs, lets you pick one in the browser, converts it to
# spoken-word audio (reusing pdf2speech.py), and serves the result back for
# in-browser playback / download, with the PDF shown alongside and
# page-synced to the currently playing track.
#
# Requires: flask, pymupdf, pyttsx3, pywin32 -- see requirements.txt
#   pip install -r requirements.txt
#
# Usage:
#   python server.py [port] [host]
#   then open http://127.0.0.1:<port> in a browser (default port 8787)

import json
import re
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request

import pdf2speech as p2s
import quiz as quizmod

HERE = Path(__file__).resolve().parent
REPO_ROOT = (HERE / ".." / "..").resolve()
AUDIO_ROOT = HERE / "audio"
PROGRESS_PATH = HERE / "progress.json"
SKIP_DIRS = {"audio", ".git", "node_modules", "__pycache__", "tools", ".vscode", ".venv"}

AUDIO_ROOT.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=None)

JOBS = {}
JOBS_LOCK = threading.Lock()

PROGRESS_LOCK = threading.Lock()


def _load_progress():
    if not PROGRESS_PATH.is_file():
        return {}
    try:
        return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


PROGRESS = _load_progress()


def is_seen(slug: str) -> bool:
    return bool(PROGRESS.get(slug, {}).get("seen"))


def slug_for(rel: str) -> str:
    s = str(Path(rel).with_suffix(""))
    s = re.sub(r"[\\/]", "__", s)
    s = re.sub(r"[^A-Za-z0-9_\-]", "_", s)
    return s


def existing_tracks(slug: str):
    d = AUDIO_ROOT / slug
    if not d.is_dir():
        return []
    return sorted(f.name for f in d.iterdir() if f.name.startswith("track_") and f.suffix == ".wav")


def has_existing_audio(slug: str) -> bool:
    return len(existing_tracks(slug)) > 0


def existing_pages(slug: str):
    path = AUDIO_ROOT / slug / "pages.json"
    if not path.is_file():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def list_notes():
    notes = []
    for pdf_path in REPO_ROOT.rglob("*.pdf"):
        rel_parts = pdf_path.relative_to(REPO_ROOT).parts
        if any(part in SKIP_DIRS or part.startswith(".") for part in rel_parts[:-1]):
            continue
        rel = "/".join(rel_parts)
        slug = slug_for(rel)
        notes.append({
            "id": slug,
            "path": rel,
            "course": rel_parts[0],
            "title": pdf_path.stem,
            "has_audio": has_existing_audio(slug),
            "seen": is_seen(slug),
        })
    notes.sort(key=lambda n: (n["course"], n["title"].lower()))
    return notes


def run_job(slug: str, pdf_path: str, voice: str, rate: int):
    try:
        paragraphs = p2s.extract_paragraphs(pdf_path)
        if not paragraphs:
            raise RuntimeError("No extractable text found (the PDF may be scanned images without OCR).")

        outdir = AUDIO_ROOT / slug
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "transcript.txt").write_text(p2s.full_text(paragraphs), encoding="utf-8")

        chunks, chunk_pages = p2s.chunk_paragraphs(paragraphs, max_chars=4000)
        n = len(chunks)
        with JOBS_LOCK:
            JOBS[slug]["total"] = n

        track_names = [f"track_{i + 1:03d}.wav" for i in range(n)]
        out_paths = [str(outdir / name) for name in track_names]

        def progress(d):
            with JOBS_LOCK:
                JOBS[slug]["done"] = d

        p2s.synthesize_many(chunks, out_paths, voice=voice, rate=rate, on_progress=progress)

        (outdir / "playlist.m3u").write_text("\n".join(track_names) + "\n", encoding="utf-8")
        (outdir / "pages.json").write_text(json.dumps(chunk_pages), encoding="utf-8")

        with JOBS_LOCK:
            JOBS[slug]["status"] = "done"
    except Exception as e:
        with JOBS_LOCK:
            JOBS[slug]["status"] = "error"
            JOBS[slug]["error"] = str(e)


@app.get("/")
def index():
    html = (HERE / "public" / "index.html").read_text(encoding="utf-8")
    return Response(html, mimetype="text/html")


@app.get("/api/notes")
def api_notes():
    return jsonify(list_notes())


@app.get("/api/voices")
def api_voices():
    try:
        return jsonify(p2s.get_voices())
    except Exception:
        return jsonify([])


@app.post("/api/convert")
def api_convert():
    body = request.get_json(force=True)
    rel = body["path"]
    voice = body.get("voice", "") or ""
    rate = int(body.get("rate", 0))

    full_pdf = (REPO_ROOT / rel).resolve()
    if not str(full_pdf).startswith(str(REPO_ROOT)):
        return jsonify({"error": "invalid path"}), 400
    if not full_pdf.is_file():
        return jsonify({"error": "PDF not found"}), 404

    slug = slug_for(rel)
    with JOBS_LOCK:
        if slug in JOBS and JOBS[slug].get("status") == "running":
            should_start = False
        else:
            JOBS[slug] = {"status": "running", "done": 0, "total": 0, "error": None}
            should_start = True

    if should_start:
        threading.Thread(target=run_job, args=(slug, str(full_pdf), voice, rate), daemon=True).start()

    return jsonify({"status": "started", "id": slug})


@app.get("/api/status")
def api_status():
    slug = request.args.get("id", "")
    if not slug:
        return jsonify({"error": "missing id"}), 400

    with JOBS_LOCK:
        job = dict(JOBS[slug]) if slug in JOBS else None

    if job is not None:
        tracks = existing_tracks(slug) if job["status"] == "done" else []
        pages = existing_pages(slug) if job["status"] == "done" else []
        return jsonify({**job, "tracks": tracks, "pages": pages})
    elif has_existing_audio(slug):
        return jsonify({"status": "done", "done": 0, "total": 0, "error": None,
                         "tracks": existing_tracks(slug), "pages": existing_pages(slug)})
    else:
        return jsonify({"status": "none", "done": 0, "total": 0, "error": None, "tracks": [], "pages": []})


@app.post("/api/progress")
def api_progress():
    body = request.get_json(force=True)
    slug = body.get("id", "")
    if not slug:
        return jsonify({"error": "missing id"}), 400
    seen = bool(body.get("seen", True))

    with PROGRESS_LOCK:
        entry = PROGRESS.setdefault(slug, {})
        entry["seen"] = seen
        entry["seen_at"] = datetime.now(timezone.utc).isoformat() if seen else None
        PROGRESS_PATH.write_text(json.dumps(PROGRESS, indent=2), encoding="utf-8")

    return jsonify({"id": slug, "seen": seen})


@app.get("/api/quiz")
def api_quiz():
    slug = request.args.get("id", "")
    if not slug:
        return jsonify({"error": "missing id"}), 400

    transcript_path = AUDIO_ROOT / slug / "transcript.txt"
    if not transcript_path.is_file():
        return jsonify({"error": "Generate audio first -- no transcript available yet."}), 404

    text = transcript_path.read_text(encoding="utf-8")
    questions = quizmod.generate_quiz(text)
    if not questions:
        return jsonify({"error": "This chapter's text is too short to build a quiz from."}), 422

    return jsonify({"questions": questions})


@app.get("/audio/<slug>/<path:file>")
def audio_file(slug, file):
    if ".." in file or "/" in file or "\\" in file:
        abort(400)
    path = AUDIO_ROOT / slug / file
    if not path.is_file():
        abort(404)
    if file.endswith(".wav"):
        mimetype = "audio/wav"
    elif file.endswith(".m3u"):
        mimetype = "audio/x-mpegurl"
    elif file.endswith(".txt"):
        mimetype = "text/plain; charset=utf-8"
    else:
        mimetype = "application/octet-stream"
    return Response(path.read_bytes(), mimetype=mimetype)


@app.get("/pdf")
def pdf_file():
    rel = request.args.get("path", "")
    if not rel:
        abort(400)
    full = (REPO_ROOT / rel).resolve()
    if not str(full).startswith(str(REPO_ROOT)) or full.suffix.lower() != ".pdf":
        abort(400)
    if not full.is_file():
        abort(404)
    return Response(full.read_bytes(), mimetype="application/pdf")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    print(f"Repo root:  {REPO_ROOT}")
    print(f"PDF Reader Bot (Python) running at http://{host}:{port}")
    if host != "127.0.0.1":
        print(f"Note: bound to {host} -- reachable by anyone on your network, with no auth.")
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
