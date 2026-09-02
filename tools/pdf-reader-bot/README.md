# pdf2speech

Turn any PDF in this repo into `.wav` audio tracks you can listen to on the
commute — either from the command line, or from a browser UI that lists
every PDF found in the repo and lets you pick one.

Pipeline: `pdftotext` (extract) -> cleanup (de-hyphenate, strip page breaks)
-> chunk into tracks -> Windows Speech API (SAPI) -> `.wav` files + an
`.m3u` playlist.

## Setup

Julia is installed (portable juliaup, added to your user PATH — open a new
terminal if `julia` isn't found yet). Two more things are already on this
machine and required: `pdftotext.exe` (from MiKTeX) and Windows' built-in
SAPI speech synthesizer.

For the CLI only, no extra packages are needed. For the web UI, install once:

```powershell
julia tools/pdf-reader-bot/install_deps.jl
```

(installs `HTTP.jl` and `JSON3.jl`)

## Web UI

```powershell
julia tools/pdf-reader-bot/server.jl
```

Then open <http://127.0.0.1:8787>. It scans the whole repo for `*.pdf`
files, groups them by course in a sidebar, and for whichever one you pick:
choose a voice/rate, click **Generate audio**, and it converts in the
background (progress bar while it runs). Once done you get an in-browser
player with per-track navigation, a downloadable `.m3u` playlist, and a
transcript link. A green dot marks notes that already have generated audio
so you don't regenerate by accident. The PDF itself is shown side-by-side
in a preview pane (via the browser's built-in PDF viewer) so you can follow
along or jump to a page while the audio plays.

Generated audio is cached under `tools/pdf-reader-bot/audio/<note-slug>/` —
copy that folder to your phone for offline listening.

By default the server only listens on `127.0.0.1` (this PC only). Pass a
different port with a first argument, or open it to your home network with
a second argument (no login/auth on this server — only do this on a network
you trust):

```powershell
julia tools/pdf-reader-bot/server.jl 8787 0.0.0.0
```

Then on your phone (same Wi-Fi), browse to `http://<your-pc's-LAN-IP>:8787`.

## CLI Usage

```powershell
# List available voices
julia pdf2speech.jl --list-voices

# Convert a PDF
julia pdf2speech.jl "..\..\cse5830-bayesian-ml\notes\week1\intro.pdf" --voice "Microsoft Zira Desktop" --rate 1
```

Output goes to `audio/<pdf-name>/` by default: `track_001.wav`,
`track_002.wav`, ..., `playlist.m3u`, and `transcript.txt` (the cleaned text,
useful for skimming or re-reading later).

### Options

| Flag | Meaning | Default |
|---|---|---|
| `--voice NAME` | SAPI voice, e.g. `Microsoft David Desktop` | system default |
| `--rate N` | speech rate, -10 (slow) to 10 (fast) | 0 |
| `--max-chars N` | characters per track before splitting | 4000 |
| `--workers N` | parallel SAPI worker processes | half the CPU threads, max 4 |
| `--outdir DIR` | output directory | `audio/<pdf-basename>` |
| `--list-voices` | print installed voices and exit | — |

## Notes

- Works offline once generated — good for the subway/no-signal drives.
- Scanned PDFs (image-only, no text layer) won't extract anything; you'd
  need OCR first (e.g. `ocrmypdf`) before this will work.
- Math-heavy notes read awkwardly as raw text (LaTeX source, symbols) since
  SAPI just reads characters literally — this works best on prose-heavy
  PDFs (papers, textbook chapters), less well on slide decks full of
  equations.

## Audio generation speed

Each PDF is split into ~4000-character chunks, one `.wav` track per chunk.
Two things make this fast:

- **Batching per worker.** Spawning a fresh `powershell.exe` process for
  every chunk means paying PowerShell startup + `System.Speech` assembly
  load (a few hundred ms, fixed cost) *per chunk*. Instead, each worker gets
  one PowerShell process that creates a single `SpeechSynthesizer` and loops
  over its whole slice of chunks, so that fixed cost is paid once per
  worker, not once per track.
- **Parallel workers.** SAPI synthesis-to-file doesn't play audio out loud,
  so it isn't limited to real-time — it's mostly CPU-bound. Multiple
  independent `SpeechSynthesizer` processes can run at once (each writing
  its own `.wav`), so chunks are split across `--workers` processes
  (default: half your CPU threads, capped at 4) that run concurrently.

For a long PDF this is typically several times faster than the old
one-process-per-chunk approach. If you want more or fewer workers (e.g. to
leave CPU headroom for other work), pass `--workers N` on the CLI; the web
UI always uses the default.
