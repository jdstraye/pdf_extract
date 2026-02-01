import json
from pathlib import Path

GT_DIR = Path('data/extracted')

def _load_gt(p: Path):
    s = json.loads(p.read_text(encoding='utf-8'))
    if isinstance(s, dict) and 'rec' in s and isinstance(s['rec'], dict):
        return s['rec']
    return s


def test_late_pays_canonical_structure():
    files = sorted(GT_DIR.glob('*_ground_truth.json'))
    bad = []
    for p in files:
        gt = _load_gt(p)
        # flat keys are canonical: ensure both exist and are integers
        lt = gt.get('late_pays_lt2yr')
        gt2 = gt.get('late_pays_gt2yr')
        if lt is None or gt2 is None:
            bad.append((p.name, 'missing flat late_pays_lt2yr or late_pays_gt2yr'))
            continue
        if not isinstance(lt, int) or not isinstance(gt2, int):
            bad.append((p.name, 'late_pays flat subfields not integers'))
        # if nested late_pays exists, ensure its values match the flat keys
        lp = gt.get('late_pays')
        if lp is not None:
            if lp.get('last_2_years') != lt:
                bad.append((p.name, 'nested last_2_years mismatch vs flat'))
            if lp.get('last_over_2_years') != gt2:
                bad.append((p.name, 'nested last_over_2_years mismatch vs flat'))
    assert not bad, f"Found late_pays canonicalization issues: {bad}"
