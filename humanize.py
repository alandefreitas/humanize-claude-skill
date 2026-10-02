#!/usr/bin/env python3
"""
humanize.py - one report with everything needed to edit a text so it stops reading as AI-written.

Runs in parallel: the model-backed AI tells scan (ai-tells/ai_tells.py, local jev server), the core
vocabulary check (simple-english/simple_english.py) and the linters for the language (vale with the packs
in vale/, proselint for English, languagetool for Spanish and Portuguese). Prints one Markdown report in
which every section says how the editor must treat it. The humanize skill (SKILL.md) is: run this, act on
the report, re-run until the report's own "Done when" condition holds.

  humanize.py FILE [--lang en|es|pt] [--spoken] [--no-model] [--no-linters] [--margin 0.1]
                   [--top 1000] [--allow w,w] [--advisory] [--json] [--verbose]
  humanize.py - < text          (stdin)

Exit codes: 0 report printed; 2 report printed but the jev server was unreachable (model section empty,
section 5 lists every criterion); 3 usage; 4 language unknown (nothing ran, pass --lang).
"""
import argparse
import bisect
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "ai-tells"))
sys.path.insert(0, os.path.join(HERE, "simple-english"))
import ai_tells  # noqa: E402
import simple_english  # noqa: E402

VALE_INI = {lang: os.path.join(HERE, "vale", lang + ".ini") for lang in ("en", "es", "pt")}
LT_LANG = {"en": "en-US", "es": "es", "pt": "pt-BR"}
MAX_LINT_ROWS = 80

DET_GUIDE = ("Binding. Fix every row in the rewrite, or keep it with a one-line reason (literal code, a list item with "
             "internal commas, a quoted title). The passive_voice rows are candidates, not verdicts: keep the passive when "
             "the actor is unknown or irrelevant, when the thing acted on is the topic, or when the field writes it that "
             "way. Rewrite it when the actor matters. passive_agent_named rows ('was fixed by the team') are the clear "
             "rewrite case.")
FLAGS_GUIDE = ("Inventory, not verdicts. A small zero-shot classifier answered one question per criterion for every "
               "sentence and paragraph. P is its probability that the pattern is present. Read each flagged unit. If the "
               "pattern is there, fix it in the rewrite. If it is not, reject the flag with a one-line reason. Rejecting is "
               "normal, especially chatbot_artifact and negative_parallelism on text that addresses the reader. Dropping a "
               "flag without saying so is not.")
VOCAB_GUIDE = ("Binding. Replace each word with a core word, or keep it with a one-line reason: a technical term whose "
               "plain paraphrase would be wrong or much longer, the ordinary name of the thing (passport, landlord), a "
               "proper noun the checker did not recognise, or precision where the core word changes the meaning "
               "(estimate vs guess). A high band (5k and up, or rare) almost always has a 1k or 2k equivalent. Do not swap "
               "a hard word for a clumsy phrase, and do not keep a word because it sounds better.")
LINT_GUIDE = ("Second opinion from regex linters. Use what is right and ignore the rest: vale's AI-writing packs are "
              "usually right. proselint also flags legitimate technical writing. languagetool's grammar and spelling are "
              "trustworthy, its style suggestions less so.")
DELETE_TEST = ("- The delete test, on every clause of the rewrite: read the clause, delete it in your head, and ask whether "
               "the reader lost a fact, an instruction or a needed nuance. If not, cut it. Empty confirmations (it is all "
               "done, just to confirm), padding verbs of intention (I went ahead and, I just wanted to), restating what a "
               "later line shows, and announcing something you did not do all fail the test. List the clauses you cut.")
SPOKEN_RULES = ("- Spoken delivery: use contractions, put the key idea at the front of each sentence, no bullet lists "
                "inside prose, vary sentence length on purpose, and read the text aloud: replace any word that does not "
                "roll off the tongue.")
DONE = ("A re-run of this report on the rewrite shows: section 1 empty, every remaining row of section 2 rejected with a "
        "reason, every remaining word of section 3 kept with a reason. Then deliver the final text (written back to the "
        "file when the input was a file), followed by the rejected flags, the kept words and the clauses you cut, each "
        "with its one-line reason. Do not introduce what this report flags: the re-run will catch it.")


# ---------------------------------------------------------------------------
# Linters
# ---------------------------------------------------------------------------
def run_cmd(cmd, timeout=180):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timed out after %ds" % timeout
    except OSError as e:
        return None, str(e)
    return p, None


def run_vale(path, lang):
    if not shutil.which("vale"):
        return dict(tool="vale", status="not installed", rows=[])
    p, err = run_cmd(["vale", "--no-global", "--config", VALE_INI[lang], "--output=JSON", path])
    if err:
        return dict(tool="vale", status=err, rows=[])
    try:
        data = json.loads(p.stdout or "{}")
    except ValueError:
        return dict(tool="vale", status="unreadable output: " + (p.stderr or p.stdout)[:200].strip(), rows=[])
    rows = []
    for items in (data.values() if isinstance(data, dict) else []):
        for it in items:
            rows.append(dict(line=it.get("Line", 0), check=it.get("Check", ""), message=it.get("Message", ""), match=it.get("Match", "")))
    rows.sort(key=lambda r: r["line"])
    return dict(tool="vale", status="ok", rows=rows)


def run_proselint(path):
    if not shutil.which("proselint"):
        return dict(tool="proselint", status="not installed", rows=[])
    p, err = run_cmd(["proselint", "-o", "json", "check", path])
    if err:
        return dict(tool="proselint", status=err, rows=[])
    rows = []
    out = (p.stdout or "").strip()
    if out:
        try:
            data = json.loads(out)
            errors = data.get("data", {}).get("errors", []) if isinstance(data, dict) else data
            for e in errors:
                rows.append(dict(line=e.get("line", 0), check=e.get("check", ""), message=e.get("message", ""), match=""))
        except ValueError:
            for line in out.splitlines():
                m = re.match(r".*?:(\d+):\d+:\s*(\S+)\s+(.*)", line)
                rows.append(dict(line=int(m.group(1)), check=m.group(2), message=m.group(3), match="") if m
                            else dict(line=0, check="", message=line, match=""))
    rows.sort(key=lambda r: r["line"])
    return dict(tool="proselint", status="ok", rows=rows)


def lt_json(args, timeout=300):
    """Run languagetool and return its JSON (it prints progress lines before the JSON object)."""
    p, err = run_cmd(["languagetool", "--json"] + args, timeout=timeout)
    if err:
        return None, err
    out = (p.stdout or "").strip()
    start = out.find("{")
    if start < 0:
        return None, "unreadable output: " + (p.stderr or out)[:200].strip()
    try:
        return json.loads(out[start:]), None
    except ValueError:
        return None, "unreadable output: " + out[start:start + 200]


def run_languagetool(path, lang, text):
    if not shutil.which("languagetool"):
        return dict(tool="languagetool", status="not installed", rows=[])
    data, err = lt_json(["-l", LT_LANG[lang], path])
    if err:
        return dict(tool="languagetool", status=err, rows=[])
    line_starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(i + 1)
    rows = []
    for m in data.get("matches", []):
        off = m.get("offset", 0)
        ctx = m.get("context") or {}
        match = (ctx.get("text") or "")[ctx.get("offset", 0): ctx.get("offset", 0) + ctx.get("length", 0)]
        rule = m.get("rule") or {}
        cat = (rule.get("category") or {}).get("name", "")
        rows.append(dict(line=bisect.bisect_right(line_starts, off), check=(cat + "/" if cat else "") + rule.get("id", ""),
                         message=m.get("message", ""), match=match))
    return dict(tool="languagetool", status="ok", rows=rows)


def lt_detect(path):
    """Language fallback when the stopword vote is inconclusive: languagetool's own detector, with its confidence."""
    if not shutil.which("languagetool"):
        return None
    data, err = lt_json(["-adl", path])
    if err or not data:
        return None
    d = (data.get("language") or {}).get("detectedLanguage") or {}
    code = (d.get("code") or "").split("-")[0].lower()
    return dict(code=code, confidence=d.get("confidence"))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def lang_sentence(info):
    c = info.get("counts") or {}
    ev = ", ".join("%s %d" % (k, c[k]) for k in ("en", "es", "pt") if k in c)
    if info["source"] == "explicit":
        return "Language %s (given)." % info["lang"]
    if info["source"] == "languagetool":
        return "Language %s (detected by languagetool, confidence %.2f; the stopword vote was inconclusive: %s)." % (
            info["lang"], info["confidence"] or 0.0, ev)
    if info["lang"] is None:
        return "Language unknown (stopword vote confidence %.2f: %s over %d words%s). Nothing ran. Pass --lang en|es|pt." % (
            info["confidence"], ev, info.get("words", 0), info.get("lt_note", ""))
    return "Language %s (detected, confidence %.2f: %s)." % (info["lang"], info["confidence"], ev)


def render(a, info, scan, vocab, lint):
    s = scan["summary"]
    out = ["# Humanize report: %s" % a.file, ""]
    out.append(lang_sentence(info) + (" Spoken mode: sentences flagged at %d words." % s["long_flag"] if a.spoken else ""))
    if s["server_error"]:
        model = "model did not run"
    elif a.no_model:
        model = "model off"
    else:
        model = "checkpoint %s answered %d criteria on %d of %d sentences and every paragraph in %d requests, %.1fs" % (
            ",".join(s["models_used"]) or "?", s["criteria"], s["sentences_checked"], s["sentences"], s["requests"], s["seconds"])
    vocab_label = vocab["label"] if "error" not in vocab else "did not run"
    if lint:
        lint_label = ", ".join("%s %d" % (x["tool"], len(x["rows"])) if x["status"] == "ok" else "%s %s" % (x["tool"], x["status"]) for x in lint)
    else:
        lint_label = "off"
    out.append("Scan: %d paragraphs, %d sentences; %s. Vocabulary: %s. Linters: %s." % (s["paragraphs"], s["sentences"], model, vocab_label, lint_label))

    det = scan["deterministic"]
    out += ["", "## 1. Deterministic findings (%d)" % len(det), "", DET_GUIDE, ""]
    out += ai_tells.deterministic_table(det)

    out += ["", "## 2. Model flags (%d)" % len(scan["flags"]), ""]
    if s["server_error"]:
        out += ["The model did not run: %s" % s["server_error"], "",
                "Apply every criterion in section 5 by reading, and say in your output that the model scan did not run."]
    elif a.no_model:
        out += ["Model checks were switched off (--no-model). Apply every criterion in section 5 by reading."]
    else:
        out += [FLAGS_GUIDE, ""]
        out += ai_tells.flags_table(scan["flags"]) if scan["flags"] else ["none at or above threshold"]
        start = [r for r in scan["ranked"] if r["flags"] >= 2][:10]
        if start:
            out += ["", "Where to start (units with two or more flags; three or more usually means rewrite the sentence from scratch):", ""]
            out += ai_tells.ranked_table(start, 10)
        if s["truncated"]:
            out += ["", "%d answers came from truncated inputs (a very long sentence or paragraph). Treat them with care." % s["truncated"]]

    if "error" in vocab:
        out += ["", "## 3. Off-list words", "", "Vocabulary check did not run: %s" % vocab["error"]]
    else:
        r = vocab["result"]
        rows = simple_english.off_list_rows(r)
        out += ["", "## 3. Off-list words (%d)" % len(rows), "", VOCAB_GUIDE, ""]
        out += ["%s. %s" % (vocab["label"], simple_english.summary_lines(r)[0]), simple_english.summary_lines(r)[1], ""]
        if rows:
            out += ["| Word | Count | Band | Context |", "|---|---|---|---|"]
            for x in rows:
                out.append("| %s | %d | %s | %s |" % (x["word"], x["count"], x["band"], ai_tells.md_escape(x["context"])))
        else:
            out.append("none")
        if r["names"]:
            out += ["", "Treated as names and not checked: " + ", ".join(sorted(r["names"])) + "."]

    if lint:
        out += ["", "## 4. Linter notes (%s)" % lint_label, "", LINT_GUIDE, ""]
        rows = [dict(x, tool=l["tool"]) for l in lint for x in l["rows"]]
        rows.sort(key=lambda x: (x["line"], x["tool"]))
        if rows:
            for x in rows[:MAX_LINT_ROWS]:
                where = ("'%s': " % x["match"]) if x["match"] and x["match"] not in x["message"] else ""
                out.append("- L%d %s %s: %s%s" % (x["line"], x["tool"], x["check"], where, x["message"]))
            if len(rows) > MAX_LINT_ROWS:
                out.append("- ... and %d more" % (len(rows) - MAX_LINT_ROWS))
        else:
            out.append("none")

    out += ["", "## 5. Rules only you can apply", ""]
    if s["server_error"] or a.no_model:
        crits = [dict(rule=c["rule"], id=c["id"], scope=c["scope"], q=ai_tells.criterion_question(c, s["lang"])) for c in ai_tells.CRITERIA]
        out += ["The model did not run, so every criterion is yours. Read every sentence and paragraph against each question:", ""]
    else:
        crits = scan["unreliable"]
        out += ["The model is not reliable on these criteria (measured in calibration), so they never appear in section 2. "
                "Read every sentence and paragraph against each question:", ""]
    for c in crits:
        if c["id"].startswith("ai_overall"):
            continue
        out.append("- %s %s (%s): %s" % (c["rule"], c["id"], c["scope"], c["q"]))
    out.append(DELETE_TEST)
    if a.spoken:
        out.append(SPOKEN_RULES)
    if a.advisory and scan["advisory"]:
        out += ["", "Hints from the model on these criteria (below its reliability bar, judge each one yourself):", ""]
        out += ai_tells.flags_table(scan["advisory"])

    out += ["", "## Done when", "", DONE, ""]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="text or Markdown file, or - for stdin")
    ap.add_argument("--lang", choices=["en", "es", "pt"], help="language of the text (default: detect, with a confidence)")
    ap.add_argument("--spoken", action="store_true", help="talk script: sentences flagged at 20 words, spoken rules added to section 5")
    ap.add_argument("--no-model", action="store_true", help="skip the jev model (deterministic checks, vocabulary and linters only)")
    ap.add_argument("--no-linters", action="store_true", help="skip vale, proselint and languagetool")
    ap.add_argument("--margin", type=float, default=0.0, help="raise every model threshold (0.1 trims flags on long documents)")
    ap.add_argument("--advisory", action="store_true", help="add the model's hits on unreliable criteria to section 5 as hints")
    ap.add_argument("--top", type=int, default=0, help="stricter vocabulary: only the first N core words (1000 for non-native readers)")
    ap.add_argument("--allow", default="", help="comma list of words the vocabulary check accepts this run")
    ap.add_argument("--url", default=ai_tells.DEFAULT_URL, help="jev server (default %(default)s)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--verbose", action="store_true", help="progress on stderr")
    a = ap.parse_args()

    tmp = None
    if a.file == "-":
        text = sys.stdin.read()
        tmp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        tmp.write(text)
        tmp.close()
        path = tmp.name
    else:
        try:
            with open(a.file, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print("cannot read %s: %s" % (a.file, e), file=sys.stderr)
            return 3
        path = a.file

    def progress(msg):
        if a.verbose:
            print(msg, file=sys.stderr, flush=True)

    try:
        if a.lang:
            d = ai_tells.detect_lang(text)
            info = dict(lang=a.lang, source="explicit", confidence=1.0, counts=d["counts"], words=d["words"])
        else:
            info = dict(ai_tells.detect_lang(text), source="detected")
            if info["lang"] is None and not a.no_linters:
                lt = lt_detect(path)
                if lt and lt["code"] in LT_LANG and (lt["confidence"] or 0) >= 0.5:
                    info = dict(info, lang=lt["code"], source="languagetool", confidence=lt["confidence"])
                elif lt and lt["code"]:
                    info["lt_note"] = "; languagetool guessed %s at %.2f" % (lt["code"], lt["confidence"] or 0.0)
        if info["lang"] is None:
            print("# Humanize report: %s\n\n%s" % (a.file, lang_sentence(info)))
            return 4
        lang = info["lang"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            f_scan = ex.submit(ai_tells.scan, text, lang=lang, url=a.url, no_model=a.no_model, margin=a.margin,
                               spoken=a.spoken, progress=progress, file=a.file)
            f_vocab = ex.submit(simple_english.check, text, lang=lang, top=a.top, allow=a.allow.split(","))
            f_lint = []
            if not a.no_linters:
                f_lint.append(ex.submit(run_vale, path, lang))
                f_lint.append(ex.submit(run_proselint, path) if lang == "en" else ex.submit(run_languagetool, path, lang, text))
            scan = f_scan.result()
            vocab = f_vocab.result()
            lint = [f.result() for f in f_lint]
        scan["lang"] = info
    finally:
        if tmp:
            os.unlink(tmp.name)

    if a.json:
        print(json.dumps(dict(file=a.file, lang=info, scan=scan, vocabulary=vocab, linters=lint), ensure_ascii=False, indent=1))
    else:
        print(render(a, info, scan, vocab, lint))
    return 2 if scan["server_error"] else 0


if __name__ == "__main__":
    sys.exit(main())
