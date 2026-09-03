# pdf2speech (Python port)

Python port of [`tools/pdf-reader-bot`](../pdf-reader-bot) (the Julia version).
Same idea, same web UI, same on-disk audio format — just a different
implementation, kept as a separate tool so the working Julia version stays
untouched. Turn any PDF in this repo into `.wav` audio tracks you can listen
to on the commute — either from the command line, or from a browser UI that
lists every PDF found in the repo, plays the audio, and shows the PDF
alongside it, synced to whichever track is currently playing.

Pipeline: PyMuPDF (extract text, page-aware) -> cleanup (de-hyphenate, strip
page breaks) -> chunk into tracks -> pyttsx3 / Windows SAPI -> `.wav` files +
an `.m3u` playlist.

## Setup

```powershell
pip install -r tools/pdf-reader-bot-py/requirements.txt
```

That installs `flask` (web UI), `pymupdf` (PDF text extraction), `pyttsx3`
(text-to-speech), and `pywin32` (needed by pyttsx3's Windows SAPI backend).

## Web UI

```powershell
python tools/pdf-reader-bot-py/server.py
```

Then open <http://127.0.0.1:8787>. It scans the whole repo for `*.pdf`
files, groups them by course in a sidebar, and for whichever one you pick:
choose a voice/rate, click **Generate audio**, and it converts in the
background (progress bar while it runs). Once done you get an in-browser
player with per-track navigation, a downloadable `.m3u` playlist, and a
transcript link. A green dot marks notes that already have generated audio
so you don't regenerate by accident.

The PDF itself is shown side-by-side in a preview pane (via the browser's
built-in PDF viewer), and it follows along automatically: each track
remembers which PDF page its text started on, so as playback advances from
track to track the preview jumps to the matching page (shown next to each
track in the list, and in the pane header). It's a best-effort sync at
chunk granularity, not per-sentence.

Generated audio is cached under `tools/pdf-reader-bot-py/audio/<note-slug>/`
— copy that folder to your phone for offline listening.

### Progress tracking + quizzes

Each note has a **"Mark as seen"** toggle (also set automatically when you
listen all the way through a note's tracks), so the sidebar shows a ✓ Seen
badge next to ones you've already been through, and a running "N / M notes
seen" count with a progress bar up top. State is stored in
`tools/pdf-reader-bot-py/progress.json` (per-machine, not committed).

Once a note has generated audio, a **"Take quiz"** button builds a short
fill-in-the-blank quiz from that chapter's transcript — good for a quick
retention check after listening. This is done entirely offline with simple
heuristics (pick a sentence, blank out a keyword, offer it plus three
decoy keywords pulled from elsewhere in the same chapter) — no external
API or model, so quality is "spot-check," not something like an LLM-written
quiz. See `quiz.py` if you want to improve the heuristics later.

By default the server only listens on `127.0.0.1` (this PC only). Pass a
different port with a first argument, or open it to your home network with
a second argument (no login/auth on this server — only do this on a network
you trust):

```powershell
python tools/pdf-reader-bot-py/server.py 8787 0.0.0.0
```

Then on your phone (same Wi-Fi), browse to `http://<your-pc's-LAN-IP>:8787`.

## CLI Usage

```powershell
# List available voices (id + name -- pyttsx3 selects by id, not name)
python pdf2speech.py --list-voices

# Convert a PDF
python pdf2speech.py "..\..\cse5830-bayesian-ml\notes\week1\intro.pdf" --rate 1
```

Output goes to `audio/<pdf-name>/` by default: `track_001.wav`,
`track_002.wav`, ..., `playlist.m3u`, and `transcript.txt` (the cleaned text,
useful for skimming or re-reading later).

### Options

| Flag | Meaning | Default |
|---|---|---|
| `--voice ID` | pyttsx3/SAPI voice id, from `--list-voices` | system default |
| `--rate N` | speech rate, -10 (slow) to 10 (fast) | 0 |
| `--max-chars N` | characters per track before splitting | 4000 |
| `--workers N` | parallel SAPI worker processes | half the CPU count, max 4 |
| `--outdir DIR` | output directory | `audio/<pdf-basename>` |
| `--list-voices` | print installed voices (id + name) and exit | — |

## Audio generation speed

Same approach as the Julia version: chunks are grouped across `--workers`
worker *processes* (default: half your CPU count, capped at 4), each
initializing one `pyttsx3` engine and looping through its whole slice of
chunks, instead of paying Python + SAPI engine startup cost per chunk. SAPI
synthesis-to-file isn't limited to real-time playback, so independent
worker processes render concurrently.

## Notes

- Works offline once generated — good for the subway/no-signal drives.
- Scanned PDFs (image-only, no text layer) won't extract anything; you'd
  need OCR first (e.g. `ocrmypdf`) before this will work.
- Math-heavy notes read awkwardly as raw text (LaTeX source, symbols) since
  SAPI just reads characters literally — this works best on prose-heavy
  PDFs (papers, textbook chapters), less well on slide decks full of
  equations.
- Voice quality here is limited by Windows SAPI. If you want noticeably
  better-sounding voices later, swapping `pyttsx3` for something like
  Piper (fast, fully local neural TTS) or `edge-tts` (free cloud voices)
  is a relatively contained change — it only touches `_worker` in
  `pdf2speech.py`, since everything else (chunking, page sync, the web UI)
  is voice-engine-agnostic.
