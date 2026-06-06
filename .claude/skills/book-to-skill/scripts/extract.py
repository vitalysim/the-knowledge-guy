#!/usr/bin/env python3
"""
book-to-skill — Stage 0 extraction.

Turns a PDF or EPUB into the raw materials the skill needs:

  <work-dir>/full_text.txt   assembled reading-order text, with inline
                             [[IMAGE: images/..]] and [[PAGE_SCAN: images/..]]
                             placeholders anchored at the position they appear
  <work-dir>/images/         every kept image + rendered pages of scanned PDFs
  <work-dir>/metadata.json   chapter offset map, image manifest, page/word/token
                             counts, scanned-document detection, cost inputs

The chapter offset map is the important part: it records the *exact* character
range of every chapter in full_text.txt, so Stage 1 can slice a chapter without
grepping and guessing. Boundaries come from the PDF outline / EPUB spine when
available, and fall back to heading regex only when they are not.

This script is pure plumbing. It does no understanding — it never decides what
a figure means or what a chapter is "about". That is the LLM's job in Stage 1.

Primary backend is PyMuPDF (fitz): one library covers text, images, tables,
the outline and page rendering. pdftotext / pypdf are text-only fallbacks used
only when PyMuPDF is missing.

Usage:
  extract.py <book.pdf|book.epub> [--mode technical|text]
             [--genre <profile>] [--work-dir DIR]
             [--min-image-dim N] [--max-images N] [--resume]
"""

from __future__ import annotations

import argparse
import hashlib
import html
import html.parser
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# --------------------------------------------------------------------------
# Tunables
# --------------------------------------------------------------------------

CHARS_PER_TOKEN = 4              # rough text token heuristic
IMAGE_TOKEN_DIVISOR = 750        # ~ (w*h)/750 tokens per image for Claude vision
IMAGE_LONG_EDGE_CAP = 1568       # API downscales long edge to ~1568px
SCANNED_PAGE_TEXT_THRESHOLD = 90 # a page with fewer real chars than this AND
                                 # heavy image coverage is treated as scanned
SCANNED_DOC_RATIO = 0.55         # if >= this fraction of pages look scanned,
                                 # flag the whole document as scanned

# Genre -> default minimum image dimension (px on the short edge).
# Image-light genres raise the bar so chapter ornaments are skipped; image-rich
# technical genres keep small-but-real diagrams. Overridable with --min-image-dim.
GENRE_MIN_IMAGE_DIM = {
    "technical":    110,
    "vuln-hunting": 110,
    "financial":    130,
    "scientific":   110,
    "productivity": 320,
    "narrative":    320,
    "biography":    320,   # mostly decorative photos
    "history":      130,   # keep maps / treaty docs / family trees
    "reference":    150,   # technique diagrams matter
    "legal":        320,   # rare structured forms; mostly skip
    "textbook":     110,   # equations / circuits / proofs
    "business":     200,   # 2x2 matrices and value-chains worth keeping
    "psychology":   200,   # experiment figures matter; padding doesn't
    "general":      150,
}
DEFAULT_MIN_IMAGE_DIM = 150


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def est_text_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def est_image_tokens(width: int, height: int) -> int:
    w = min(width, IMAGE_LONG_EDGE_CAP)
    h = min(height, IMAGE_LONG_EDGE_CAP)
    return max(1, (w * h) // IMAGE_TOKEN_DIVISOR)


def sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha1_file(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slugify(text: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s[:maxlen].rstrip("-")) or "section"


CHAPTER_HEADING_RE = re.compile(
    r"^\s*(?:"
    r"chapter\s+\d+|chapter\s+[ivxlcdm]+|"        # Chapter 7 / Chapter IV
    r"part\s+\d+|part\s+[ivxlcdm]+|"              # Part 2 / Part II
    r"\d{1,2}\s+[A-Z][A-Za-z]|"                   # "7 Replication"
    r"[A-Z][A-Z0-9 \-–—:'’]{6,80}\s*$|" # ALL-CAPS title line

    r"\d{1,2}\.\s+[A-Z][A-Za-z]"                  # "7. Replication"
    r")",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------
# Book-native chapter numbering
# --------------------------------------------------------------------------
#
# Every chapter gets a `book_number` derived from its title — the canonical
# label downstream renderers use (`ch07`, `intro`, `preface`, `appendix-a`,
# `fm`, `bm`). The extraction `index` is kept as a stable insertion order,
# but is NOT user-facing.
#
# `parse_book_number_kind` classifies a title; `assign_book_numbers` does
# a second pass to convert classifications into final string labels (so we
# can sequentially number bare-titled chapters like Sethi's "Optimize Your
# Credit Cards" where the title carries no number at all).

_ROMAN = {"i":1,"v":5,"x":10,"l":50,"c":100,"d":500,"m":1000}

def _roman_to_int(s: str) -> int | None:
    s = s.lower()
    if not s or any(c not in _ROMAN for c in s):
        return None
    total, prev = 0, 0
    for c in reversed(s):
        v = _ROMAN[c]
        total += -v if v < prev else v
        prev = v
    return total if 0 < total < 100 else None


_RE_NUM_CHAPTER  = re.compile(r"^\s*chapter\s+(\d+)\b", re.I)
_RE_ROM_CHAPTER  = re.compile(r"^\s*chapter\s+([ivxlcdm]+)\b", re.I)
_RE_BARE_NUM     = re.compile(r"^\s*(\d{1,2})\s*[\.\):—–\-]\s*[A-Za-z]")
_RE_APPENDIX     = re.compile(r"^\s*appendix\s+([a-z])\b", re.I)
_RE_APPENDICES   = re.compile(r"^\s*appendi[cx]es\b", re.I)
_RE_PART         = re.compile(r"^\s*part\s+(\d+|[ivxlcdm]+)\b", re.I)
# Front/back-matter regexes use prefix-matching (no trailing \b) because
# titles like "Acknowledgments" / "Endorsements" / "References" have a
# following word-character that defeats \b. Prefix matching is safe here:
# every alternative below is a unique-enough prefix to identify the kind.
_RE_FRONT_MATTER = re.compile(
    r"^\s*(?:"
    r"praise|endorsement|advance\s+praise|"
    r"title\s*page|half[\s-]?title|cover|frontispiece|"
    r"copyright|dedication|"
    r"acknowledg|contents|table\s+of\s+contents|toc|"
    r"front\s+matter|colophon\s+\(front\)|"
    r"about\s+the\s+author|author'?s\s+note|note\s+on\s+the|"
    r"how\s+to\s+use\s+this\s+book|"
    r"editor'?s\s+note"
    r")", re.I)
_RE_BACK_MATTER  = re.compile(
    r"^\s*(?:"
    r"index\b|colophon|bibliography|references?|note$|notes?\s+\(|endnotes|"
    r"glossary|further\s+reading|resources|back\s+matter|"
    r"about\s+no\s*starch|free\s+.*\s+tools"
    r")", re.I)
_RE_INTRO        = re.compile(r"^\s*introduction\b", re.I)
_RE_PREFACE      = re.compile(r"^\s*preface\b", re.I)
_RE_PROLOGUE     = re.compile(r"^\s*prologue\b", re.I)
_RE_POSTSCRIPT   = re.compile(r"^\s*post[-\s]?script\b", re.I)
_RE_EPILOGUE     = re.compile(r"^\s*epilogue\b", re.I)
_RE_FOREWORD     = re.compile(r"^\s*fore[-\s]?word\b", re.I)
_RE_AFTERWORD    = re.compile(r"^\s*after[-\s]?word\b", re.I)


def parse_book_number_kind(title: str) -> tuple:
    """Classify a chapter title. Returns a tuple — final label assigned by
    `assign_book_numbers` after seeing the whole sequence.

    Possible returns:
      ("num", n)         — explicit Arabic chapter number
      ("rom", n)         — Roman-numeral chapter number, already decoded
      ("named", label)   — Introduction/Preface/Prologue/etc.
      ("appendix", "a")  — lettered appendix
      ("fm",)            — front matter (praise, copyright, TOC, …)
      ("bm",)            — back matter (index, colophon, bibliography, …)
      ("chapter",)       — looks like a real chapter but no number found
      None               — could not classify (caller falls back to index)
    """
    if not title:
        return None
    t = title.strip()
    # Order matters: specific patterns first, then bare-number, then named,
    # then matter-buckets, finally generic-chapter fallthrough.
    if m := _RE_NUM_CHAPTER.match(t):
        return ("num", int(m.group(1)))
    if m := _RE_ROM_CHAPTER.match(t):
        n = _roman_to_int(m.group(1))
        return ("rom", n) if n else ("chapter",)
    if m := _RE_APPENDIX.match(t):
        return ("appendix", m.group(1).lower())
    if _RE_APPENDICES.match(t):
        # Generic "Appendices" / "Appendix" with no letter — bundled.
        return ("named", "appendix")
    if m := _RE_PART.match(t):
        g = m.group(1)
        n = int(g) if g.isdigit() else _roman_to_int(g)
        if n is not None:
            return ("part", n)
    if _RE_INTRO.match(t):      return ("named", "intro")
    if _RE_PREFACE.match(t):    return ("named", "preface")
    if _RE_PROLOGUE.match(t):   return ("named", "prologue")
    if _RE_POSTSCRIPT.match(t): return ("named", "postscript")
    if _RE_EPILOGUE.match(t):   return ("named", "epilogue")
    if _RE_FOREWORD.match(t):   return ("named", "foreword")
    if _RE_AFTERWORD.match(t):  return ("named", "afterword")
    if _RE_FRONT_MATTER.match(t): return ("fm",)
    if _RE_BACK_MATTER.match(t):  return ("bm",)
    if m := _RE_BARE_NUM.match(t):
        return ("num", int(m.group(1)))
    # Heuristic: title starts with a capital letter and looks like a real
    # chapter (≥ 2 alphabetic words or ≥ 10 chars). Anything ALL-CAPS is
    # also treated as a chapter.
    if re.match(r"^\s*[A-Z]", t) and len(t) >= 4:
        return ("chapter",)
    return None


def _disambiguate_named_duplicates(labels: list[str]) -> list[str]:
    """If multiple entries collapsed to the same named label (e.g. two
    "Introduction" segments), suffix them: intro, intro-2, intro-3."""
    seen: dict[str, int] = {}
    out = []
    for lab in labels:
        if lab is None:
            out.append(None); continue
        if lab in seen:
            seen[lab] += 1
            out.append(f"{lab}-{seen[lab]}")
        else:
            seen[lab] = 1
            out.append(lab)
    return out


def assign_book_numbers(chapters: list[dict]) -> None:
    """Mutate `chapters` in place, adding a `book_number` (str | None).

    Two-pass: classify by title, then sequentially number any
    ("chapter",) entries (bare titles) while respecting explicit numbers
    already declared in titles like "Chapter 7 — …".
    """
    kinds = [parse_book_number_kind(c.get("title") or "") for c in chapters]
    explicit_nums = {k[1] for k in kinds if k and k[0] in ("num", "rom")}
    next_n = 1
    raw_labels: list[str | None] = []
    for k in kinds:
        if k is None:
            raw_labels.append(None)
        elif k[0] in ("num", "rom"):
            raw_labels.append(f"ch{k[1]:02d}")
        elif k[0] == "named":
            raw_labels.append(k[1])
        elif k[0] == "appendix":
            raw_labels.append(f"appendix-{k[1]}")
        elif k[0] == "part":
            raw_labels.append(f"part-{k[1]}")
        elif k[0] in ("fm", "bm"):
            raw_labels.append(k[0])
        elif k[0] == "chapter":
            while next_n in explicit_nums:
                next_n += 1
            raw_labels.append(f"ch{next_n:02d}")
            next_n += 1
        else:
            raw_labels.append(None)
    labels = _disambiguate_named_duplicates(raw_labels)
    for ch, lab in zip(chapters, labels):
        if lab is None:
            # Classification failed for this title. Fall back to a
            # deterministic, easily-spottable label so no downstream
            # filename ever ends up as `None.txt`. The "-unclassified"
            # suffix lets the user grep for these and fix titles
            # manually if desired.
            lab = f"ch{ch['index']:02d}-unclassified"
        ch["book_number"] = lab


# --------------------------------------------------------------------------
# Reading-order block sorting (handles 1- and 2-column layouts)
# --------------------------------------------------------------------------

def sort_blocks_reading_order(blocks: list[dict], page_width: float) -> list[dict]:
    """Sort mixed text/image blocks into human reading order.

    `blocks` is a list of dicts with an 'bbox' = (x0, y0, x1, y1). Detects a
    simple two-column layout (a clear vertical gutter near the page centre) and
    reads the left column fully before the right; otherwise sorts top-to-bottom.
    Multi-column academic layouts beyond two columns are not handled precisely.
    """
    if not blocks:
        return []
    mid = page_width / 2.0
    left = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 < mid]
    right = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 >= mid]
    # Two-column only if both sides are substantially populated.
    if len(left) >= 3 and len(right) >= 3 and min(len(left), len(right)) / len(blocks) > 0.30:
        left.sort(key=lambda b: (round(b["bbox"][1], 1), b["bbox"][0]))
        right.sort(key=lambda b: (round(b["bbox"][1], 1), b["bbox"][0]))
        return left + right
    return sorted(blocks, key=lambda b: (round(b["bbox"][1], 1), b["bbox"][0]))


# --------------------------------------------------------------------------
# PDF extraction via PyMuPDF
# --------------------------------------------------------------------------

def extract_pdf_fitz(pdf_path: str, work: "WorkDir", mode: str,
                     min_image_dim: int, max_images: int) -> dict | None:
    """Primary PDF path. Returns an extraction result dict or None if fitz absent."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None

    doc = fitz.open(pdf_path)
    images_dir = work.images_dir
    images_dir.mkdir(parents=True, exist_ok=True)

    text_parts: list[str] = []
    page_offsets: list[int] = []      # char offset where each page begins
    image_manifest: list[dict] = []
    seen_hashes: dict[str, str] = {}  # content hash -> saved relative path
    scanned_pages = 0
    cursor = 0                        # running char offset into the assembled text

    want_images = mode != "text-only-fallback"

    for pno in range(doc.page_count):
        page = doc[pno]
        page_offsets.append(cursor)
        pw = page.rect.width or 612.0

        # --- gather text blocks ------------------------------------------
        items: list[dict] = []
        raw_text_len = 0
        try:
            for b in page.get_text("blocks"):
                # b = (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 7 and b[6] == 0 and b[4] and b[4].strip():
                    items.append({"kind": "text", "bbox": b[:4], "text": b[4]})
                    raw_text_len += len(b[4].strip())
        except Exception:
            pass

        # --- gather image placements -------------------------------------
        page_image_xrefs: list[tuple[int, tuple]] = []
        if want_images:
            try:
                for info in page.get_image_info(xrefs=True):
                    xref = info.get("xref", 0)
                    if xref:
                        page_image_xrefs.append((xref, tuple(info.get("bbox", (0, 0, 0, 0)))))
            except Exception:
                pass

        # --- decide: is this a scanned (image-only) page? ----------------
        is_scanned_page = (
            raw_text_len < SCANNED_PAGE_TEXT_THRESHOLD
            and len(page_image_xrefs) > 0
        )

        if is_scanned_page:
            scanned_pages += 1
            rel = f"images/page_{pno + 1:04d}.png"
            try:
                pix = page.get_pixmap(dpi=150)
                pix.save(str(work.dir / rel))
                image_manifest.append({
                    "type": "page_scan", "path": rel, "page": pno + 1,
                    "width": pix.width, "height": pix.height,
                    "est_tokens": est_image_tokens(pix.width, pix.height),
                })
                placeholder = f"\n[[PAGE_SCAN: {rel} | page {pno + 1}]]\n"
            except Exception:
                placeholder = f"\n[[PAGE_SCAN_FAILED: page {pno + 1}]]\n"
            text_parts.append(placeholder)
            cursor += len(placeholder)
            continue

        # --- normal page: interleave text + embedded images -------------
        for xref, bbox in page_image_xrefs:
            items.append({"kind": "image", "bbox": bbox, "xref": xref})

        ordered = sort_blocks_reading_order(items, pw)
        page_chunks: list[str] = []
        for it in ordered:
            if it["kind"] == "text":
                page_chunks.append(it["text"])
                continue
            # image block
            if len(image_manifest) >= max_images:
                continue
            xref = it["xref"]
            try:
                extracted = doc.extract_image(xref)
            except Exception:
                continue
            data = extracted.get("image")
            if not data:
                continue
            w, h = extracted.get("width", 0), extracted.get("height", 0)
            if min(w, h) < min_image_dim:
                continue  # decorative / too small to carry meaning
            digest = sha1_bytes(data)
            if digest in seen_hashes:
                continue  # repeated logo / ornament already captured
            ext = extracted.get("ext", "png")
            rel = f"images/img_p{pno + 1:04d}_x{xref}.{ext}"
            try:
                (work.dir / rel).write_bytes(data)
            except Exception:
                continue
            seen_hashes[digest] = rel
            image_manifest.append({
                "type": "figure", "path": rel, "page": pno + 1,
                "width": w, "height": h,
                "est_tokens": est_image_tokens(w, h),
            })
            page_chunks.append(f"\n[[IMAGE: {rel} | page {pno + 1}]]\n")

        # --- tables (technical mode only) --------------------------------
        if mode == "technical":
            try:
                tabs = page.find_tables()
                for t in tabs.tables:
                    md = t.to_markdown()
                    if md and md.strip():
                        page_chunks.append("\n" + md.strip() + "\n")
            except Exception:
                pass

        page_text = "\n".join(page_chunks).strip() + "\n\n"
        text_parts.append(page_text)
        cursor += len(page_text)

    full_text = "".join(text_parts)

    # --- chapter offset map ---------------------------------------------
    chapters = chapters_from_pdf_outline(doc, page_offsets, full_text)
    if len(chapters) < 2:
        chapters = chapters_from_heading_regex(full_text)

    meta_title = (doc.metadata or {}).get("title") or Path(pdf_path).stem
    meta_author = (doc.metadata or {}).get("author") or ""
    page_count = doc.page_count
    doc.close()

    scanned_ratio = scanned_pages / page_count if page_count else 0.0
    return {
        "full_text": full_text,
        "chapters": chapters,
        "images": image_manifest,
        "page_count": page_count,
        "title": meta_title,
        "author": meta_author,
        "method": "pymupdf",
        "scanned_pages": scanned_pages,
        "scanned_pages_ratio": round(scanned_ratio, 3),
        "scan_cost_warning": scanned_ratio >= 0.10,
        "is_scanned_document": scanned_ratio >= SCANNED_DOC_RATIO,
    }


def chapters_from_pdf_outline(doc, page_offsets: list[int], full_text: str) -> list[dict]:
    """Build chapter ranges from the PDF bookmark outline (the reliable path).

    Many books put Parts at level 1 and real chapters at level 2 — picking
    level 1 alone then yields a handful of huge "chapters" that defeat the
    map-reduce design. Strategy: try the shallowest level that produces (a)
    at least 4 entries and (b) a median slice under MAX_MEDIAN_CHARS. Fall
    back to mixed levels only if no single level qualifies.
    """
    try:
        toc = doc.get_toc(simple=True)  # [[level, title, page], ...]
    except Exception:
        return []
    if not toc:
        return []

    MAX_MEDIAN_CHARS = 60_000   # ~15K tokens — above this we drop a level

    def build(entries):
        raw = []
        for _level, title, page in entries:
            idx = max(0, min(page - 1, len(page_offsets) - 1))
            raw.append({"title": (title or "").strip(),
                        "char_start": page_offsets[idx]})
        raw.sort(key=lambda c: c["char_start"])
        return finalize_chapter_ranges(raw, len(full_text))

    def median_size(chs):
        if not chs:
            return 0
        sizes = sorted(c["char_end"] - c["char_start"] for c in chs)
        return sizes[len(sizes) // 2]

    # Try each depth from shallowest down to 3; pick the first one that has
    # enough entries AND a reasonable median chapter size.
    best = []
    for depth in (1, 2, 3):
        entries = [e for e in toc if e[0] <= depth]
        chs = build(entries)
        if len(chs) >= 4 and median_size(chs) <= MAX_MEDIAN_CHARS:
            return chs
        # Track the most-granular option as a fallback.
        if len(chs) > len(best):
            best = chs

    # Nothing met both bars — return the deepest option we found.
    return best


def chapters_from_heading_regex(full_text: str) -> list[dict]:
    """Fallback: detect chapter starts by scanning lines for heading patterns."""
    raw, offset = [], 0
    for line in full_text.splitlines(keepends=True):
        if CHAPTER_HEADING_RE.match(line) and len(line.strip()) < 90:
            raw.append({"title": line.strip(), "char_start": offset})
        offset += len(line)
    # Collapse near-duplicate detections (heading echoed in a running header).
    deduped = []
    for c in raw:
        if deduped and c["char_start"] - deduped[-1]["char_start"] < 400:
            continue
        deduped.append(c)
    if not deduped:
        deduped = [{"title": "Full Text", "char_start": 0}]
    return finalize_chapter_ranges(deduped, len(full_text))


def finalize_chapter_ranges(raw: list[dict], total_len: int) -> list[dict]:
    """Assign char_end, index, slug, and book_number to each detected
    chapter start. `index` is extraction order (stable internal id);
    `book_number` is the book-native label (`ch07`, `intro`, `preface`,
    `appendix-a`, `fm`, `bm`) used by all renderers."""
    out = []
    for i, c in enumerate(raw):
        end = raw[i + 1]["char_start"] if i + 1 < len(raw) else total_len
        if end <= c["char_start"]:
            continue
        out.append({
            "index": len(out) + 1,
            "title": c["title"] or f"Section {len(out) + 1}",
            "slug": slugify(c["title"]),
            "char_start": c["char_start"],
            "char_end": end,
            "est_tokens": (end - c["char_start"]) // CHARS_PER_TOKEN,
        })
    assign_book_numbers(out)
    return out


# --------------------------------------------------------------------------
# PDF text-only fallbacks (no images, used only if PyMuPDF is unavailable)
# --------------------------------------------------------------------------

def extract_pdf_text_only(pdf_path: str) -> dict | None:
    text = _pdftotext(pdf_path) or _pypdf(pdf_path)
    if not text or not text.strip():
        return None
    chapters = chapters_from_heading_regex(text)
    return {
        "full_text": text, "chapters": chapters, "images": [],
        "page_count": text.count("\f") + 1, "title": Path(pdf_path).stem,
        "author": "", "method": "text-only-fallback",
        "scanned_pages": 0, "scanned_pages_ratio": 0.0, "scan_cost_warning": False, "is_scanned_document": False,
    }


def _pdftotext(pdf_path: str) -> str | None:
    if not shutil.which("pdftotext"):
        return None
    try:
        r = subprocess.run(["pdftotext", "-layout", pdf_path, "-"],
                           capture_output=True, text=True, timeout=300)
        return r.stdout if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        return None


def _pypdf(pdf_path: str) -> str | None:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # legacy
        except ImportError:
            return None
    try:
        reader = PdfReader(pdf_path)
        return "\f".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return None


# --------------------------------------------------------------------------
# EPUB extraction
# --------------------------------------------------------------------------

class _HTMLText(html.parser.HTMLParser):
    """HTML -> text that also emits [[IMAGE: ..]] markers for <img> tags."""

    SKIP = {"script", "style", "head"}
    BLOCK = {"p", "br", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}

    def __init__(self, img_resolver):
        super().__init__()
        self._out: list[str] = []
        self._skip = 0
        self._img_resolver = img_resolver

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        if tag in self.BLOCK:
            self._out.append("\n")
        if tag == "img":
            src = dict(attrs).get("src", "")
            rel = self._img_resolver(src)
            if rel:
                self._out.append(f"\n[[IMAGE: {rel}]]\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self._out.append(data)

    def text(self) -> str:
        return html.unescape("".join(self._out))


def extract_epub(epub_path: str, work: "WorkDir",
                 min_image_dim: int, max_images: int) -> dict | None:
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        return _extract_epub_stdlib(epub_path, work)

    try:
        book = epub.read_epub(epub_path)
    except Exception:
        return _extract_epub_stdlib(epub_path, work)

    images_dir = work.images_dir
    images_dir.mkdir(parents=True, exist_ok=True)

    # Save every image item up front; map original href -> saved relative path.
    href_to_rel: dict[str, str] = {}
    image_manifest: list[dict] = []
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        if len(image_manifest) >= max_images:
            break
        data = item.get_content()
        if not data:
            continue
        name = Path(item.get_name()).name
        rel = f"images/{name}"
        try:
            (work.dir / rel).write_bytes(data)
        except Exception:
            continue
        w, h = _image_dims(data)
        if w and h and min(w, h) < min_image_dim:
            # keep the file but it likely will not be worth a vision read
            pass
        image_manifest.append({
            "type": "figure", "path": rel, "page": None,
            "width": w, "height": h,
            "est_tokens": est_image_tokens(w or 600, h or 600),
        })
        # index by several href spellings so resolver lookups hit
        for key in {item.get_name(), name, "../" + item.get_name()}:
            href_to_rel[key] = rel

    def resolve(src: str) -> str | None:
        if not src:
            return None
        cand = src.split("/")[-1]
        return href_to_rel.get(src) or href_to_rel.get(cand)

    # Walk the spine: each spine document is treated as one chapter.
    text_parts: list[str] = []
    chapters_raw: list[dict] = []
    cursor = 0
    skip_names = ("nav", "toc", "cover", "title", "copyright")
    for spine_id, _linear in book.spine:
        item = book.get_item_with_id(spine_id)
        if item is None:
            continue
        # Skip navigation / front-matter documents — they are not chapters.
        if getattr(item, "get_type", lambda: None)() == ebooklib.ITEM_NAVIGATION:
            continue
        name_l = (item.get_name() or "").lower()
        if any(k in name_l for k in skip_names):
            continue
        try:
            raw_html = item.get_content().decode("utf-8", errors="replace")
        except Exception:
            continue
        parser = _HTMLText(resolve)
        parser.feed(raw_html)
        body = parser.text().strip()
        if not body:
            continue
        title = _first_heading(raw_html) or Path(item.get_name()).stem
        chapters_raw.append({"title": title, "char_start": cursor})
        block = body + "\n\n"
        text_parts.append(block)
        cursor += len(block)

    full_text = "".join(text_parts)
    title = book.get_metadata("DC", "title")
    author = book.get_metadata("DC", "creator")
    return {
        "full_text": full_text,
        "chapters": finalize_chapter_ranges(chapters_raw, len(full_text)),
        "images": image_manifest,
        "page_count": len(chapters_raw),
        "title": (title[0][0] if title else Path(epub_path).stem),
        "author": (author[0][0] if author else ""),
        "method": "ebooklib",
        "scanned_pages": 0,
        "scanned_pages_ratio": 0.0,
        "scan_cost_warning": False,
        "is_scanned_document": False,
    }


def _extract_epub_stdlib(epub_path: str, work: "WorkDir") -> dict | None:
    """Last-resort EPUB extractor using only the standard library (text only)."""
    try:
        with zipfile.ZipFile(epub_path) as zf:
            names = zf.namelist()
            opf = next((n for n in names if n.endswith(".opf")), None)
            order = []
            if opf:
                opf_text = zf.read(opf).decode("utf-8", errors="replace")
                order = re.findall(r'href=["\']([^"\']+\.x?html)["\']', opf_text)
            html_files = order or sorted(n for n in names if n.endswith((".html", ".xhtml")))
            parts, chapters_raw, cursor = [], [], 0
            for name in html_files:
                try:
                    raw = zf.read(name).decode("utf-8", errors="replace")
                except Exception:
                    continue
                p = _HTMLText(lambda s: None)
                p.feed(raw)
                body = p.text().strip()
                if not body:
                    continue
                chapters_raw.append({
                    "title": _first_heading(raw) or Path(name).stem,
                    "char_start": cursor,
                })
                block = body + "\n\n"
                parts.append(block)
                cursor += len(block)
            full_text = "".join(parts)
            if not full_text.strip():
                return None
            return {
                "full_text": full_text,
                "chapters": finalize_chapter_ranges(chapters_raw, len(full_text)),
                "images": [], "page_count": len(chapters_raw),
                "title": Path(epub_path).stem, "author": "",
                "method": "zipfile-stdlib",
                "scanned_pages": 0, "scanned_pages_ratio": 0.0, "scan_cost_warning": False, "is_scanned_document": False,
            }
    except Exception:
        return None


def _first_heading(raw_html: str) -> str | None:
    m = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", raw_html, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() or None


def _image_dims(data: bytes) -> tuple[int, int]:
    try:
        import fitz
        pix = fitz.Pixmap(data)
        return pix.width, pix.height
    except Exception:
        return 0, 0


# --------------------------------------------------------------------------
# Work directory
# --------------------------------------------------------------------------

class WorkDir:
    def __init__(self, path: str):
        self.dir = Path(path)
        self.images_dir = self.dir / "images"
        self.text_file = self.dir / "full_text.txt"
        self.meta_file = self.dir / "metadata.json"
        self.spine_file = self.dir / "spine.md"
        self.progress_file = self.dir / "progress.json"


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="book-to-skill Stage 0 extractor")
    ap.add_argument("book", help="path to a .pdf or .epub file")
    ap.add_argument("--mode", choices=["technical", "text"], default="text")
    ap.add_argument("--genre", default="general")
    ap.add_argument("--work-dir", default="/tmp/book_skill_work")
    ap.add_argument("--min-image-dim", type=int, default=None,
                    help="minimum image short-edge px; default depends on --genre")
    ap.add_argument("--max-images", type=int, default=400)
    ap.add_argument("--coverage", choices=["standard", "complete"], default="standard",
                    help="complete: floor the image threshold to 110px so real "
                         "figures aren't dropped before the LLM sees them "
                         "(used by /book-to-skill complete-coverage mode)")
    ap.add_argument("--resume", action="store_true",
                    help="skip extraction if outputs already match the source")
    args = ap.parse_args()

    if not os.path.exists(args.book):
        print(f"ERROR: file not found: {args.book}", file=sys.stderr)
        return 1

    work = WorkDir(args.work_dir)
    src_hash = sha1_file(args.book)

    # Resume: reuse a previous extraction if it is for the same source file.
    if args.resume and work.meta_file.exists():
        try:
            prev = json.loads(work.meta_file.read_text())
            if prev.get("source_sha1") == src_hash and work.text_file.exists():
                print(f"RESUME: reusing existing extraction in {work.dir}")
                print(json.dumps({"resumed": True, **{
                    k: prev.get(k) for k in
                    ("chapter_count", "image_count", "estimated_total_tokens")
                }}, indent=2))
                return 0
        except Exception:
            pass

    work.dir.mkdir(parents=True, exist_ok=True)

    ext = Path(args.book).suffix.lower()
    if ext not in (".pdf", ".epub"):
        with open(args.book, "rb") as f:
            head = f.read(8)
        if head[:4] == b"%PDF":
            ext = ".pdf"
        elif head[:2] == b"PK":
            ext = ".epub"
        else:
            print("ERROR: unsupported format. Supported: .pdf, .epub", file=sys.stderr)
            return 1

    min_dim = (args.min_image_dim if args.min_image_dim is not None
               else GENRE_MIN_IMAGE_DIM.get(args.genre, DEFAULT_MIN_IMAGE_DIM))
    # Complete-coverage mode must not drop a real figure before the LLM ever
    # sees it. Floor the genre threshold to the technical baseline (110px) — an
    # explicit --min-image-dim still wins. (seen_hashes + max_images still bound
    # cost; the Step-7.5 coverage audit classifies any survivor as load-bearing
    # vs decorative.)
    if args.coverage == "complete" and args.min_image_dim is None:
        min_dim = min(min_dim, 110)

    print(f"Extracting {ext.upper()[1:]}: {args.book}")
    print(f"  mode={args.mode} genre={args.genre} coverage={args.coverage} min_image_dim={min_dim}px")

    if ext == ".pdf":
        result = extract_pdf_fitz(args.book, work, args.mode, min_dim, args.max_images)
        if result is None:
            print("  PyMuPDF unavailable -> text-only fallback (images will be skipped)")
            result = extract_pdf_text_only(args.book)
    else:
        result = extract_epub(args.book, work, min_dim, args.max_images)

    if result is None or not result["full_text"].strip():
        print("ERROR: extraction produced no text.\n"
              "  Install PyMuPDF for best results:  pip3 install PyMuPDF ebooklib beautifulsoup4",
              file=sys.stderr)
        return 1

    full_text = result["full_text"]
    work.text_file.write_text(full_text, encoding="utf-8")

    # Pre-cut each chapter into its own raw text file. Stage 1 subagents then
    # read one whole file instead of slicing full_text.txt by char offset.
    raw_dir = work.dir / "raw_chapters"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for ch in result["chapters"]:
        slice_text = full_text[ch["char_start"]:ch["char_end"]]
        # File stem uses book_number when available (canonical, book-native);
        # falls back to extraction-order index only if classification failed.
        stem = ch.get("book_number") or f"ch{ch['index']:02d}"
        raw_path = raw_dir / f"{stem}.txt"
        raw_path.write_text(slice_text, encoding="utf-8")
        ch["raw_text_path"] = str(raw_path)

    text_tokens = est_text_tokens(full_text)
    image_tokens = sum(img.get("est_tokens", 0) for img in result["images"])

    # Chapter-granularity diagnosis: warn if extracted slices look like Parts
    # (too few, or each one too big) rather than real chapters.
    chapter_sizes = sorted(c["char_end"] - c["char_start"] for c in result["chapters"]) or [0]
    median_chapter_chars = chapter_sizes[len(chapter_sizes) // 2]
    granularity_warning = None
    if len(result["chapters"]) < 5:
        granularity_warning = (
            f"only {len(result['chapters'])} chapter(s) detected — "
            f"likely Part-level over-merging; consider manual re-split"
        )
    elif median_chapter_chars > 50_000:
        granularity_warning = (
            f"median chapter is {median_chapter_chars:,} chars "
            f"(~{median_chapter_chars // 4:,} tokens) — likely contains "
            f"multiple real chapters; consider manual re-split"
        )

    metadata = {
        "source_file": str(Path(args.book).resolve()),
        "source_sha1": src_hash,
        "filename": Path(args.book).name,
        "format": ext[1:],
        "extraction_method": result["method"],
        "extraction_mode": args.mode,
        "genre": args.genre,
        "title": result["title"],
        "author": result["author"],
        "page_count": result["page_count"],
        "chars": len(full_text),
        "words": len(full_text.split()),
        "estimated_text_tokens": text_tokens,
        "estimated_image_tokens": image_tokens,
        "estimated_total_tokens": text_tokens + image_tokens,
        "chapter_count": len(result["chapters"]),
        "chapters": result["chapters"],
        "chapters_source": "raw_chapters",
        "granularity_warning": granularity_warning,
        "median_chapter_chars": median_chapter_chars,
        "image_count": len(result["images"]),
        "images": result["images"],
        "scanned_pages": result["scanned_pages"],
        "scanned_pages_ratio": result.get("scanned_pages_ratio", 0.0),
        "scan_cost_warning": result.get("scan_cost_warning", False),
        "is_scanned_document": result["is_scanned_document"],
        "work_dir": str(work.dir),
        "full_text_path": str(work.text_file),
    }
    work.meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

    print("\nExtraction complete:")
    print(f"  Title       : {result['title']}")
    print(f"  Method      : {result['method']}")
    print(f"  Pages/items : {result['page_count']}")
    print(f"  Words       : {len(full_text.split()):,}")
    print(f"  Chapters    : {len(result['chapters'])} (offset map written)")
    print(f"  Images kept : {len(result['images'])}  (~{image_tokens:,} vision tokens)")
    print(f"  Text tokens : ~{text_tokens:,}")
    if result["is_scanned_document"]:
        print(f"  NOTE        : looks like a SCANNED document "
              f"({result['scanned_pages']} image-only pages) — "
              f"chapter text will come from vision OCR, expect higher cost.")
    elif result.get("scan_cost_warning"):
        print(f"  WARNING     : {result['scanned_pages']} of "
              f"{result['page_count']} pages are image-only "
              f"({result.get('scanned_pages_ratio', 0):.0%}) — "
              f"vision-OCR cost will be elevated.", file=sys.stderr)
    if granularity_warning:
        print(f"  WARNING     : chapter granularity — {granularity_warning}",
              file=sys.stderr)
    print(f"\n  text -> {work.text_file}")
    print(f"  meta -> {work.meta_file}")
    print(f"  imgs -> {work.images_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
