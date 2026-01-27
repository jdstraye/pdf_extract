from src.scripts.pdf_color_extraction import sort_factors_by_bbox


def test_sort_by_bbox_simple():
    cfs = [
        {'factor': 'A', 'page': 0, 'bbox': [0, 10, 1, 11]},
        {'factor': 'B', 'page': 0, 'bbox': [0, 5, 1, 6]},
        {'factor': 'C', 'page': 1, 'bbox': [0, 2, 1, 3]},
        {'factor': 'D'},
    ]
    out = sort_factors_by_bbox(cfs)
    assert [f['factor'] for f in out] == ['B', 'A', 'C', 'D']
