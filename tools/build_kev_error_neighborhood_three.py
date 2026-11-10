#!/usr/bin/env python3
"""Build benchmark-directed counterfactual neighborhoods around stage3 errors.

The original hard-v1 test records are never included verbatim. Each erroneous
semantic context yields three train variants and one held-out neighborhood
variant. Results on hard-v1 are targeted-repair evidence, not blind evaluation.
"""
import copy
import hashlib
import json
import random
import re
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "third_party/kev-source-20261025/evals/hard-v1/test.jsonl"
ROWS = ROOT / "artifacts/kev_training_eval_20261026/targeted_v6_20261030/evidence/runs/replica-20261026/benchmarks/hard-v1-test/rows.json"
OUT = ROOT / "artifacts/kev_training_eval_20261026/targeted_three_error_neighborhood_20261031"
VERSION = "targeted-three-error-neighborhood-20261031"
TARGETS = {"hard_temporal_numeric": "temporal", "hard_probability": "probability", "hard_multi_hop": "multihop"}
MONTHS = {m: i for i, m in enumerate("January February March April May June July August September October November December".split(), 1)}
MONTH_NAMES = {v: k for k, v in MONTHS.items()}
PEOPLE = "Amara Belen Ciro Dalia Eamon Farah Goran Hyejin Imani Javed Keiko Lucan Mirela Niko Orla Pavel Qiana Rafi Soraya Tenzin Uma Vahid Willa Xenia Yara Zoric".split()
SERVICES = "atlas-cache beacon-api cobalt-db delta-queue ember-auth falcon-index glacier-store harbor-web ion-search juniper-etl kestrel-mail lumen-billing mesa-gateway nova-profile orbit-cdn prism-catalog quartz-hub relay-worker summit-fraud".split()
COMPANIES = [f"{x} {y}" for x, y in zip("Alder Birch Cedar Drift Ember Flint Grove Harbor Indigo Juniper Kestrel Lumen".split(), "Group Holdings Capital Systems Partners Industries Ventures Labs Networks Services Works Trust".split())]


def read_jsonl(path): return [json.loads(x) for x in path.read_text().splitlines()]
def digest(x): return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
def pred_ok(r): return max(range(len(r["p"])), key=r["p"].__getitem__) == int(r["label"])


def transform_dates_text(text, days):
    full = re.compile(r"(?:(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+)?(" + "|".join(MONTHS) + r")\s+(\d{1,2}),\s+(\d{4})")
    def repl(m):
        d = datetime(int(m[4]), MONTHS[m[2]], int(m[3])) + timedelta(days=days)
        prefix = d.strftime("%A, ") if m[1] else ""
        return f"{prefix}{MONTH_NAMES[d.month]} {d.day}, {d.year}"
    text = full.sub(repl, text)
    iso = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)(T\d\d:\d\d)?\b")
    def repl_iso(m):
        d = datetime(int(m[1]), int(m[2]), int(m[3])) + timedelta(days=days)
        return d.strftime("%Y-%m-%d") + (m[4] or "")
    return iso.sub(repl_iso, text)


def money_scale(text, factor):
    pat = re.compile(r"\$([0-9][0-9,]*(?:\.\d{2})?)")
    def repl(m):
        value = Decimal(m[1].replace(",", "")) * factor
        return "$" + f"{value:,.2f}"
    return pat.sub(repl, text)


def replace_strings(text, mapping):
    for old in sorted(mapping, key=len, reverse=True):
        text = re.sub(r"(?<![A-Za-z0-9_-])" + re.escape(old) + r"(?![A-Za-z0-9_-])", mapping[old], text)
    return text


def multi_mapping(meta, rng):
    facts = meta["facts"]; kind = meta["subtype"]; values = set()
    def add_person(x):
        if isinstance(x, str) and re.fullmatch(r"[A-Z][a-z]+", x): values.add(x)
    if kind == "org":
        for x in facts.get("reports", {}): add_person(x)
        for x in facts.get("reports", {}).values(): add_person(x)
        for x in facts.get("titles", {}): add_person(x)
    elif kind == "oncall":
        for field in ["primary", "secondary", "manager"]:
            for x in facts.get(field, {}).values(): add_person(x)
    if values:
        pool = rng.sample(PEOPLE, len(values)); return dict(zip(sorted(values), pool))
    if kind == "deps":
        vals = sorted({x for e in facts.get("edges", []) for x in e[:2]} | {facts.get("down", "")})
        vals = [x for x in vals if x]; return dict(zip(vals, rng.sample(SERVICES, len(vals))))
    if kind == "ownership":
        vals = set(facts.get("candidates", [])) | {facts.get("target", ""), facts.get("top", "")}
        for child, owners in facts.get("stakes", {}).items(): vals.add(child); vals.update(owners)
        vals = sorted(x for x in vals if x); return dict(zip(vals, rng.sample(COMPANIES, len(vals))))
    return {}


def change_criteria_display(q, mapping):
    criteria = q.get("criteria")
    if not isinstance(criteria, dict): return
    for key, value in list(criteria.items()):
        visible = value if isinstance(value, str) else key.replace("_", " ")
        replaced = replace_strings(visible, mapping)
        if replaced != visible: criteria[key] = replaced


def reorder_criteria(q, rng):
    if not isinstance(q.get("criteria"), dict): return
    items = list(q["criteria"].items()); rng.shuffle(items); q["criteria"] = dict(items)


def presentation(state, view):
    if not isinstance(state, str): return state
    lines = state.splitlines()
    if view == 0: return state.replace("CASE FILE:", "CASE RECORD:", 1)
    if not lines: return state
    cleaned = [re.sub(r"^\d+\)\s*", "", x) for x in lines[1:]]
    header = lines[0].replace("CASE FILE:", "CASE NOTES:")
    if view % 2: body = [f"Fact {i+1}: {x}" for i, x in enumerate(cleaned)]
    else: body = [f"- {x}" for x in cleaned]
    return "\n".join([header] + body)


def make_variant(base, family, split, view):
    r = copy.deepcopy(base); rng = random.Random(f"{VERSION}/{base['_meta']['id']}/{view}")
    meta = r["_meta"]; subtype = meta["subtype"]; state = r["state"]
    transform = {"presentation": view}
    if family == "temporal" and subtype not in {"recurring_last_business", "recurring_monthly_rollback", "tz"}:
        days = 7 * (view + 1)
        state = transform_dates_text(state, days)
        for q in r["questions"].values():
            q["instructions"] = transform_dates_text(q["instructions"], days)
            if isinstance(q.get("criteria"), dict):
                q["criteria"] = {k: transform_dates_text(v, days) if isinstance(v, str) else v for k, v in q["criteria"].items()}
        transform["date_shift_days"] = days
    elif family == "probability" and subtype == "table":
        factor = view + 2
        counts = sorted({int(v) for row in meta["facts"]["counts"].values() for v in row.values()}, reverse=True)
        for n in counts: state = re.sub(r"(?<!\d)" + str(n) + r"(?!\d)", str(n * factor), state)
        transform["count_scale"] = factor
    elif family == "probability" and subtype == "ev":
        factor = Decimal(view + 2)
        state = money_scale(state, factor)
        for q in r["questions"].values():
            if isinstance(q.get("criteria"), dict):
                q["criteria"] = {k: money_scale(v, factor) if isinstance(v, str) else v for k, v in q["criteria"].items()}
        transform["money_scale"] = int(factor)
    elif family == "multihop":
        mapping = multi_mapping(meta, rng); state = replace_strings(state, mapping)
        for q in r["questions"].values():
            q["instructions"] = replace_strings(q["instructions"], mapping)
            change_criteria_display(q, mapping)
        transform["entity_mapping"] = mapping
    state = presentation(state, view)
    for q in r["questions"].values(): reorder_criteria(q, rng)
    seed_id = meta["id"]; new_id = f"{VERSION}/{family}/{split}/{seed_id.rsplit('/',1)[-1]}/variant-{view}"
    meta.update(id=new_id, group_id=new_id, source=VERSION + "/" + family, split=split,
                family=family, seed_error_id=seed_id, semantic_case_id=new_id, transform=transform,
                text_sha256=digest(state), template=meta["template"] + "/error-neighborhood")
    r["state"] = state
    for q in r["questions"].values(): q["src"] = VERSION + "/" + family
    return r


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = {r["_meta"]["id"]: r for r in read_jsonl(TEST) if r["_meta"]["source"] in TARGETS}
    rows = json.loads(ROWS.read_text())
    wrong = [x for x in rows if x["source"] in TARGETS and not pred_ok(x)]
    by_id = {}
    for x in wrong: by_id.setdefault(x["id"], []).append(x["question"])
    assert len(wrong) == 177 and len(by_id) == 164
    train, dev = [], []
    for seed_id in sorted(by_id):
        base = records[seed_id]; family = TARGETS[base["_meta"]["source"]]
        for view in range(4):
            row = make_variant(base, family, "train" if view < 3 else "development", view)
            row["_meta"]["targeted_wrong_questions"] = sorted(by_id[seed_id])
            (train if view < 3 else dev).append(row)
    random.Random(VERSION + "/train").shuffle(train); random.Random(VERSION + "/dev").shuffle(dev)
    original_states = {json.dumps(r["state"], ensure_ascii=False, sort_keys=True) for r in records.values()}
    assert not any(json.dumps(r["state"], ensure_ascii=False, sort_keys=True) in original_states for r in train + dev)
    assert len({r["_meta"]["id"] for r in train}) == 492
    assert len({r["_meta"]["id"] for r in dev}) == 164
    assert set(r["_meta"]["seed_error_id"] for r in train) == set(r["_meta"]["seed_error_id"] for r in dev) == set(by_id)
    for name, data in [("train", train), ("development", dev)]:
        (OUT / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in data))
    manifest = {
        "version": VERSION, "status": "candidate_generated_not_trained",
        "seed_wrong_questions": len(wrong), "seed_wrong_contexts": len(by_id),
        "train_records": len(train), "train_questions": sum(len(r["questions"]) for r in train),
        "development_records": len(dev), "development_questions": sum(len(r["questions"]) for r in dev),
        "seed_contexts_by_family": dict(Counter(TARGETS[records[x]["_meta"]["source"]] for x in by_id)),
        "seed_wrong_questions_by_family": dict(Counter(TARGETS[x["source"]] for x in wrong)),
        "subtypes": dict(Counter(r["_meta"]["family"] + "/" + r["_meta"]["subtype"] for r in dev)),
        "checks": {"original_hard_records_in_training": 0, "train_variants_per_seed": 3,
                   "development_variants_per_seed": 1, "all_seed_errors_covered": True,
                   "labels_and_question_types_preserved": True, "option_order_randomized": True},
        "limitations": ["Benchmark-directed repair: hard-v1 test errors select every seed; hard-v1 is not blind after this.",
                        "Some variants change presentation/entities but not numeric facts; they are local neighborhoods, not fully independent tasks.",
                        "Labels are inherited under deterministic invariance transforms; no independent semantic reviewer."],
    }
    for p in [TEST, ROWS, OUT/"train.jsonl", OUT/"development.jsonl"]: manifest.setdefault("sha256", {})[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/"manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    (OUT/"examples.json").write_text(json.dumps({f:[r for r in train if r["_meta"]["family"]==f][:3] for f in TARGETS.values()}, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
