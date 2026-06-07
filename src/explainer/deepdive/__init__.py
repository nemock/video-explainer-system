"""Deep-dive orchestrator + assembler — the long-form layer over the single-project
`explainer` engine. A "program" (one ~24-min film) is an ordered list of segments, each
its own `explainer` project (or a pre-rendered interstitial MP4); assembly conforms every
segment to one master-format contract and concatenates them RAM-safely (concat demuxer +
stream copy). Pure Python, zero LLM calls — the Claude-driven planning/authoring lives in
the `/deepdive` skill (Phase 2.2+). See deep-dive/ARCHITECTURE.md §3–§16."""
