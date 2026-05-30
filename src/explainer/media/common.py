"""Shared helpers for the narrate stage (Kokoro + operator voiceover + the recorder)."""


def effective_segments(proj, script):
    """The full segment list narrated/recorded: the authored script segments plus an
    auto-appended CTA segment from the brand (so Kokoro, the operator recorder, and the
    operator-narrate path all agree on the same list + ids)."""
    segments = list(script["segments"])
    brand = proj.brand or {}
    spoken_cta = (brand.get("cta") or {}).get("spoken")
    if spoken_cta and not any(s.get("slide") == "cta" for s in segments):
        next_id = (max(s["id"] for s in segments) + 1) if segments else 0
        segments.append({"id": next_id, "slide": "cta", "text": spoken_cta})
    return segments
