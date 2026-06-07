"""Packaging (ARCHITECTURE §12.5) — the deterministic, on-brand YouTube thumbnail composite +
the title-variants scaffold. The thumbnail is an FWF-styled 1280x720 card rendered headlessly
(deep-purple field + grain/vignette + condensed Archivo keyword text + D-rocket logo + optional
operator selfie corner) — repeatable, no AI needed. Title variants are authored by the
`/deepdive` skill (benefit-forward, D9); this writes their file."""
import json
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"
ARCHIVO = ASSETS / "fonts" / "archivo-wdth-wght-normal.woff2"
# same fixed-seed grain as the fwf deck theme (deterministic).
_GRAIN = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'"
          "%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' "
          "numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E"
          "%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E")


def _default_logo(program):
    """Resolve the program brand's logo (FFW brg-logo-purple) for the thumbnail, or None."""
    from .. import brand
    d, data = brand.resolve(program.brand or "FFW")
    if d and data and data.get("logo") and (d / data["logo"]).exists():
        return (d / data["logo"]).resolve()
    return None


def _html(text, accent, logo, selfie, handle):
    words = text.split()
    aset = {w.lower().strip(".,") for w in (accent or [])}
    kw = " ".join(f'<span class="ac">{w}</span>' if w.lower().strip(".,") in aset else w for w in words)
    logo_html = f'<img class="logo" src="file://{logo}">' if logo else ""
    selfie_html = f'<img class="selfie" src="file://{selfie}">' if selfie else ""
    handle_html = f'<div class="handle">{handle}</div>' if handle else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:'Archivo';src:url('file://{ARCHIVO}') format('woff2');font-weight:100 900;font-stretch:62% 125%;}}
*{{margin:0;box-sizing:border-box}}
html,body{{width:1280px;height:720px;background:#36185B;overflow:hidden;font-family:'Archivo',sans-serif}}
.stage{{position:relative;width:1280px;height:720px}}
.vig{{position:absolute;inset:0;background:radial-gradient(120% 95% at 50% 42%,transparent 50%,rgba(0,0,0,.5))}}
.grain{{position:absolute;inset:0;opacity:.07;mix-blend-mode:overlay;background-size:160px 160px;background-image:url("{_GRAIN}")}}
.logo{{position:absolute;top:46px;left:58px;height:92px;object-fit:contain;z-index:3}}
.kw{{position:absolute;left:64px;right:{'520px' if selfie else '64px'};top:50%;transform:translateY(-50%);z-index:3;
  color:#fff;font-weight:800;font-stretch:74%;text-transform:uppercase;letter-spacing:-.01em;font-size:118px;line-height:.96}}
.kw .ac{{color:#757BBD}}
.handle{{position:absolute;bottom:42px;left:64px;z-index:3;color:#CCC;font-weight:700;font-stretch:80%;
  text-transform:uppercase;letter-spacing:.04em;font-size:34px}}
.selfie{{position:absolute;bottom:0;right:0;height:78%;z-index:2;object-fit:contain;filter:drop-shadow(-12px 0 30px rgba(0,0,0,.45))}}
</style></head><body><div class="stage">
<div class="vig"></div><div class="grain"></div>
{logo_html}<div class="kw">{kw}</div>{handle_html}{selfie_html}
</div></body></html>"""


def thumbnail(program, text, out, *, accent=None, logo=None, selfie=None, handle="@davesaunders"):
    """Render a 1280x720 FWF thumbnail. `text` = the 3–5-word keyword line (some words can be
    accented in indigo). `selfie` (optional) sits in the bottom-right. Deterministic."""
    from playwright.sync_api import sync_playwright
    logo = logo or _default_logo(program)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = _html(text, accent, logo, selfie, handle)
    tmp = out.parent / "_thumb.html"
    tmp.write_text(html)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars", "--disable-gpu"])
        page = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        page.goto(tmp.as_uri())
        page.wait_for_timeout(250)  # let the bundled font load
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1280, "height": 720})
        b.close()
    tmp.unlink(missing_ok=True)
    return {"thumbnail": str(out), "text": text, "accent": accent, "logo": str(logo) if logo else None,
            "selfie": str(selfie) if selfie else None}


def write_title_variants(program, variants, chosen=0):
    """Write packaging/title-variants.md (benefit-forward variants authored by the skill). The
    chosen variant seeds the YouTube title + the X promo hook later."""
    out = program.dir / "packaging" / "title-variants.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Title variants — {program.title}", "",
             "_Benefit-forward (sell the transformation, not the topic — D9). The chosen one seeds "
             "the YouTube title + X hook._", ""]
    for i, v in enumerate(variants):
        lines.append(f"- [{'x' if i == chosen else ' '}] {v}")
    out.write_text("\n".join(lines) + "\n")
    return {"title_variants": str(out), "count": len(variants), "chosen": chosen}


TITLE_TEMPLATE = [
    "<Outcome they get> — <the surprising mechanism>",
    "How to <do the hard thing> without <the common pain>",
    "The <N>-part system behind <result>",
    "Why <common belief> is wrong (and what to do instead)",
    "<Number> <things> that <deliver the outcome>",
]
