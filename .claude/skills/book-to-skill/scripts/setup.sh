#!/usr/bin/env bash
# book-to-skill — dependency setup (uv-based).
#
# Creates a uv-managed virtual environment inside the skill directory and
# installs the Python libraries the extractor needs. Safe to run repeatedly:
# if the venv exists and everything imports, it exits immediately.
#
#   PyMuPDF        primary backend — text, images, tables, outline, rendering
#   ebooklib       EPUB parsing
#   beautifulsoup4 EPUB HTML handling
#   pypdf          text-only PDF fallback (used only if PyMuPDF is unavailable)
set -u

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQ="${SKILL_DIR}/requirements.txt"
VENV_DIR="${SKILL_DIR}/.venv"

if ! command -v uv >/dev/null 2>&1; then
  echo "book-to-skill: 'uv' is required but not installed." >&2
  echo "  Install with:  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  echo "  (or)           brew install uv" >&2
  exit 1
fi

check() {
  [ -x "${VENV_DIR}/bin/python" ] || return 1
  "${VENV_DIR}/bin/python" - <<'PY' 2>/dev/null
import importlib, sys
for mod in ("fitz", "ebooklib", "bs4", "pypdf"):
    try:
        importlib.import_module(mod)
    except Exception:
        sys.exit(1)
sys.exit(0)
PY
}

if [ -d "${VENV_DIR}" ] && check; then
  echo "book-to-skill: all extraction dependencies present."
  exit 0
fi

echo "book-to-skill: creating uv venv and installing extraction dependencies..."

# Create the venv if missing.
if [ ! -d "${VENV_DIR}" ]; then
  uv venv --python 3.10 "${VENV_DIR}" || {
    echo "book-to-skill: failed to create venv with uv." >&2
    exit 1
  }
fi

# Install dependencies into the skill's venv.
if ! VIRTUAL_ENV="${VENV_DIR}" uv pip install -r "${REQ}"; then
  echo "WARNING: uv pip install did not succeed cleanly." >&2
  echo "         Install manually:  VIRTUAL_ENV=${VENV_DIR} uv pip install -r ${REQ}" >&2
fi

# poppler-utils gives the text-only pdftotext fallback. Best-effort only —
# never fail the run over it; PyMuPDF already covers the primary path.
if ! command -v pdftotext >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get install -y poppler-utils >/dev/null 2>&1 || true
  elif command -v brew >/dev/null 2>&1; then
    brew install poppler >/dev/null 2>&1 || true
  fi
fi

if check; then
  echo "book-to-skill: dependencies ready (venv at ${VENV_DIR})."
  exit 0
else
  echo "book-to-skill: core dependencies still missing — the extractor will" >&2
  echo "run in reduced (text-only, no images) mode if PyMuPDF is unavailable." >&2
  exit 0
fi
