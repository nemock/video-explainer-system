"""INGEST — source material -> sources/ (extracted text, framed screenshots/figures,
citations.json). PDF via PyMuPDF; URL via Playwright. No LLM calls."""
import json, re
from pathlib import Path


def _sources_dir(proj):
    p = proj.dir / "sources"
    p.mkdir(exist_ok=True)
    return p


def _load_citations(sdir):
    f = sdir / "citations.json"
    return json.loads(f.read_text()) if f.exists() else {"sources": []}


def _save_citations(sdir, cites):
    (sdir / "citations.json").write_text(json.dumps(cites, indent=2))


def _parse_pages(spec, n):
    if not spec:
        return list(range(min(n, 4)))  # default: first 4 pages
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a) - 1, int(b)))
        elif part:
            out.add(int(part) - 1)
    return sorted(i for i in out if 0 <= i < n)


def ingest_pdf(proj, pdf_path, pages=None, zoom=2.0):
    import fitz
    sdir = _sources_dir(proj)
    doc = fitz.open(str(pdf_path))
    sid = "src" + str(len(_load_citations(sdir)["sources"]) + 1)

    text = "\n\n".join(doc[i].get_text() for i in range(doc.page_count))
    text_rel = f"sources/{sid}_text.md"
    (proj.dir / text_rel).write_text(text)

    idxs = _parse_pages(pages, doc.page_count)
    images = []
    mat = fitz.Matrix(zoom, zoom)
    for i in idxs:
        rel = f"sources/{sid}_page-{i+1:02d}.png"
        doc[i].get_pixmap(matrix=mat).save(str(proj.dir / rel))
        images.append(rel)

    title = (doc.metadata or {}).get("title") or Path(pdf_path).stem
    cites = _load_citations(sdir)
    cites["sources"].append({"id": sid, "kind": "pdf", "ref": str(pdf_path),
                             "title": title, "pages": [i + 1 for i in idxs],
                             "images": images, "text": text_rel})
    _save_citations(sdir, cites)
    return {"source_id": sid, "title": title, "pages_rendered": [i + 1 for i in idxs],
            "images": images, "text": text_rel}


def ingest_url(proj, url, width=1280, height=1600, full_page=False):
    from playwright.sync_api import sync_playwright
    sdir = _sources_dir(proj)
    sid = "src" + str(len(_load_citations(sdir)["sources"]) + 1)
    slug = re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:40]
    img_rel = f"sources/{sid}_{slug}.png"
    text = ""
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--hide-scrollbars"])
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.screenshot(path=str(proj.dir / img_rel), full_page=full_page)
        try:
            text = page.inner_text("body")
        except Exception:
            text = ""
        browser.close()
    text_rel = f"sources/{sid}_text.md"
    (proj.dir / text_rel).write_text(text)

    cites = _load_citations(sdir)
    cites["sources"].append({"id": sid, "kind": "url", "ref": url, "title": url,
                             "images": [img_rel], "text": text_rel})
    _save_citations(sdir, cites)
    return {"source_id": sid, "url": url, "images": [img_rel], "text": text_rel}
