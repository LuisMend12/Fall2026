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
#   --workers N         parallel SAPI worker processes, default: half the CPU threads (max 4)
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

function extract_pages(pdftotext::String, pdf_path::String)
    isfile(pdf_path) || error("PDF not found: $pdf_path")
    raw = read(`$pdftotext -layout $pdf_path -`, String)
    return split(raw, "\f")   # pdftotext emits a form-feed between pages
end

function clean_page_text(raw::AbstractString)
    text = replace(raw, r"-\n(?=[a-z])" => "")          # de-hyphenate words split across lines
    text = replace(text, r"(?<!\n)\n(?!\n)" => " ")     # join wrapped lines within a paragraph
    text = replace(text, r"[ \t]{2,}" => " ")           # collapse repeated spaces
    text = replace(text, r"\n{3,}" => "\n\n")           # collapse excess blank lines
    return String(strip(text))
end

# Paragraphs across the whole document, each tagged with its 1-based PDF page
# number, so playback can later be synced back to a page in the PDF viewer.
function extract_paragraphs(pdftotext::String, pdf_path::String)
    pages = extract_pages(pdftotext, pdf_path)
    paragraphs = Tuple{Int,String}[]
    for (pnum, page) in enumerate(pages)
        cleaned = clean_page_text(page)
        for p in split(cleaned, "\n\n")
            p = strip(p)
            isempty(p) || push!(paragraphs, (pnum, p))
        end
    end
    return paragraphs
end

full_text(paragraphs::Vector{Tuple{Int,String}}) = join((p for (_, p) in paragraphs), "\n\n")

# Groups paragraphs into <=max_chars chunks. Returns (chunks, chunk_pages)
# where chunk_pages[i] is the PDF page the i-th chunk's text starts on.
function chunk_paragraphs(paragraphs::Vector{Tuple{Int,String}}; max_chars::Int=4000)
    chunks = String[]
    chunk_pages = Int[]
    buf = IOBuffer()
    len = 0
    start_page = 0
    for (pnum, p) in paragraphs
        if len > 0 && len + length(p) > max_chars
            push!(chunks, String(take!(buf)))
            push!(chunk_pages, start_page)
            len = 0
        end
        len == 0 && (start_page = pnum)
        write(buf, p, "\n\n")
        len += length(p)
    end
    if len > 0
        push!(chunks, String(take!(buf)))
        push!(chunk_pages, start_page)
    end
    return chunks, chunk_pages
end

function list_voices()
    ps = """
    Add-Type -AssemblyName System.Speech
    (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() |
        ForEach-Object { \$_.VoiceInfo.Name }
    """
    run(`powershell -NoProfile -Command $ps`)
end

function default_worker_count(n_chunks::Int)
    return clamp(Sys.CPU_THREADS ÷ 2, 1, min(4, n_chunks))
end

function split_into_groups(n_items::Int, n_groups::Int)
    n_groups = clamp(n_groups, 1, n_items)
    base, rem = divrem(n_items, n_groups)
    groups = UnitRange{Int}[]
    start = 1
    for g in 1:n_groups
        sz = base + (g <= rem ? 1 : 0)
        sz == 0 && continue
        push!(groups, start:(start + sz - 1))
        start += sz
    end
    return groups
end

# Builds one PowerShell script that speaks several chunks in a single process
# (one Add-Type + SpeechSynthesizer for the whole group), instead of paying
# PowerShell/assembly startup cost per chunk. Appends a line to `progress_path`
# after each track so the caller can poll fine-grained progress.
function worker_script(items::Vector{Tuple{String,String}}, progress_path::String; voice::String="", rate::Int=0)
    lines = String[
        "Add-Type -AssemblyName System.Speech",
        "\$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer",
        "\$synth.Rate = $rate",
    ]
    isempty(voice) || push!(lines, "\$synth.SelectVoice('$(replace(voice, "'" => "''"))')")
    for (text_path, out_wav) in items
        push!(lines, "\$synth.SetOutputToWaveFile('$(replace(out_wav, "'" => "''"))')")
        push!(lines, "\$synth.Speak((Get-Content -Raw -Encoding UTF8 '$(replace(text_path, "'" => "''"))'))")
        push!(lines, "Add-Content -Path '$(replace(progress_path, "'" => "''"))' -Value '1'")
    end
    push!(lines, "\$synth.Dispose()")
    return join(lines, "\n")
end

# Synthesizes `chunks` to `out_paths` (same length, same order) using up to
# `workers` SAPI processes running concurrently, each handling a contiguous
# slice of chunks in a single PowerShell invocation. Two independent wins over
# spawning one process per chunk: (1) the fixed cost of starting PowerShell
# and loading System.Speech is paid `workers` times instead of once per
# chunk, and (2) multiple SpeechSynthesizer processes can render in parallel
# since each writes to its own wav file. `on_progress(done_count)`, if given,
# is called as tracks complete (polled, so it may lag slightly behind reality).
function synthesize_many(chunks::Vector{String}, out_paths::Vector{String};
                          voice::String="", rate::Int=0,
                          workers::Int=default_worker_count(length(chunks)),
                          on_progress=nothing)
    @assert length(chunks) == length(out_paths)
    n = length(chunks)
    n == 0 && return

    tmp_dir = mktempdir()
    try
        groups = split_into_groups(n, workers)
        procs = Base.Process[]
        progress_files = String[]

        for (gi, rng) in enumerate(groups)
            items = Tuple{String,String}[]
            for i in rng
                text_path = joinpath(tmp_dir, "chunk_$(i).txt")
                write(text_path, chunks[i])
                push!(items, (text_path, out_paths[i]))
            end
            progress_path = joinpath(tmp_dir, "progress_$(gi).txt")
            write(progress_path, "")
            push!(progress_files, progress_path)

            script = worker_script(items, progress_path; voice=voice, rate=rate)
            ps_path = joinpath(tmp_dir, "worker_$(gi).ps1")
            write(ps_path, script)
            push!(procs, run(`powershell -NoProfile -ExecutionPolicy Bypass -File $ps_path`; wait=false))
        end

        count_done() = sum(pf -> count(!isempty, split(read(pf, String), "\n")), progress_files)

        watcher = on_progress === nothing ? nothing : @async begin
            while any(p -> !process_exited(p), procs)
                on_progress(count_done())
                sleep(0.3)
            end
        end

        foreach(wait, procs)
        watcher === nothing || wait(watcher)
        on_progress === nothing || on_progress(count_done())

        for p in procs
            p.exitcode == 0 || error("Speech synthesis worker failed (exit code $(p.exitcode))")
        end
    finally
        rm(tmp_dir, force=true, recursive=true)
    end
end

function parse_args(args)
    opts = Dict{String,Any}("rate" => 0, "voice" => "", "max_chars" => 4000, "outdir" => "", "workers" => 0)
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
        elseif a == "--workers"
            i += 1; opts["workers"] = parse(Int, args[i])
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
    paragraphs = extract_paragraphs(pdftotext, pdf)
    isempty(paragraphs) && error("No extractable text found (the PDF may be scanned images without OCR).")

    outdir = isempty(opts["outdir"]) ? joinpath("audio", splitext(basename(pdf))[1]) : opts["outdir"]
    mkpath(outdir)

    transcript_path = joinpath(outdir, "transcript.txt")
    write(transcript_path, full_text(paragraphs))

    chunks, chunk_pages = chunk_paragraphs(paragraphs; max_chars=opts["max_chars"])
    n = length(chunks)
    workers = opts["workers"] > 0 ? opts["workers"] : default_worker_count(n)
    println("Split into $n track(s). Synthesizing with Windows SAPI ($workers worker(s) in parallel)...")

    track_names = ["track_$(lpad(idx, 3, '0')).wav" for idx in 1:n]
    out_paths = [joinpath(outdir, name) for name in track_names]
    synthesize_many(chunks, out_paths; voice=opts["voice"], rate=opts["rate"], workers=workers,
        on_progress = d -> print("\r  [$d/$n] tracks done"))
    println()
    write(joinpath(outdir, "playlist.m3u"), join(track_names, "\n") * "\n")

    println("\nDone. Audio tracks + playlist.m3u written to: $outdir")
    println("Copy that folder to your phone and queue playlist.m3u for the commute.")
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
