# humanize: design notes

Companion to the README. The skill file is deliberately short (run the scanner, act on its report, re-run until clean). This file holds the reasoning: why the pieces look the way they do, where the rules come from, which decisions were measured, and the history. `RULES.md` is the ruleset itself.

## How a run works

1. `humanize.py` reads the file (or stdin into a temp file) and detects the language with a stopword and orthography vote that returns a confidence. Below the bar it asks languagetool's detector (`-adl`), and if that is not en/es/pt either, it stops with exit 4 and asks for `--lang`. The decision and its evidence are the first line of the report.
2. Three things run in parallel: `ai_tells.scan()` (deterministic checks plus the model, unless `--no-model`), `simple_english.check()`, and the linters for the language (vale with the bundled config, then proselint or languagetool).
3. The report has five sections plus a "Done when" condition. Section 1 (deterministic) and section 3 (off-list words) are binding: fix or justify every row. Section 2 (model flags) is an inventory the editor confirms or rejects by reading, starting from the units with the most flags. Section 4 (linters) is a second opinion. Section 5 lists the criteria the model is not reliable on, printed from `criteria.py` in the text's language, plus the delete test and, with `--spoken`, the spoken-delivery rules. When the model did not run, section 5 lists every criterion instead.
4. The skill rewrites, re-runs, and stops when a run meets "Done when": section 1 empty, every remaining flag rejected with a reason, every remaining off-list word kept with a reason.

Design principle behind the split: anything a script can decide is decided by the script and printed as a table the editor must account for row by row. Anything that needs judgment is printed as a question next to the table it belongs to. The skill prompt never restates a rule, because a rule stated in a prompt is the part a model applies least consistently, while a question asked of a classifier about one sentence is answered the same way every time.

## Why a custom skill

The first setup (May 2026) used two upstream skills installed by `git clone`: `blader/humanizer` (Wikipedia's 29 patterns) and `hardikpandya/stop-slop` (opinionated rules plus a 5-axis rubric). Two problems: stop-slop banned every adverb, which is wrong for technical writing (*lazily, atomically, explicitly, recursively* carry meaning), and patching the upstream file would be lost on every pull; and neither called local linters, which catch a different surface than an LLM rewriter. So both rulesets were merged into one file under our control, the adverb rule was refined, and tool calls were added. In September 2026 the vocabulary rule and `simple_english.py` arrived; on 2026-10-02 the model-backed scan replaced the prompt as the main detection pass, and later that day the command became this skill.

## Source provenance

The ruleset grew out of an internal research pass in May 2026 (three research agents, about 120 sources). It covered why commercial "humanizer" tools are unreliable (no tier-1 review, they optimise for detector bypass rather than readability), what peer-reviewed work says about few-shot voice imitation (arXiv 2509.14543, 2509.24930, 2604.24444), the tool landscape, and why structural patterns matter more than vocabulary swaps.

| Rules | Source | Why |
|---|---|---|
| A to E (patterns 1 to 29) | Wikipedia "Signs of AI writing" via `blader/humanizer` | Authoritative, community-maintained, broad |
| F1 to F13 | `hardikpandya/stop-slop`, selective import | Throat-clearing, emphasis crutches, jargon, false agency, rhythm, quotable lines |
| F14 to F16 | Personal | Hard wrap, redundant confirmations, headless statements (recurring in the author's drafts) |
| G (adverbs) | Personal refinement of stop-slop | Its "ban all adverbs" overcorrects for technical writing |
| H (spoken delivery) | MIT "How to Speak" (Patrick Winston), writing-for-radio rules | Talks need different rules than prose |
| I (sentence length) | Personal | Written prose had no length guardrail |
| J (core vocabulary) + `simple_english.py` | Personal, September 2026 | Plain vocabulary applied by a script, not by feel |
| Vale, proselint, languagetool | Personal | Mechanical surface before the rewrite |
| Model-backed scan | Personal, October 2026 | Every rule that can be a yes/no question is asked of a classifier per sentence |

Strunk and White is not cited directly. proselint draws on it (with Garner, Orwell, Pinker, Gopen and Swan), and rule G is in effect a refinement of Strunk's adverb rule for technical writing. Pullum's "50 Years of Stupid Grammar Advice" (2009) is a fair critique of copying it verbatim into a 2026 ruleset.

Deliberately excluded: stop-slop's blanket passive ban (kept as rule 13's judgment instead), its three-item-list ban (folded into rule 10), `mshumer/unslop`'s empirical pattern discovery (separate tooling investment), `yzhao062/agent-style` (duplicates vale), and the 5-axis Directness/Rhythm/Trust/Authenticity/Density rubric with its three-iteration scoring loop (retired in the skill conversion: it was a self-audit prompt rather than a measurement, two runs scored the same text differently, and the re-run loop against the scanner's own "Done when" condition replaced it with something checkable).

## Decisions worth remembering

**Adverbs (rule G).** Flag only adverbs that add no semantic load, with special attention to the passive-plus-filler fingerprint (*it is generally considered*, *the code was completely refactored*). The test is whether removing the adverb changes the technical meaning. The model criterion `filler_adverb` carries the keep-list in its question.

**Passive voice (rule 13).** The model was asked the rule-13 judgment and scored AUC 0.37. Tested on plain passive detection it also failed (0.24 on "The library was deprecated in 2019", 0.87 on the active "The team fixed the bug"). So grammar went to a regex: be-verb plus past participle (regular -ed/-en with a known-participle guard, plus an irregular list; ser forms plus -ado/-ido for es/pt, estar forms excluded as stative). The check reports `passive_agent_named` when a "by" agent follows and `passive_voice` otherwise, and the report treats the latter as candidates for the rule-13 test, since the rule itself says passive is not a tell by itself.

**Semicolons (rules 14 and 14b).** The rewrite used to swap em dashes for semicolons until semicolon density became its own tell (June 2026). Rule 14 now defaults to a full stop and forbids the semicolon swap; 14b removes semicolons already in the input; `humanize-local/SemicolonOveruse.yml` catches them in vale; the deterministic check catches them in the scan.

**Hard-wrapped prose (F14).** LLMs wrap output at 60 to 80 columns and the breaks survive copy-paste into forms, slides and mail clients. The deterministic check flags paragraphs whose lines cluster at one width without sentence-final punctuation.

**Core vocabulary (rule J).** Every other vocabulary rule is a banlist and can only catch words someone listed. Rule J inverts it: only words on a core list pass. The NGSL (2,818 headwords, about 92% of everyday English) with generated inflections; es/pt use the top 3,000 lemmas from OpenSubtitles (hermitdave/FrequencyWords) matched by lemma with `simplemma`, which skews conversational and suits messages better than formal prose. Names and acronyms are skipped by capitalisation. Other standards considered: Plain English (a style guide, not a list), ASD-STE100 (aerospace, too narrow), VOA Learning English (about 1,500 words, but the NGSL is corpus-derived and documented; `--top 1000` gives comparable strictness).

**Model-backed scan.** Every rule in A to G that can be a yes/no question about a sentence or paragraph is a criterion. The jev server answers typed questions (`noul` = calibrated P(yes), `score` = ordered levels, `choice`) in one forward pass per state, no text generation, so nothing is parsed or hallucinated; a 50-sentence document costs about six batched requests. Explicit yes/no option labels on every question measured slightly better than bare questions (mean AUC 0.898 vs 0.889). Calibration uses hard negatives (every other criterion's positives count as negatives), precision-first thresholds (smallest value with at most 5% false positives, floor 0.30, ceiling 0.90), and a measured reliability bar (AUC at least 0.75 and the threshold still catches half the positives). English: 24 of 37 criteria reliable; Spanish 14; Portuguese 12. Unreliable criteria never become flags; they are printed in section 5 as questions for the editor, so nothing silently drops out of the ruleset. Human technical documentation still draws about one flag per sentence (mostly `chatbot_artifact` and `negative_parallelism`), which is why rejecting flags explicitly is part of the workflow. Numbers and procedure in `ai-tells/README.md`.

**Language detection.** The jev model was tried on 2026-10-02 as a language identifier, both as a four-way `choice` question (en/es/pt/other) and as three yes/no questions, on both checkpoints. It answered near chance (the `english` checkpoint called French and a list of file names English; the `multilingual` checkpoint called English "other" and Portuguese "en"). So detection stays deterministic: a vote over language-specific stopwords (shared es/pt words removed) plus orthographic marks (ã õ ç ção não é você for pt; ñ ¿ ¡ y el los las for es), with confidence = the winner's margin over the runner-up, scaled down below 8 hits. Below 0.35 it is unknown, languagetool's detector (`-adl`) is consulted, and if that is not en/es/pt either the run stops with exit 4 and says what it saw. The report always prints the decision with its evidence so the user can override with `--lang`.

**Linters.** Vale's AI-writing packs are high-signal and mechanical. proselint catches pre-LLM prose hygiene (clichés, weasel words) and also flags legitimate technical writing. languagetool replaces proselint for es/pt (offline JVM, `brew install languagetool`); its pt-BR style rules are richer than its Spanish ones, so the Spanish vale pack carries more of the style load. All of it is a second opinion in section 4, never binding.

**Multi-language.** One skill, not three: structural rules (dashes, wrap, length, copula avoidance, passive judgment, hedging) apply unchanged across languages; vocabulary rules apply in spirit through the es/pt criteria questions and vale packs. Portuguese is Brazilian only, Spanish is Latin American neutral; adding pt-PT or peninsular Spanish is a copy-and-tune-vocabulary job. The es/pt vale vocabulary lists were trimmed before publishing to words that are disproportionately AI tells (figurative metaphors like *tapiz*/*tapeçaria*, English calques like *alavancar*, abstract overuse like *panorama tecnológico*, phrase markers like *divisor de águas*), dropping everyday words like *fundamental, crucial, destacar, ressaltar* that native speakers use in conversation.

## Editing guide

The README has the short version. The reasoning behind each entry:

- **A rule changes.** Edit `RULES.md`, then the component it names: the question in `ai-tells/criteria.py` (then re-run `calibrate.py --write`, see `ai-tells/README.md`), or the regex in `deterministic_checks()` in `ai-tells/ai_tells.py`.
- **A new personal banned phrase.** Prefer a criterion question (model) or, for a literal string, a rule in `vale/styles/humanize-local/` (survives `vale sync`). Do not edit the upstream `signs-of-ai-writing` pack; `vale sync` overwrites it.
- **A word keeps showing up off-list.** `--allow word` for one run, an inline `<!-- simple-english-allow: word -->` for one document, `simple-english/allowlist.txt` only when it recurs across many documents.
- **The report's handling text.** The guide strings at the top of `humanize.py`.
- **The skill's behaviour.** `SKILL.md`, which should stay a handful of steps. If you find yourself adding a rule there, it belongs in a component and this file instead.
- **Spanish or Portuguese reliability.** Add positives to `ai-tells/samples_langs.py` for the 11 criteria without samples and re-run calibration with `--model multilingual --lang es|pt`.

Things to avoid: a "ban all X" rule without an exception list (the adverb mistake); examples piled into the rules (one per rule is enough); rules or tool specifications in `SKILL.md`.

## Known limitations

- No voice profile. The skill matches a writing sample when the user gives one, but nothing collects samples. Five to ten annotated samples would be the highest-leverage next step.
- F15 and F16 (redundancy, headless statements) measured AUC 0.58 and 0.63 and stay judgment rules. The delete test in section 5 is the only guard.
- Language detection covers en, es, pt. Anything else stops with exit 4.
- Detector bypass is not a goal. The structural fixes incidentally pass most detectors.
- The scanner does not rewrite and does not score prose quality. The "Done when" condition is a floor, not a ceiling.

## Update log

- **2026-10-02 (evening): command became a skill.** The 41 KB slash command (rules, steps and tool specs in one prompt) and its design document were replaced by this folder; the two tools and the vale configs moved in. New `humanize.py` orchestrator runs the three checks in parallel and prints one report with per-section handling instructions and a "Done when" condition; `ai_tells.py` gained `scan()`, confidence-scored language detection and `--spoken`; `simple_english.py` gained `check()`. Retired: the 5-axis rubric and its iteration loop, the prompt-side language heuristic, and every rule statement in the prompt (they live in `RULES.md` and the components). The jev model was measured as a language identifier and rejected (see Decisions). Trigger: the author asked for a short skill that runs the tools and acts on their output, with the complexity in the code and the provenance in a README.
- **2026-10-02: model-backed scan.** `ai_tells.py` replaced the prompt's own reading as the main detection pass: every criterion in `criteria.py` asked of the jev server about every sentence and paragraph, deterministic checks in the same pass, calibration with hard negatives and precision-first thresholds. Vale and proselint became supplementary. Trigger: the author set up the jev server that day and asked for the humanize pass to query it for every combination of text piece and criterion.
- **2026-09-02: core vocabulary (rule J).** `simple_english.py` and the NGSL list; the off-list table is binding. Trigger: plain vocabulary is, in the author's view, the biggest single factor in text not reading as AI, and "use simple words" as a prose instruction was too easy to ignore.
- **2026-06-05: rule 14b and the vale rule.** Semicolons already in the input were not being removed and no vale rule caught them. Added the removal rule, the `humanize-local` style, and the output ban.
- **2026-06-02: rule 14 forbids the semicolon swap.** The rewrite had been trading em dashes for semicolons.
- **2026-05-18: Spanish and Portuguese.** Language detection, per-language linters (vale packs authored, languagetool installed), es/pt vocabulary lists trimmed to AI-disproportionate words, dialect choices recorded.
- **2026-05-15: first version and first-use fixes.** Merged Wikipedia's 29 patterns with stop-slop, refined the adverb rule, added vale and proselint, added the rubric. Same day after a CppCon abstract test: rule 13 rewritten with explicit keep and rewrite cases, rule I added, per-axis minimums and structural caps added to the rubric, iteration loop made explicit, F14 (hard wrap) added after a wrapped bio.
