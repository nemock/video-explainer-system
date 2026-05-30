"""Pronunciation lexicon (PRD R3). Lets the author write natural text ("MCP", "AI")
while Kokoro speaks the intended form ("M C P", "A I") — and captions still show the
original token. Maps a normalized display token -> spoken replacement (1+ words).
Project overrides live in <project>/lexicon.json ({"token": "spoken form"})."""
import json, re

DEFAULT = {
    "mcp": "M C P", "ai": "A I", "agi": "A G I", "llm": "L L M", "llms": "L L Ms",
    "gpt": "G P T", "gpt4": "G P T four", "api": "A P I", "apis": "A P Is",
    "sdk": "S D K", "ui": "U I", "ux": "U X", "url": "U R L", "urls": "U R Ls",
    "gpu": "G P U", "cpu": "C P U", "css": "C S S", "html": "H T M L",
    "http": "H T T P", "https": "H T T P S", "sql": "sequel", "json": "jason",
    "usb": "U S B", "usbc": "U S B C", "ssd": "S S D", "saas": "sass",
    "ml": "M L", "nlp": "N L P", "ocr": "O C R", "tts": "T T S",
}


def load(project_dir, extra=None):
    """DEFAULT + project <dir>/lexicon.json + `extra` (e.g. a brand's lexicon).
    All keys are normalized to the lookup form, so authors can write "davesaunders.net"
    and it matches the token regardless of punctuation/case."""
    lex = dict(DEFAULT)
    p = (project_dir / "lexicon.json") if hasattr(project_dir, "joinpath") else None
    try:
        if p and p.exists():
            lex.update(json.loads(p.read_text()))
    except Exception:
        pass
    if extra:
        lex.update(extra)
    return {_key(k): v for k, v in lex.items()}


def _key(tok):
    return re.sub(r"[^a-z0-9]", "", tok.lower())


def expand(text, lex):
    """Return [(display_token, [spoken_token, ...]), ...] preserving trailing punctuation."""
    pairs = []
    for tok in text.split():
        m = re.match(r"^(\W*)(.*?)(\W*)$", tok)
        core, trail = m.group(2), m.group(3)
        spoken = lex.get(_key(core))
        if spoken:
            toks = spoken.split()
            if trail:
                toks[-1] = toks[-1] + trail
        else:
            toks = [tok]
        pairs.append((tok, toks))
    return pairs


def spoken_text(text, lex):
    return " ".join(s for _, toks in expand(text, lex) for s in toks)
