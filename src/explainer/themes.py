"""Theme family (PRD §8.5) — named presets so a channel produces a *family* of
looks, not one. Each theme = palette + a motion personality (the default per-slide
intro transition). A slide can override with its own `transition`."""

THEMES = {
    "midnight": {"bg": "#0b1020", "fg": "#f5f7ff", "accent": "#5b8cff", "accent2": "#ff7a59", "motion": "rise"},
    "paper":    {"bg": "#f5f2ea", "fg": "#1b1b2a", "accent": "#d8432f", "accent2": "#2a7de1", "motion": "fade"},
    "sunset":   {"bg": "#1a1020", "fg": "#fff4ee", "accent": "#ff7a59", "accent2": "#ffd166", "motion": "pop"},
    "forest":   {"bg": "#0c1a14", "fg": "#eafff4", "accent": "#3ddc84", "accent2": "#ffd166", "motion": "rise"},
    "mono":     {"bg": "#101012", "fg": "#fafafa", "accent": "#f5d90a", "accent2": "#9aa0a6", "motion": "slide"},
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
