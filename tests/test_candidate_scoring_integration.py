import pytest
from src.scripts.pdf_color_extraction import extract_pdf_all_fields
from pathlib import Path


def test_include_candidate_scores_for_user_1314():
    pdf_path = '/home/jdstraye/proj/shifi/pdf_extract.git/data/pdf_analysis/user_1314_credit_summary_2025-09-01_092724.pdf'
    rec = extract_pdf_all_fields(pdf_path, include_spans=True, include_candidate_scores=True)
    assert 'candidate_scores' in rec
    cs = rec['candidate_scores']
    assert isinstance(cs, list)
    # each entry should have factor and integer score
    assert all('factor' in c and 'score' in c for c in cs)
    assert all(isinstance(c['score'], int) for c in cs)
