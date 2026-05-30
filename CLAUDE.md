# CLAUDE.md — Explainer System

## Operating rules (read first, every session)

1. **Ask, don't assume.** If something is unclear, ask before writing a single line. Never make silent assumptions about intent, architecture, or requirements.
2. **Simplest solution first.** Always implement the simplest thing that could work. Do not add abstractions or flexibility that weren't explicitly requested.
3. **Don't touch unrelated code.** If a file or function is not directly part of the current task, do not modify it, even if you think it could be improved.
4. **Flag uncertainty explicitly.** If you are not confident about an approach or technical detail, say so before proceeding. Confidence without certainty causes more damage than admitting a gap.

---

## What this project is

A local-first **Claude Code skill** (`/explainer`) that turns a topic or source document into a **visually dynamic HTML explainer deck** and a **narrated MP4**, end-to-end, using only local/free tools plus the operator's Claude subscription. No paid SaaS in the generation path. Inspired by `github.com/prajwal-y/video_explainer` but drops ElevenLabs (→ Kokoro) and Remotion/React (→ plain HTML deck rendered via headless-Chrome frame capture + ffmpeg).

**`PRD.md` is the source of truth for the design.** Read it before proposing or building anything. If this file and the PRD ever disagree, the PRD wins — and flag the discrepancy (rule 4).

## Hard constraints (from the PRD — do not violate without asking)

- **Target machine:** Apple **M3, 16 GB unified memory, Metal — no CUDA**. Budget against unified memory, not VRAM. Serialize the memory-heavy stages (don't run Kokoro + Chrome capture + ffmpeg concurrently).
- **Aligner:** Apple-Silicon-native forced alignment (torchaudio `forced_align` / openai-/mlx-whisper). **WhisperX is not viable here** — do not reintroduce it as the default.
- **Generation/media split:** Claude is confined to the generation stages (intake → research → outline → script + one QA pass). The media path (narrate → align → render → mux) is **pure Python, zero Claude calls**, so renders run unattended.
- **Boundary:** generation only. Write the labeled output dir + versioned `manifest.json` and stop. **This tool never posts to social platforms.**
- **Render correctness:** all motion is driven by a single JS animation driver under CDP virtual time + seeded RNG. **Raw CSS animations/transitions are forbidden on captured elements.**
- **Resumability:** a stage is "done" only via a success marker carrying an input hash, written atomically (temp + rename). File existence alone never means done.

## Shell discipline (inherited from the global CLAUDE.md)

The global `~/.claude/CLAUDE.md` rules apply. Most relevant here:
- **No `for`/`while` loops, no brace expansion, no multi-statement `;`-chains** in Bash. Split into separate calls or use a plain glob.
- **Never poll a long-running render.** Render/build steps are synchronous — run them in the foreground and let them finish; read the log/artifacts afterward.
- Invoke Python/Node helpers by **absolute path**; pass absolute paths as args (don't `cd` into subdirectories).
- All parallelism lives **inside** a synchronous Python helper (a worker pool that blocks until done) — never as backgrounded shell jobs the orchestrator polls.

## Decisions already made (don't relitigate without asking)

- Music: default **ON (low bed) for 9:16**, **OFF for 16:9/deck**.
- Render engine: **owned Playwright frame-capture path** (not HyperFrames), isolated behind a narrow swappable interface.
- Confirmation gates: cheap pre-render gate **plus** an optional post-script / pre-narration checkpoint.

## Working style for this repo

- De-risk in the order the PRD's phases prescribe; **Phase 0 measurements (render time, peak memory) are go/no-go gates**, not warm-ups.
- Lock inter-stage JSON schemas and the manifest contract early — they are load-bearing.
- Prefer a maintained dependency you control over a niche one (the render-engine call is an example of this principle).
