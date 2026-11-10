#!/usr/bin/env python3
"""Build solver-labelled probability and long-policy data without reading test items.

This is a second, structurally richer targeted set.  Gold labels come only from
the deterministic solvers below.  The rendered text is deliberately separated
from the latent program, and development/test use disjoint vocabulary and
surface forms.  It does *not* copy any frozen Kev evaluation record.
"""

import hashlib
import json
import random
import statistics
from collections import Counter
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "kev_training_eval_20261026" / "targeted_v2_probability_policy"
VERSION = "targeted-v2-20261029"
SEED = 20261029
SIZES = {
    "train": {"probability": 3600, "policy": 1800},
    "development": {"probability": 400, "policy": 200},
    "test": {"probability": 400, "policy": 200},
}

VOCAB = {
    "train": {
        "orgs": ["Northwind", "Aster", "Harbor", "Cobalt", "Juniper", "Riverside"],
        "people": ["Avery", "Mina", "Ravi", "Elena", "Noah", "Sofia"],
        "products": ["HarborPass", "AsterShield", "CobaltCare", "JuniperPlus"],
    },
    "development": {
        "orgs": ["Meridian", "Orchard", "Summit", "Lattice", "Crescent", "Saffron"],
        "people": ["Inez", "Cal", "Yara", "Benoit", "Luca", "Mara"],
        "products": ["MeridianCover", "OrchardPlan", "SummitGuard", "LatticeChoice"],
    },
    "test": {
        "orgs": ["Ember", "Kestrel", "Vantage", "Solace", "Grove", "Fjord"],
        "people": ["Keiko", "Omar", "Zuri", "Hugo", "Anya", "Dae"],
        "products": ["EmberBenefit", "KestrelProtect", "VantagePlan", "SolaceCover"],
    },
}


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def cents(value):
    return "${:,}.{:02d}".format(value // 100, value % 100)


def percent(value):
    return "{:.1f}%".format(float(value * 100))


def shuffled_choice(rng, instruction, options, answer, source):
    """Return a Kev choice question and non-model-visible canonical values."""
    options = list(options)
    rng.shuffle(options)
    criteria, values, label = {}, {}, None
    for key, pair in zip("abcdefghij", options):
        value, text = pair
        criteria[key] = text
        values[key] = value
        if value == answer:
            label = key
    if label is None or len(set(values.values())) != len(values):
        raise ValueError("missing or non-unique gold option")
    return {
        "type": "choice", "instructions": instruction, "criteria": criteria,
        "label": label, "src": source, "_option_values": values,
    }


def make_record(split, family, ordinal, state, questions, facts, subtype, template):
    rid = "{}/{}/{}/{:05d}".format(VERSION, family, split, ordinal)
    rendered_questions, option_values = {}, {}
    for name, question in questions.items():
        question = dict(question)
        option_values[name] = question.pop("_option_values")
        rendered_questions[name] = question
    return {
        "state": state,
        "questions": rendered_questions,
        "_meta": {
            "id": rid, "group_id": rid, "source": "targeted_v2_{}".format(family),
            "split": split, "family": family, "subtype": subtype, "template": template,
            "facts": facts, "option_values": option_values,
            "text_sha256": stable_hash(state),
        },
    }


# ---------------------------------------------------------------------------
# Probability programs and their deterministic solver.


def probability_value(facts):
    kind = facts["kind"]
    if kind == "bayes":
        base, sensitivity, fpr = (Fraction(facts[k]) for k in ("base", "sensitivity", "fpr"))
        return base * sensitivity / (base * sensitivity + (1 - base) * fpr)
    if kind == "table":
        return Fraction(facts["a"], facts["a"] + facts["b"])
    if kind == "independent":
        ps = [Fraction(v) for v in facts["probabilities"]]
        if facts["event"] == "any":
            product = Fraction(1)
            for p in ps:
                product *= 1 - p
            return 1 - product
        product = Fraction(1)
        for p in ps:
            product *= p
        return product
    if kind == "expected_value":
        scores = {}
        for name, item in facts["projects"].items():
            scores[name] = Fraction(item["p"]) * int(item["gain"]) + (1 - Fraction(item["p"])) * int(item["loss"]) - int(item["cost"])
        return max(scores, key=scores.get)
    if kind == "compare":
        a = Fraction(facts["a_success"]) * Fraction(facts["a_given"])
        b = Fraction(facts["b_success"]) * Fraction(facts["b_given"])
        return "A" if a > b else "B"
    raise ValueError(kind)


def numeric_distractors(rng, correct, mode):
    if mode == "bucket":
        value = float(correct)
        buckets = [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.0001)]
        answer = next("{}%–{}%".format(int(lo * 100), int(hi * 100)) for lo, hi in buckets if lo <= value < hi)
        options = [("{}%–{}%".format(int(lo * 100), int(hi * 100)), "between {}% and {}%".format(int(lo * 100), int(hi * 100))) for lo, hi in buckets]
        return answer, options
    answer = percent(correct)
    candidates = [correct, 1 - correct, min(Fraction(99, 100), correct + Fraction(rng.choice([8, 12, 18, 25]), 100)),
                  max(Fraction(1, 100), correct - Fraction(rng.choice([8, 12, 18, 25]), 100))]
    values = []
    for candidate in candidates:
        rendered = percent(candidate)
        if rendered not in values:
            values.append(rendered)
    while len(values) < 4:
        rendered = "{}.0%".format(rng.randint(1, 99))
        if rendered not in values:
            values.append(rendered)
    return answer, [(value, value) for value in values[:4]]


def render_probability_state(split, facts, form, rng):
    org = rng.choice(VOCAB[split]["orgs"])
    person = rng.choice(VOCAB[split]["people"])
    kind = facts["kind"]
    lead = {
        "train": "{}'s audit note records the following figures.".format(org),
        "development": "{} is reviewing a closed-world operating report.".format(person),
        "test": "Use only the stated figures; unrelated operational notes do not change the calculation.",
    }[split]
    if kind == "bayes":
        text = ("{} A condition is present in {} of accounts. The screening rule flags an affected account with probability {} and flags an unaffected account with probability {}. "
                "A randomly selected account has been flagged.".format(lead, percent(Fraction(facts["base"])), percent(Fraction(facts["sensitivity"])), percent(Fraction(facts["fpr"]))))
        value = probability_value(facts)
        if form == "more_likely":
            threshold = Fraction(facts["threshold"])
            question = "Is the probability that the flagged account is affected greater than {}?".format(percent(threshold))
            options, answer = [("yes", "Yes"), ("no", "No")], "yes" if value > threshold else "no"
        else:
            question = "What is the posterior probability that the flagged account is affected?"
            answer, options = numeric_distractors(rng, value, form)
        return text, question, answer, options
    if kind == "table":
        text = ("{} In a review of service renewals, {} customers both renewed and used feature X; {} used feature X but did not renew. "
                "Among customers not using feature X, {} renewed and {} did not.".format(lead, facts["a"], facts["b"], facts["c"], facts["d"]))
        value = probability_value(facts)
        if form == "more_likely":
            threshold = Fraction(facts["threshold"])
            question = "Conditional on using feature X, is renewal more likely than {}?".format(percent(threshold))
            options, answer = [("yes", "Yes"), ("no", "No")], "yes" if value > threshold else "no"
        else:
            question = "Conditional on using feature X, what is the probability of renewal?"
            answer, options = numeric_distractors(rng, value, form)
        return text, question, answer, options
    if kind == "independent":
        ps = [Fraction(v) for v in facts["probabilities"]]
        description = "; ".join("service {} succeeds with probability {}".format(i + 1, percent(p)) for i, p in enumerate(ps))
        text = "{} {}. The services fail independently.".format(lead, description)
        value = probability_value(facts)
        event_text = "at least one service succeeds" if facts["event"] == "any" else "every service succeeds"
        if form == "more_likely":
            threshold = Fraction(facts["threshold"])
            question = "Is it more likely than {} that {}?".format(percent(threshold), event_text)
            options, answer = [("yes", "Yes"), ("no", "No")], "yes" if value > threshold else "no"
        else:
            question = "What is the probability that {}?".format(event_text)
            answer, options = numeric_distractors(rng, value, form)
        return text, question, answer, options
    if kind == "expected_value":
        entries = []
        for name, item in facts["projects"].items():
            entries.append("{}: {} chance of {}, otherwise {}, with an up-front cost of {}".format(name, percent(Fraction(item["p"])), cents(int(item["gain"]) * 100), cents(abs(int(item["loss"])) * 100), cents(int(item["cost"]) * 100)))
        text = "{} Choose using expected net value (expected payoff minus cost). {}.".format(lead, ". ".join(entries))
        answer = probability_value(facts)
        question = "Which project has the highest expected net value?"
        options = [(name, "Select {}".format(name)) for name in facts["projects"]]
        return text, question, answer, options
    if kind == "compare":
        text = ("{} Plan A has a {} probability of passing its preliminary screen and then a {} probability of success. "
                "Plan B has a {} probability of passing its preliminary screen and then a {} probability of success. The two-stage figures are conditional as stated.".format(
                    lead, percent(Fraction(facts["a_given"])), percent(Fraction(facts["a_success"])), percent(Fraction(facts["b_given"])), percent(Fraction(facts["b_success"]))))
        answer = probability_value(facts)
        return text, "Which plan has the higher overall probability of success?", answer, [("A", "Plan A"), ("B", "Plan B")]
    raise ValueError(kind)


def gen_probability(split, ordinal, rng):
    kind = rng.choices(["bayes", "table", "independent", "expected_value", "compare"], [28, 15, 22, 20, 15])[0]
    form = rng.choices(["value", "bucket", "more_likely", "choice"], [51, 23, 10, 16])[0]
    if kind in ("expected_value", "compare"):
        form = "choice"
    if kind == "bayes":
        facts = {"kind": kind, "base": str(Fraction(rng.choice([2, 4, 6, 8, 12, 18, 25]), 100)), "sensitivity": str(Fraction(rng.choice([60, 70, 75, 80, 85, 90, 95]), 100)), "fpr": str(Fraction(rng.choice([2, 5, 8, 10, 15, 20, 25]), 100)), "threshold": str(Fraction(rng.choice([20, 30, 40, 50, 60, 70]), 100))}
    elif kind == "table":
        facts = {"kind": kind, "a": rng.randint(12, 95), "b": rng.randint(12, 95), "c": rng.randint(12, 95), "d": rng.randint(12, 95), "threshold": str(Fraction(rng.choice([25, 35, 45, 55, 65, 75]), 100))}
    elif kind == "independent":
        facts = {"kind": kind, "probabilities": [str(Fraction(rng.choice([35, 45, 55, 60, 65, 70, 75, 80, 85, 90]), 100)) for _ in range(rng.choice([2, 3, 4]))], "event": rng.choice(["any", "all"]), "threshold": str(Fraction(rng.choice([35, 45, 55, 65, 75, 85]), 100))}
    elif kind == "expected_value":
        names = rng.sample(["Atlas", "Beacon", "Cedar", "Delta", "Ember", "Fjord"], 4)
        projects = {}
        for name in names:
            projects[name] = {"p": str(Fraction(rng.choice([25, 35, 45, 55, 65, 75]), 100)), "gain": rng.randrange(100, 550, 25), "loss": -rng.randrange(25, 220, 25), "cost": rng.randrange(0, 160, 20)}
        facts = {"kind": kind, "projects": projects}
    else:
        facts = {"kind": kind, "a_given": str(Fraction(rng.choice([35, 45, 55, 65, 75, 85]), 100)), "a_success": str(Fraction(rng.choice([35, 45, 55, 65, 75, 85]), 100)), "b_given": str(Fraction(rng.choice([35, 45, 55, 65, 75, 85]), 100)), "b_success": str(Fraction(rng.choice([35, 45, 55, 65, 75, 85]), 100))}
        while probability_value(facts) == "B" and Fraction(facts["a_given"]) * Fraction(facts["a_success"]) == Fraction(facts["b_given"]) * Fraction(facts["b_success"]):
            facts["b_success"] = str(Fraction(rng.choice([35, 45, 55, 65, 75, 85]), 100))
    state, instruction, answer, options = render_probability_state(split, facts, form, rng)
    question = shuffled_choice(rng, instruction, options, answer, "targeted_v2_probability")
    return make_record(split, "probability", ordinal, state, {"decision": question}, facts, "{}:{}".format(kind, form), "probability-v{}".format({"train": 1, "development": 2, "test": 3}[split]))


# ---------------------------------------------------------------------------
# Long-policy programs.  All policy decisions are made by the interpreter.


DOMAIN = {
    "lodging": {"title": "Lodging Interruption Benefit", "event": "a booked stay became unusable after a transport disruption"},
    "equipment": {"title": "Portable Equipment Repair Benefit", "event": "a covered tablet was damaged by a sudden accidental drop"},
    "residence": {"title": "Residence Emergency Service Benefit", "event": "a sudden plumbing leak damaged the insured residence"},
    "allowance": {"title": "Professional Development Allowance", "event": "an approved training course was cancelled by its provider"},
}


def solve_policy(facts):
    if not facts["purchased"]:
        return "deny_not_purchased", 0
    if not facts["covered_event"]:
        return "deny_not_covered", 0
    if facts["excluded"]:
        return "deny_exclusion", 0
    if facts["report_days"] > facts["notice_days"]:
        return "deny_late", 0
    usable_limit = min(facts["limit"], facts["sublimit"])
    payable = min(facts["loss"], usable_limit) - facts["deductible"]
    if payable <= 0:
        return "deny_deductible", 0
    return "pay", payable


def policy_options(rng, facts):
    outcome, amount = solve_policy(facts)
    outcome_text = {
        "deny_not_purchased": "Deny because the relevant benefit was not purchased.",
        "deny_not_covered": "Deny because the described event is outside the covered event definition.",
        "deny_exclusion": "Deny because a stated exclusion applies.",
        "deny_late": "Deny because the reporting deadline was missed.",
        "deny_deductible": "Deny because the loss does not exceed the deductible.",
        "pay": "Approve the claim under the applicable benefit.",
    }
    outcomes = [(key, value) for key, value in outcome_text.items()]
    max_without_deductible = min(facts["loss"], facts["limit"], facts["sublimit"])
    wrong_limit = max(0, min(facts["loss"], facts["limit"]) - facts["deductible"])
    amount_values = [amount, max_without_deductible, wrong_limit, max(0, facts["loss"] - facts["deductible"]), 0]
    dedup = []
    for value in amount_values:
        if value not in dedup:
            dedup.append(value)
    while len(dedup) < 4:
        candidate = max(0, amount + rng.choice([-1, 1]) * rng.randrange(2500, 30000, 2500))
        if candidate not in dedup:
            dedup.append(candidate)
    return outcome, outcomes, amount, [(str(value), cents(value)) for value in dedup[:5]]


def clause_library(split, rng, domain, index):
    org = rng.choice(VOCAB[split]["orgs"])
    product = rng.choice(VOCAB[split]["products"])
    if index == 0:
        return ("Section 1 — Contract administration. {} maintains the {} plan. Identifiers in this handbook are administrative only. "
                "A heading, marketing example, or comparison chart does not itself grant coverage. Claims staff must apply the schedule, definitions, exclusions, and settlement provisions together.").format(org, product)
    generic = [
        "The administrator may request invoices, receipts, and a concise chronology. A request for documents is not an admission of liability and does not extend a deadline unless a written extension is issued.",
        "Examples in training materials illustrate common situations only. When an example conflicts with the schedule of benefits, the schedule and the applicable endorsement control.",
        "Benefits are considered separately. A benefit that is listed but not purchased has no available limit. A purchased benefit remains subject to its own event definition, exclusions, reporting rule, and settlement calculation.",
        "Amounts quoted in summaries may be rounded for explanation. The payable amount is computed from the covered loss, any applicable sublimit, and the deductible in the order stated in the settlement clause.",
        "The plan does not reimburse speculative future costs, routine maintenance, ordinary wear, or a charge that is not supported by the described covered event. This paragraph does not create an additional exclusion beyond the applicable benefit section.",
        "A claimant should report an incident promptly and preserve reasonable evidence. Different benefits can have different notice periods; the notice period for the selected benefit governs that benefit.",
    ]
    return "Section {} — {} administrative provision. {}".format(index + 1, domain["title"], rng.choice(generic))


def render_policy(split, facts, rng):
    target = DOMAIN[facts["domain"]]
    domains = list(DOMAIN)
    rng.shuffle(domains)
    if facts["domain"] not in domains[:4]:
        domains[0] = facts["domain"]
    domains = list(dict.fromkeys(domains))
    while len(domains) < 4:
        domains.append(rng.choice(list(DOMAIN)))
    purchased_text = "purchased" if facts["purchased"] else "not purchased"
    schedule = [
        "SCHEDULE OF BENEFITS — {} is {}. Limit: {}. Event sublimit: {}. Deductible: {}. Notice period: {} days.".format(
            target["title"], purchased_text, cents(facts["limit"]), cents(facts["sublimit"]), cents(facts["deductible"]), facts["notice_days"])
    ]
    for domain_name in domains:
        if domain_name == facts["domain"]:
            continue
        distractor = DOMAIN[domain_name]
        schedule.append("SCHEDULE OF BENEFITS — {} is {}. Its separate event definition and limits do not apply to another benefit.".format(distractor["title"], rng.choice(["purchased", "not purchased"])))
    target_clauses = [
        "BENEFIT DEFINITION — {} applies only when {}.".format(target["title"], target["event"]),
        "EXCLUSIONS — The benefit does not apply where {}.".format("the loss resulted from an excluded circumstance" if facts["excluded"] else "an exclusion expressly applies"),
        "NOTICE — A claim under this benefit must be reported no later than {} days after the event.".format(facts["notice_days"]),
        "SETTLEMENT — After confirming purchase, event eligibility, exclusions, and timely notice, pay the lesser of the covered loss, the benefit limit, and the event sublimit, then subtract the deductible. A non-positive result is not payable.",
    ]
    incident = ("CLAIM FILE — {} reports that {}. The reported loss is {}. The incident was reported {} days later. "
                "For this file, the event {} within the selected benefit definition, and an exclusion {}.".format(
                    rng.choice(VOCAB[split]["people"]), target["event"], cents(facts["loss"]), facts["report_days"],
                    "falls" if facts["covered_event"] else "does not fall", "does apply" if facts["excluded"] else "does not apply"))
    sections = [clause_library(split, rng, target, 0), "\n".join(schedule)]
    for domain_name in domains:
        domain = DOMAIN[domain_name]
        if domain_name == facts["domain"]:
            sections.append("SECTION — {}\n{}".format(domain["title"], "\n".join(target_clauses)))
        else:
            text = ("SECTION — {}\nThis separate benefit concerns {}. It has its own purchase status, event definition, limits, deductible, exclusions, and notice rule. "
                    "It must not be substituted for the benefit identified in the claim file.").format(domain["title"], domain["event"])
            sections.append(text)
        sections.append(clause_library(split, rng, domain, len(sections)))
    sections.append(incident)
    target_chars = rng.randint(5200, 14500)
    padding_index = 0
    while len("\n\n".join(sections)) < target_chars:
        sections.append(clause_library(split, rng, target, 20 + padding_index))
        padding_index += 1
    return "\n\n".join(sections)


def gen_policy(split, ordinal, rng):
    domain = rng.choice(list(DOMAIN))
    facts = {
        "domain": domain,
        "purchased": rng.random() < .78,
        "covered_event": rng.random() < .86,
        "excluded": rng.random() < .20,
        "report_days": rng.randint(1, 60),
        "notice_days": rng.choice([10, 14, 21, 30, 45]),
        "loss": rng.randrange(10000, 420000, 2500),
        "limit": rng.choice([75000, 100000, 150000, 250000, 350000]),
        "sublimit": rng.choice([50000, 75000, 100000, 125000, 175000, 250000]),
        "deductible": rng.choice([0, 5000, 10000, 25000, 50000]),
    }
    state = render_policy(split, facts, rng)
    outcome, outcome_options, amount, amount_options = policy_options(rng, facts)
    questions = {
        "outcome": shuffled_choice(rng, "What is the correct claim outcome under the selected benefit?", outcome_options, outcome, "targeted_v2_policy"),
        "amount": shuffled_choice(rng, "What amount should be paid under the selected benefit?", amount_options, str(amount), "targeted_v2_policy"),
    }
    return make_record(split, "policy", ordinal, state, questions, facts, "long_multi_benefit:{}".format(domain), "policy-v{}".format({"train": 1, "development": 2, "test": 3}[split]))


# ---------------------------------------------------------------------------
# Validation, split isolation and output.


def verify_record(record):
    facts = record["_meta"]["facts"]
    family = record["_meta"]["family"]
    values = record["_meta"]["option_values"]
    if family == "probability":
        kind = facts["kind"]
        if kind in ("expected_value", "compare"):
            expected = probability_value(facts)
        else:
            expected = probability_value(facts)
            if record["_meta"]["subtype"].endswith(":more_likely"):
                expected = "yes" if expected > Fraction(facts["threshold"]) else "no"
            elif record["_meta"]["subtype"].endswith(":bucket"):
                value = float(expected)
                expected = next("{}%–{}%".format(int(lo * 100), int(hi * 100)) for lo, hi in [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.0001)] if lo <= value < hi)
            else:
                expected = percent(expected)
        question = record["questions"]["decision"]
        if values["decision"][question["label"]] != expected:
            raise AssertionError("probability label mismatch")
    else:
        outcome, amount = solve_policy(facts)
        for name, expected in (("outcome", outcome), ("amount", str(amount))):
            question = record["questions"][name]
            if values[name][question["label"]] != expected:
                raise AssertionError("policy label mismatch")


def write_jsonl(path, records):
    with path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    all_hashes, result = set(), {}
    for split, sizes in SIZES.items():
        records = []
        for family, count in sizes.items():
            produced = 0
            attempts = 0
            while produced < count:
                attempts += 1
                if attempts > count * 40:
                    raise RuntimeError("dedup exhausted for {} {}".format(split, family))
                rng = random.Random("{}:{}:{}:{}".format(SEED, split, family, attempts))
                record = gen_probability(split, produced, rng) if family == "probability" else gen_policy(split, produced, rng)
                digest = record["_meta"]["text_sha256"]
                if digest in all_hashes:
                    continue
                verify_record(record)
                all_hashes.add(digest)
                records.append(record)
                produced += 1
        rng = random.Random("{}:shuffle:{}".format(SEED, split))
        rng.shuffle(records)
        path = OUT / "{}.jsonl".format(split)
        write_jsonl(path, records)
        family_counts = Counter(record["_meta"]["family"] for record in records)
        question_count = sum(len(record["questions"]) for record in records)
        policy_lengths = [len(record["state"]) for record in records if record["_meta"]["family"] == "policy"]
        result[split] = {
            "records": len(records), "questions": question_count, "families": dict(sorted(family_counts.items())),
            "policy_state_chars": {"min": min(policy_lengths), "median": statistics.median(policy_lengths), "mean": round(statistics.mean(policy_lengths), 1), "max": max(policy_lengths)},
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    manifest = {
        "version": VERSION, "seed": SEED, "purpose": "source-disjoint probability and long-policy continuation data",
        "labeling": "deterministic solvers only; labels are recomputed before write",
        "split_policy": "split-specific vocabulary/templates plus global exact-text hash exclusion",
        "probability": {"mechanisms": ["bayes", "table", "independent", "expected_value", "compare"], "forms": ["value", "bucket", "more_likely", "choice"]},
        "policy": {"record_questions": ["outcome", "amount"], "domains": ["lodging", "equipment", "residence", "allowance"], "state_char_target": [5200, 14500]},
        "outputs": result,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    (OUT / "README.md").write_text("# targeted-v2 probability + long-policy\n\nGenerated with `tools/build_targeted_v2_probability_policy.py`. Labels come from deterministic solvers; this set contains no frozen Kev evaluation records.\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build()
