"""Convert PDF(s) to a ground-truth-like JSON file.

By default this emits a text-only GT matching the schema used in `data/extracted/*_ground_truth.json`.
Optionally `--include-spans` will attach page/bbox/spans/canonical_key using the auto-mapper workflow.

Usage:
  python scripts/pdf_to_ground_truth.py data/pdf_analysis/user_1131_credit_summary_2025-09-01_132805.pdf --include-spans --dry-run
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime
from pathlib import Path
import shutil
import sys

# ensure package root is importable when run as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scripts.pdf_color_extraction import extract_pdf_all_fields
from scripts.auto_map_unvalidated import map_file


def default_out_path(pdf_path: Path) -> Path:
    # derive user id prefix from filename
    stem = pdf_path.stem
    now = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
    out_name = f"{stem}_ground_truth_unvalidated.json"
    return Path('data/extracted') / out_name


def build_text_only_gt(rec: dict, include_spans: bool = False) -> dict:
    # rec may be the top-level dict returned by extract_pdf_all_fields
    # if it contains a .get('rec'), prefer that
    if 'rec' in rec and isinstance(rec['rec'], dict):
        source = rec['rec']
    else:
        source = rec
    out = {}
    # Normalize credit_score nested dict if present
    if isinstance(source.get('credit_score'), dict):
        cs = source.get('credit_score', {})
        source = dict(source)
        source['credit_score'] = cs.get('value')
        source['credit_score_color'] = cs.get('color')

    # Build a deterministic canonical order that reflects the "credit report details" layout
    # while allowing derived flat keys for nested structures. This keeps ordering stable and
    # consistent with `scripts/reorder_gt_files.py` expectations.
    TOP_LINE = ['filename','source','age','address','credit_score','credit_score_color','credit_freeze','fraud_alert','deceased']
    DETAILS = [
        'age', 'address',
        'revolving_open_count','revolving_open_total',
        'real_estate_open_count','real_estate_open_total',
        'line_of_credit_accounts_open_count','line_of_credit_accounts_open_total',
        'installment_open_count','installment_open_total',
        'miscellaneous_accounts_open_count','miscellaneous_accounts_open_total',
        'public_records','collections_open','collections_closed','inquiries_lt6mo','late_pays_lt2yr','late_pays_gt2yr'
    ]

    # helper to copy if present in source
    def _copy_if_present(k):
        if k in source and k not in out:
            out[k] = source.get(k)
            if include_spans:
                for suff in ('_bbox','_page','_spans'):
                    sk = f"{k}{suff}"
                    if sk in source:
                        out[sk] = source[sk]

    # 1) top line fields in canonical order
    for k in TOP_LINE:
        _copy_if_present(k)

    # 2) details: preserve the order as presented in the PDF by iterating over source keys
    # and handling the canonical mappings as we encounter them. Any detail keys not seen in the
    # source will be appended later to ensure presence for downstream consumers.
    seen_details = []
    detail_key_variants = {
        'age': ['age'],
        'address': ['address'],
        'revolving_open_count': ['revolving_open_count','revolving_accounts_open'],
        'revolving_open_total': ['revolving_open_total','revolving_accounts_open'],
        'real_estate_open_count': ['real_estate_open_count','real_estate_open'],
        'real_estate_open_total': ['real_estate_open_total','real_estate_open'],
        'line_of_credit_accounts_open_count': ['line_of_credit_accounts_open_count','line_of_credit_accounts_open'],
        'line_of_credit_accounts_open_total': ['line_of_credit_accounts_open_total','line_of_credit_accounts_open'],
        'installment_open_count': ['installment_open_count','installment_accounts_open'],
        'installment_open_total': ['installment_open_total','installment_accounts_open'],
        'miscellaneous_accounts_open_count': ['miscellaneous_accounts_open_count','miscellaneous_accounts_open'],
        'miscellaneous_accounts_open_total': ['miscellaneous_accounts_open_total','miscellaneous_accounts_open'],
        'public_records': ['public_records'],
        'collections_open': ['collections_open','collections'],
        'collections_closed': ['collections_closed','collections'],
        'inquiries_lt6mo': ['inquiries_lt6mo'],
        'late_pays_lt2yr': ['late_pays_lt2yr','late_pays'],
        'late_pays_gt2yr': ['late_pays_gt2yr','late_pays'],
    }

    # walk the source keys in order and map them to canonical detail keys
    for s_k in list(source.keys()):
        # skip transient keys
        if s_k in ('pdf_file','all_lines_obj','inquiries_6mo','inquiries_last_6_months'):
            continue
        # late_pays nested
        if s_k == 'late_pays' and isinstance(source.get('late_pays'), dict):
            lp = source.get('late_pays')
            out['late_pays_lt2yr'] = lp.get('last_2_years') if lp.get('last_2_years') is not None else 0
            out['late_pays_gt2yr'] = lp.get('last_over_2_years') if lp.get('last_over_2_years') is not None else 0
            seen_details.extend(['late_pays_lt2yr','late_pays_gt2yr'])
            continue
        # collections nested
        if s_k == 'collections' and isinstance(source.get('collections'), dict):
            c = source.get('collections')
            out['collections_open'] = c.get('open')
            out['collections_closed'] = c.get('closed')
            seen_details.extend(['collections_open','collections_closed'])
            continue
        # account nested mappings
        if s_k in ('revolving_accounts_open','installment_accounts_open','real_estate_open','line_of_credit_accounts_open','miscellaneous_accounts_open') and isinstance(source.get(s_k), dict):
            nd = source.get(s_k)
            mapping = {
                'revolving_accounts_open': ('revolving_open_count','revolving_open_total'),
                'installment_accounts_open': ('installment_open_count','installment_open_total'),
                'real_estate_open': ('real_estate_open_count','real_estate_open_total'),
                'line_of_credit_accounts_open': ('line_of_credit_accounts_open_count','line_of_credit_accounts_open_total'),
                'miscellaneous_accounts_open': ('miscellaneous_accounts_open_count','miscellaneous_accounts_open_total'),
            }
            ckey, tkey = mapping[s_k]
            out[ckey] = nd.get('count')
            out[tkey] = nd.get('amount')
            seen_details.extend([ckey,tkey])
            continue
        # flat detail keys present in source (e.g., age, address, revolving_open_count)
        for canon_k, variants in detail_key_variants.items():
            if s_k in variants and canon_k not in seen_details and canon_k not in out:
                # handle derived variants where necessary
                if canon_k in ('late_pays_lt2yr','late_pays_gt2yr'):
                    # prefer source flat values if present
                    if canon_k in source:
                        out[canon_k] = source.get(canon_k)
                    # else will be filled later with default if missing
                else:
                    out[canon_k] = source.get(s_k)
                seen_details.append(canon_k)
                break

    # ensure any DETAILS keys not seen are appended (to preserve canonical presence)
    for k in DETAILS:
        if k not in out:
            # attempt to derive late_pays from source if possible
            if k in ('late_pays_lt2yr','late_pays_gt2yr') and 'late_pays' in source and isinstance(source.get('late_pays'), dict):
                lp = source.get('late_pays')
                out['late_pays_lt2yr'] = lp.get('last_2_years') if lp.get('last_2_years') is not None else 0
                out['late_pays_gt2yr'] = lp.get('last_over_2_years') if lp.get('last_over_2_years') is not None else 0
                continue
            _copy_if_present(k)

    # 3) credit_factors if present
    if 'credit_factors' in source:
        out['credit_factors'] = []
        for cf in source.get('credit_factors'):
            out_cf = {'factor': cf.get('factor')}
            if 'hex' in cf and isinstance(cf.get('hex'), str) and cf.get('hex'):
                if not cf.get('hex').startswith('#') and cf.get('hex') in ('red','green','black','neutral','amber'):
                    out_cf['color'] = cf.get('hex')
                    out_cf['hex'] = None
                else:
                    out_cf['hex'] = cf.get('hex')
            if 'color' in cf and cf.get('color') is not None:
                out_cf['color'] = cf.get('color')
            # derive color from hex or spans if missing
            if 'color' not in out_cf:
                try:
                    from src.scripts.pdf_color_extraction import hex_to_rgb, map_color_to_cat
                    if out_cf.get('hex'):
                        rgb = hex_to_rgb(out_cf.get('hex'))
                        if rgb:
                            out_cf['color'] = map_color_to_cat(rgb)
                    elif include_spans and cf.get('spans'):
                        for s in cf.get('spans'):
                            if s.get('rgb'):
                                out_cf['color'] = map_color_to_cat(tuple(s.get('rgb')))
                                break
                            if s.get('hex'):
                                rgb = hex_to_rgb(s.get('hex'))
                                if rgb:
                                    out_cf['color'] = map_color_to_cat(rgb)
                                    break
                except Exception:
                    pass
            for key in ('bbox','page','spans','canonical_key'):
                if key in cf:
                    out_cf[key] = cf[key]
            out['credit_factors'].append(out_cf)

    # 4) finally, append any remaining keys in source that weren't covered above
    for k in list(source.keys()):
        if k in ('pdf_file','all_lines_obj','inquiries_6mo','inquiries_last_6_months','collections','revolving_accounts_open','installment_accounts_open','real_estate_open','line_of_credit_accounts_open','miscellaneous_accounts_open','late_pays'):
            # skip transient/legacy/nested keys; these are represented with flat keys instead
            continue
        if k in out:
            continue
        if k.endswith(('_bbox','_page','_spans')):
            continue
        out[k] = source.get(k)
        if include_spans:
            for suff in ('_bbox','_page','_spans'):
                sk = f"{k}{suff}"
                if sk in source:
                    out[sk] = source[sk]
    # Accept legacy aliases and canonicalize to 'inquiries_lt6mo'
    if 'inquiries_last_6_months' in source and 'inquiries_lt6mo' not in out:
        out['inquiries_lt6mo'] = source.get('inquiries_last_6_months')
    if 'inquiries_lt6mo' in source and 'inquiries_lt6mo' not in out:
        out['inquiries_lt6mo'] = source.get('inquiries_lt6mo')
    # canonicalize credit_factors to minimal shape
    cfs = source.get('credit_factors', [])
    out['credit_factors'] = []
    for cf in cfs:
        out_cf = {'factor': cf.get('factor')}
        # preserve raw hex when present
        if 'hex' in cf and isinstance(cf.get('hex'), str) and cf.get('hex'):
            # if the extractor mistakenly put a canonical color name into 'hex', normalize
            if not cf.get('hex').startswith('#') and cf.get('hex') in ('red','green','black','neutral','amber'):
                out_cf['color'] = cf.get('hex')
                out_cf['hex'] = None
            else:
                out_cf['hex'] = cf.get('hex')
        # prefer explicit color if provided
        if 'color' in cf and cf.get('color') is not None:
            out_cf['color'] = cf.get('color')
        # derive color from hex or spans if missing
        if 'color' not in out_cf:
            try:
                from src.scripts.pdf_color_extraction import hex_to_rgb, map_color_to_cat
                if out_cf.get('hex'):
                    rgb = hex_to_rgb(out_cf.get('hex'))
                    if rgb:
                        out_cf['color'] = map_color_to_cat(rgb)
                elif include_spans and cf.get('spans'):
                    for s in cf.get('spans'):
                        if s.get('rgb'):
                            out_cf['color'] = map_color_to_cat(tuple(s.get('rgb')))
                            break
                        if s.get('hex'):
                            rgb = hex_to_rgb(s.get('hex'))
                            if rgb:
                                out_cf['color'] = map_color_to_cat(rgb)
                                break
            except Exception:
                # non-fatal: leave color missing
                pass
        # copy bbox/page/spans/canonical_key if available from extractor
        for key in ('bbox','page','spans','canonical_key'):
            if key in cf:
                out_cf[key] = cf[key]
        out['credit_factors'].append(out_cf)

    # also copy any top-level color keys present in the source (e.g., monthly_payments_color)
    for sk in source:
        if sk.endswith('_color') and sk not in out:
            out[sk] = source[sk]

    # If nested late_pays dict present, derive flat canonical keys and DO NOT keep nested representation
    if 'late_pays' in source and isinstance(source.get('late_pays'), dict):
        lp = source.get('late_pays')
        out['late_pays_lt2yr'] = lp.get('last_2_years') if lp.get('last_2_years') is not None else 0
        out['late_pays_gt2yr'] = lp.get('last_over_2_years') if lp.get('last_over_2_years') is not None else 0
    # Accept legacy flat late-pays keys and prefer flat canonical keys (do NOT construct nested 'late_pays')
    if 'late_pays_lt2yr' in source:
        out['late_pays_lt2yr'] = source.get('late_pays_lt2yr')
    if 'late_pays_gt2yr' in source:
        out['late_pays_gt2yr'] = source.get('late_pays_gt2yr')
    # Ensure numeric defaults for stability
    if 'late_pays_lt2yr' not in out:
        out['late_pays_lt2yr'] = 0
    if 'late_pays_gt2yr' not in out:
        out['late_pays_gt2yr'] = 0

    # Normalize collections nested dict into flat counts if present so GT comparisons are stable
    if 'collections' in source and 'collections_open' not in out:
        c = source.get('collections')
        if isinstance(c, dict):
            out['collections_open'] = c.get('open')
            out['collections_closed'] = c.get('closed')
            # also expose count-named keys used in some GT fixtures
            out['collections_open_count'] = c.get('open')
            out['collections_closed_count'] = c.get('closed')

    # Flatten nested account structures for line_of_credit and miscellaneous into flat count/total keys
    account_mappings = [
        ('line_of_credit_accounts_open', 'line_of_credit_accounts_open_count', 'line_of_credit_accounts_open_total'),
        ('miscellaneous_accounts_open', 'miscellaneous_accounts_open_count', 'miscellaneous_accounts_open_total'),
    ]
    for nkey, ckey, tkey in account_mappings:
        if nkey in source and isinstance(source.get(nkey), dict):
            nd = source.get(nkey)
            out[ckey] = nd.get('count')
            out[tkey] = nd.get('amount')
        # If flat keys are present in source, they were already copied above; do NOT emit nested dicts
        out.pop(nkey, None)

    # Build canonical output following the order in which the PDF presents items
    # (iterate the source keys and map nested structures into flat keys in-place).
    ordered_out = {}
    for k in list(source.keys()):
        # skip transient/legacy keys
        if k in ('pdf_file','all_lines_obj','inquiries_6mo','inquiries_last_6_months'):
            continue
        # nested late_pays -> flat
        if k == 'late_pays' and isinstance(source.get('late_pays'), dict):
            lp = source.get('late_pays')
            ordered_out['late_pays_lt2yr'] = lp.get('last_2_years') if lp.get('last_2_years') is not None else 0
            ordered_out['late_pays_gt2yr'] = lp.get('last_over_2_years') if lp.get('last_over_2_years') is not None else 0
            continue
        # collections nested -> flat
        if k == 'collections' and isinstance(source.get('collections'), dict):
            c = source.get('collections')
            ordered_out['collections_open'] = c.get('open')
            ordered_out['collections_closed'] = c.get('closed')
            continue
        # nested account categories -> flat count/total
        if k in ('revolving_accounts_open','installment_accounts_open','real_estate_open','line_of_credit_accounts_open','miscellaneous_accounts_open') and isinstance(source.get(k), dict):
            nd = source.get(k)
            mapping = {
                'revolving_accounts_open': ('revolving_open_count','revolving_open_total'),
                'installment_accounts_open': ('installment_open_count','installment_open_total'),
                'real_estate_open': ('real_estate_open_count','real_estate_open_total'),
                'line_of_credit_accounts_open': ('line_of_credit_accounts_open_count','line_of_credit_accounts_open_total'),
                'miscellaneous_accounts_open': ('miscellaneous_accounts_open_count','miscellaneous_accounts_open_total'),
            }
            ckey, tkey = mapping[k]
            ordered_out[ckey] = nd.get('count')
            ordered_out[tkey] = nd.get('amount')
            continue
        # regular copy of simple keys
        if k in source and not k.endswith(('_bbox','_page','_spans')):
            ordered_out[k] = source.get(k)

    # Ensure flat late_pays keys and numeric defaults are present
    if 'late_pays_lt2yr' not in ordered_out:
        ordered_out['late_pays_lt2yr'] = source.get('late_pays_lt2yr') if 'late_pays_lt2yr' in source else 0
    if 'late_pays_gt2yr' not in ordered_out:
        ordered_out['late_pays_gt2yr'] = source.get('late_pays_gt2yr') if 'late_pays_gt2yr' in source else 0

    # Append any remaining keys from the source that weren't explicitly handled
    for k in list(source.keys()):
        if k in ordered_out:
            continue
        if k in ('pdf_file','all_lines_obj','inquiries_6mo','inquiries_last_6_months','collections','revolving_accounts_open','installment_accounts_open','real_estate_open','line_of_credit_accounts_open','miscellaneous_accounts_open','late_pays'):
            continue
        if k.endswith(('_bbox','_page','_spans')):
            continue
        ordered_out[k] = source.get(k)

    # Finally, copy any top-level color fields that were not set yet
    for sk in source:
        if sk.endswith('_color') and sk not in ordered_out:
            ordered_out[sk] = source[sk]

    # If span inclusion requested, copy *_bbox/_page/_spans keys for the top-level fields we've included
    if include_spans:
        for k in list(ordered_out.keys()):
            for suff in ('_bbox','_page','_spans'):
                sk = f"{k}{suff}"
                if sk in source and sk not in ordered_out:
                    ordered_out[sk] = source[sk]

    # Accept legacy inquiries aliases to ensure inquiries_lt6mo is present in canonical output
    if 'inquiries_last_6_months' in source and 'inquiries_lt6mo' not in ordered_out:
        ordered_out['inquiries_lt6mo'] = source.get('inquiries_last_6_months')
    if 'inquiries_lt6mo' in source and 'inquiries_lt6mo' not in ordered_out:
        ordered_out['inquiries_lt6mo'] = source.get('inquiries_lt6mo')

    # Re-order to place account counts first (matching canonical expectations across GT files),
    # followed by late_pays, then the remaining keys in their source order.
    account_seq = ['revolving_open_count','revolving_open_total','installment_open_count','installment_open_total','real_estate_open_count','real_estate_open_total','line_of_credit_accounts_open_count','line_of_credit_accounts_open_total','miscellaneous_accounts_open_count','miscellaneous_accounts_open_total']
    final = {}
    for k in account_seq:
        if k in ordered_out:
            final[k] = ordered_out.pop(k)
    # late pays next
    for k in ('late_pays_lt2yr','late_pays_gt2yr'):
        if k in ordered_out:
            final[k] = ordered_out.pop(k)
    # append remaining in source order
    for k, v in ordered_out.items():
        final[k] = v
    out = final

    return out


def attach_spans_to_gt(gt_json_path: Path, pdf_path: Path) -> Path:
    # use the existing auto-mapper: write a temporary unvalidated input and call map_file
    tmp_unvalidated = gt_json_path.with_suffix('.tmp_unvalidated.json')
    shutil.copy(gt_json_path, tmp_unvalidated)
    mapped_json, rows = map_file(str(tmp_unvalidated))
    # read original GT and enrich factors
    gt = json.loads(gt_json_path.read_text(encoding='utf-8'))
    for i, row in enumerate(rows):
        # map by factor text
        ftext = row.get('factor')
        for cf in gt.get('credit_factors', []):
            if cf.get('factor','').strip() == ftext.strip():
                if row.get('page') is not None:
                    cf['page'] = row.get('page')
                if row.get('bbox') is not None:
                    cf['bbox'] = row.get('bbox')
                if row.get('spans') is not None:
                    cf['spans'] = row.get('spans')
                if row.get('canonical_key'):
                    cf['canonical_key'] = row.get('canonical_key')
                break

    # --- Attach spans for top-level fields (credit_score, monthly_payments, credit_freeze, fraud_alert, deceased, inquiries)
    try:
        doc_rec = extract_pdf_all_fields(str(pdf_path), include_spans=True)
        lines = doc_rec.get('all_lines_obj') or doc_rec.get('lines') or []

        def _line_text(ln):
            # safe join
            return ''.join([s.get('text','') for s in ln.get('spans', [])]).strip() if ln.get('spans') else ln.get('text','').strip() if ln.get('text') else ''

        def _find_by_text(t):
            if not t:
                return None
            t_low = t.strip().lower()
            for ln in lines:
                txt = _line_text(ln).strip()
                txt_low = txt.lower()
                if txt == t or t in txt or txt in t or txt_low == t_low or t_low in txt_low or txt_low in t_low:
                    return ln
            return None

        # credit score (match numeric string)
        if gt.get('credit_score') is not None:
            cs_txt = str(gt.get('credit_score'))
            ln = _find_by_text(cs_txt)
            if ln:
                gt['credit_score_bbox'] = ln.get('bbox')
                gt['credit_score_page'] = ln.get('page')
                gt['credit_score_spans'] = ln.get('spans')
        # monthly payments: only attach spans when exact numeric matches are found (no phrase-based fallbacks)
        if gt.get('monthly_payments') is not None:
            amt = gt.get('monthly_payments')
            candidates = [f'${amt}', str(amt)]
            found = None
            for c in candidates:
                found = _find_by_text(c)
                if found:
                    break
            if found:
                gt['monthly_payments_bbox'] = found.get('bbox')
                gt['monthly_payments_page'] = found.get('page')
                gt['monthly_payments_spans'] = found.get('spans')

        # Map explicit headings (credit_freeze, fraud_alert, deceased, inquiries) by proximity when possible
        for heading, key, value_type in (
            ("credit freeze", "credit_freeze", "bool"),
            ("fraud alert", "fraud_alert", "bool"),
            ("deceased", "deceased", "bool"),
            ("inquires", "inquiries_lt6mo", "int"),
            ("inquiries", "inquiries_lt6mo", "int"),
        ):
            ln_h = _find_by_text(heading)
            if not ln_h:
                continue
            try:
                idx = lines.index(ln_h)
            except ValueError:
                continue
            for nxt in lines[idx + 1 : idx + 4]:
                txt = _line_text(nxt).strip().lower()
                if value_type == "bool":
                    if txt in ("yes", "no", "y", "n"):
                        gt[key] = 1 if txt.startswith("y") else 0
                        gt[f"{key}_bbox"] = nxt.get("bbox")
                        gt[f"{key}_page"] = nxt.get("page")
                        gt[f"{key}_spans"] = nxt.get("spans")
                        break
                elif value_type == "int":
                    if txt.isdigit():
                        val = int(txt)
                        gt["inquiries_lt6mo"] = val
                        gt["inquiries_lt6mo_bbox"] = nxt.get("bbox")
                        gt["inquiries_lt6mo_page"] = nxt.get("page")
                        gt["inquiries_lt6mo_spans"] = nxt.get("spans")
                        # For backward compatibility, also populate legacy keys when present in GT
                        if 'inquiries_last_6_months' in gt:
                            gt['inquiries_last_6_months'] = val
                            gt['inquiries_last_6_months_bbox'] = nxt.get('bbox')
                            gt['inquiries_last_6_months_page'] = nxt.get('page')
                            gt['inquiries_last_6_months_spans'] = nxt.get('spans')
                        break

        # Note: previously we removed some phrase-based heuristics; the above checks are conservative and
        # only map explicit, near-by span values rather than broad phrase lists.

    except Exception:
        # best-effort: do not raise on mapping failures
        pass
    # write enriched GT to a new file
    enriched = gt_json_path.with_name(gt_json_path.stem + '.with_spans.json')
    enriched.write_text(json.dumps(gt, indent=2), encoding='utf-8')
    tmp_unvalidated.unlink(missing_ok=True)
    return enriched


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('pdfs', nargs='+')
    ap.add_argument('--include-spans', action='store_true')
    ap.add_argument('--out', help='override output path')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--backup', action='store_true')
    args = ap.parse_args(argv)

    for p in args.pdfs:
        pdf = Path(p)
        if not pdf.exists():
            print('missing PDF', p); continue
        rec = extract_pdf_all_fields(str(pdf), include_spans=args.include_spans)
        gt = build_text_only_gt(rec, include_spans=args.include_spans)
        outp = Path(args.out) if args.out else default_out_path(pdf)
        if args.dry_run:
            print('DRY-RUN would write:', outp)
            print(json.dumps(gt, indent=2)[:1000])
            if args.include_spans:
                # For convenience, run the auto-mapper on a temporary copy so the user can preview attached spans
                import tempfile
                tmp = Path(tempfile.mkdtemp()) / (outp.name + '.dryrun.json')
                tmp.write_text(json.dumps(gt, indent=2), encoding='utf-8')
                try:
                    enriched = attach_spans_to_gt(tmp, pdf)
                    print('\nDRY-RUN enriched preview (first 1000 chars):')
                    print(enriched.read_text(encoding='utf-8')[:1000])
                    print('\nDRY-RUN spans were attached (preview only, not written)')
                except Exception as e:
                    print('DRY-RUN span-attachment failed:', e)
                finally:
                    try:
                        tmp.unlink(missing_ok=True)
                        tmp.parent.rmdir()
                    except Exception:
                        pass
            continue
        # backup if target exists
        if outp.exists() and args.backup:
            bak = outp.with_suffix(outp.suffix + '.bak')
            bak.write_text(outp.read_text(encoding='utf-8'), encoding='utf-8')
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(gt, indent=2), encoding='utf-8')
        print('WROTE', outp)
        if args.include_spans:
            enriched = attach_spans_to_gt(outp, pdf)
            print('WROTE enriched spans JSON', enriched)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())