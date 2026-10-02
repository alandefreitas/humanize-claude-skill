# ai-tells

Model-backed scan for AI-writing patterns, the main detection pass of the humanize skill (`humanize.py` one folder up imports `scan()` from here). It cuts a text into paragraphs and sentences and asks the local jev server (laya-serve, `POST /v1/systemone/batch`) every criterion in `criteria.py` about every unit, then reports every (unit, criterion) pair. Deterministic checks run in the same pass.

```zsh
~/.claude/skills/humanize/ai-tells/ai_tells.py FILE                 # Markdown report, auto language
~/.claude/skills/humanize/ai-tells/ai_tells.py FILE --lang pt       # force es/pt (routes to the multilingual checkpoint)
~/.claude/skills/humanize/ai-tells/ai_tells.py FILE --all           # full unit x criterion matrix
~/.claude/skills/humanize/ai-tells/ai_tells.py FILE --advisory      # also show hits of unreliable criteria
~/.claude/skills/humanize/ai-tells/ai_tells.py FILE --json          # machine-readable
~/.claude/skills/humanize/ai-tells/ai_tells.py FILE --no-model      # deterministic checks only
~/.claude/skills/humanize/ai-tells/ai_tells.py FILE --margin 0.1    # fewer flags; --threshold 0.6 sets one global threshold
```

Exit codes: 0 ok, 1 with `--strict` when anything was flagged, 2 server unreachable, 3 usage.

## What it does

1. Segments Markdown: front matter, HTML comments, fenced code and tables are skipped; headings, paragraphs, blockquotes and lists become units. List items are split into sentences like prose. Inline markup is stripped for the model, kept for the deterministic checks. Each unit has an id (`P3.S2` = paragraph 3, sentence 2) and a line number.
2. Deterministic checks (no model): passive voice (B13, en/es/pt; `passive_agent_named` when a "by" agent follows, `passive_voice` otherwise, both for the editor's rule-13 judgment), title-case headings (C17), emoji (C18), em/en dashes (C14), prose semicolons (C14b), curly quotes (C19), mechanical bold and bold-inline-header lists (C15/C16), hard-wrapped prose (F14), hyphenated pairs (E26, en), heading restatement (E29), 35+/50+ word sentences (I; 20/30 with --spoken), Wh-/So- openers (F11, en), three equal-length sentences in a row (F13), literal filler phrases (E23, en/es/pt), literal `serves as`/`stands as` (B8, en). The model was tried on plain passive detection and failed it (0.24 on "The library was deprecated in 2019", 0.87 on the active "The team fixed the bug"), which is why grammar checks are regex here.
3. Model checks: every sentence (3+ words) and every paragraph is sent with the criteria of its scope. Noul questions carry explicit option labels ("yes, the pattern is clearly present" / "no, this is plain writing without it"), which measured better than bare questions. Questions are batched 8 per request, 48 states per request, so a 50-sentence document costs about 6 requests and a few seconds once the model is warm. The first request waits for the idle server to load (about 10 to 15 s).
4. Report: deterministic findings, model flags (reliable criteria at or above their threshold), per-criterion summary, units ranked by number of flags, and with `--all` the full matrix.

## Calibration and reliability

`calibrate.py` measures every criterion on `samples.py` (2 to 3 positive sentences per criterion, 42 plain human sentences including a dozen in technical-documentation register, 6 plain paragraphs; es/pt sets in `samples_langs.py`) and writes `thresholds.json` under `checkpoint/lang`. Negatives for a criterion are the plain sentences plus every other criterion's positives (hard negatives), so a criterion only counts as reliable when it is specific to its own pattern, not when it merely smells like AI. Two broad criteria (ai_vocabulary, filler_adverb) are exempt from hard negatives (`plain_neg_only`), because their pattern legitimately co-occurs with the others.

Threshold rule is precision first, since flags are an inventory the editor must act on: the smallest value that keeps the false-positive rate on all negatives at or below 5% (at least 0.10 above the highest negative when the classes separate), floor 0.30, ceiling 0.90. Reliable = AUC >= 0.75 against all negatives and that threshold still catches at least half of the positives.

Results on 2026-10-02 (laya checkpoints at revision 55cf4c4, labels on):

| Set | Mean AUC | Reliable criteria | Mean FPR at threshold |
|---|---|---|---|
| english/en | 0.84 | 24 of 37 | 0.06 |
| multilingual/es | 0.80 (26 measured) | 14 of 37 | 0.03 |
| multilingual/pt | 0.75 (26 measured) | 12 of 37 | 0.03 |

Unreliable for English and therefore advisory only (`--advisory`), never flags: rule_of_three (B10), passive_hidden_actor (B13), filler_phrase (E23, covered by the deterministic literal check), authority_trope (E27), signposting (E28), throat_clearing (F1), challenges_future (A6), elegant_variation (B11), narrator_distance (F10), redundant_confirmation (F15), headless_statement (F16), and both `ai_overall` scores. Those are printed in section 5 of the humanize report for the editor's reading; Vale still covers the vocabulary lists mechanically. The report header always prints the current unreliable list, so trust the header over this paragraph after a recalibration.

What to expect on real text: a 16-sentence synthetic AI sample gets about 39 flags, almost all right. A 52-sentence excerpt of a human-written technical README gets about 59 flags, roughly one per sentence, mostly chatbot_artifact and negative_parallelism on documentation sentences that address the reader or contain a contrast. Rejecting those by reading is part of the workflow; `--margin 0.1` trims them if a document is long.

Spanish and Portuguese: 26 of the 37 criteria have samples (2 positives each, 18 plain negatives, 3 paragraphs); the other 11 are unreliable by construction until someone adds samples. Add positives to `samples_langs.py` and re-run with `--lang`.

Re-run calibration after changing a question in `criteria.py`, adding samples, or upgrading the checkpoints:

```zsh
~/.claude/skills/humanize/ai-tells/calibrate.py --model english --lang en --write
~/.claude/skills/humanize/ai-tells/calibrate.py --model multilingual --lang es --write
~/.claude/skills/humanize/ai-tells/calibrate.py --model multilingual --lang pt --write
```

## Files

- `ai_tells.py`: the scanner (stdlib only).
- `criteria.py`: the 37 criteria, each with rule letter, scope, type, and question text in en (and es/pt where the examples are language-bound). Edit here to add a criterion; per-criterion `threshold` keys override `thresholds.json`.
- `samples.py`: labeled English calibration set; `samples_langs.py`: Spanish and Portuguese. Add positives for a new criterion and more plain negatives in the registers you write in.
- `calibrate.py`: measures and writes `thresholds.json`.
- `thresholds.json`: generated; keyed by checkpoint, then criterion: threshold, reliable, auc.

## Server

The jev server is a running `laya-serve` (from the [laya](https://github.com/convaiinnovations/laya) project) that answers `POST /v1/systemone/batch`. The default URL is `http://127.0.0.1:8123`; `JEV_URL` or `LAYA_BASE_URL` override it (a stock `laya-serve` listens on port 8000). The first request after the server unloads its idle checkpoint waits for the reload. Requests retry on 503; a truncated answer (very long sentence) splits its question group and retries.
