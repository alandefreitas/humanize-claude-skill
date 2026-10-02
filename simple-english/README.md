# simple-english

Deterministic core-vocabulary checker used by the humanize skill (rule J in `../RULES.md`; `humanize.py` one folder up imports `check()` from here).

```zsh
~/.claude/skills/humanize/simple-english/simple_english.py FILE            # NGSL, default
~/.claude/skills/humanize/simple-english/simple_english.py FILE --top 1000 # stricter: first 1,000 NGSL words
~/.claude/skills/humanize/simple-english/simple_english.py FILE --list ogden850
~/.claude/skills/humanize/simple-english/simple_english.py FILE --allow mdspan,constexpr --json
~/.claude/skills/humanize/simple-english/simple_english.py FILE --lang es       # or pt
```

Every word that is not in the list (after accepting inflections, irregular forms, hyphen parts, contractions, names, acronyms) is printed with its count, its BNC/COCA 1k frequency band (higher = rarer, "rare" = outside 25k) and a context excerpt. The same run prints Flesch-Kincaid grade, average sentence length and every 35+ word sentence.

## Word lists (`wordlists/`)

- `ngsl.txt`: New General Service List 1.2, 2,818 headwords, frequency ordered (Browne, Culligan and Phillips, CC BY-SA 4.0). Covers about 92% of general English text.
- `ogden850.txt`: Ogden's Basic English, 850 words (from Wiktionary, Appendix:Basic_English_word_list).
- `bnc_coca_bands.csv`: Paul Nation's BNC/COCA 25,000 headwords with their 1k band, used only to label how rare an off-list word is.
- `es.txt`, `pt.txt`: top 3,000 lemmas by frequency from hermitdave/FrequencyWords (MIT, OpenSubtitles 2018, es and pt_br), lemmatised with simplemma and aggregated per lemma. `es_ranked.txt` and `pt_ranked.txt` hold the full ranking (about 25k and 30k lemmas) for the band labels. Rebuild with `build_wordlists.py`.

Spanish and Portuguese need the `simplemma` package (`python3 -m pip install --user simplemma`, built with 2.0.0). Words are matched by lemma, with a participle-to-infinitive fallback, since the script's inflection generator is English-only. Readability for es is Fernandez-Huerta ease and for pt the Martins et al. Flesch adaptation, both 0 to 100, higher is easier.

## Allowing words

- `allowlist.txt` (this folder): words you use across many documents. Inflections are generated for them too.
- `--allow a,b` or `--allow-file PATH`: per run.
- `<!-- simple-english-allow: a b -->` inside a Markdown file: per document (only for files that stay Markdown, it leaves a comment in the source).

Exit code is 0 unless `--strict` is given and off-list words remain (then 1).
