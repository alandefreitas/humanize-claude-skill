#!/usr/bin/env python3
"""
ai_tells.py - scan a text for AI-writing patterns with the local jev server.

Cuts a Markdown or plain-text file into paragraphs and sentences, then asks
the jev server (laya-serve, POST /v1/systemone/batch) every criterion in
criteria.py about every unit of text, and reports every (unit, criterion)
pair. Deterministic checks (em dashes, semicolons, curly quotes, emojis,
hard-wrapped prose, sentence length, rhythm, title-case headings, bold
inline headers, hyphenated pairs, Wh-/So- openers) run locally in the same
pass, so one run covers the whole mechanical side of the humanize skill.
humanize.py (one folder up) imports scan() from here.

Usage:
  ai_tells.py FILE [--lang en|es|pt] [--threshold 0.5] [--model auto|english|multilingual|typed_decisions]
                   [--criteria id,id] [--scope sentence,paragraph] [--all] [--json] [--strict]
                   [--no-model] [--spoken] [--url http://127.0.0.1:8123] [--timeout 300] [--min-words 3]

Exit codes: 0 ok, 1 --strict and flags found, 2 server unreachable or failed, 3 usage.
Stdlib only.
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from criteria import CRITERIA  # noqa: E402

DEFAULT_URL = os.environ.get("JEV_URL") or os.environ.get("LAYA_BASE_URL") or "http://127.0.0.1:8123"
THRESHOLDS_FILE = os.path.join(HERE, "thresholds.json")
NOUL_LABELS = {"true": "yes, the pattern is clearly present", "false": "no, this is plain writing without it"}
QUESTIONS_PER_REQUEST = 8     # the model reads state + all questions in one pass; keep the head budget safe
STATES_PER_REQUEST = 48

# ---------------------------------------------------------------------------
# Language detection: a stopword and orthography vote with a confidence number.
# (The jev model was measured on this task on 2026-10-02 and answered near
# chance for all three languages, so detection stays deterministic.)
# ---------------------------------------------------------------------------
STOP = {
    "en": "the of and to in is that with for on as are was this it be by you from or at not have can will which".split(),
    "es": "el la y en un una es los las con del al lo más pero sus su".split(),
    "pt": "o e em um uma é dos das com do da na no ao mais mas seu sua você não".split(),
}
MARKS = {
    "pt": re.compile(r"[ãõ]|ção|ções|\bnão\b|\bé\b|\bvocê\b"),
    "es": re.compile(r"ñ|¿|¡|\by\b|\bel\b|\blos\b|\blas\b"),
}
URL_RE = re.compile(r"https?://\S+|www\.\S+")


def prose_only(text, limit=6000):
    """Drop markup, code and URLs so language detection sees words."""
    t = text[:limit]
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = URL_RE.sub(" ", t)
    t = re.sub(r"!?\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"`[^`]*`", " ", t)
    return t


def detect_lang(text):
    """Return dict(lang=en|es|pt|None, confidence 0..1, counts per language, words seen).

    lang is None (unknown) when there are fewer than 8 words, fewer than 3 stopword hits, or the best language
    does not beat the runner-up clearly. confidence is the share of the winner's evidence the runner-up does
    not share, scaled down when there are fewer than 8 hits.
    """
    head = prose_only(text).lower()
    words = re.findall(r"[a-záéíóúàâêôçãõñü]+", head)[:800]
    counts = {}
    for lang, stops in STOP.items():
        ss = set(stops)
        counts[lang] = sum(1 for w in words if w in ss)
    for lang, rx in MARKS.items():
        counts[lang] += len(rx.findall(head))
    order = sorted(counts, key=lambda k: counts[k], reverse=True)
    best, second = order[0], order[1]
    if len(words) < 8 or counts[best] < 3:
        return dict(lang=None, confidence=0.0, counts=counts, words=len(words))
    margin = (counts[best] - counts[second]) / counts[best]
    conf = round(margin * min(1.0, counts[best] / 8.0), 2)
    return dict(lang=best if conf >= 0.35 else None, confidence=conf, counts=counts, words=len(words))


# ---------------------------------------------------------------------------
# Markdown segmentation
# ---------------------------------------------------------------------------
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_RE = re.compile(r"^(\s*)([-*+]|\d{1,3}[.)])\s+(.*)$")
TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
HR_RE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
QUOTE_RE = re.compile(r"^\s{0,3}>\s?(.*)$")
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF\U0001F900-\U0001F9FF⭐⭕⌚-⌛⏩-⏺✅❌✨‼⁉️]")


def strip_inline(text):
    """Markdown inline markup -> plain text for the model and the sentence splitter."""
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)              # images
    t = re.sub(r"\[\s*\]\([^)]*\)", "", t)                       # links with no text (badges)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)             # links -> text
    t = URL_RE.sub("", t)                                       # bare URLs
    t = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", t)            # ref links
    t = re.sub(r"<[^>\n]+>", "", t)                             # html tags / autolinks
    t = re.sub(r"(\*\*|__)(.+?)\1", r"\2", t)                   # bold
    t = re.sub(r"(?<!\w)(\*|_)(?=\S)(.+?)(?<=\S)\1(?!\w)", r"\2", t)  # italics
    t = re.sub(r"`([^`]*)`", r"\1", t)                          # code spans -> content
    t = re.sub(r"\\([\\`*_{}\[\]()#+\-.!>])", r"\1", t)        # escapes
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def segment(text):
    """Return a list of blocks: dict(kind, line, raw, text, lines, items)."""
    lines = text.split("\n")
    blocks = []
    i = 0
    n = len(lines)
    # front matter
    if n and lines[0].strip() == "---":
        for j in range(1, n):
            if lines[j].strip() in ("---", "..."):
                blocks.append(dict(kind="frontmatter", line=1, raw="\n".join(lines[: j + 1]), text="", lines=lines[: j + 1]))
                i = j + 1
                break
    # drop html comments (multi-line) by blanking them
    joined = "\n".join(lines[i:])
    joined = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), joined, flags=re.S)
    rest = joined.split("\n")
    base = i
    i = 0
    n = len(rest)
    while i < n:
        line = rest[i]
        if not line.strip():
            i += 1
            continue
        m = FENCE_RE.match(line)
        if m:
            fence = m.group(1)
            j = i + 1
            while j < n and not rest[j].strip().startswith(fence):
                j += 1
            blocks.append(dict(kind="code", line=base + i + 1, raw="\n".join(rest[i: j + 1]), text="", lines=rest[i: j + 1]))
            i = j + 1
            continue
        if HR_RE.match(line):
            i += 1
            continue
        m = HEADING_RE.match(line)
        if m:
            blocks.append(dict(kind="heading", line=base + i + 1, raw=line, text=strip_inline(m.group(2)), level=len(m.group(1)), lines=[line]))
            i += 1
            continue
        if TABLE_RE.match(line):
            j = i
            while j < n and TABLE_RE.match(rest[j]):
                j += 1
            blocks.append(dict(kind="table", line=base + i + 1, raw="\n".join(rest[i:j]), text="", lines=rest[i:j]))
            i = j
            continue
        if LIST_RE.match(line):
            j = i
            items = []
            cur = None
            while j < n and rest[j].strip():
                lm = LIST_RE.match(rest[j])
                if lm:
                    if cur is not None:
                        items.append(cur)
                    cur = dict(line=base + j + 1, raw=rest[j], text=lm.group(3), indent=len(lm.group(1)))
                elif cur is not None:
                    cur["text"] += " " + rest[j].strip()
                    cur["raw"] += "\n" + rest[j]
                j += 1
            if cur is not None:
                items.append(cur)
            for it in items:
                it["text"] = strip_inline(it["text"])
            blocks.append(dict(kind="list", line=base + i + 1, raw="\n".join(rest[i:j]), text="\n".join(it["text"] for it in items), lines=rest[i:j], items=items))
            i = j
            continue
        # paragraph or blockquote: consecutive non-blank, non-special lines
        j = i
        while j < n and rest[j].strip() and not FENCE_RE.match(rest[j]) and not HEADING_RE.match(rest[j]) \
                and not TABLE_RE.match(rest[j]) and not LIST_RE.match(rest[j]) and not HR_RE.match(rest[j]):
            j += 1
        chunk = rest[i:j]
        quote = all(QUOTE_RE.match(l) for l in chunk)
        plain = [QUOTE_RE.match(l).group(1) if quote else l for l in chunk]
        blocks.append(dict(kind="quote" if quote else "paragraph", line=base + i + 1, raw="\n".join(chunk),
                           text=strip_inline(" ".join(l.strip() for l in plain)), lines=chunk))
        i = j
    return blocks


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------
ABBREV = set("""e.g i.e etc vs cf dr mr mrs ms prof sr jr st no nos fig figs approx dept inc ltd co corp
u.s u.k a.m p.m ca al ed eds vol pp p ex min max sra srta dra ud uds pág págs art arts núm
tel ref sec seq op cit ibid""".split())
END_RE = re.compile(r"([.!?…]+)([\"'”’)\]]*)(\s+)(?=[\"'“‘(\[]?[A-ZÀ-ÝÁÉÍÓÚÑÇ0-9¿¡])")


def split_sentences(text):
    text = text.strip()
    if not text:
        return []
    out = []
    start = 0
    for m in END_RE.finditer(text):
        end = m.end(2)
        before = text[start: m.start(1)]
        last = re.findall(r"[\w.]+$", before)
        last_word = last[0].lower().rstrip(".") if last else ""
        punct = m.group(1)
        if "." in punct and "!" not in punct and "?" not in punct:
            if last_word in ABBREV or re.fullmatch(r"[a-z]", last_word) or re.fullmatch(r"[A-Z]", last[0] if last else "") \
                    or re.fullmatch(r"\d+", last_word) and re.match(r"\s+\d", text[m.start(3) - 1:]):
                continue
            if re.fullmatch(r"(?:[a-z]\.)+[a-z]?", last_word):  # e.g, i.e, u.s
                continue
        out.append(text[start:end].strip())
        start = m.end(3)
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return [s for s in out if s]


def word_count(s):
    return len(re.findall(r"[\w'’-]+", s))


def is_prose(s, min_words):
    """At least min_words words and mostly letters: skips badge rows, paths, option lists, ascii art."""
    if word_count(s) < min_words:
        return False
    body = re.sub(r"\s+", "", s)
    letters = sum(1 for ch in body if ch.isalpha())
    return bool(body) and letters / len(body) >= 0.6


# ---------------------------------------------------------------------------
# Units: the things we ask the model about
# ---------------------------------------------------------------------------
def build_units(blocks, min_words):
    paragraphs = []   # dict(idx, line, kind, text, raw, sentences=[...])
    pidx = 0
    for b in blocks:
        if b["kind"] in ("paragraph", "quote", "list"):
            pidx += 1
            para = dict(idx=pidx, line=b["line"], kind=b["kind"], text=b["text"].replace("\n", " ") if b["kind"] != "list" else b["text"], raw=b["raw"], sentences=[], block=b)
            if b["kind"] == "list":
                for it in b["items"]:
                    for s in split_sentences(it["text"]):
                        para["sentences"].append(dict(text=s, line=it["line"], item=True))
            else:
                for s in split_sentences(b["text"]):
                    para["sentences"].append(dict(text=s, line=b["line"], item=False))
            for k, s in enumerate(para["sentences"], 1):
                s["idx"] = k
                s["para"] = pidx
                s["id"] = "P%d.S%d" % (pidx, k)
                s["words"] = word_count(s["text"])
                s["eligible"] = is_prose(s["text"], min_words)
            paragraphs.append(para)
    return paragraphs


# ---------------------------------------------------------------------------
# Deterministic checks
# ---------------------------------------------------------------------------
FILLER_PHRASES = {
    "en": re.compile(r"\b(in order to|due to the fact that|at this point in time|has the ability to|have the ability to|it is important to note that|it is worth noting that|it should be noted that|in terms of|for the purpose of|in the event that|with regard to|a (?:wide|large) (?:variety|range|number) of|the vast majority of|in today's world|in this day and age)\b", re.I),
    "es": re.compile(r"\b(con el fin de|debido al hecho de que|en este momento|tiene la capacidad de|es importante señalar que|cabe mencionar que|cabe destacar que|en términos de|a fin de|en el caso de que|con respecto a|una amplia (?:variedad|gama) de|la gran mayoría de|en el mundo actual|hoy en día)\b", re.I),
    "pt": re.compile(r"\b(a fim de|devido ao fato de que|neste momento|tem a capacidade de|é importante notar que|vale mencionar que|vale destacar que|em termos de|com o objetivo de|no caso de que|com relação a|uma ampla (?:variedade|gama) de|a grande maioria de|no mundo atual|nos dias de hoje)\b", re.I),
}
IRREGULAR_PARTICIPLES = r"""made done given taken seen known written built held kept left lost found told sent spent brought bought
caught taught thought sought fought set put cut hit let shut read said paid laid met led fed sold understood shown grown thrown blown
drawn worn torn born sworn chosen frozen broken spoken stolen woken driven ridden hidden bitten forgotten gotten begun run sung hung
struck stuck won spun dug fallen eaten beaten forgiven risen shaken mistaken overridden undertaken withdrawn rewritten split
reset upset cast broadcast quit bound wound ground meant dealt dreamt felt slept swept wept burnt learnt spelt lent bent""".split()
PASSIVE = {
    "en": re.compile(r"\b(am|is|are|was|were|be|been|being|get|gets|got|getting)\s+(?:(?:not|also|often|still|then|already|never|usually|generally|always|only|just|being)\s+)?(\w+(?:ed|en)|%s)\b(\s+by\s+(?:the\s+|a\s+|an\s+)?\w+)?" % "|".join(IRREGULAR_PARTICIPLES), re.I),
    "es": re.compile(r"\b(fue|fueron|es|son|era|eran|será|serán|ha sido|han sido|había sido|sido)\s+(?:(?:no|también|ya|siempre|nunca)\s+)?(\w+(?:ado|ada|ados|adas|ido|ida|idos|idas)|hech[oa]s?|dich[oa]s?|escrit[oa]s?|vist[oa]s?|puest[oa]s?|abiert[oa]s?|rot[oa]s?|muert[oa]s?|vuelt[oa]s?|cubiert[oa]s?|resuelt[oa]s?|impres[oa]s?|satisfech[oa]s?)\b(\s+por\s+(?:el\s+|la\s+|los\s+|las\s+|un\s+|una\s+)?\w+)?", re.I),
    "pt": re.compile(r"\b(foi|foram|é|são|era|eram|será|serão|tem sido|têm sido|tinha sido|sido|sendo)\s+(?:(?:não|também|já|sempre|nunca)\s+)?(\w+(?:ado|ada|ados|adas|ido|ida|idos|idas)|feit[oa]s?|dit[oa]s?|escrit[oa]s?|vist[oa]s?|post[oa]s?|abert[oa]s?|cobert[oa]s?|mort[oa]s?|pag[oa]s?|gast[oa]s?|ganh[oa]s?|impress[oa]s?|aceit[oa]s?|entregues?|salv[oa]s?)\b(\s+(?:pelo|pela|pelos|pelas|por)\s+\w+)?", re.I),
}
# participial adjectives and states that are not passives in practice
NOT_PASSIVE = set("""interested tired bored excited worried concerned pleased surprised scared confused satisfied disappointed used supposed
located based related limited married born called named known unchanged unknown unrelated unused untested unfinished unsupported
unaffected undefined unspecified unexpected unavailable unlimited closed open dead alive ready done finished""".split())
HYPHEN_PAIRS = re.compile(r"\b(cross-functional|client-facing|data-driven|decision-making|well-known|high-quality|real-time|long-term|short-term|end-to-end|user-friendly|cutting-edge|state-of-the-art|cost-effective|wide-ranging|far-reaching|ever-evolving|fast-paced|game-changing|forward-thinking|results-driven|hands-on|in-depth|much-needed|well-being)\b", re.I)
WH_SO_RE = re.compile(r"^(What|Why|How|So)\b[,\s]", re.I)
BOLD_HEADER_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\*\*[^*]+\*\*\s*[:：]")
BOLD_INLINE_HEADER = re.compile(r"(^|\n)\*\*[^*\n]{2,60}\*\*\s*[:：]")
SMALL_WORDS = set("a an the and or but nor for so yet at by in of on to up as vs via per with from into onto over".split())


def is_title_case(h):
    words = [w for w in re.findall(r"[A-Za-zÀ-ÿ][\w'’-]*", h)]
    if len(words) < 3:
        return False
    caps = [w for w in words[1:] if w[0].isupper() and w.lower() not in SMALL_WORDS and not w.isupper()]
    lowers = [w for w in words[1:] if w[0].islower() and w.lower() not in SMALL_WORDS]
    return len(caps) >= 2 and len(caps) > len(lowers)


def looks_hard_wrapped(block):
    lines = [l for l in block["lines"] if l.strip()]
    if len(lines) < 3:
        return False
    body = lines[:-1]
    lens = [len(l.rstrip()) for l in body]
    med = sorted(lens)[len(lens) // 2]
    if not (45 <= med <= 110):
        return False
    close = sum(1 for L in lens if abs(L - med) <= 15)
    endings = sum(1 for l in body if re.search(r"[.!?:;]\s*$", l) or l.endswith("  ") or l.endswith("\\"))
    return close / len(body) >= 0.6 and endings / len(body) < 0.5


def deterministic_checks(blocks, paragraphs, lang, long_flag=35, long_hard=50):
    finds = []  # dict(rule, check, where, line, detail)

    def add(rule, check, where, line, detail):
        finds.append(dict(rule=rule, check=check, where=where, line=line, detail=detail))

    prev_heading = None
    for b in blocks:
        if b["kind"] == "heading":
            if is_title_case(b["text"]):
                add("C17", "title_case_heading", "heading", b["line"], b["text"])
            if EMOJI_RE.search(b["raw"]):
                add("C18", "emoji", "heading", b["line"], b["text"])
            prev_heading = b
            continue
        if b["kind"] in ("paragraph", "quote", "list"):
            raw = b["raw"]
            if "—" in raw or "–" in raw and re.search(r"\w\s?–\s?\w", raw):
                add("C14", "em_dash", "P?", b["line"], "%d em/en dash(es)" % (raw.count("—") + raw.count("–")))
            semis = len(re.findall(r"\w;[\s)]", raw))
            if semis:
                add("C14b", "semicolon", "P?", b["line"], "%d semicolon(s) in prose" % semis)
            if re.search(r"[“”‘’]", raw):
                add("C19", "curly_quotes", "P?", b["line"], "curly quotes")
            if EMOJI_RE.search(raw):
                add("C18", "emoji", "P?", b["line"], "emoji in prose or bullets")
            bolds = len(re.findall(r"\*\*[^*\n]+\*\*", raw))
            if BOLD_INLINE_HEADER.search(raw) or any(BOLD_HEADER_ITEM.match(l) for l in b["lines"]):
                add("C16", "bold_inline_header", "P?", b["line"], "bold term + colon list")
            elif bolds >= 2:
                add("C15", "mechanical_bold", "P?", b["line"], "%d bold spans" % bolds)
            if b["kind"] == "paragraph" and looks_hard_wrapped(b):
                add("F14", "hard_wrap", "P?", b["line"], "%d lines wrapped at ~%d columns" % (len(b["lines"]), sorted(len(l) for l in b["lines"])[len(b["lines"]) // 2]))
            if lang == "en":
                for m in HYPHEN_PAIRS.finditer(raw):
                    add("E26", "hyphen_pair", "P?", b["line"], m.group(0))
            if prev_heading is not None and b["kind"] == "paragraph":
                sents = split_sentences(b["text"])
                if len(sents) == 1:
                    hw = set(w.lower() for w in re.findall(r"\w+", prev_heading["text"]) if len(w) > 3)
                    pw = set(w.lower() for w in re.findall(r"\w+", b["text"]))
                    if hw and len(hw & pw) / len(hw) >= 0.6:
                        add("E29", "heading_restatement", "P?", b["line"], "one-line paragraph restates the heading")
            prev_heading = None
    # fill paragraph ids by line
    line_to_pid = {p["line"]: "P%d" % p["idx"] for p in paragraphs}
    for f in finds:
        if f["where"] == "P?":
            f["where"] = line_to_pid.get(f["line"], "P?")
    # sentence-level
    for p in paragraphs:
        runs = []
        for s in p["sentences"]:
            if s["words"] >= long_hard:
                add("I", "sentence_too_long", s["id"], s["line"], "%d words (hard limit %d)" % (s["words"], long_hard))
            elif s["words"] >= long_flag:
                add("I", "sentence_long", s["id"], s["line"], "%d words (flag at %d)" % (s["words"], long_flag))
            for m in FILLER_PHRASES[lang].finditer(s["text"]):
                add("E23", "filler_phrase_literal", s["id"], s["line"], m.group(0))
            for m in PASSIVE[lang].finditer(s["text"]):
                part = m.group(2).lower()
                if lang == "en" and (part in NOT_PASSIVE or (part.endswith("en") and part not in IRREGULAR_PARTICIPLES and not part.endswith(("tten", "ken", "zen", "sen", "iven", "oven", "aken")))):
                    continue
                agent = m.group(3)
                if agent:
                    add("B13", "passive_agent_named", s["id"], s["line"], "'%s%s' names the actor: rewrite active (rule 13)" % (m.group(1) + " " + m.group(2), agent))
                else:
                    add("B13", "passive_voice", s["id"], s["line"], "'%s %s': judge with rule 13 (keep if actor unknown or irrelevant)" % (m.group(1), m.group(2)))
            if lang == "en" and WH_SO_RE.match(s["text"]):
                add("F11", "wh_so_opener", s["id"], s["line"], s["text"][:80])
            if lang == "en" and re.search(r"\b(serves|stands) as\b", s["text"], re.I):
                add("B8", "copula_avoidance_literal", s["id"], s["line"], re.search(r"\b(serves|stands) as\b", s["text"], re.I).group(0))
        # rhythm: 3+ consecutive sentences within 20% of each other's length (and 8+ words)
        ws = [s["words"] for s in p["sentences"]]
        k = 0
        while k < len(ws):
            j = k
            while j + 1 < len(ws) and ws[j + 1] >= 8 and ws[k] >= 8 and abs(ws[j + 1] - ws[k]) <= max(2, 0.2 * ws[k]):
                j += 1
            if j - k + 1 >= 3:
                add("F13", "rhythm_equal_length", "P%d.S%d-S%d" % (p["idx"], k + 1, j + 1), p["sentences"][k]["line"], "sentences of %s words" % ", ".join(str(w) for w in ws[k: j + 1]))
            k = j + 1
    return finds


# ---------------------------------------------------------------------------
# jev client
# ---------------------------------------------------------------------------
class JevError(Exception):
    pass


def post(url, path, body, timeout):
    req = urllib.request.Request(url.rstrip("/") + path, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        if e.code == 503:
            time.sleep(2)
            return post(url, path, body, timeout)
        raise JevError("HTTP %d from %s: %s" % (e.code, path, detail[:400]))
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        raise JevError("cannot reach jev server at %s (%s)" % (url, e))


def warm_up(url, timeout):
    t0 = time.time()
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/health", timeout=timeout) as r:
            h = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise JevError("cannot reach jev server at %s (%s). Start laya-serve or set JEV_URL; --no-model runs the deterministic checks only" % (url, e))
    return h, time.time() - t0


def question_payload(crit, lang, labels=True):
    q = crit["q"].get(lang) or crit["q"]["en"]
    if crit["type"] == "score":
        return {"type": "score", "instructions": q, "criteria": list(crit["levels"])}
    if labels:
        return {"type": "noul", "instructions": q, "criteria": dict(NOUL_LABELS)}
    return {"type": "noul", "instructions": q}


def load_thresholds():
    """thresholds.json written by calibrate.py: {model: {criteria: {id: {threshold, reliable, auc}}}}."""
    if not os.path.exists(THRESHOLDS_FILE):
        return {}
    with open(THRESHOLDS_FILE) as f:
        return json.load(f)


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i: i + n]


def run_model(url, timeout, lang, model, states, crits, progress, labels=True):
    """states: list of dicts; crits: criteria sharing one state shape. Returns {state_i: {crit_id: answer}}, {state_i: routed model}, stats."""
    results = {i: {} for i in range(len(states))}
    routed = {}
    stats = dict(requests=0, input_tokens=0, truncated=0, retried=0)
    qsize = QUESTIONS_PER_REQUEST
    todo = [(list(cgroup), list(range(len(states)))) for cgroup in chunks(crits, qsize)]
    while todo:
        cgroup, sidx = todo.pop(0)
        questions = {c["id"]: question_payload(c, lang, labels) for c in cgroup}
        for sgroup in chunks(sidx, STATES_PER_REQUEST):
            body = {"states": [states[i] for i in sgroup], "questions": questions}
            if lang != "en":
                body["lang"] = lang
            if model and model != "auto":
                body["model"] = model
            progress("  %d states x %d questions" % (len(sgroup), len(questions)))
            resp = post(url, "/v1/systemone/batch", body, timeout)
            stats["requests"] += 1
            stats["input_tokens"] += (resp.get("total_usage") or {}).get("input_tokens", 0)
            for i, res in zip(sgroup, resp["results"]):
                routed[i] = (res.get("routing") or {}).get("model") or res.get("model")
                usage = res.get("usage") or {}
                if usage.get("truncated") and len(cgroup) > 1:
                    # split this question group for this state and redo
                    stats["retried"] += 1
                    half = len(cgroup) // 2
                    todo.append((cgroup[:half], [i]))
                    todo.append((cgroup[half:], [i]))
                    continue
                if usage.get("truncated"):
                    stats["truncated"] += 1
                for cid, ans in res["answers"].items():
                    results[i][cid] = ans
    return results, routed, stats


def answer_value(crit, ans):
    """Normalise an answer to a 0..1 'how much does this tell apply' value plus confidence."""
    if ans is None:
        return None, None
    if crit["type"] == "score":
        n = len(crit["levels"]) - 1
        return round(float(ans.get("score", 0)) / n, 4) if n else 0.0, ans.get("answer_confidence", ans.get("confidence"))
    return round(float(ans.get("noul", 0)), 4), ans.get("answer_confidence", ans.get("confidence"))


# ---------------------------------------------------------------------------
# Scan (library entry point, used by humanize.py) and report
# ---------------------------------------------------------------------------
def excerpt(s, n=110):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def md_escape(s):
    return s.replace("|", "\\|")


def sort_key(uid):
    m = re.match(r"P(\d+)(?:\.S(\d+))?", uid)
    return (int(m.group(1)), int(m.group(2) or 0))


def criterion_question(crit, lang):
    return crit["q"].get(lang) or crit["q"]["en"]


def scan(text, lang=None, url=DEFAULT_URL, timeout=300, model="auto", threshold=None, margin=0.0, labels=True,
         no_model=False, criteria=None, scopes=("sentence", "paragraph"), min_words=3, spoken=False, progress=None,
         file="<text>"):
    """Run the deterministic checks and the model checks on `text`.

    lang is en, es, pt, or None to detect (an unknown language runs the checks as English and says so in
    result["lang"]). Returns a dict: lang (lang, source, confidence, counts, words), summary, deterministic,
    flags, advisory, per_criterion, ranked, unreliable (criteria the editor must apply by reading, with their
    question text), matrix, units, sentences, paragraphs, server_error. Every flag and ranked row carries its
    unit text and line, so callers need no lookups.
    """
    progress = progress or (lambda msg: None)
    detected = detect_lang(text)
    if lang:
        lang_info = dict(lang=lang, source="explicit", confidence=1.0, counts=detected["counts"], words=detected["words"])
    else:
        lang_info = dict(detected, source="detected")
    lang_eff = lang_info["lang"] or "en"
    blocks = segment(text)
    paragraphs = build_units(blocks, min_words)
    sentences = [s for p in paragraphs for s in p["sentences"]]
    long_flag, long_hard = (20, 30) if spoken else (35, 50)
    det = deterministic_checks(blocks, paragraphs, lang_eff, long_flag, long_hard)

    scopes = set(scopes)
    wanted = set(criteria) if criteria else None
    crits = [c for c in CRITERIA if c["scope"] in scopes and (wanted is None or c["id"] in wanted)]
    if wanted:
        unknown = wanted - {c["id"] for c in CRITERIA}
        if unknown:
            raise ValueError("unknown criteria: %s" % ", ".join(sorted(unknown)))

    matrix = {}      # unit id -> {crit id: (value, confidence)}
    unit_model = {}  # unit id -> checkpoint that answered
    stats = dict(requests=0, input_tokens=0, truncated=0, retried=0)
    thresholds = load_thresholds()
    health = None
    warm = 0.0
    t0 = time.time()
    server_error = None
    if not no_model and crits:
        try:
            health, warm = warm_up(url, timeout)
            progress("jev server ok (%.1fs, loaded: %s)" % (warm, ",".join(health.get("loaded", []))))
            groups = {}
            for c in crits:
                groups.setdefault((c["scope"], bool(c.get("context"))), []).append(c)
            para_by_idx = {p["idx"]: p for p in paragraphs}
            for (scope, ctx), cgroup in groups.items():
                if scope == "sentence":
                    units = [s for s in sentences if s["eligible"]]
                    states = [({"sentence": s["text"], "paragraph": excerpt(para_by_idx[s["para"]]["text"], 700)} if ctx else {"sentence": s["text"]}) for s in units]
                    ids = [s["id"] for s in units]
                else:
                    units = [p for p in paragraphs if is_prose(p["text"], min_words)]
                    states = [{"paragraph": p["text"]} for p in units]
                    ids = ["P%d" % p["idx"] for p in units]
                if not states:
                    continue
                progress("%s scope%s: %d units x %d criteria" % (scope, " (with context)" if ctx else "", len(states), len(cgroup)))
                res, routed, st = run_model(url, timeout, lang_eff, model, states, cgroup, progress, labels=labels)
                for k in stats:
                    stats[k] += st[k]
                cmap = {c["id"]: c for c in cgroup}
                for i, uid in enumerate(ids):
                    unit_model[uid] = routed.get(i)
                    for cid, ans in res[i].items():
                        matrix.setdefault(uid, {})[cid] = answer_value(cmap[cid], ans)
        except JevError as e:
            server_error = str(e)
            progress("ERROR: " + server_error)
    elapsed = time.time() - t0

    crit_by_id = {c["id"]: c for c in CRITERIA}
    models_used = sorted(set(m for m in unit_model.values() if m))
    cal_model = None
    for m in models_used or ["english"]:
        if m + "/" + lang_eff in thresholds:
            cal_model = m + "/" + lang_eff
        elif m in thresholds:
            cal_model = m
    if cal_model is None:
        cal_model = "english/en" if "english/en" in thresholds else ("english" if "english" in thresholds else None)
    cal = (thresholds.get(cal_model) or {}).get("criteria", {}) if cal_model else {}

    def thr(cid):
        if threshold is not None:
            base = threshold
        elif "threshold" in crit_by_id[cid]:
            base = crit_by_id[cid]["threshold"]
        elif cid in cal:
            base = cal[cid]["threshold"]
        else:
            base = 0.5
        return round(base + margin, 2)

    def reliable(cid):
        if cid in cal:
            return bool(cal[cid]["reliable"])
        if cal:
            return False  # calibrated set exists but this criterion was never measured
        return not cid.startswith("ai_overall")

    sent_by_id = {s["id"]: s for s in sentences}
    para_by_id = {"P%d" % p["idx"]: p for p in paragraphs}

    def unit_text(uid):
        return sent_by_id[uid]["text"] if uid in sent_by_id else para_by_id[uid]["text"]

    def unit_line(uid):
        return sent_by_id[uid]["line"] if uid in sent_by_id else para_by_id[uid]["line"]

    flags, advisory = [], []
    for uid, row in matrix.items():
        for cid, (val, conf) in row.items():
            if val is not None and val >= thr(cid):
                item = dict(where=uid, line=unit_line(uid), crit=cid, rule=crit_by_id[cid]["rule"], p=val, confidence=conf,
                            threshold=thr(cid), text=unit_text(uid))
                (flags if reliable(cid) else advisory).append(item)
    flags.sort(key=lambda f: (sort_key(f["where"]), -f["p"]))
    advisory.sort(key=lambda f: (sort_key(f["where"]), -f["p"]))

    per_criterion = []
    for c in crits:
        vals = [row[c["id"]][0] for row in matrix.values() if c["id"] in row and row[c["id"]][0] is not None]
        if vals:
            per_criterion.append(dict(rule=c["rule"], crit=c["id"], scope=c["scope"], units=len(vals),
                                      flags=sum(1 for v in vals if v >= thr(c["id"])), max_p=max(vals), mean_p=sum(vals) / len(vals)))
    ranked = []
    for uid, row in matrix.items():
        fl = [(cid, v) for cid, (v, _) in row.items() if v is not None and reliable(cid) and v >= thr(cid)]
        ranked.append(dict(where=uid, line=unit_line(uid), flags=len(fl), excess=sum(v - thr(cid) for cid, v in fl),
                           criteria=[cid for cid, _ in sorted(fl, key=lambda x: -x[1])], text=unit_text(uid)))
    ranked.sort(key=lambda r: (-r["flags"], -r["excess"]))
    unreliable = [dict(id=c["id"], rule=c["rule"], scope=c["scope"], q=criterion_question(c, lang_eff)) for c in crits if not reliable(c["id"])]
    checked = sum(1 for s in sentences if s["eligible"])
    flagged_units = set(f["where"] for f in flags)
    clean = [s["id"] for s in sentences if s["eligible"] and s["id"] not in flagged_units]
    summary = dict(file=file, lang=lang_eff, lang_source=lang_info["source"], lang_confidence=lang_info["confidence"], model=model,
                   models_used=models_used, thresholds_from=cal_model, url=url, paragraphs=len(paragraphs), sentences=len(sentences),
                   sentences_checked=checked, criteria=len(crits), deterministic_findings=len(det), flags=len(flags),
                   requests=stats["requests"], input_tokens=stats["input_tokens"], truncated=stats["truncated"], seconds=round(elapsed, 1),
                   warm_up_seconds=round(warm, 1), server_loaded=(health or {}).get("loaded"), server_error=server_error,
                   threshold=threshold, margin=margin, advisory=len(advisory), clean_sentences=len(clean),
                   unreliable_criteria=[u["id"] for u in unreliable], spoken=spoken, long_flag=long_flag, long_hard=long_hard)
    return dict(file=file, lang=lang_info, summary=summary, deterministic=det, flags=flags, advisory=advisory, per_criterion=per_criterion,
                ranked=ranked, unreliable=unreliable, server_error=server_error,
                matrix={uid: {cid: dict(p=v, confidence=c, flag=(v is not None and v >= thr(cid)), reliable=reliable(cid))
                              for cid, (v, c) in row.items()} for uid, row in matrix.items()},
                units={uid: dict(text=unit_text(uid), line=unit_line(uid)) for uid in matrix},
                sentences=[dict(id=s["id"], line=s["line"], words=s["words"], text=s["text"]) for s in sentences],
                paragraphs=[dict(id="P%d" % p["idx"], line=p["line"], kind=p["kind"], text=p["text"]) for p in paragraphs])


def lang_line(info):
    """One sentence about the language decision, for report headers."""
    c = info.get("counts") or {}
    ev = ", ".join("%s %d" % (k, c[k]) for k in ("en", "es", "pt") if k in c)
    if info["source"] == "explicit":
        return "Language %s (given)." % info["lang"]
    if info["lang"] is None:
        return "Language unknown (confidence %.2f, stopword evidence: %s, %d words); checks ran as English. Pass --lang en|es|pt." % (
            info["confidence"], ev, info.get("words", 0))
    return "Language %s (detected, confidence %.2f, stopword evidence: %s)." % (info["lang"], info["confidence"], ev)


def deterministic_table(det):
    if not det:
        return ["none"]
    out = ["| Where | Line | Rule | Check | Detail |", "|---|---|---|---|---|"]
    for f in sorted(det, key=lambda f: (f["line"], f["rule"])):
        out.append("| %s | L%d | %s | %s | %s |" % (f["where"], f["line"], f["rule"], f["check"], md_escape(excerpt(f["detail"], 90))))
    return out


def flags_table(flags):
    out = ["| Where | Line | P | Rule | Criterion | Text |", "|---|---|---|---|---|---|"]
    for f in flags:
        out.append("| %s | L%d | %.2f | %s | %s | %s |" % (f["where"], f["line"], f["p"], f["rule"], f["crit"], md_escape(excerpt(f["text"]))))
    return out


def ranked_table(ranked, limit=15):
    out = ["| Where | Line | Flags | Criteria | Text |", "|---|---|---|---|---|"]
    for row in (ranked if limit is None else ranked[:limit]):
        if row["flags"] == 0 and limit is not None:
            break
        out.append("| %s | L%d | %d | %s | %s |" % (row["where"], row["line"], row["flags"], ", ".join(row["criteria"]), md_escape(excerpt(row["text"], 90))))
    return out


def render_markdown(r, show_all=False, show_advisory=False):
    s = r["summary"]
    out = ["# AI tells scan: %s" % r["file"], ""]
    out.append(lang_line(r["lang"]) + " Checkpoint %s via %s. %d paragraphs, %d sentences (%d sent to the model), %d model criteria, %d requests, %d input tokens, %.1fs.%s" % (
        ",".join(s["models_used"]) or s["model"], s["url"], s["paragraphs"], s["sentences"], s["sentences_checked"], s["criteria"],
        s["requests"], s["input_tokens"], s["seconds"], " Spoken mode: sentences flagged at %d words." % s["long_flag"] if s["spoken"] else ""))
    has_matrix = bool(r["matrix"])
    if has_matrix:
        if s["threshold"] is not None:
            out.append("Flag threshold %.2f for every criterion%s." % (s["threshold"], " plus margin %.2f" % s["margin"] if s["margin"] else ""))
        elif s["thresholds_from"]:
            out.append("Per-criterion thresholds from thresholds.json (calibrated on %s%s)%s. Unreliable criteria (%s) never count as flags; use --advisory to see their hits." % (
                s["thresholds_from"], "" if s["thresholds_from"].split("/")[0] in s["models_used"] else ", not the checkpoint that answered",
                " plus margin %.2f" % s["margin"] if s["margin"] else "", ", ".join(s["unreliable_criteria"]) or "none"))
        else:
            out.append("No thresholds.json found, flagging at P >= 0.50. Run calibrate.py --write.")
        out.append("P is the model's probability that the pattern is present (or the normalised level for score questions).")
    if r["server_error"]:
        out += ["", "**Model checks did not run:** %s" % r["server_error"]]
    if s["truncated"]:
        out.append("**%d answers came from truncated inputs** (very long sentence or paragraph); treat them with care." % s["truncated"])
    out += ["", "## Deterministic findings (%d)" % len(r["deterministic"]), ""]
    out += deterministic_table(r["deterministic"])
    if has_matrix:
        out += ["", "## Model flags (%d)" % len(r["flags"]), ""]
        out += flags_table(r["flags"]) if r["flags"] else ["none at or above threshold"]
        out += ["", "## Per-criterion summary", "", "| Rule | Criterion | Scope | Units | Flags | Max P | Mean P |", "|---|---|---|---|---|---|---|"]
        for c in r["per_criterion"]:
            out.append("| %s | %s | %s | %d | %d | %.2f | %.2f |" % (c["rule"], c["crit"], c["scope"], c["units"], c["flags"], c["max_p"], c["mean_p"]))
        if show_advisory and r["advisory"]:
            out += ["", "## Advisory hits from unreliable criteria (%d, judge yourself)" % len(r["advisory"]), ""]
            out += flags_table(r["advisory"])
        out += ["", "## Units ranked by flags", ""]
        out += ranked_table(r["ranked"], None if show_all else 15)
        if show_all:
            out += ["", "## Full matrix", ""]
            for uid in sorted(r["matrix"], key=sort_key):
                row = r["matrix"][uid]
                items = sorted(((cid, a) for cid, a in row.items() if a["p"] is not None), key=lambda x: -x[1]["p"])
                out.append("- **%s** (L%d) %s" % (uid, r["units"][uid]["line"], md_escape(excerpt(r["units"][uid]["text"], 90))))
                out.append("  " + ", ".join("%s %.2f%s" % (cid, a["p"], ("*" if a["reliable"] else "?") if a["flag"] else "") for cid, a in items))
        out += ["", "Clean sentences (no model flag): %d of %d checked." % (s["clean_sentences"], s["sentences_checked"])]
    out += ["", "Summary: %d deterministic findings, %d model flags%s over %d sentences and %d paragraphs (lang %s, checkpoint %s, %.1fs)." % (
        len(r["deterministic"]), len(r["flags"]), " (+%d advisory)" % len(r["advisory"]) if r["advisory"] else "", s["sentences"], s["paragraphs"],
        s["lang"], ",".join(s["models_used"]) or s["model"], s["seconds"])]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("file")
    ap.add_argument("--lang", choices=["en", "es", "pt"], help="language of the text (default: auto-detect)")
    ap.add_argument("--threshold", type=float, help="one flag threshold for every criterion (default: per-criterion thresholds from thresholds.json, else 0.5)")
    ap.add_argument("--margin", type=float, default=0.0, help="added to every threshold (positive = fewer flags)")
    ap.add_argument("--no-labels", action="store_true", help="ask noul questions without explicit yes/no option labels (thresholds were calibrated WITH labels)")
    ap.add_argument("--advisory", action="store_true", help="also list hits of unreliable criteria (AUC < 0.75 in calibration); never counted as flags")
    ap.add_argument("--spoken", action="store_true", help="talk script: flag sentences at 20 words (hard limit 30) instead of 35/50")
    ap.add_argument("--model", default="auto", help="auto | english | multilingual | typed_decisions")
    ap.add_argument("--criteria", help="comma list of criterion ids to run (default: all)")
    ap.add_argument("--scope", default="sentence,paragraph", help="comma list: sentence, paragraph")
    ap.add_argument("--all", action="store_true", help="print the full unit x criterion matrix, not only flags")
    ap.add_argument("--json", action="store_true", help="JSON output instead of Markdown")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any flag is found")
    ap.add_argument("--no-model", action="store_true", help="deterministic checks only, do not call the server")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--timeout", type=float, default=300, help="seconds per request (first request waits for the model to load)")
    ap.add_argument("--min-words", type=int, default=3, help="sentences shorter than this are not sent to the model")
    ap.add_argument("--quiet", action="store_true", help="no progress on stderr")
    a = ap.parse_args()

    def progress(msg):
        if not a.quiet:
            print(msg, file=sys.stderr, flush=True)

    try:
        with open(a.file, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print("cannot read %s: %s" % (a.file, e), file=sys.stderr)
        return 3
    try:
        r = scan(text, lang=a.lang, url=a.url, timeout=a.timeout, model=a.model, threshold=a.threshold, margin=a.margin,
                 labels=not a.no_labels, no_model=a.no_model, criteria=[x.strip() for x in a.criteria.split(",")] if a.criteria else None,
                 scopes=[x.strip() for x in a.scope.split(",")], min_words=a.min_words, spoken=a.spoken, progress=progress, file=a.file)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 3
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(render_markdown(r, a.all, a.advisory))
    if r["server_error"]:
        return 2
    if a.strict and (r["flags"] or r["deterministic"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
