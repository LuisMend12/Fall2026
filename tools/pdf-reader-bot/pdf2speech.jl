#!/usr/bin/env julia
#
# pdf2speech.jl — turn a PDF into spoken-word audio tracks for offline listening.
#
# Pipeline: pdftotext (extract) -> text cleanup -> chunk into tracks
#           -> Windows Speech API (System.Speech.Synthesis) -> .wav files
#
# Requires: `pdftotext` on PATH (ships with MiKTeX / poppler / Git for Windows)
#           and Windows (uses the built-in SAPI voices). No Julia packages needed.
#
# Usage:
#   julia pdf2speech.jl <path-to.pdf> [options]
#
# Options:
#   --outdir DIR      output directory (default: ./audio/<pdf-basename>)
#   --voice NAME       SAPI voice name, e.g. "Microsoft Zira Desktop"
#   --rate N           speech rate, -10 (slow) to 10 (fast), default 0
#   --max-chars N       characters per track before splitting, default 4000
#   --list-voices      print installed voices and exit
#
# Example:
#   julia pdf2speech.jl notes/week1/intro.pdf --voice "Microsoft Zira Desktop" --rate 1

function find_pdftotext()
    try
        run(pipeline(`pdftotext -v`, stdout=devnull, stderr=devnull))
        return "pdftotext"
    catch
        error("`pdftotext` not found on PATH. Install poppler-utils, or make sure " *
              "MiKTeX's bin directory (contains pdftotext.exe) is on PATH.")
    end
end

function extract_text(pdftotext::String, pdf_path::String)
    isfile(pdf_path) || error("PDF not found: $pdf_path")
    return read(`$pdftotext -layout $pdf_path -`, String)
end

function clean_text(raw::AbstractString)
    text = replace(raw, "\f" => "\n\n")               # page breaks -> paragraph breaks
    text = replace(text, r"-\n(?=[a-z])" => "")         # de-hyphenate words split across lines
    text = replace(text, r"(?<!\n)\n(?!\n)" => " ")     # join wrapped lines within a paragraph
    text = replace(text, r"[ \t]{2,}" => " ")           # collapse repeated spaces
    text = replace(text, r"\n{3,}" => "\n\n")           # collapse excess blank lines
    return String(strip(text))
end

function chunk_text(text::AbstractString; max_chars::Int=4000)
    paras = split(text, "\n\n")
    chunks = String[]
    buf = IOBuffer()
    len = 0
    for p in paras
        p = strip(p)
        isempty(p) && continue
        if len > 0 && len + length(p) > max_chars
            push!(chunks, String(take!(buf)))
            len = 0
        end
        write(buf, p, "\n\n")
        len += length(p)
    end
    len > 0 && push!(chunks, String(take!(buf)))
    return chunks
end

function list_voices()
    ps = """
    Add-Type -AssemblyName System.Speech
    (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() |
        ForEach-Object { \$_.VoiceInfo.Name }
    """
    run(`powershell -NoProfile -Command $ps`)
end

function synthesize(text::String, out_wav::String; voice::String="", rate::Int=0)
    text_path = tempname() * ".txt"
    write(text_path, text)
    ps_lines = String[
        "Add-Type -AssemblyName System.Speech",
        "\$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer",
        "\$synth.Rate = $rate",
    ]
    isempty(voice) || push!(ps_lines, "\$synth.SelectVoice('$(replace(voice, "'" => "''"))')")
    push!(ps_lines, "\$synth.SetOutputToWaveFile('$(replace(out_wav, "'" => "''"))')")
    push!(ps_lines, "\$text = Get-Content -Raw -Encoding UTF8 '$(replace(text_path, "'" => "''"))'")
    push!(ps_lines, "\$synth.Speak(\$text)")
    push!(ps_lines, "\$synth.Dispose()")

    ps_path = tempname() * ".ps1"
    write(ps_path, join(ps_lines, "\n"))
    try
        run(`powershell -NoProfile -ExecutionPolicy Bypass -File $ps_path`)
    finally
        rm(ps_path, force=true)
        rm(text_path, force=true)
    end
end

function parse_args(args)
    opts = Dict{String,Any}("rate" => 0, "voice" => "", "max_chars" => 4000, "outdir" => "")
    pdf = nothing
    i = 1
    while i <= length(args)
        a = args[i]
        if a == "--list-voices"
            opts["list_voices"] = true
        elseif a == "--outdir"
            i += 1; opts["outdir"] = args[i]
        elseif a == "--voice"
            i += 1; opts["voice"] = args[i]
        elseif a == "--rate"
            i += 1; opts["rate"] = parse(Int, args[i])
        elseif a == "--max-chars"
            i += 1; opts["max_chars"] = parse(Int, args[i])
        elseif pdf === nothing
            pdf = a
        else
            error("Unrecognized argument: $a")
        end
        i += 1
    end
    return pdf, opts
end

function main()
    pdf, opts = parse_args(ARGS)

    if get(opts, "list_voices", false)
        list_voices()
        return
    end

    pdf === nothing && error("Usage: julia pdf2speech.jl <path-to.pdf> [--voice NAME] [--rate N] [--outdir DIR] [--max-chars N] | --list-voices")

    pdftotext = find_pdftotext()
    println("Extracting text from $pdf ...")
    raw = extract_text(pdftotext, pdf)
    text = clean_text(raw)
    isempty(text) && error("No extractable text found (the PDF may be scanned images without OCR).")

    outdir = isempty(opts["outdir"]) ? joinpath("audio", splitext(basename(pdf))[1]) : opts["outdir"]
    mkpath(outdir)

    transcript_path = joinpath(outdir, "transcript.txt")
    write(transcript_path, text)

    chunks = chunk_text(text; max_chars=opts["max_chars"])
    println("Split into $(length(chunks)) track(s). Synthesizing with Windows SAPI...")

    playlist = IOBuffer()
    for (idx, chunk) in enumerate(chunks)
        track_name = "track_$(lpad(idx, 3, '0')).wav"
        out_wav = joinpath(outdir, track_name)
        println("  [$idx/$(length(chunks))] -> $track_name")
        synthesize(chunk, out_wav; voice=opts["voice"], rate=opts["rate"])
        write(playlist, track_name, "\n")
    end
    write(joinpath(outdir, "playlist.m3u"), String(take!(playlist)))

    println("\nDone. Audio tracks + playlist.m3u written to: $outdir")
    println("Copy that folder to your phone and queue playlist.m3u for the commute.")
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
