"""Lightweight wrapper to produce canonical (text-only) JSON from a PDF.

Designed for downstream repos like ../pre_auth.git to call/import.

Usage (CLI):
  python -m src.extract_pdf_preauth /path/to/foo.pdf --out /path/to/out.json

Programmatic API:
  from src.extract_pdf_preauth import extract_to_canonical
  d = extract_to_canonical("data/pdf_analysis/user_1234.pdf")

This will run the extractor with spans disabled and return the canonical JSON
as produced by build_text_only_gt(rec, include_spans=False).
"""
from __future__ import annotations
from pathlib import Path
import json
import argparse
import sys

# allow running from repo root without installing
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scripts.pdf_color_extraction import extract_pdf_all_fields
from scripts.pdf_to_ground_truth import build_text_only_gt


def extract_to_canonical(pdf_path: str | Path) -> dict:
    """Extract the PDF and return the canonical text-only ground-truth dict.

    This intentionally runs without spans and drops layout metadata.
    """
    pdf_path = str(pdf_path)
    rec = extract_pdf_all_fields(pdf_path, include_spans=False)
    canon = build_text_only_gt(rec, include_spans=False)
    return canon


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="extract_pdf_preauth")
    ap.add_argument("pdf", help="path to PDF file")
    ap.add_argument("--out", help="optional output path for canonical JSON (default stdout)")
    args = ap.parse_args(argv)

    out = extract_to_canonical(args.pdf)
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("WROTE", p)
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())