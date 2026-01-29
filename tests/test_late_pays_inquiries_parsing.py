import json
from pathlib import Path
import pytest
pytest.importorskip("fitz", reason="PyMuPDF required for PDF extraction")

from src.scripts.pdf_color_extraction import extract_pdf_all_fields

CASES = [
    ("user_1140_credit_summary_2025-09-01_132703", {'late_pays_gt2yr': 6}),
    ("user_1314_credit_summary_2025-09-01_092724", {'inquiries_last_6_months': 2}),
    ("user_582_credit_summary_2025-09-01_100800", {'late_pays_gt2yr': 1}),
    ("user_692_credit_summary_2025-09-01_105038", {'late_pays_gt2yr': 40}),
]

@pytest.mark.parametrize("uid,expected", CASES)
def test_late_pays_and_inquiries_parsing(uid, expected):
    pdf = Path(f'data/pdf_analysis/{uid}.pdf')
    rec = extract_pdf_all_fields(str(pdf), include_spans=True)
    # normalize to top-level flattened keys
    if 'rec' in rec and isinstance(rec['rec'], dict):
        rec = rec['rec']
    for k, v in expected.items():
        assert rec.get(k) == v, f"{uid}: expected {k}={v} got {rec.get(k)}"
