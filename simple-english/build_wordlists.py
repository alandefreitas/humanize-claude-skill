#!/usr/bin/env python3
"""
Rebuild wordlists/es.txt, es_ranked.txt, pt.txt, pt_ranked.txt.

Source: hermitdave/FrequencyWords (MIT), OpenSubtitles 2018 top-50k token
lists for es and pt_br. Each token is lemmatised with simplemma, counts are
summed per lemma, lemmas are ranked by total count. The top 3,000 lemmas
become the core list (same order of magnitude as the English NGSL's 2,818).

Usage: build_wordlists.py [--top 3000]
Needs: python3 -m pip install --user simplemma ; network access for the download.
"""
import argparse, collections, os, re, urllib.request
import simplemma

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "wordlists")
SRC = {
    "es": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/es/es_50k.txt",
    "pt": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/pt_br/pt_br_50k.txt",
}
ONE_LETTER = {"es": set("aeoyu"), "pt": set("aeoéàáó")}
LETTERS = re.compile(r"^[^\W\d_]+$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=3000)
    args = ap.parse_args()
    for lang, url in SRC.items():
        raw = urllib.request.urlopen(url).read().decode("utf-8")
        agg = collections.Counter()
        for line in raw.splitlines():
            w, _, c = line.strip().partition(" ")
            if not c.isdigit() or not LETTERS.match(w):
                continue
            if len(w) == 1 and w not in ONE_LETTER[lang]:
                continue
            lem = simplemma.lemmatize(w, lang=lang).lower()
            if not LETTERS.match(lem):
                lem = w
            agg[lem] += int(c)
        ranked = [w for w, _ in agg.most_common()]
        with open(os.path.join(OUT, f"{lang}_ranked.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(ranked) + "\n")
        with open(os.path.join(OUT, f"{lang}.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(ranked[: args.top]) + "\n")
        print(f"{lang}: {len(ranked)} lemmas, top {args.top} written (simplemma {simplemma.__version__})")


if __name__ == "__main__":
    main()
