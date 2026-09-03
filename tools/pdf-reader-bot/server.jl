#!/usr/bin/env julia
#
# server.jl — local web front end for pdf2speech.
#
# Scans the repo for PDFs, lets you pick one in the browser, converts it to
# spoken-word audio (reusing pdf2speech.jl), and serves the result back for
# in-browser playback / download.
#
# Requires: HTTP.jl, JSON3.jl  (run `julia tools/pdf-reader-bot/install_deps.jl` once)
#
# Usage:
#   julia tools/pdf-reader-bot/server.jl [port]
#   then open http://127.0.0.1:<port> in a browser (default port 8787)

using HTTP
using JSON3

include(joinpath(@__DIR__, "pdf2speech.jl"))

const REPO_ROOT = normpath(joinpath(@__DIR__, "..", ".."))
const AUDIO_ROOT = joinpath(@__DIR__, "audio")
const SKIP_DIRS = Set(["audio", ".git", "node_modules", ".julia", "tools", ".vscode"])

mkpath(AUDIO_ROOT)

const JOBS = Dict{String,Dict{Symbol,Any}}()
const JOBS_LOCK = ReentrantLock()

function slug_for(rel::String)
    s = splitext(rel)[1]
    s = replace(s, r"[\\/]" => "__")
    s = replace(s, r"[^A-Za-z0-9_\-]" => "_")
    return s
end

function existing_tracks(slug::String)
    dir = joinpath(AUDIO_ROOT, slug)
    isdir(dir) || return String[]
    return sort(filter(f -> startswith(f, "track_") && endswith(f, ".wav"), readdir(dir)))
end

has_existing_audio(slug::String) = !isempty(existing_tracks(slug))

function existing_pages(slug::String)
    path = joinpath(AUDIO_ROOT, slug, "pages.json")
    isfile(path) || return Int[]
    try
        return Int.(JSON3.read(read(path, String)))
    catch
        return Int[]
    end
end

function list_notes()
    notes = NamedTuple[]
    for (root, dirs, files) in walkdir(REPO_ROOT)
        filter!(d -> !(d in SKIP_DIRS) && !startswith(d, "."), dirs)
        for f in files
            lowercase(splitext(f)[2]) == ".pdf" || continue
            full = joinpath(root, f)
            rel = replace(relpath(full, REPO_ROOT), "\\" => "/")
            slug = slug_for(rel)
            course = split(rel, "/")[1]
            title = splitext(f)[1]
            push!(notes, (id=slug, path=rel, course=course, title=title, has_audio=has_existing_audio(slug)))
        end
    end
    sort!(notes, by = n -> (n.course, lowercase(n.title)))
    return notes
end

function get_voices()
    ps = """
    Add-Type -AssemblyName System.Speech
    (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() |
        ForEach-Object { \$_.VoiceInfo.Name }
    """
    out = read(`powershell -NoProfile -Command $ps`, String)
    return [strip(l) for l in split(out, "\n") if !isempty(strip(l))]
end

function json_response(data; status::Int=200)
    return HTTP.Response(status, ["Content-Type" => "application/json"], JSON3.write(data))
end

function run_job(slug::String, pdf_path::String, voice::String, rate::Int)
    try
        pdftotext = find_pdftotext()
        paragraphs = extract_paragraphs(pdftotext, pdf_path)
        isempty(paragraphs) && error("No extractable text found (the PDF may be scanned images without OCR).")

        outdir = joinpath(AUDIO_ROOT, slug)
        mkpath(outdir)
        write(joinpath(outdir, "transcript.txt"), full_text(paragraphs))

        chunks, chunk_pages = chunk_paragraphs(paragraphs; max_chars=4000)
        n = length(chunks)
        lock(JOBS_LOCK) do
            JOBS[slug][:total] = n
        end

        track_names = ["track_$(lpad(idx, 3, '0')).wav" for idx in 1:n]
        out_paths = [joinpath(outdir, name) for name in track_names]
        synthesize_many(chunks, out_paths; voice=voice, rate=rate,
            on_progress = d -> lock(JOBS_LOCK) do
                JOBS[slug][:done] = d
            end)
        write(joinpath(outdir, "playlist.m3u"), join(track_names, "\n") * "\n")
        write(joinpath(outdir, "pages.json"), JSON3.write(chunk_pages))

        lock(JOBS_LOCK) do
            JOBS[slug][:status] = "done"
        end
    catch e
        msg = sprint(showerror, e)
        lock(JOBS_LOCK) do
            JOBS[slug][:status] = "error"
            JOBS[slug][:error] = msg
        end
        @error "conversion failed" slug exception=e
    end
end

function handle_notes(::HTTP.Request)
    return json_response(list_notes())
end

function handle_voices(::HTTP.Request)
    try
        return json_response(get_voices())
    catch e
        return json_response(String[]; status=200)
    end
end

function handle_convert(req::HTTP.Request)
    body = JSON3.read(String(req.body))
    rel = String(body["path"])
    voice = haskey(body, "voice") ? String(body["voice"]) : ""
    rate = haskey(body, "rate") ? Int(body["rate"]) : 0

    full_pdf = joinpath(REPO_ROOT, rel)
    normpath(full_pdf) |> p -> startswith(p, REPO_ROOT) || return json_response((error="invalid path",); status=400)
    isfile(full_pdf) || return json_response((error="PDF not found",); status=404)

    slug = slug_for(rel)
    should_start = lock(JOBS_LOCK) do
        if haskey(JOBS, slug) && get(JOBS[slug], :status, "") == "running"
            return false
        end
        JOBS[slug] = Dict{Symbol,Any}(:status => "running", :done => 0, :total => 0, :error => nothing)
        return true
    end

    should_start && @async run_job(slug, full_pdf, voice, rate)

    return json_response((status="started", id=slug))
end

function handle_status(req::HTTP.Request)
    qp = HTTP.queryparams(HTTP.URI(req.target))
    slug = get(qp, "id", "")
    isempty(slug) && return json_response((error="missing id",); status=400)

    job = lock(JOBS_LOCK) do
        haskey(JOBS, slug) ? copy(JOBS[slug]) : nothing
    end

    if job !== nothing
        tracks = job[:status] == "done" ? existing_tracks(slug) : String[]
        pages = job[:status] == "done" ? existing_pages(slug) : Int[]
        return json_response((status=job[:status], done=job[:done], total=job[:total], error=job[:error], tracks=tracks, pages=pages))
    elseif has_existing_audio(slug)
        return json_response((status="done", done=0, total=0, error=nothing, tracks=existing_tracks(slug), pages=existing_pages(slug)))
    else
        return json_response((status="none", done=0, total=0, error=nothing, tracks=String[], pages=Int[]))
    end
end

function handle_audio(req::HTTP.Request)
    params = HTTP.getparams(req)
    slug = get(params, "slug", "")
    file = get(params, "file", "")
    if isempty(slug) || isempty(file) || occursin("..", file) || occursin('/', file) || occursin('\\', file)
        return HTTP.Response(400, "bad request")
    end
    path = joinpath(AUDIO_ROOT, slug, file)
    isfile(path) || return HTTP.Response(404, "not found")
    ctype = endswith(file, ".wav") ? "audio/wav" :
            endswith(file, ".m3u") ? "audio/x-mpegurl" :
            endswith(file, ".txt") ? "text/plain; charset=utf-8" : "application/octet-stream"
    return HTTP.Response(200, ["Content-Type" => ctype], read(path))
end

function handle_pdf(req::HTTP.Request)
    qp = HTTP.queryparams(HTTP.URI(req.target))
    rel = get(qp, "path", "")
    isempty(rel) && return HTTP.Response(400, "missing path")

    full = normpath(joinpath(REPO_ROOT, rel))
    (startswith(full, REPO_ROOT) && lowercase(splitext(full)[2]) == ".pdf") ||
        return HTTP.Response(400, "bad request")
    isfile(full) || return HTTP.Response(404, "not found")

    return HTTP.Response(200, ["Content-Type" => "application/pdf"], read(full))
end

function handle_index(::HTTP.Request)
    path = joinpath(@__DIR__, "public", "index.html")
    return HTTP.Response(200, ["Content-Type" => "text/html; charset=utf-8"], read(path))
end

function build_router()
    router = HTTP.Router()
    HTTP.register!(router, "GET", "/", handle_index)
    HTTP.register!(router, "GET", "/api/notes", handle_notes)
    HTTP.register!(router, "GET", "/api/voices", handle_voices)
    HTTP.register!(router, "POST", "/api/convert", handle_convert)
    HTTP.register!(router, "GET", "/api/status", handle_status)
    HTTP.register!(router, "GET", "/audio/{slug}/{file}", handle_audio)
    HTTP.register!(router, "GET", "/pdf", handle_pdf)
    return router
end

function main()
    port = length(ARGS) >= 1 ? parse(Int, ARGS[1]) : 8787
    host = length(ARGS) >= 2 ? ARGS[2] : "127.0.0.1"
    router = build_router()
    println("Repo root:  $REPO_ROOT")
    println("PDF Reader Bot running at http://$host:$port")
    host != "127.0.0.1" && println("Note: bound to $host — reachable by anyone on your network, with no auth.")
    HTTP.serve(router, host, port)
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
