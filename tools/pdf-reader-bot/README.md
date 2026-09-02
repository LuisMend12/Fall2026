# pdf2speech

Turn a PDF into `.wav` audio tracks you can copy to your phone and listen to
on the commute.

Pipeline: `pdftotext` (extract) -> cleanup (de-hyphenate, strip page breaks)
-> chunk into tracks -> Windows Speech API (SAPI) -> `.wav` files + an
`.m3u` playlist.

No Julia packages required — only the standard library, plus two things
your machine already has: `pdftotext.exe` (from MiKTeX) and Windows' built-in
speech synthesizer.

## Setup

Julia itself isn't installed yet. Easiest path (Windows):

```powershell
choco install julia -y
```

or install [juliaup](https://github.com/JuliaLang/juliaup) directly. Then
open a new terminal so `julia` is on PATH.

## Usage

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
