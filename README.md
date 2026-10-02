# humanize

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that removes the signs of AI-generated writing from a text, in English, Spanish or Portuguese.

A scanner finds the problems, not the model's own reading. The scanner asks a small local classifier one question per writing pattern for every sentence and paragraph. It runs deterministic checks too: dashes, semicolons, hard wrap, sentence length, title case, passive voice and more. Every word goes against a core vocabulary list. The usual prose linters run as well. Then it prints one report, and every section of the report says what the editor must do with it. The skill is five steps: put the text in a file, run the scanner, act on the report, run it again until the report says the text is done, deliver.

A model does not apply a rule from a prompt ("avoid filler phrases") the same way twice, and a model editing its own output tends to miss what it just wrote. A classifier answers a question about one sentence the same way every time. A regex does not get tired. A word list has no taste. The language model keeps the work only it can do: it rewrites, and it judges the few rules no classifier was reliable on.

## Requirements

- Python 3.10 or newer. The scripts use only the standard library.
- Only for the model pass: a running [laya](https://github.com/convaiinnovations/laya) server (`pip install laya`, then `laya-serve`). Without it, `--no-model` runs everything else, and the report lists the criteria the editor must apply by reading.
- Only for the linters: [vale](https://vale.sh), [proselint](https://github.com/amperser/proselint) (English), [LanguageTool](https://languagetool.org) (Spanish, Portuguese, and a second opinion on the language). The report leaves out a missing tool and says so.
- Only for Spanish and Portuguese vocabulary: `pip install simplemma`.

On macOS, one command installs the three linters: `brew install vale proselint languagetool`.

## Install

```sh
git clone https://github.com/alandefreitas/humanize-claude-skill ~/humanize-claude-skill
ln -s ~/humanize-claude-skill ~/.claude/skills/humanize
vale sync --config ~/humanize-claude-skill/vale/en.ini     # downloads the signs-of-ai-writing pack
```

Claude Code picks the skill up from `~/.claude/skills/` on the next session. Any other agent framework that reads a `SKILL.md` works the same way. The scripts do not depend on Claude Code.

The model pass expects the laya server at `http://127.0.0.1:8123`. Set `JEV_URL` to point elsewhere, for example `JEV_URL=http://127.0.0.1:8000` for a stock `laya-serve`.

## Usage

Inside Claude Code, call the skill with a file:

```
/humanize path/to/draft.md
/humanize --lang pt path/to/draft.md
/humanize --spoken path/to/talk-script.md
```

You can also paste the text after the command. The skill writes pasted text to a temporary file and runs the scanner. It rewrites, runs the scanner again, and returns the final text with the flags it rejected, the words it kept and the clauses it cut, each with a one-line reason.

From the shell, run the scanner alone:

```sh
humanize.py FILE                      # the full report
humanize.py FILE --lang es            # skip language detection
humanize.py FILE --spoken             # talk script: 20-word sentence limit, spoken-delivery rules
humanize.py FILE --no-model           # without the laya server
humanize.py FILE --no-linters         # without vale, proselint, languagetool
humanize.py FILE --margin 0.1         # fewer model flags on a long document
humanize.py FILE --top 1000           # stricter vocabulary (non-native readers)
humanize.py FILE --allow mdspan,constexpr
humanize.py FILE --json               # everything, machine-readable
humanize.py - < FILE                  # stdin
```

Exit codes: 0 report printed, 2 report printed but the model server was down, 3 usage, 4 language unknown (pass `--lang`).

Each of the two underlying tools also runs on its own. The scan is `ai-tells/ai_tells.py`, where `--all` prints the full unit by criterion matrix and `--advisory` adds hits below the reliability bar. The vocabulary check is `simple-english/simple_english.py`, where `--list ogden850` switches to Basic English.

## The report

```
# Humanize report: draft.md

Language en (detected, confidence 1.00: en 38, es 0, pt 0).
Scan: 4 paragraphs, 11 sentences; checkpoint english answered 37 criteria ...

## 1. Deterministic findings (12)      binding: fix, or keep with a one-line reason
## 2. Model flags (29)                 inventory: confirm by reading, or reject with a reason
## 3. Off-list words (15)              binding: replace with a core word, or keep with a reason
## 4. Linter notes (vale 5, proselint 0)   second opinion
## 5. Rules only you can apply         the criteria the model is not reliable on, plus the delete test
## Done when                           section 1 empty, every remaining flag rejected, every remaining word justified
```

Section 2 lists each flag with the model's probability, and it ranks the sentences with the most flags so the editor knows where to start. Section 5 comes from the criteria file, in the language of the text. When the model did not run, section 5 lists every criterion and the report says so.

## Languages

English, Spanish (Latin American neutral) and Brazilian Portuguese. A vote over stopwords and spelling marks detects the language and reports its confidence on the first line of the report. When the vote cannot decide, the scanner asks LanguageTool's detector. If that is not one of the three languages either, the scanner stops and asks for `--lang`.

The structural rules apply unchanged across languages. The vocabulary rules have per-language criteria questions, vale packs and core word lists. The classifier is less reliable outside English (24 of 37 criteria for English, 14 for Spanish, 12 for Portuguese), so more of the work lands in section 5 there.

## What is where

| Path | What it is |
|---|---|
| `SKILL.md` | The skill: five steps, no rules, no tool details. |
| `humanize.py` | The entry point: language detection, the three checks in parallel, one report. |
| `RULES.md` | The rules (A to J), each marked with the component that checks it. |
| `DESIGN.md` | Why the pieces look the way they do, measured decisions, history. |
| `ai-tells/` | The model-backed scan: `ai_tells.py` (sentence splitting, deterministic checks, laya client), `criteria.py` (37 questions), `calibrate.py` with the sample sets, `thresholds.json` (generated), and a README with the calibration numbers. |
| `simple-english/` | The core vocabulary check: `simple_english.py`, `wordlists/`, `allowlist.txt`, `build_wordlists.py`. |
| `vale/` | `en.ini`, `es.ini`, `pt.ini` and `styles/`: the English pack (downloaded, not tracked), the Spanish and Portuguese packs, and `humanize-local` for personal rules. |

## Changing things

- A word keeps showing up off-list. Use `--allow word` for one run, `<!-- simple-english-allow: word -->` inside one document, or `simple-english/allowlist.txt` when it shows up in every document.
- The scanner misses a pattern. If the pattern can be a yes/no question about a sentence or paragraph, add a criterion to `ai-tells/criteria.py` and two or three positive samples to `ai-tells/samples.py`. Then run `ai-tells/calibrate.py --model english --lang en --write`, so the new criterion gets a measured threshold and reliability flag. If the pattern is an exact string, a rule in `vale/styles/humanize-local/` is cheaper. If it needs no model, add a regex to `deterministic_checks()` in `ai-tells/ai_tells.py`.
- A rule changes. Edit `RULES.md` first, then the component it names.
- The handling text in the report. Edit the guide strings at the top of `humanize.py`.
- Another language. Add a stopword list in `detect_lang()`, a core word list from `build_wordlists.py`, a vale pack, translated criteria questions, and a sample set in `ai-tells/samples_langs.py` for calibration.

Do not add a "ban all X" rule without an exception list, and do not put rules in `SKILL.md`. It should stay a few steps.

## Credits

The rules come from Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) (patterns 1 to 29), [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) (the F rules) and personal additions (adverbs, spoken delivery, sentence length, core vocabulary, hard wrap, empty confirmations, headless statements). `DESIGN.md` records what came from each source, what did not, and why.

The project includes or downloads these data and tools:

- [New General Service List](https://www.newgeneralservicelist.com/) 1.2 (Browne, Culligan and Phillips), CC BY-SA 4.0.
- Ogden's Basic English 850, from Wiktionary, CC BY-SA.
- BNC/COCA frequency bands (Paul Nation), used to label how rare an off-list word is.
- Spanish and Portuguese frequency lists from [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords) (OpenSubtitles 2018), MIT.
- The English vale pack [ammil-industries/vale-signs-of-ai-writing](https://github.com/ammil-industries/vale-signs-of-ai-writing), which `vale sync` downloads.
- [laya](https://github.com/convaiinnovations/laya), the classifier server behind the model pass.

## License

Boost Software License 1.0, see `LICENSE`. The included word lists keep their own licenses, listed above.
