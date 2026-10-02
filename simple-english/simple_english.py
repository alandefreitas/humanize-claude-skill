#!/usr/bin/env python3
"""
simple_english.py - deterministic core-vocabulary check for the humanize skill.

Reads a text or Markdown file and reports every word that is NOT in a core
English vocabulary list (default: the New General Service List, 2,818
headwords, ~92% coverage of everyday English). Inflections (-s, -ed, -ing,
-er, -est, -ly, -ness, un-) and irregular forms are accepted automatically,
so "running" and "went" match "run" and "go".

Also reports readability numbers (Flesch-Kincaid grade, sentence lengths)
so the same run covers rule I of the humanize ruleset. humanize.py (one folder
up) imports check() from here.

Usage:
  simple_english.py FILE [--list ngsl|ogden] [--top N] [--allow w1,w2]
                         [--allow-file PATH] [--json] [--strict] [--lang en]

Inline directive inside a document (HTML comment, any number of them):
  <!-- simple-english-allow: mdspan constexpr Boost -->

Exit codes: 0 ok, 1 --strict and off-list words found, 2 usage / no list.
"""
import argparse
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORDLISTS = os.path.join(HERE, "wordlists")
GLOBAL_ALLOW = os.path.join(HERE, "allowlist.txt")

# --------------------------------------------------------------------------
# Irregular forms -> lemma. Deliberately generous: anything here counts as
# "in list" if its lemma is in the list.
# --------------------------------------------------------------------------
IRREGULAR_VERBS = """
be am is are was were been being
have has had having
do does did done doing
go goes went gone going
say says said
make makes made
get gets got gotten
see sees saw seen
know knows knew known
take takes took taken
come comes came
think thinks thought
give gives gave given
find finds found
tell tells told
become becomes became
leave leaves left
feel feels felt
bring brings brought
begin begins began begun
keep keeps kept
hold holds held
write writes wrote written
stand stands stood
hear hears heard
let lets
mean means meant
set sets
meet meets met
run runs ran running
pay pays paid
sit sits sat
speak speaks spoke spoken
lie lies lay lain lying
lead leads led
read reads
grow grows grew grown
lose loses lost
fall falls fell fallen
send sends sent
build builds built
understand understands understood
draw draws drew drawn
break breaks broke broken
spend spends spent
cut cuts
rise rises rose risen
drive drives drove driven
buy buys bought
wear wears wore worn
choose chooses chose chosen
seek seeks sought
throw throws threw thrown
catch catches caught
deal deals dealt
win wins won
forget forgets forgot forgotten
lay lays laid
sell sells sold
fight fights fought
teach teaches taught
eat eats ate eaten
fly flies flew flown
shoot shoots shot
hit hits
sing sings sang sung
hide hides hid hidden
strike strikes struck stricken
hang hangs hung
shake shakes shook shaken
ride rides rode ridden
feed feeds fed
sleep sleeps slept
steal steals stole stolen
swim swims swam swum
bend bends bent
bind binds bound
bite bites bit bitten
bleed bleeds bled
blow blows blew blown
burn burns burnt
burst bursts
cost costs
creep creeps crept
dig digs dug
dream dreams dreamt
drink drinks drank drunk
freeze freezes froze frozen
hurt hurts
kneel kneels knelt
lend lends lent
light lights lit
quit quits
ring rings rang rung
seek seeks sought
shine shines shone
shut shuts
sink sinks sank sunk
slide slides slid
spin spins spun
split splits
spread spreads
spring springs sprang sprung
stick sticks stuck
sting stings stung
sweep sweeps swept
swing swings swung
tear tears tore torn
wake wakes woke woken
weep weeps wept
wind winds wound
withdraw withdraws withdrew withdrawn
arise arises arose arisen
awake awakes awoke awoken
forbid forbids forbade forbidden
forgive forgives forgave forgiven
mistake mistakes mistook mistaken
overcome overcomes overcame
undertake undertakes undertook undertaken
prove proves proved proven
show shows showed shown
can could
will would
shall should
may might
must
ought
"""

IRREGULAR_NOUNS = """
child children
man men
woman women
person people persons
foot feet
tooth teeth
mouse mice
goose geese
life lives
wife wives
knife knives
leaf leaves
half halves
self selves
shelf shelves
wolf wolves
thief thieves
loaf loaves
calf calves
sheep
fish fishes
series
species
means
news
analysis analyses
basis bases
crisis crises
criterion criteria
phenomenon phenomena
medium media
datum data
index indices indexes
appendix appendices
matrix matrices
formula formulae formulas
"""

IRREGULAR_ADJ = """
good better best
bad worse worst
far farther further farthest furthest
little less least
much more most
many more most
well better best
old elder eldest older oldest
late later latest last
"""

IRREGULAR_PRON = """
i me my mine myself
we us our ours ourselves
you your yours yourself yourselves
he him his himself
she her hers herself
it its itself
they them their theirs themselves
who whom whose
one ones oneself
"""

# Frequent words that are not NGSL headwords but are part of any "simple
# English" (numbers, days, months, contraction tails). Always allowed.
SUPPLEMENT = """
zero one two three four five six seven eight nine ten eleven twelve thirteen
fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty
sixty seventy eighty ninety hundred thousand million billion
first second third fourth fifth sixth seventh eighth ninth tenth
monday tuesday wednesday thursday friday saturday sunday
january february march april may june july august september october november december
n't 's 'll 're 've 'd 'm
ok okay hi hello bye yes no an whoever mr mrs ms dr o'clock
email website app download upload password login click laptop smartphone wifi internet browser screenshot podcast blog spreadsheet selfie emoji tablet keyboard delete google
am pm a.m. p.m. e.g. i.e. etc vs
"""


def _irregular_map():
    m = {}
    for block in (IRREGULAR_VERBS, IRREGULAR_NOUNS, IRREGULAR_ADJ, IRREGULAR_PRON):
        for line in block.strip().splitlines():
            parts = line.split()
            if not parts:
                continue
            lemma = parts[0]
            for f in parts:
                m.setdefault(f, set()).add(lemma)
    return m


IRREGULAR = _irregular_map()

VOWELS = set("aeiou")


def inflections(head):
    """Generate the inflected/derived forms accepted for a headword."""
    forms = {head}
    if not head.isalpha():
        return forms
    h = head
    ends = h.endswith
    # plural / 3rd person / past / participle / comparative / superlative
    if ends("y") and len(h) > 1 and h[-2] not in VOWELS:
        stem = h[:-1]
        forms.update({stem + "ies", stem + "ied", stem + "ier", stem + "iest", stem + "ily", stem + "iness"})
    if ends(("s", "x", "z", "ch", "sh")):
        forms.add(h + "es")
    forms.add(h + "s")
    if ends("e"):
        forms.update({h + "d", h[:-1] + "ing", h + "r", h + "st"})
        if ends("le"):
            forms.add(h[:-1] + "y")  # simple -> simply
        if ends("ie"):
            forms.add(h[:-2] + "ying")  # die -> dying
    else:
        forms.update({h + "ed", h + "ing", h + "er", h + "est"})
    # consonant doubling: stop -> stopped, big -> bigger
    if len(h) >= 3 and h[-1] not in VOWELS and h[-1] not in "wxy" and h[-2] in VOWELS and h[-3] not in VOWELS:
        c = h[-1]
        forms.update({h + c + "ed", h + c + "ing", h + c + "er", h + c + "est"})
    # adverbs and nouns
    if ends("ic"):
        forms.add(h + "ally")
    elif ends("ll"):
        forms.add(h + "y")  # full -> fully
    elif not ends("y"):
        forms.add(h + "ly")
    forms.add(h + "ness")
    # negation prefix (transparent)
    forms.update({"un" + f for f in list(forms)})
    return forms


def load_words(path):
    words = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            w = line.strip().lower()
            if w and not w.startswith("#"):
                words.append(w)
    return words


def build_lexicon(list_name, top, extra_words):
    path = os.path.join(WORDLISTS, f"{list_name}.txt")
    if not os.path.exists(path):
        sys.exit(f"simple_english: no word list at {path}")
    heads = load_words(path)
    if top:
        heads = heads[:top]
    n_heads = len(heads)
    if LANG != "en":
        lex = {h: h for h in heads}
        for w in SUPPLEMENT_LANG.get(LANG, "").split() + list(extra_words):
            lex.setdefault(w, w)
        return lex, n_heads
    heads = list(dict.fromkeys(heads + SUPPLEMENT.split() + list(extra_words)))
    headset = set(heads)
    lex = {}
    for h in heads:
        for f in inflections(h):
            lex.setdefault(f, h)
    # irregular forms whose lemma is in the list
    for form, lemmas in IRREGULAR.items():
        for lem in lemmas:
            if lem in headset:
                lex.setdefault(form, lem)
    return lex, n_heads


def load_bands():
    path = os.path.join(WORDLISTS, "bnc_coca_bands.csv")
    bands = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            next(fh, None)
            for line in fh:
                w, _, b = line.strip().rpartition(",")
                if w and b.isdigit():
                    bands.setdefault(w, int(b))
    return bands


def band_of(word, bands):
    """Approximate BNC/COCA 1k-band of a word (tries a few stripped forms)."""
    cands = [word]
    for suf, rep in (("ies", "y"), ("ied", "y"), ("ier", "y"), ("iest", "y"), ("ily", "y"),
                     ("es", ""), ("s", ""), ("ed", ""), ("ed", "e"), ("d", ""), ("ing", ""),
                     ("ing", "e"), ("ly", ""), ("ally", ""), ("er", ""), ("er", "e"), ("est", ""),
                     ("est", "e"), ("ness", ""), ("ment", ""), ("tion", "te"), ("tion", ""), ("ity", ""),
                     ("able", ""), ("able", "e"), ("ive", "e"), ("al", ""), ("ous", "")):
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            cands.append(word[: -len(suf)] + rep)
            if len(word) - len(suf) >= 4 and word[-len(suf) - 1] == word[-len(suf) - 2]:
                cands.append(word[: -len(suf) - 1] + rep)  # stopped -> stop
    if word.startswith("un") and len(word) > 5:
        cands.append(word[2:])
    for lemmas in (IRREGULAR.get(word),):
        if lemmas:
            cands.extend(sorted(lemmas))
    # second stripping pass so "settings" -> "setting" -> "set"
    for c in list(cands[1:]):
        for suf, rep in (("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"), ("er", ""), ("ly", ""), ("s", "")):
            if c.endswith(suf) and len(c) - len(suf) >= 3:
                stem = c[: -len(suf)]
                cands.append(stem + rep)
                if len(stem) >= 3 and stem[-1] == stem[-2]:
                    cands.append(stem[:-1] + rep)
    found = [bands[c] for c in cands if c in bands]
    return min(found) if found else None


# --------------------------------------------------------------------------
# Text preparation
# --------------------------------------------------------------------------
FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
URL_RE = re.compile(r"https?://\S+|www\.\S+|\S+@\S+\.\S+")
HTML_TAG_RE = re.compile(r"<[^>\n]+>")
MD_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
MD_REF_RE = re.compile(r"^\s*\[[^\]]+\]:\s*\S+.*$", re.M)
FRONT_MATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.S)
DIRECTIVE_RE = re.compile(r"<!--\s*simple-english-allow:\s*(.*?)-->", re.S | re.I)
MD_SYNTAX_RE = re.compile(r"^[ \t]*(?:[#>*+-]+|\d+[.)])\s*|\*\*|__|(?<!\w)[*_](?!\w)|(?<!\w)[*_]|[*_](?!\w)|\|", re.M)
APOS = "’ʼ′"
WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?(?:-[^\W\d_]+(?:['’][^\W\d_]+)?)*")
LANG = "en"          # set by configure(); analyse() reads it
LEMMATIZE = None     # simplemma-backed callable for es/pt, None for en
RANKED = {}          # lemma -> rank (es/pt), used for band labels
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])[\"'”’)\]]*\s+(?=[\"'“‘(\[]*[A-Z0-9])|\n+")

ABBREV_RE = re.compile(r"(?<![A-Za-z])(?:e\.g\.|i\.e\.|etc\.|vs\.|a\.m\.|p\.m\.|cf\.|approx\.|no\.)(?![A-Za-z])", re.I)
CODEY_TOKEN_RE = re.compile(r"(?<!\S)\S*[0-9_]\S*")

CONTRACTION_TAILS = {"s", "ll", "re", "ve", "d", "m", "t"}


def prepare(text):
    directives = []
    for m in DIRECTIVE_RE.finditer(text):
        directives.extend(m.group(1).split())
    text = FRONT_MATTER_RE.sub("", text)
    text = FENCE_RE.sub(" ", text)
    text = INLINE_CODE_RE.sub(" ", text)
    text = DIRECTIVE_RE.sub(" ", text)
    text = HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = MD_LINK_RE.sub(r"\1", text)
    text = MD_REF_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = ABBREV_RE.sub(" ", text)
    text = CODEY_TOKEN_RE.sub(" ", text)
    text = MD_SYNTAX_RE.sub(" ", text)
    return text, [d.lower() for d in directives]


def split_sentences(text):
    parts = SENT_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p and p.strip()]


def syllables(word):
    w = word.lower()
    if LANG != "en":
        groups = re.findall(r"[aeiouyáéíóúàâêôãõüÿ]+", w)
        return max(1, len(groups))
    w = re.sub(r"[^a-z]", "", w)
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    groups = re.findall(r"[aeiouy]+", w)
    return max(1, len(groups))


def split_contraction(tok):
    tok = tok.replace("’", "'")
    if LANG != "en":
        return [tok]
    if "'" in tok:
        base, _, tail = tok.rpartition("'")
        if tail.lower() in CONTRACTION_TAILS:
            if tail.lower() == "t" and base.lower().endswith("n"):
                return [base[:-1], "n't"] if base.lower() not in ("can", "won", "shan", "ain") else [
                    {"can": "can", "won": "will", "shan": "shall", "ain": "be"}[base.lower()], "n't"]
            return [base, "'" + tail.lower()]
    return [tok]


# Modern everyday words missing from the subtitle-derived es/pt lists.
SUPPLEMENT_LANG = {
    "es": "app apps email emails wifi internet web link links chat whatsapp online celular smartphone laptop "
          "contraseña usuario archivo carpeta pantalla botón menú descargar subir clic pdf",
    "pt": "app apps email emails wifi internet web link links chat whatsapp online celular smartphone laptop notebook "
          "senha usuário arquivo pasta tela botão menu baixar enviar clique pdf",
}


def lemma_candidates(low):
    """Lemma guesses for es/pt: simplemma's lemma plus participle -> infinitive."""
    cands = []
    if LEMMATIZE is not None:
        cands.append(LEMMATIZE(low))
    for suf in ("adas", "ados", "ada", "ado"):
        if low.endswith(suf):
            cands.append(low[: -len(suf)] + "ar")
            break
    for suf in ("idas", "idos", "ida", "ido"):
        if low.endswith(suf):
            stem = low[: -len(suf)]
            cands.extend([stem + "er", stem + "ir"])
            break
    return cands


def is_core(low, lex, allow):
    if low in allow or low in lex:
        return True
    if LANG != "en":
        return any(c in lex or c in allow for c in lemma_candidates(low))
    return False


def readability(asl, asw):
    """Language-appropriate readability. Returns (label, value)."""
    if LANG == "es":
        # Fernandez-Huerta ease, 0-100, higher is easier (60-70 = normal)
        return "Fernandez-Huerta ease", 206.84 - 60 * asw - 1.02 * asl
    if LANG == "pt":
        # Flesch adapted for Portuguese (Martins et al. 1996), 0-100, higher is easier
        return "Flesch ease (pt)", 248.835 - 1.015 * asl - 84.6 * asw
    return "Flesch-Kincaid grade", 0.39 * asl + 11.8 * asw - 15.59


def analyse(text, lex, allow, bands):
    sentences = split_sentences(text)
    total_words = 0
    total_syll = 0
    in_list = 0
    names = {}
    names_ctx = {}
    acronyms = {}
    off = {}
    seen_lower = set()
    long_sentences = []
    for si, sent in enumerate(sentences, 1):
        toks = WORD_RE.findall(sent)
        n_words = len(toks)
        if n_words == 0:
            continue
        if n_words >= 35:
            long_sentences.append((si, n_words, sent))
        first = True
        # Title Case line (heading): every alphabetic token capitalised, so
        # capitalisation carries no name signal. Check all words normally.
        alpha = [t for t in toks if t[0].isalpha()]
        title_case = len(alpha) >= 3 and all(t[0].isupper() for t in alpha)
        for tok in toks:
            pieces = split_contraction(tok)
            for piece in pieces:
                if not piece:
                    continue
                total_words += 1
                total_syll += syllables(piece)
                low = piece.lower()
                if piece[0].islower():
                    seen_lower.add(low)
                if is_core(low, lex, allow):
                    in_list += 1
                elif "-" in low and all(is_core(p, lex, allow) for p in low.split("-") if p):
                    in_list += 1
                elif piece.isupper() and len(piece) >= 2:
                    acronyms[piece] = acronyms.get(piece, 0) + 1
                elif piece[0].isupper() and not first and not title_case and low not in lex:
                    names[piece] = names.get(piece, 0) + 1
                    names_ctx.setdefault(piece, (si, sent))
                else:
                    entry = off.setdefault(low, {"count": 0, "sentences": []})
                    entry["count"] += 1
                    if len(entry["sentences"]) < 2:
                        entry["sentences"].append((si, sent))
            first = False
    # A "name" that also appears in lowercase somewhere in the document is an
    # ordinary word that happened to be capitalised: reclassify it.
    for nm in list(names):
        low = nm.lower()
        if low in seen_lower:
            cnt = names.pop(nm)
            entry = off.setdefault(low, {"count": 0, "sentences": []})
            entry["count"] += cnt
            if len(entry["sentences"]) < 2 and nm in names_ctx:
                entry["sentences"].append(names_ctx[nm])
    n_sent = sum(1 for s in sentences if WORD_RE.search(s))
    asl = total_words / n_sent if n_sent else 0.0
    asw = total_syll / total_words if total_words else 0.0
    fk_label, fk = readability(asl, asw) if total_words else ("Flesch-Kincaid grade", 0.0)
    for w, e in off.items():
        if LANG == "en":
            e["band_k"] = band_of(w, bands)
        else:
            ranks = [RANKED[c] for c in [w] + lemma_candidates(w) if c in RANKED]
            rank = min(ranks) if ranks else None
            e["band_k"] = (rank // 1000 + 1) if rank else None
    return {
        "words": total_words,
        "sentences": n_sent,
        "in_list": in_list,
        "in_list_pct": (100.0 * in_list / total_words) if total_words else 0.0,
        "off_list": off,
        "names": names,
        "acronyms": acronyms,
        "avg_sentence_words": asl,
        "fk_grade": fk,
        "readability_label": fk_label,
        "long_sentences": long_sentences,
    }


def excerpt(sent, word, width=70):
    s = " ".join(sent.split())
    m = re.search(r"\b" + re.escape(word) + r"\b", s, re.I)
    if not m:
        return s[:width]
    start = max(0, m.start() - width // 2)
    end = min(len(s), m.end() + width // 2)
    out = s[start:end]
    if start > 0:
        out = "..." + out
    if end < len(s):
        out += "..."
    return out


def configure(lang):
    """Set the module-level language state. Returns None, or a message when the language cannot be checked."""
    global LANG, LEMMATIZE, RANKED
    lang = re.split(r"[_.\-]", (lang or "en").strip().lower())[0] or "en"
    LANG, LEMMATIZE, RANKED = lang, None, {}
    if lang == "en":
        return None
    lp = os.path.join(WORDLISTS, f"{lang}.txt")
    if not os.path.exists(lp):
        return f"no core vocabulary list for '{lang}' yet (expected {lp})"
    try:
        import simplemma
    except ImportError:
        return f"'{lang}' needs the simplemma package for lemmatisation. Install with: python3 -m pip install --user simplemma"
    LEMMATIZE = lambda w, _l=lang: simplemma.lemmatize(w, lang=_l).lower()
    rp = os.path.join(WORDLISTS, f"{lang}_ranked.txt")
    if os.path.exists(rp):
        RANKED = {w: i for i, w in enumerate(load_words(rp))}
    return None


def check(text, lang="en", list_name="ngsl", top=0, allow=(), allow_files=(), use_global_allow=True):
    """Library entry point (humanize.py uses it). Returns dict(result, label, list, headwords, allow_sources) or dict(error)."""
    err = configure(lang)
    if err:
        return dict(error=err)
    text, directives = prepare(text)
    allowed = set(directives)
    allowed.update(w.strip().lower() for w in allow if w and w.strip())
    allow_sources = []
    if use_global_allow and os.path.exists(GLOBAL_ALLOW):
        gl = load_words(GLOBAL_ALLOW)
        allowed.update(gl)
        allow_sources.append(f"global {len(gl)}")
    for p in allow_files:
        af = load_words(p)
        allowed.update(af)
        allow_sources.append(f"{os.path.basename(p)} {len(af)}")
    if directives:
        allow_sources.append(f"inline {len(directives)}")
    if LANG == "en":  # allowed words get their inflections too
        allow_lex = {}
        for w in list(allowed):
            for f in inflections(w):
                allow_lex.setdefault(f, w)
        allowed = set(allow_lex)
    list_used = list_name if LANG == "en" else LANG
    lex, n_heads = build_lexicon(list_used, top, [])
    r = analyse(text, lex, allowed, load_bands())
    label = f"{list_used.upper()} ({n_heads:,} headwords" + (f", top {top}" if top else "") + ")"
    if allow_sources:
        label += " + allowlist (" + ", ".join(allow_sources) + ")"
    return dict(result=r, label=label, list=list_used, headwords=n_heads, allow_sources=allow_sources)


def off_list_rows(r):
    """Off-list entries sorted by count: dicts with word, count, band, context."""
    rows = []
    for w, e in sorted(r["off_list"].items(), key=lambda kv: (-kv[1]["count"], kv[0])):
        sent = e["sentences"][0][1] if e["sentences"] else ""
        rows.append(dict(word=w, count=e["count"], band=(f"{e['band_k']}k" if e["band_k"] else "rare"), context=excerpt(sent, w)))
    return rows


def summary_lines(r):
    return [f"Words: {r['words']} | in core list: {r['in_list_pct']:.1f}% | off-list unique: {len(r['off_list'])}"
            f" | names skipped: {len(r['names'])} | acronyms skipped: {len(r['acronyms'])}",
            f"Readability: {r['readability_label']} {r['fk_grade']:.1f} | sentences: {r['sentences']}"
            f" | avg {r['avg_sentence_words']:.1f} words/sentence | 35+ word sentences: {len(r['long_sentences'])}"]


def render_text(c, file, max_show=200):
    r = c["result"]
    out = [f"Simple English check: {file}", f"List: {c['label']}"] + summary_lines(r) + [""]
    rows = off_list_rows(r)
    if rows:
        out.append("Off-list words (replace each with a core word, or justify keeping it):")
        wmax = min(24, max(len(x["word"]) for x in rows))
        out.append(f"  {'word'.ljust(wmax)}  count  band   context")
        for x in rows[:max_show]:
            out.append(f"  {x['word'].ljust(wmax)}  {str(x['count']).ljust(5)}  {x['band'].ljust(5)}  \"{x['context']}\"")
        if len(rows) > max_show:
            out.append(f"  ... and {len(rows) - max_show} more (use --max-show)")
    else:
        out.append("Off-list words: none")
    if r["names"]:
        out += ["", "Capitalised mid-sentence (treated as names, not checked): " + ", ".join(sorted(r["names"]))]
    if r["acronyms"]:
        out.append("Acronyms (not checked): " + ", ".join(sorted(r["acronyms"])))
    if r["long_sentences"]:
        out += ["", "Long sentences (35+ words, rule I):"]
        for i, n, s in r["long_sentences"]:
            out.append(f"  #{i} ({n} words): \"{' '.join(s.split())[:160]}{'...' if len(s) > 160 else ''}\"")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="text or markdown file ('-' for stdin)")
    ap.add_argument("--lang", default="en", help="language code: en, es, pt (es/pt need simplemma)")
    ap.add_argument("--list", default="ngsl", choices=["ngsl", "ogden850"], help="core list (default ngsl)")
    ap.add_argument("--top", type=int, default=0, help="use only the first N headwords (NGSL is frequency ordered)")
    ap.add_argument("--allow", default="", help="comma-separated extra allowed words")
    ap.add_argument("--allow-file", action="append", default=[], help="extra allowlist file(s)")
    ap.add_argument("--no-global-allow", action="store_true", help="ignore the global allowlist.txt")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any off-list word remains")
    ap.add_argument("--max-show", type=int, default=200, help="max off-list words to print")
    args = ap.parse_args()

    if args.file == "-":
        text = sys.stdin.read()
    elif not os.path.isfile(args.file):
        sys.exit(f"simple_english: file not found: {args.file!r}")
    else:
        text = open(args.file, encoding="utf-8", errors="replace").read()
    c = check(text, lang=args.lang, list_name=args.list, top=args.top, allow=args.allow.split(","),
              allow_files=args.allow_file, use_global_allow=not args.no_global_allow)
    if "error" in c:
        print(f"simple_english: {c['error']}. Skipping vocabulary check.")
        return 0
    r = c["result"]
    if args.json:
        out = dict(r)
        out["off_list"] = {x["word"]: {"count": x["count"], "band": x["band"], "context": x["context"]} for x in off_list_rows(r)}
        out["long_sentences"] = [{"index": i, "words": n, "text": s} for i, n, s in r["long_sentences"]]
        out["list"] = {"name": c["list"], "headwords": c["headwords"], "allow": c["allow_sources"]}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(render_text(c, args.file, args.max_show))
    if args.strict and r["off_list"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
