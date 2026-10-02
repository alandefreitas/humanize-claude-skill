#!/usr/bin/env python3
"""
calibrate.py - measure how well the jev server separates positives from
negatives for every criterion in criteria.py, using samples.py.

  calibrate.py [--model english,multilingual,typed_decisions] [--no-labels] [--json] [--write]

For each criterion it prints AUC (probability that a random positive scores
above a random negative), mean P on positives and negatives, the threshold
that maximises balanced accuracy, and the false-positive rate at 0.5. The
last table ranks models if several are given (--model a,b,c).

Explicit noul option labels ("yes, the pattern is clearly present" / "no, plain
writing") are on by default, as in ai_tells.py; --no-labels measures without them.

Negatives for a criterion are the plain human samples PLUS the positives of
every other criterion ("hard negatives": AI-flavoured sentences without this
pattern), so a criterion only counts as reliable when it is specific, not when
it merely smells AI. Both AUCs are printed (plain / hard).

--write stores per-model thresholds and reliability in thresholds.json, which
ai_tells.py reads. Threshold rule (precision first, because flags are an
inventory the editor must act on): the threshold is the smallest value that
keeps the false-positive rate on all negatives at or below MAX_FPR (0.05),
and at least 0.10 above the highest negative when the classes separate; floor
0.30, ceiling 0.90. A criterion is reliable when AUC against all negatives
>= 0.75 and that threshold still catches at least half of its positives;
unreliable ones are reported as advisory only, never as flags.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from criteria import CRITERIA  # noqa: E402
import samples  # noqa: E402
from ai_tells import post, warm_up, DEFAULT_URL, question_payload, answer_value, chunks, QUESTIONS_PER_REQUEST, STATES_PER_REQUEST, THRESHOLDS_FILE  # noqa: E402

RELIABLE_AUC = 0.75
MAX_FPR = 0.05
FLOOR, CEIL = 0.30, 0.90


def threshold_rule(pos, neg):
    max_neg, min_pos = max(neg), min(pos)
    if min_pos > max_neg:
        t = max((min_pos + max_neg) / 2, max_neg + 0.10)
    else:
        allowed = int(MAX_FPR * len(neg))          # how many negatives may sit at/above the threshold
        srt = sorted(neg, reverse=True)
        t = srt[allowed] + 0.01 if allowed < len(srt) else srt[-1] + 0.01
    return round(min(CEIL, max(FLOOR, t)), 2)


def auc(pos, neg):
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(pos) * len(neg))


def best_threshold(pos, neg):
    cands = sorted(set(pos + neg))
    best, bt = -1, 0.5
    for t in cands:
        tpr = sum(1 for p in pos if p >= t) / len(pos)
        tnr = sum(1 for n in neg if n < t) / len(neg)
        ba = (tpr + tnr) / 2
        if ba > best:
            best, bt = ba, round(t, 2)
    return bt, best


def run(model, use_labels, url, timeout, lang="en"):
    POS, NEG_SENTENCES, NEG_PARAGRAPHS = samples.for_lang(lang)
    crit_by_scope = {}
    for c in CRITERIA:
        crit_by_scope.setdefault((c["scope"], bool(c.get("context"))), []).append(c)
    # build the state pool per scope: every positive of every criterion of that scope + the negatives
    out = {}
    stats = dict(requests=0, tokens=0, seconds=0.0)
    for (scope, ctx), crits in crit_by_scope.items():
        key = "sentence" if scope == "sentence" else "paragraph"
        texts = []
        for c in crits:
            texts += POS.get(c["id"], [])
        texts += NEG_SENTENCES if scope == "sentence" else NEG_PARAGRAPHS
        texts = list(dict.fromkeys(texts))
        states = [({"sentence": t, "paragraph": t} if ctx else {key: t}) for t in texts]
        answers = {t: {} for t in texts}
        for cgroup in chunks(crits, QUESTIONS_PER_REQUEST):
            questions = {}
            for c in cgroup:
                questions[c["id"]] = question_payload(c, lang, use_labels)
            if lang != "en":
                pass
            for sgroup in chunks(list(range(len(states))), STATES_PER_REQUEST):
                body = {"states": [states[i] for i in sgroup], "questions": questions}
                if model != "auto":
                    body["model"] = model
                if lang != "en":
                    body["lang"] = lang
                t0 = time.time()
                resp = post(url, "/v1/systemone/batch", body, timeout)
                stats["seconds"] += time.time() - t0
                stats["requests"] += 1
                stats["tokens"] += (resp.get("total_usage") or {}).get("input_tokens", 0)
                for i, res in zip(sgroup, resp["results"]):
                    for cid, ans in res["answers"].items():
                        c = next(x for x in cgroup if x["id"] == cid)
                        answers[texts[i]][cid] = answer_value(c, ans)[0]
        negs = NEG_SENTENCES if scope == "sentence" else NEG_PARAGRAPHS
        for c in crits:
            cid = c["id"]
            pos = [answers[t][cid] for t in POS.get(cid, []) if cid in answers[t]]
            plain = [answers[t][cid] for t in negs if cid in answers[t]]
            others = [t for cc in crits if cc["id"] != cid and not cc["id"].startswith("ai_overall") for t in POS.get(cc["id"], []) if t not in POS.get(cid, [])]
            hard = [answers[t][cid] for t in dict.fromkeys(others) if cid in answers[t]]
            if cid.startswith("ai_overall"):
                # every other criterion's positives are positives for the overall score; only plain text is negative
                pos += hard
                hard = []
            if c.get("plain_neg_only"):
                hard = []
            if not pos:
                # no samples in this language: unreliable by construction, but keep the negatives' spread on record
                neg = plain + hard
                out[cid] = dict(rule=c["rule"], scope=scope, n_pos=0, n_neg=len(neg), auc=None, auc_plain=None, auc_hard=None,
                                mean_pos=None, mean_neg=round(sum(neg) / len(neg), 3) if neg else None,
                                max_neg=round(max(neg), 3) if neg else None, min_pos=None, tpr=None, fpr=None,
                                threshold=0.5, reliable=False)
                continue
            neg = plain + hard
            t_all = threshold_rule(pos, neg)
            auc_all = auc(pos, neg)
            tpr = sum(1 for p in pos if p >= t_all) / len(pos)
            out[cid] = dict(rule=c["rule"], scope=scope, n_pos=len(pos), n_neg=len(neg), auc=round(auc_all, 3),
                            auc_plain=round(auc(pos, plain), 3), auc_hard=round(auc(pos, hard), 3) if hard else None,
                            mean_pos=round(sum(pos) / len(pos), 3), mean_neg=round(sum(neg) / len(neg), 3),
                            max_neg=round(max(neg), 3), min_pos=round(min(pos), 3), tpr=round(tpr, 2),
                            fpr=round(sum(1 for n in neg if n >= t_all) / len(neg), 2),
                            threshold=t_all, reliable=bool(auc_all >= RELIABLE_AUC and tpr >= 0.5))
    return out, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="english", help="comma list of checkpoints to compare")
    ap.add_argument("--lang", default="en", help="en, es or pt: which sample set and question language to use; thresholds are stored under model/lang")
    ap.add_argument("--no-labels", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true", help="store thresholds and reliability per model in thresholds.json")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--timeout", type=float, default=300)
    a = ap.parse_args()
    warm_up(a.url, a.timeout)
    results = {}
    for model in a.model.split(","):
        model = model.strip()
        res, st = run(model, not a.no_labels, a.url, a.timeout, a.lang)
        results[model + "/" + a.lang] = dict(criteria=res, stats=st)
        if a.json:
            continue
        print("\n## model=%s lang=%s labels=%s  (%d requests, %d tokens, %.1fs)\n" % (model, a.lang, not a.no_labels, st["requests"], st["tokens"], st["seconds"]))
        print("| Rule | Criterion | AUC all | AUC plain | AUC hard | mean P+ | mean P- | threshold | TPR | FPR | reliable |")
        print("|---|---|---|---|---|---|---|---|---|---|---|")
        f2 = lambda v: "-" if v is None else "%.2f" % v
        for cid, r in res.items():
            print("| %s | %s | %s | %s | %s | %s | %s | %.2f | %s | %s | %s |" % (
                r["rule"], cid, f2(r["auc"]), f2(r["auc_plain"]), f2(r["auc_hard"]), f2(r["mean_pos"]), f2(r["mean_neg"]), r["threshold"], f2(r["tpr"]), f2(r["fpr"]), "yes" if r["reliable"] else ("no samples" if r["n_pos"] == 0 else "NO")))
        aucs = [r["auc"] for r in res.values() if r["auc"] is not None]
        fprs = [r["fpr"] for r in res.values() if r["fpr"] is not None]
        print("\nmean AUC %.3f over %d measured criteria; reliable: %d of %d; mean FPR at threshold %.2f" % (
            sum(aucs) / len(aucs), len(aucs), sum(1 for r in res.values() if r["reliable"]), len(res), sum(fprs) / len(fprs)))
    if a.json:
        print(json.dumps(results, indent=1))
    if a.write:
        store = {}
        if os.path.exists(THRESHOLDS_FILE):
            with open(THRESHOLDS_FILE) as f:
                store = json.load(f)
        POS_, NEG_S_, NEG_P_ = samples.for_lang(a.lang)
        for model, r in results.items():
            store[model] = dict(generated=time.strftime("%Y-%m-%d"), labels=not a.no_labels, lang=a.lang, n_neg_sentences=len(NEG_S_),
                                criteria={cid: dict(threshold=x["threshold"], reliable=x["reliable"], auc=x["auc"]) for cid, x in r["criteria"].items()})
        with open(THRESHOLDS_FILE, "w") as f:
            json.dump(store, f, indent=1, sort_keys=True)
        print("\nwrote %s for models: %s" % (THRESHOLDS_FILE, ", ".join(results)))


if __name__ == "__main__":
    main()
