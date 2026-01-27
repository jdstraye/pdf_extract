import fitz
import tempfile
from pathlib import Path
from src.scripts.pdf_color_extraction import extract_pdf_all_fields


def _make_tmp_pdf(lines, tmp_path: Path):
    doc = fitz.open()
    y = 20
    for text, color in lines:
        # color expected as None or RGB tuple of floats
        if color is not None:
            doc.new_page()
            p = doc[-1]
            p.insert_text((20, y), text, fontsize=11, color=color)
        else:
            # append to first page
            if len(doc) == 0:
                doc.new_page()
            p = doc[0]
            p.insert_text((20, y), text, fontsize=11)
        y += 20
    out = tmp_path / 'tmp.pdf'
    doc.save(str(out))
    doc.close()
    return out


def test_credit_card_open_totals_and_monthly_color_flags(tmp_path):
    # Construct a minimal PDF with relevant lines
    lines = [
        ('Credit Card Open Totals', None),
        ('$20,483', (1.0, 0.0, 0.0)),  # red-ish
        ('$17,650 116%', None),
        ('$549', None),
        ('$123/mo', (1.0, 0.0, 0.0)),  # red monthly payments so color is detected
    ]
    pdf_path = _make_tmp_pdf(lines, tmp_path)

    # When include_spans=False, top-level color keys should not be present
    rec_no_spans = extract_pdf_all_fields(str(pdf_path), include_spans=False)
    assert 'credit_card_open_totals' in rec_no_spans
    assert 'hex' not in rec_no_spans['credit_card_open_totals']
    assert 'monthly_payments_color' not in rec_no_spans or rec_no_spans.get('monthly_payments_color') is None

    # When include_spans=True, monthly_payments_color should be set and bbox attached
    rec_spans = extract_pdf_all_fields(str(pdf_path), include_spans=True)
    assert 'credit_card_open_totals' in rec_spans
    assert 'hex' not in rec_spans['credit_card_open_totals']
    assert rec_spans.get('monthly_payments_color') is not None
    assert 'monthly_payments_bbox' in rec_spans