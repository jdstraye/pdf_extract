import pytest
from src.scripts.pdf_color_extraction import compute_candidate_score


def test_compute_score_paid_off_and_numeric():
    cand = {'factor': 'Paid Off 200k+ RE/RE', 'hex': None, 'color': None}
    score = compute_candidate_score(cand)
    # short line (len<40) -> +2, has digits -> +1, has 'paid' -> +1 => total >=4
    assert score >= 3


def test_compute_score_colored_span_strong():
    cand = {'factor': 'Some Factor', 'hex': '#ff0000', 'color': 'red'}
    score = compute_candidate_score(cand)
    assert score >= 5
