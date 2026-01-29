"""Lightweight pdf color extraction helpers (test-focused)

This module provides a small, well-documented subset of the original
extractor used by the test suite. It intentionally implements simple,
readable logic sufficient for unit tests and for iterating on extraction
quality in follow-up work.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Tuple


def parse_count_amount_pair(s: str) -> Tuple[Optional[int], Optional[int]]:
    s = (s or "").strip()
    # Ignore obvious monthly-payment phrases (e.g., "$123/mo")
    if re.search(r"\bmo\b|/mo|per month", s, flags=re.IGNORECASE):
        return None, None
    if "/" not in s:
        return None, None
    parts = [p.strip() for p in s.split("/")]
    count = None
    amount = None
    for p in parts:
        if re.search(r"\$\s*[0-9,]+", p):
            amount = int(re.sub(r"[^0-9]", "", p))
        elif re.search(r"\d", p):
            count = int(re.sub(r"[^0-9]", "", p))
    return count, amount


def parse_public_records(txt: str) -> Tuple[Optional[int], str]:
    txt = (txt or "").strip()
    # Look for a clear numeric following "Public Records" or a standalone line.
    m = re.search(r"Public Records[:\s]*\n?\s*(\d+)", txt, flags=re.IGNORECASE)
    if m:
        return int(m.group(1)), ""
    # fallback: search for an isolated line containing only a digit near the phrase
    if "Public Records" in txt:
        lines = txt.splitlines()
        for i, L in enumerate(lines):
            if "Public Records" in L:
                # check next non-empty line
                for nxt in lines[i + 1 : i + 4]:
                    if nxt.strip().isdigit():
                        return int(nxt.strip()), ""
    return None, ""


def parse_count_count_pair(s: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse 'n / m' where both are integers (e.g., collections open/closed)."""
    if not s:
        return None, None
    m = re.search(r"(\d+)\s*/\s*(\d+)", s)
    if m:
        try:
            return int(m.group(1)), int(m.group(2))
        except Exception:
            return None, None
    return None, None


def load_expectations_from_dir(d: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not d.exists():
        return out
    for p in d.glob("**/*.json"):
        try:
            with p.open("r", encoding="utf8") as fh:
                out[str(p)] = json.load(fh)
        except Exception:
            # ignore non-json files or parse errors for tests
            out[str(p)] = None
    return out


def median_5x5(pixels: List[List[int]]) -> int:
    # Very small fallback median for a 5x5 block represented as nested lists
    vals = [v for row in pixels for v in row]
    if not vals:
        return 0
    return int(median(vals))


# Color helpers (small, deterministic mapping used by pdf_to_ground_truth and tests)
def hex_to_rgb(h: Optional[str]) -> Optional[Tuple[int,int,int]]:
    if not h or not isinstance(h, str):
        return None
    h = h.strip().lstrip('#')
    if len(h) != 6:
        return None
    try:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return (r,g,b)
    except Exception:
        return None


def map_color_to_cat(rgb: Tuple[int,int,int]) -> str:
    """Map an RGB color to a coarse category: 'red', 'green', 'black', 'neutral'.

    Refined heuristics: treat orange/amber-like hues (where green is still fairly high)
    as 'neutral' rather than 'red' to match GT labeling for amber-ish scores.
    """
    if not rgb or not isinstance(rgb, tuple) or len(rgb) != 3:
        return 'black'
    r,g,b = rgb
    # refined red: require red dominance but not a high green component (avoid amber/orange)
    if r > g + 40 and r > b + 40 and r > 100 and g < 120:
        return 'red'
    if g > r + 40 and g > b + 40 and g > 100:
        return 'green'
    # dark greys considered black
    if r < 80 and g < 80 and b < 80:
        return 'black'
    return 'neutral'


def normalize_address_string(s: str) -> str:
    """Normalize an address string into a deterministic form.

    Examples:
    - '3070 Lakecrest Cir\nLexington, KY. 40513' -> '3070 Lakecrest Cir, Lexington, KY 40513'
    - '1208 LEMOND DR, MIDDLETOWN, DE. 19709' -> '1208 Lemond Dr, Middletown, DE 19709'
    """
    import re
    def titleize(part: str) -> str:
        return ' '.join([w.capitalize() for w in re.split(r"\s+", part.strip()) if w])
    s0 = (s or '').replace('.', '')
    s0 = re.sub(r'\s+', ' ', s0).strip()
    # Try pattern: 'Street, City, ST ZIP'
    m = re.search(r'(?P<street>.*?),\s*(?P<city>[A-Za-z\.\s]+),?\s*(?P<state>[A-Za-z]{2})\.?\s*(?P<zip>\d{5})', s0)
    if m:
        street = m.group('street').strip()
        city = m.group('city').strip()
        state = m.group('state').upper()
        zipc = m.group('zip')
        return f"{titleize(street)}, {titleize(city)}, {state} {zipc}"
    # Try newline-separated 'Street\nCity, ST ZIP'
    if '\n' in s0:
        parts = [p.strip() for p in s0.splitlines() if p.strip()]
        if len(parts) >= 2:
            street = parts[0]
            city = parts[-1]
            m2 = re.search(r'(?P<cityname>.*),\s*(?P<state>[A-Za-z]{2})\.?\s*(?P<zip>\d{5})', city)
            if m2:
                cityname = m2.group('cityname').strip()
                state = m2.group('state').upper()
                zipc = m2.group('zip')
                return f"{titleize(street)}, {titleize(cityname)}, {state} {zipc}"
    # Fallback: Title-case and remove extra punctuation
    s2 = re.sub(r'\s*,\s*', ', ', s0)
    return titleize(s2)


def extract_credit_factors_from_doc(doc: Any, page_limit: int = 2) -> List[Dict[str, Any]]:
    """Minimal extractor that returns an empty-but-valid list for tests.

    A fuller implementation belongs in the canonical extractor. This
    simple version avoids heavy dependencies while tests are being
    iterated on.
    """
    out: List[Dict[str, Any]] = []
    # Attempt to iterate small number of pages when a fitz.Document is passed
    try:
        for i, page in enumerate(doc):
            if i >= page_limit:
                break
            # Return a placeholder dict for each page to keep types consistent
            out.append({"factor": f"page_{i}_placeholder", "page": i, "bbox": [0, 0, 0, 0]})
    except Exception:
        # If doc is not an iterator, return empty list
        return []
    return out


def extract_pdf_all_fields(doc_or_path: Any, page_limit: int = 2, include_spans: bool = False, include_candidate_scores: bool = False) -> Dict[str, Any]:
    """Extract a minimal record object from a PDF path or opened doc.

    Parameters are intentionally permissive to mirror the test-suite
    expectations. This implementation is conservative and returns
    predictable shapes for use in higher-level mapping logic and tests.
    """
    import fitz

    # open path if necessary
    doc = None
    path_input = None
    if isinstance(doc_or_path, (str, os.PathLike)):
        path_input = str(doc_or_path)
        doc = fitz.open(str(doc_or_path))
    else:
        doc = doc_or_path

    rec: Dict[str, Any] = {}
    # record source path & filename for canonicalization
    if path_input:
        rec['pdf_file'] = path_input
        rec['source'] = path_input
        try:
            rec['filename'] = os.path.basename(path_input)
        except Exception:
            pass

    # lines representation used by attach_spans_to_gt tests
    all_lines: List[Dict[str, Any]] = []

    def _intcolor_to_rgb(ci: Any) -> Optional[Tuple[int,int,int]]:
        try:
            ci = int(ci)
            r = (ci >> 16) & 255
            g = (ci >> 8) & 255
            b = ci & 255
            return (r, g, b)
        except Exception:
            return None

    try:
        for pi, page in enumerate(doc):
            # use the dict text output to get span-level color metadata
            pdict = page.get_text("dict")
            for b in pdict.get("blocks", []):
                for ln in b.get("lines", []):
                    spans = []
                    for s in ln.get("spans", []):
                        st = s.get("text", "")
                        span = {"text": st}
                        # convert numeric color to rgb/hex when available (populate so
                        # factor color detection works even when include_spans=False)
                        if s.get("color") is not None:
                            rgb = _intcolor_to_rgb(s.get("color"))
                            if rgb:
                                span["rgb"] = rgb
                                span["hex"] = "#" + "".join(f"{c:02x}" for c in rgb)
                        spans.append(span)
                    if not spans:
                        continue
                    bbox = ln.get("bbox") or b.get("bbox") or [0,0,0,0]
                    line = {"page": pi, "spans": spans, "bbox": [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])]} 
                    all_lines.append(line)
    except Exception:
        # if doc is not iterable or has no pages
        all_lines = []

    rec["all_lines_obj"] = all_lines
    # populate a minimal credit_factors list (one per page placeholder)
    rec["credit_factors"] = extract_credit_factors_from_doc(doc, page_limit=page_limit)

    # credit card open totals: collect nearby $-prefixed lines after a heading
    cco_idx = None
    for i, ln in enumerate(all_lines):
        txt = (ln.get("spans", [])[0].get("text", "") or "").lower()
        if "credit card open totals" in txt:
            cco_idx = i
            break
    if cco_idx is not None:
        amounts = []
        for nxt in all_lines[cco_idx + 1 : cco_idx + 6]:
            t = (nxt.get("spans", [])[0].get("text", "") or "").strip()
            if t.startswith("$") or re.search(r"\$\d", t):
                amounts.append(t)
        rec["credit_card_open_totals"] = {"amounts": amounts}
        # when spans requested, try to infer a color for the credit card totals from nearby spans
        if include_spans:
            for nxt in all_lines[cco_idx + 1 : cco_idx + 6]:
                spans = nxt.get('spans') or []
                # prefer span that contains the monetary token
                preferred = None
                for s in spans:
                    if s.get('text') and ('$' in s.get('text') or re.search(r"\$\d", s.get('text'))):
                        preferred = s
                        break
                # otherwise prefer any colored span
                if not preferred:
                    for s in spans:
                        if s.get('rgb') or s.get('hex'):
                            preferred = s
                            break
                if not preferred:
                    continue
                rgb = None
                if preferred.get('rgb'):
                    rgb = tuple(preferred.get('rgb'))
                elif preferred.get('hex'):
                    rgb = hex_to_rgb(preferred.get('hex'))
                if rgb:
                    rec['credit_card_open_totals_color'] = map_color_to_cat(rgb)
                    rec['credit_card_open_totals_bbox'] = nxt.get('bbox')
                    rec['credit_card_open_totals_page'] = nxt.get('page')
                    rec['credit_card_open_totals_spans'] = spans
                    break
    # monthly payments color detection (test-oriented)
    if include_spans:
        mp_line = None
        for ln in all_lines:
            if "/mo" in (" " + ln.get("spans", [])[0].get("text", "")) or "/mo" in ln.get("spans", [])[0].get("text", ""):
                mp_line = ln
                break
        if mp_line:
            spans = mp_line.get('spans') or []
            preferred = None
            for s in spans:
                if s.get('text') and ('/mo' in s.get('text') or '$' in s.get('text')):
                    preferred = s
                    break
            if not preferred and spans:
                preferred = spans[0]
            if preferred:
                if preferred.get('hex'):
                    rec["monthly_payments_color"] = preferred.get("hex")
                elif preferred.get('rgb'):
                    rec["monthly_payments_color"] = "#%02x%02x%02x" % tuple(preferred.get('rgb'))
                rec["monthly_payments_bbox"] = mp_line.get("bbox")
    else:
        # no spans requested; do not expose color or bbox
        rec.setdefault("monthly_payments_color", None)

    # ---- Table and top-level field detection (small, test-focused heuristics)
    def _line_text(ln):
        if not ln:
            return ''
        if ln.get('spans'):
            return '\n'.join([s.get('text','') for s in ln.get('spans')]).strip()
        return ln.get('text','').strip()

    # Age (e.g., 'Age: 49')
    for ln in all_lines:
        txt = _line_text(ln)
        m = re.search(r'Age[:\s]*([0-9]{1,3})', txt, flags=re.IGNORECASE)
        if m:
            try:
                rec['age'] = int(m.group(1))
            except Exception:
                pass
            break

    # Addresses: detect contiguous street block(s) followed by city block(s) and pair them in order
    addresses = []
    street_like = re.compile(r"\d+|\b(st|rd|dr|ln|ave|blvd|way|ct|circle|ste|suite)\b", re.IGNORECASE)
    city_like = re.compile(r"\b[A-Za-z][A-Za-z\.\s]+,\s*[A-Z]{2}\.?\s*\d{5}\b")
    i = 0
    while i < len(all_lines):
        # collect a block of street-like lines
        streets = []
        while i < len(all_lines) and street_like.search(_line_text(all_lines[i]) or '') and not city_like.search(_line_text(all_lines[i]) or ''):
            t = _line_text(all_lines[i]).strip()
            if t and not re.search(r'credit|age|name|report date|categories', t.lower()):
                streets.append(t)
            i += 1
        # collect a block of city-like lines immediately following
        cities = []
        j = i
        while j < len(all_lines) and city_like.search(_line_text(all_lines[j]) or ''):
            cities.append(_line_text(all_lines[j]).strip())
            j += 1
        if streets and cities:
            # pair up min(len(streets), len(cities))
            for k in range(min(len(streets), len(cities))):
                addresses.append(f"{streets[k]}, {cities[k]}")
            i = j
        else:
            i += 1

    # Normalize addresses using a module-level helper
    if addresses:
        seen = set()
        deduped = []
        for a in addresses:
            na = normalize_address_string(a)
            if na not in seen:
                deduped.append(na)
                seen.add(na)
        rec['address'] = deduped


    # Credit score: search near the 'Credit Score' label (within +/-3 lines)
    cs_indices = [i for i,ln in enumerate(all_lines) if 'credit score' in _line_text(ln).lower()]
    for idx in cs_indices:
        for j in range(idx - 3, idx + 4):
            if j < 0 or j >= len(all_lines):
                continue
            t = _line_text(all_lines[j]).strip()
            if t and t.isdigit():
                try:
                    rec['credit_score'] = int(t)
                except Exception:
                    pass
                # try to capture color from nearby spans (if requested)
                if include_spans:
                    for k in range(max(0, j - 2), min(len(all_lines), j + 3)):
                        ln2 = all_lines[k]
                        spans = ln2.get('spans') or []
                        # prefer a span that contains the numeric score text
                        preferred = None
                        for s in spans:
                            if s.get('text') and t in s.get('text'):
                                preferred = s
                                break
                        # otherwise prefer any span with rgb/hex
                        if not preferred:
                            for s in spans:
                                if s.get('rgb') or s.get('hex'):
                                    preferred = s
                                    break
                        if preferred:
                            if preferred.get('rgb'):
                                rec['credit_score_color'] = map_color_to_cat(tuple(preferred.get('rgb')))
                            elif preferred.get('hex'):
                                rgb = hex_to_rgb(preferred.get('hex'))
                                if rgb:
                                    rec['credit_score_color'] = map_color_to_cat(rgb)
                            if rec.get('credit_score_color'):
                                rec['credit_score_bbox'] = ln2.get('bbox')
                                rec['credit_score_page'] = ln2.get('page')
                                rec['credit_score_spans'] = spans
                                break
                break
        if rec.get('credit_score') is not None:
            break
    # fallback: if a numeric line exists at top (first few lines) that looks like a score and not many digits
    if 'credit_score' not in rec or rec.get('credit_score') is None:
        for ln in all_lines[:6]:
            t = _line_text(ln).strip()
            if t.isdigit() and 300 <= int(t) <= 850:
                rec['credit_score'] = int(t)
                # attach color and spans from this numeric line when requested
                if include_spans:
                    spans = ln.get('spans') or []
                    preferred = None
                    for s in spans:
                        if s.get('text') and t in s.get('text'):
                            preferred = s
                            break
                    if not preferred:
                        for s in spans:
                            if s.get('rgb') or s.get('hex'):
                                preferred = s
                                break
                    if preferred:
                        if preferred.get('rgb'):
                            rec['credit_score_color'] = map_color_to_cat(tuple(preferred.get('rgb')))
                        elif preferred.get('hex'):
                            rgb = hex_to_rgb(preferred.get('hex'))
                            if rgb:
                                rec['credit_score_color'] = map_color_to_cat(rgb)
                        if rec.get('credit_score_color'):
                            rec['credit_score_bbox'] = ln.get('bbox')
                            rec['credit_score_page'] = ln.get('page')
                            rec['credit_score_spans'] = spans
                break

    # Monthly payments (fallback numeric search)
    if 'monthly_payments' not in rec:
        for ln in all_lines:
            txt = _line_text(ln)
            m = re.search(r'\$\s*([0-9,]+)\s*/?\s*mo', txt, flags=re.IGNORECASE)
            if m:
                rec['monthly_payments'] = int(m.group(1).replace(',', ''))
                if include_spans and ln.get('spans') and ln['spans'][0].get('hex'):
                    rec['monthly_payments_color'] = ln['spans'][0].get('hex')
                    rec['monthly_payments_bbox'] = ln.get('bbox')
                break

    # Boolean indicators: credit_freeze, fraud_alert, deceased (look for label + nearby Yes/No/1/0)
    def _parse_bool_text(t: str):
        if not t:
            return None
        s = t.strip().lower()
        if s in ('yes','y','true','t','1'):
            return 1
        if s in ('no','n','false','f','0'):
            return 0
        # attempt to extract single word token
        m = re.search(r'\b(yes|no|y|n|true|false|1|0)\b', s)
        if m:
            return 1 if m.group(1) in ('yes','y','true','1') else 0
        return None

    for heading, key in (('credit freeze', 'credit_freeze'), ('fraud alert', 'fraud_alert'), ('deceased', 'deceased')):
        found = None
        found_idx = None
        for i, ln in enumerate(all_lines):
            txt = _line_text(ln).strip()
            if heading in txt.lower():
                # check same line tokens
                val = _parse_bool_text(txt)
                if val is not None:
                    found = (val, ln)
                    found_idx = i
                    break
                # check next few lines for explicit yes/no
                for j in range(i+1, min(len(all_lines), i+4)):
                    nt = _line_text(all_lines[j]).strip()
                    val = _parse_bool_text(nt)
                    if val is not None:
                        found = (val, all_lines[j])
                        found_idx = j
                        break
                if found:
                    break
                # check previous few lines (values may appear above headings in compact layouts)
                for j in range(i-1, max(-1, i-7), -1):
                    if j < 0:
                        break
                    pt = _line_text(all_lines[j]).strip()
                    val = _parse_bool_text(pt)
                    if val is not None:
                        found = (val, all_lines[j])
                        found_idx = j
                        break
                if found:
                    break
        if found:
            rec[key] = found[0]
            # Prefer the nearest span to the heading when include_spans=True
            if include_spans:
                best = None
                best_dist = None
                # if we have a found_idx from above, use it as center; otherwise locate heading index
                center_idx = found_idx if found_idx is not None else 0
                for j in range(max(0, center_idx - 4), min(len(all_lines), center_idx + 5)):
                    ln2 = all_lines[j]
                    if ln2.get('spans'):
                        # compute vertical distance between headings and candidate
                        try:
                            head_bbox = all_lines[center_idx].get('bbox')
                            cand_bbox = ln2.get('bbox')
                            dy = abs((head_bbox[1] + head_bbox[3]) / 2 - (cand_bbox[1] + cand_bbox[3]) / 2)
                        except Exception:
                            dy = 0
                        if best is None or dy < best_dist:
                            best = ln2
                            best_dist = dy
                if best is not None:
                    rec[f"{key}_bbox"] = best.get('bbox')
                    rec[f"{key}_page"] = best.get('page')
                    rec[f"{key}_spans"] = best.get('spans')
                    # choose a span that likely contains the indicator text, otherwise any colored span
                    spans = best.get('spans') or []
                    preferred = None
                    for s in spans:
                        txt = (s.get('text') or '').strip().lower()
                        if re.search(r'\b(yes|no|y|n|1|0|true|false)\b', txt):
                            preferred = s
                            break
                    if not preferred:
                        for s in spans:
                            if s.get('rgb') or s.get('hex'):
                                preferred = s
                                break
                    if preferred:
                        if preferred.get('rgb'):
                            rec[f"{key}_color"] = map_color_to_cat(tuple(preferred.get('rgb')))
                        elif preferred.get('hex'):
                            rgb = hex_to_rgb(preferred.get('hex'))
                            if rgb:
                                rec[f"{key}_color"] = map_color_to_cat(rgb)
                else:
                    # fallback to attaching spans from the originally found line if any
                    spans = found[1].get('spans') or []
                    if spans:
                        rec[f"{key}_bbox"] = found[1].get('bbox')
                        rec[f"{key}_page"] = found[1].get('page')
                        rec[f"{key}_spans"] = spans
                        # pick preferred span from the fallback candidate
                        preferred = None
                        for s in spans:
                            txt = (s.get('text') or '').strip().lower()
                            if re.search(r'\b(yes|no|y|n|1|0|true|false)\b', txt):
                                preferred = s
                                break
                        if not preferred:
                            for s in spans:
                                if s.get('rgb') or s.get('hex'):
                                    preferred = s
                                    break
                        if preferred:
                            if preferred.get('rgb'):
                                rec[f"{key}_color"] = map_color_to_cat(tuple(preferred.get('rgb')))
                            elif preferred.get('hex'):
                                rgb = hex_to_rgb(preferred.get('hex'))
                                if rgb:
                                    rec[f"{key}_color"] = map_color_to_cat(rgb)

    # Table recognition: map category lines to nested account dicts where possible
    category_map = [
        ('revolving accounts', 'revolving_accounts_open'),
        ('installment accounts', 'installment_accounts_open'),
        ('real estate', 'real_estate_open'),
        ('line of credit', 'line_of_credit_accounts_open'),
        ('miscellaneous', 'miscellaneous_accounts_open'),
    ]
    for i, ln in enumerate(all_lines):
        txt = _line_text(ln).lower()
        for key, outkey in category_map:
            if key in txt:
                # handle explicit 'No ... Accounts' cases
                if re.search(r'no .*accounts', txt):
                    rec[outkey] = {'count': 0, 'amount': 0}
                    if outkey == 'revolving_accounts_open':
                        rec['revolving_open_count'] = 0
                        rec['revolving_open_total'] = 0
                    elif outkey == 'installment_accounts_open':
                        rec['installment_open_count'] = 0
                        rec['installment_open_total'] = 0
                    elif outkey == 'real_estate_open':
                        rec['real_estate_open_count'] = 0
                        rec['real_estate_open_total'] = 0
                    elif outkey == 'line_of_credit_accounts_open':
                        rec['line_of_credit_accounts_open_count'] = 0
                        rec['line_of_credit_accounts_open_total'] = 0
                    elif outkey == 'miscellaneous_accounts_open':
                        rec['miscellaneous_accounts_open_count'] = 0
                        rec['miscellaneous_accounts_open_total'] = 0
                    break
                # try parse a count/amount pair in the same line first
                m_pair = re.search(r'(\d+\s*/\s*\$?\s*[0-9,]+)', txt)
                if m_pair:
                    count, amt = parse_count_amount_pair(m_pair.group(1))
                else:
                    count, amt = None, None
                # if not found, inspect the next few lines for a pair pattern or explicit 'No ...'
                if count is None and amt is None:
                    for nxt in all_lines[i + 1 : i + 8]:
                        nt = _line_text(nxt)
                        if re.search(r'no .*accounts', nt.lower()):
                            count, amt = 0, 0
                            break
                        m_pair = re.search(r'(\d+\s*/\s*\$?\s*[0-9,]+)', nt)
                        if m_pair:
                            count, amt = parse_count_amount_pair(m_pair.group(1))
                            break
                if count is not None or amt is not None:
                    rec[outkey] = {'count': count, 'amount': amt}
                    # also expose flat keys expected by the canonicalizer/tests
                    if outkey == 'revolving_accounts_open':
                        rec['revolving_open_count'] = count
                        rec['revolving_open_total'] = amt
                    elif outkey == 'installment_accounts_open':
                        rec['installment_open_count'] = count
                        rec['installment_open_total'] = amt
                    elif outkey == 'real_estate_open':
                        rec['real_estate_open_count'] = count
                        rec['real_estate_open_total'] = amt
                    elif outkey == 'line_of_credit_accounts_open':
                        rec['line_of_credit_accounts_open_count'] = count
                        rec['line_of_credit_accounts_open_total'] = amt
                    elif outkey == 'miscellaneous_accounts_open':
                        rec['miscellaneous_accounts_open_count'] = count
                        rec['miscellaneous_accounts_open_total'] = amt
                break

    # Collections: parse 'Collections (Open/Closed)' followed by 'n / m' where both are integers
    for i, ln in enumerate(all_lines):
        t = _line_text(ln).lower()
        if 'collections' in t:
            found = False
            # look for inline 'n / m'
            for nxt in all_lines[i + 1 : i + 6]:
                cc_text = _line_text(nxt)
                a, b = parse_count_count_pair(cc_text)
                if a is not None or b is not None:
                    rec['collections'] = {'open': a, 'closed': b}
                    rec['collections_open'] = a
                    rec['collections_closed'] = b
                    found = True
                    break
            if not found:
                # fallback: check next two non-empty lines as separate numbers
                vals = []
                for nxt in all_lines[i + 1 : i + 6]:
                    nt = _line_text(nxt).strip()
                    if nt and nt.isdigit():
                        vals.append(int(nt))
                    if len(vals) >= 2:
                        break
                if vals:
                    a = vals[0] if len(vals) >= 1 else None
                    b = vals[1] if len(vals) >= 2 else None
                    if a is not None or b is not None:
                        rec['collections'] = {'open': a, 'closed': b}
                        rec['collections_open'] = a
                        rec['collections_closed'] = b
                        found = True
            # leave as-is if not found (do not set to 0 implicitly)

    # Inquiries: parse counts near the 'Inquires' heading into inquiries_last_6_months (and alias inquiries_6mo)
    for i, ln in enumerate(all_lines):
        txt = _line_text(ln)
        if 'inquir' in txt.lower():
            total = 0
            found_any = False
            for nxt in all_lines[i + 1 : i + 20]:
                nt = _line_text(nxt)
                m = re.search(r"(\d+)\s+inq", nt, flags=re.IGNORECASE)
                if m:
                    n = int(m.group(1))
                    found_any = True
                    # consider time windows expressed as months to be within 6 months
                    if re.search(r"\b(\d+\s*-\s*\d+\s*mo|\d+\s*mo|last\s*\d+\s*mo|last\s*6\s*months)\b", nt, flags=re.IGNORECASE) or re.search(r"last\s*6\s*months", txt, flags=re.IGNORECASE):
                        total += n
                    else:
                        # if 'Last' not explicit but the timeframe mentions months, count it
                        if re.search(r"mo|month", nt, flags=re.IGNORECASE):
                            total += n
                        else:
                            # if no timeframe info, include as conservative default
                            total += n
            if found_any or re.search(r"last\s*6\s*months", txt, flags=re.IGNORECASE):
                rec['inquiries_last_6_months'] = total
                rec['inquiries_6mo'] = total

    # Late pays: parse lines near 'Late Pays' to compute last_2_years and last_over_2_years
    for i, ln in enumerate(all_lines):
        txt = _line_text(ln).lower()
        if 'late pay' in txt or 'lates +2yr' in txt or 'lates +2yr' in txt:
            l2 = 0
            lgt2 = 0
            # First pass: look for explicit 'X ... in Y mo/yrs' patterns, prefer these
            for nxt in all_lines[i + 1 : i + 20]:
                nt = _line_text(nxt)
                # lines like '2 Rev Lates in 4-6 mo' or '1 RE Late in 6-12 mo' or '40 RE Lates in 2-4 yrs'
                m2 = re.search(r'(\d+)\s+(?:\w+\s+)*late[s]?\s+.*\bin\b\s*(\d+)(?:\s*-\s*(\d+))?\s*(mo|yr|yrs)?', nt, flags=re.IGNORECASE)
                if m2:
                    num = int(m2.group(1))
                    unit = (m2.group(4) or '').lower()
                    # if the timeframe mentions months, classify as last_2_years
                    if 'mo' in unit or re.search(r'\bmo\b', nt, flags=re.IGNORECASE):
                        l2 += num
                    else:
                        # treat 'yrs' or year ranges as >2yrs bucket
                        lgt2 += num
                    continue
                # fallback: capture 'Lates +2yr: X/...' only if we have not already captured year-based lates
                m = re.search(r'lates\s*\+2yr\s*:\s*(\d+)', nt, flags=re.IGNORECASE)
                if m and lgt2 == 0:
                    lgt2 += int(m.group(1))
                    continue
            if l2 or lgt2:
                rec['late_pays'] = {'last_2_years': l2, 'last_over_2_years': lgt2}
                rec['late_pays_gt2yr'] = lgt2


    # Credit card totals: normalize any 'amounts' captured into structured fields when possible
    if 'credit_card_open_totals' in rec and isinstance(rec['credit_card_open_totals'], dict):
        cco = dict(rec['credit_card_open_totals'])
        amounts = cco.get('amounts') or []
        def _inum(s):
            if not s: return None
            m = re.search(r'\$\s*([0-9,]+)', s)
            if m:
                try:
                    return int(m.group(1).replace(',', ''))
                except Exception:
                    return None
            return None
        parsed = {}
        # heuristic mapping when three amounts present: balance, limit+percent, payment
        if len(amounts) >= 1:
            parsed['balance'] = _inum(amounts[0])
        if len(amounts) >= 2:
            # second may include percent
            pct_m = re.search(r'(\d+)%', amounts[1])
            if pct_m:
                parsed['Percent'] = int(pct_m.group(1))
            parsed['limit'] = _inum(amounts[1])
        if len(amounts) >= 3:
            parsed['Payment'] = _inum(amounts[2])
        # only set structured dict if we found at least one numeric value
        if any(v is not None for v in parsed.values()):
            rec['credit_card_open_totals'] = parsed
        else:
            rec['credit_card_open_totals'] = None

    # --- Credit factors: look for a 'Credit Factors' header and capture following lines as factors
    cf_idx = None
    for i, ln in enumerate(all_lines):
        if 'credit factors' in _line_text(ln).lower():
            cf_idx = i
            break
    factors = []
    if cf_idx is not None:
        for nxt in all_lines[cf_idx + 1 : cf_idx + 120]:
            txt = _line_text(nxt).strip()
            if not txt:
                break
            low = txt.lower()
            # stop at other section headers
            if re.search(r'credit alerts|public records|categories|inquir|late pays|credit report', low):
                break
            # detect and stop at table-like headers to avoid capturing table rows as factors
            table_headers = ('open accounts','revolving accounts','line of credit accounts','real estate accounts','installment accounts','miscellaneous accounts','closed accounts','no line of credit accounts','no real estate accounts','no installment accounts','no miscellaneous accounts')
            if low in table_headers:
                break
            # ignore short markers
            if txt.strip() == '#':
                continue

            # detect explicit color word at end of factor text (e.g., '... green')
            text_color = None
            mcol = re.search(r'\b(red|green|black|neutral|amber)\b\s*$', txt, flags=re.IGNORECASE)
            if mcol:
                text_color = mcol.group(1).lower()
                txt = re.sub(r'\s*\b(red|green|black|neutral|amber)\b\s*$', '', txt, flags=re.IGNORECASE).strip()

            # each non-header line is treated as a credit factor candidate
            cf = {'factor': txt}

            # color detection from spans (if available) preferred over textual hint
            span_color = None
            if nxt.get('spans'):
                s = nxt.get('spans')[0]
                rgb = None
                if s.get('rgb'):
                    rgb = tuple(s.get('rgb'))
                elif s.get('hex'):
                    rgb = hex_to_rgb(s.get('hex'))
                if rgb:
                    span_color = map_color_to_cat(rgb)
                    cf['hex'] = '#' + ''.join(f"{c:02x}" for c in rgb)
                    cf['color'] = span_color

            if not span_color and text_color:
                cf['color'] = text_color

            factors.append(cf)
    # if we found factors, append them (preserve earlier placeholder behavior otherwise)
    if factors:
        rec['credit_factors'] = factors
        # derive counts
        rec['red_credit_factors_count'] = sum(1 for f in factors if f.get('color') == 'red')
        rec['green_credit_factors_count'] = sum(1 for f in factors if f.get('color') == 'green')
        rec['black_credit_factors_count'] = sum(1 for f in factors if f.get('color') == 'black')

    # candidate scores
    if include_candidate_scores:
        rec["candidate_scores"] = []
        for cf in rec.get("credit_factors", []):
            rec["candidate_scores"].append({"factor": cf.get("factor"), "score": compute_candidate_score(cf)})

    return rec


def normalize_factors(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in raw:
        nr = dict(r)
        nr.setdefault("color", None)
        # preserve hex if present; tests allow either None or the same hex
        nr.setdefault("hex", nr.get("hex"))
        out.append(nr)
    return out


def compute_candidate_score(cand: Dict[str, Any]) -> int:
    score = 0
    text = (cand.get("factor") or "").lower()
    if len(text) < 40:
        score += 2
    if re.search(r"\d", text):
        score += 1
    if "paid" in text:
        score += 1
    if cand.get("hex") or cand.get("color"):
        score += 3
    # Ensure non-negative integer
    return max(int(score), 0)


def sort_factors_by_bbox(cfs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def keyfn(x: Dict[str, Any]):
        page = x.get("page", 9999)
        bbox = x.get("bbox") or [0, 9999, 0, 0]
        y = bbox[1] if len(bbox) > 1 else 9999
        return (page, y)

    # Keep stable ordering for items without bbox/page by sorting with high default values
    return sorted(cfs, key=keyfn)


# Expose a friendly module-level API for tests
__all__ = [
    "parse_count_amount_pair",
    "parse_public_records",
    "load_expectations_from_dir",
    "median_5x5",
    "hex_to_rgb",
    "map_color_to_cat",
    "normalize_address_string",
    "extract_credit_factors_from_doc",
    "extract_pdf_all_fields",
    "normalize_factors",
    "compute_candidate_score",
    "sort_factors_by_bbox",
]
