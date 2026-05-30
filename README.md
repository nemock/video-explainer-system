# video-explainer-system

A **local-first Claude Code skill** (`/explainer`) that turns a topic or a source document into a **visually dynamic HTML explainer deck** and a **narrated, captioned MP4** — end to end, on your own machine, using only local/free tools plus a Claude subscription. **No paid SaaS anywhere in the generation path.**

It runs on Apple Silicon (an M3/16 GB Mac), renders a 20–30 s short in roughly a minute, and stops at a clean, labeled output directory + a versioned `manifest.json` ready for a downstream poster. It does **not** post to social platforms — generation only.

*Status: **v1.0.0** — built, working, and polished enough that the tool generated [its own explainer video](#) about itself. Built as a Claude Code skill.*

---

## Why this exists

This started from a simple itch.

There's a great open-source project, [`prajwal-y/video_explainer`](https://github.com/prajwal-y/video_explainer), that turns technical documents into explainer videos. The architecture is excellent — and I borrowed its single best idea (generate the audio *first*, then sync visuals to word-level timestamps). But its default path leans on **ElevenLabs** for narration and **Remotion/React** for rendering: a metered voice subscription and a source-available framework with a paid company license.

And that's the pattern everywhere you look. To make one short video the "normal" way, you end up renting four or five different cloud services — a voice subscription here, a stock-footage subscription there, an avatar plan, a render credit meter — each one a recurring bill, each one uploading your work to someone else's servers.

I just wasn't interested in that. I have a perfectly capable computer sitting right here. There's a tiny, excellent text-to-speech model ([Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)) that runs locally and sounds great. There's a forced aligner in `torchaudio`. There's a headless browser and `ffmpeg`. **Why rent what I can run?**

Yes, doing it locally might take a few minutes longer per video. So what? That's the whole point — this much capability, free, on the machine in front of me, with nothing leaving my desk. That's the beauty of where the technology is right now. This project is that conviction, built out: **inspired by `video_explainer`, with every paid dependency stripped out and replaced with something local.**

---

## What it does

Give it a topic (or point it at a PDF/URL) and it will:

1. **Research & script** — Claude researches the topic, captures sourced facts to a small local wiki, and writes a voice-over script and a structured deck.
2. **Narrate locally** — Kokoro-82M synthesizes the narration (≈5× faster than real time on an M3), loudness-normalized to broadcast level.
3. **Align** — `torchaudio` MMS_FA forced alignment produces word-level timestamps (the Apple-Silicon-native replacement for WhisperX), driving **word-synced kinetic captions** and SRT/VTT.
4. **Build a deck** — a fixed-theme, data-driven HTML deck (hook · statement · diagram · figure · payoff slide types) with a **template family** of themes, varied transitions, a subtle ambient motion layer, and an optional **source figure** framed from an ingested PDF/URL.
5. **Render** — a deterministic JS animation engine captured frame-by-frame via Playwright headless Chrome, encoded with `ffmpeg` (VideoToolbox). One project renders **multiple aspect ratios at once** (9:16 / 16:9 / 4:5 / 1:1) with per-platform safe zones.
6. **Brand & CTA** — an optional brand library stamps a **watermark on every slide** and auto-appends a **spoken + visual call-to-action end slide** (logo, product image, link).
7. **Package** — writes a labeled output dir, a standalone reusable HTML deck, captions, per-aspect MP4s, and a **versioned `manifest.json`** carrying AI-disclosure metadata and per-platform captions for a downstream poster. **Then it stops.**

A motion/pacing **QA** pass (ffmpeg `freezedetect` × the word timeline) flags visual dead air and weak pacing.

## How it's built

- **Local & free stack:** Kokoro-82M (TTS) · torchaudio MMS_FA (alignment) · plain HTML + a seeded JS animation driver · Playwright frame capture · ffmpeg/VideoToolbox. The only "AI service" is the operator's **existing Claude subscription** — no metered API key.
- **Generation / media split:** Claude is confined to the generation stages; the media path (narrate → align → render → mux) is **pure Python with zero LLM calls**, so renders run unattended.
- **Deterministic by construction:** seeded RNG + CDP virtual time; raw CSS animation is forbidden on captured elements, so the same project renders the same frames every time.
- **Apple-Silicon-native:** no CUDA; memory-heavy stages are serialized for a 16 GB unified-memory budget.
- **Generation only:** the boundary ends at the output dir + manifest. A separate tool (e.g. a Blotato adapter) can post; this one never does.

See **[PRD.md](PRD.md)** for the full architecture, phase-by-phase build log, risks, and the multi-perspective council review that shaped it, and the `/explainer` **[skill](skills/explainer/SKILL.md)** for usage.

## Quick start (sketch)

```bash
explainer scaffold "what is a vector database" --brand FFW
# Claude authors script.json + deck.json (research, hook, slides)…
explainer media outputs/<date>_what-is-a-vector-database
#  → deck/index.html, video/explainer_9x16.mp4, captions/, manifest.json
explainer handoff outputs/<date>_…   # per-platform, blotato-ready post specs (still never posts)
```

---

## Market analysis — where this fits

This is a deliberately narrow, opinionated tool. There is a large and good market of alternatives; for many people one of them is the **better** choice. Here's an honest map, with references.

### 1. Cloud "faceless" & avatar video generators (SaaS)
The biggest category. Type a script or prompt, get a finished video on the vendor's servers.

- **Faceless / stock-montage:** [Pictory](https://pictory.ai/), [InVideo AI](https://invideo.io/), [Fliki](https://fliki.ai/), [Revid.ai](https://www.revid.ai/), [AutoShorts.ai](https://autoshorts.ai/)
- **Avatars & premium voice:** [Synthesia](https://www.synthesia.io/), [HeyGen](https://www.heygen.com/), [Colossyan](https://www.colossyan.com/), [D-ID](https://www.d-id.com/), [ElevenLabs](https://elevenlabs.io/) (the exact voice service this project replaced with local Kokoro)

**How they differ:** all are cloud subscriptions ($6–$199+/mo), metered by minutes/credits, and your script and source material are uploaded to their servers. They offer things we simply don't: photoreal talking-head **avatars** and **voice cloning**, **100+ languages** with one-click translation/dubbing, **millions of licensed stock clips** ([Pictory](https://pictory.ai/faceless-ai-video-generator)) and **frontier generative video** (InVideo's Sora 2 / VEO), polished web editors, and — notably — **auto-posting/scheduling** straight to TikTok/YouTube ([AutoShorts.ai](https://autoshorts.ai/), [Revid.ai](https://www.revid.ai/)).

**What we do differently:** 100% local and offline-capable (nothing leaves your Mac), no per-video metering, a *designed animated deck* rather than a stock montage or a talking head, real source-figure ingestion, and multi-aspect output from one project.

### 2. AI presentation & doc-to-video tools
- [Gamma](https://gamma.app/) (best-in-class PDF/PPTX → designed deck), [Google Vids](https://workspace.google.com/products/vids/), [Canva Magic Studio](https://www.canva.com/magic-studio/), [Beautiful.ai](https://www.beautiful.ai/). (Tome has [pivoted away](https://venturebeat.com/technology/tomes-founders-ditch-viral-presentation-app-with-20m-users-to-build-ai) from this space.)

**How they differ:** these are superb at *decks* and live in the cloud with real-time collaboration, hosting, share links, huge template/stock libraries, and broad export — strengths we don't chase. Most are deck-first; only some emit a true narrated MP4. We span both (a reusable HTML deck **and** a narrated video) but as a single-user, local, file-based tool.

### 3. Open-source programmatic-video frameworks
The render-engine layer.

- [Remotion](https://www.remotion.dev/) (React; mature, but a paid [company license](https://www.remotion.dev/docs/license) above 3 employees), [Revideo](https://github.com/redotvideo/revideo) (MIT, license-clean), [Motion Canvas](https://motioncanvas.io/) (MIT, editor-centric), [HyperFrames](https://github.com/heygen-com/hyperframes) (Apache-2.0; **architecturally the closest** to our HTML + virtual-clock capture path).

**How they differ:** these are **libraries you build a pipeline around**, not finished tools. They give far more raw animation power (React/canvas, Three.js, GSAP, Lottie) and, for Remotion/Revideo, cloud-render scaling to thousands of videos. We deliberately trade that flexibility for an **end-to-end skill** with batteries included (TTS, alignment, scripting, captions, branding) and no React/licensing dependency — closest in spirit to HyperFrames, but as a whole pipeline.

### 4. Open-source end-to-end pipelines & the paper→video niche
The closest cousins.

- **Topic→video pipelines:** [`video_explainer`](https://github.com/prajwal-y/video_explainer) (our inspiration), [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo), [ShortGPT](https://github.com/RayVentura/ShortGPT)
- **Paper / doc → explainer:** [Paper2Video](https://github.com/showlab/Paper2Video) (full academic talk + talking head, but assumes a 48 GB CUDA GPU), [Manimator](https://github.com/HyperCluster-Tech/manimator) (3Blue1Brown-style Manim math animation), [NotebookLM Video Overviews](https://notebooklm.google/) (zero-setup, cloud, polished), [repo-explainer](https://github.com/johnpsasser/repo-explainer)

**How they differ:** these are the genuine end-to-end alternatives — and several are excellent. But almost all of them **call a metered LLM API** (GPT-4.1/Gemini) and many default to paid TTS, stock footage, or a CUDA GPU. MoneyPrinterTurbo/ShortGPT build *stock-clip montages* and can **auto-publish**; the Manim tools do true equation/proof animation we can't match; Paper2Video produces a far more complete academic artifact (talking head, cursor grounding, a published benchmark). We're the one tuned to run **entirely on a consumer Apple-Silicon Mac with no metered API** — reusing your Claude *subscription* instead of a per-token key — and aimed at short, social-format video with hook + kinetic captions + branding.

---

## What we deliberately **don't** do

These are choices, not gaps — and for some users they're dealbreakers, which is fine:

- **No posting.** We write a labeled dir + manifest and stop. (Tools like AutoShorts.ai/Revid.ai auto-publish; pair us with a separate poster instead.)
- **No avatars or voice cloning.** No talking head, no cloned voice — a single local Kokoro voice.
- **No stock footage or generative B-roll.** The visual is a designed animated deck, not photoreal video.
- **No big multilingual catalog.** Effectively single-language per the local voice; no one-click translation/dubbing.
- **No cloud editor, hosting, collaboration, or template marketplace.** Single-user, local, file-based.
- **No turnkey cross-platform packaging.** Apple-Silicon-first; not a Windows/Docker/cloud product (today).

## Who should use something else

- **You want zero setup and a polished result in a browser, today** → [NotebookLM](https://notebooklm.google/), [Gamma](https://gamma.app/), or [Pictory](https://pictory.ai/).
- **You need a human presenter, voice cloning, or 100+ languages** → [Synthesia](https://www.synthesia.io/), [HeyGen](https://www.heygen.com/), [ElevenLabs](https://elevenlabs.io/).
- **You want a set-and-forget faceless channel that posts itself** → [AutoShorts.ai](https://autoshorts.ai/), [Revid.ai](https://www.revid.ai/).
- **You're a developer who wants maximum animation control or cloud-scale rendering** → [Remotion](https://www.remotion.dev/), [Revideo](https://github.com/redotvideo/revideo), [HyperFrames](https://github.com/heygen-com/hyperframes).
- **You're animating math/theorems or academic talks** → [Manimator](https://github.com/HyperCluster-Tech/manimator), [Paper2Video](https://github.com/showlab/Paper2Video).

## Who this **is** for

You, if you: own a capable machine and would rather run things on it than rent them; care that your source material and scripts never leave your desk; want zero marginal cost per video beyond a Claude subscription you already pay for; like a *designed, deterministic, reproducible* deck aesthetic over stock montages or avatars; and are happy to own the (small) setup in exchange for a free, private, end-to-end pipeline.

A few minutes longer per render, run locally and free, with nothing leaving your machine. That trade is the entire point.

---

*Built as a Claude Code skill. Design & build log: [PRD.md](PRD.md). Conventions: [CLAUDE.md](CLAUDE.md). Generation-only — this tool never posts to social platforms.*
