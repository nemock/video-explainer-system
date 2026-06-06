"""Theme family (PRD §8.5) — named presets so a channel produces a *family* of
looks, not one. Each theme = palette + a motion personality (the default per-slide
intro transition). A slide can override with its own `transition`."""

THEMES = {
    "midnight": {"bg": "#0b1020", "fg": "#f5f7ff", "accent": "#5b8cff", "accent2": "#ff7a59", "motion": "rise"},
    "paper":    {"bg": "#f5f2ea", "fg": "#1b1b2a", "accent": "#d8432f", "accent2": "#2a7de1", "motion": "fade"},
    "sunset":   {"bg": "#1a1020", "fg": "#fff4ee", "accent": "#ff7a59", "accent2": "#ffd166", "motion": "pop"},
    "forest":   {"bg": "#0c1a14", "fg": "#eafff4", "accent": "#3ddc84", "accent2": "#ffd166", "motion": "rise"},
    "mono":     {"bg": "#101012", "fg": "#fafafa", "accent": "#f5d90a", "accent2": "#9aa0a6", "motion": "slide"},
    # BRG MedTech: cream bg, navy text, teal accent (+ warm-rust accent2 for caution/contrast).
    # Pair with a brand whose logo reads on cream (e.g. the navy-gradient BRG mark).
    "medtech":  {"bg": "#f5f0eb", "fg": "#1b2b4b", "accent": "#0d7377", "accent2": "#c2410c", "motion": "fade"},
    # BRG Founder Tip Tuesday: deep-forest bg, parchment text, brass accent (+ clay accent2).
    # The established FTT identity (forest #1E3A2F / brass #C9A24A / parchment #F0E8D2).
    # Pair with a brand whose logo reads on forest (the BRGFTT brand). NOT the neon-green
    # `forest` theme above. Fraunces display + Inter body via the optional `fonts` field.
    "founder":  {"bg": "#1E3A2F", "fg": "#F0E8D2", "accent": "#C9A24A", "accent2": "#B5654A", "motion": "fade",
                 "fonts": {"display": "Fraunces", "body": "Inter"}},
    # Founders Who Finish (deep-dive long-form): flat deep-purple bg + grain/vignette,
    # white text, ONE indigo accent (accent2 == accent so no off-brand red ever leaks).
    # Montserrat 800 Condensed in the kit -> bundled as Archivo variable (wght+wdth) which
    # has a real width axis; the condensed cut + ALL-CAPS titles / sentence-case body live in
    # the `[data-theme="fwf"]` block of deck.css. `ambient:false` kills the drifting accent
    # glow (the kit forbids gradients except the vignette). Pair with the FFW brand.
    "fwf":      {"bg": "#36185B", "fg": "#FFFFFF", "accent": "#757BBD", "accent2": "#757BBD", "motion": "fade",
                 "ambient": False, "fonts": {"display": "Archivo", "body": "Archivo"}},
}
DEFAULT = "midnight"
VALID_MOTION = {"rise", "fade", "pop", "slide"}


def resolve(spec):
    """spec may be a theme name (str), an override dict, or None."""
    theme = dict(THEMES[DEFAULT])
    if isinstance(spec, str) and spec in THEMES:
        theme.update(THEMES[spec])
    elif isinstance(spec, dict):
        theme.update(spec)
    return theme
